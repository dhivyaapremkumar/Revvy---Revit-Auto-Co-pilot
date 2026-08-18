"""Code-RAG service: ingestion (extract -> chunk -> embed -> store) and
cited similarity search over Tamil Nadu Building Code (TNCDBR) documents.

Text extraction: `.txt` (UTF-8 decode) and `.pdf` (via `pypdf`, a pure-Python
PDF text extractor) are supported. Any other extension raises
`ValidationError` — scanned/image-only PDFs will extract empty text per
page, which is a known `pypdf` limitation (no OCR); such documents should
be pre-converted to text before upload.

Chunking: a naive but section-aware splitter. It first tries to split on
building-code-style headings (e.g. "Section 4.2", "Clause 3.1.2", "4.2.1
Means of Escape") so a chunk never straddles a section boundary. Any
resulting piece still longer than `CODE_RAG_CHUNK_SIZE_CHARS` is further
divided with a character-count sliding window
(`CODE_RAG_CHUNK_OVERLAP_CHARS` overlap) so embeddings stay within a
sensible token budget; those sub-chunks keep the same `section_reference`
so citations remain accurate.

Similarity search: pgvector cosine distance via
`CodeChunk.embedding.cosine_distance(query_vector)` (HNSW-indexed, see
`app.models.code_chunk`). Cosine *similarity* = 1 - cosine *distance*.
`CODE_RAG_SIMILARITY_THRESHOLD` (default 0.75) is the minimum similarity a
chunk must clear to be considered relevant; below that, per CLAUDE.md, we
return "not found in ingested code" instead of guessing.
"""
from __future__ import annotations

import io
import logging
import re
from pathlib import Path

import ftfy
from pypdf import PdfReader
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.exceptions import NotFoundError, ValidationError
from app.models.code_chunk import CodeChunk
from app.models.code_document import CodeDocument, CodeDocumentSourceType
from app.models.code_query_log import CodeQueryLog
from app.models.user import User
from app.schemas.code_rag import CodeRagCitation, CodeRagQueryResponse
from app.services import llm_service

logger = logging.getLogger(__name__)


# A plain "one or more digits, optionally dotted, then any text" pattern
# (the previous version of this regex) also matches PDF table rows and
# dimension lines that start a wrapped line with a number -- e.g. "1.5 m
# 1.5 m 3.0 m up to 6.0 m" or "12.0 m in height)" -- which got misfiled as
# section headings, corrupting citations across the whole document.
# Requiring a capitalized word (a real title) right after the number, and
# bounding how long that title can run, rejects those while still matching
# real headings like "35. Planning Parameters for Non High Rise Buildings"
# and "4.9.3 Table no1- Desirable Lift size".
_SECTION_HEADING_RE = re.compile(
    r"^\s*(Section|Clause|Chapter)\s+[\d.]{1,10}\s+[A-Z][a-z].{3,80}$"
    r"|^\s*(Section|Clause|Chapter)\s+[\d.]{1,10}\s*$"
    r"|^\s*\d{1,3}(\.\d{1,3}){0,3}\.?\s+[A-Z][a-z].{4,100}$",
    re.MULTILINE,
)

SUPPORTED_EXTENSIONS = {".txt", ".pdf"}


def extract_text(filename: str, content: bytes) -> str:
    """Extract raw text from an uploaded document.

    Raises `ValidationError` for unsupported file types.

    PDF caveat: some government/gazette PDFs embed fonts with a broken or
    missing ToUnicode CMap for punctuation glyphs (smart quotes, em-dashes,
    decorative leader dots) -- pypdf (and PyMuPDF, independently confirmed)
    can only recover these as the Unicode replacement character U+FFFD
    ("<27>"), which is unrecoverable data loss at the PDF-encoding level, not
    a bug in this extraction step. `ftfy.fix_text` is still run because it
    repairs genuine mojibake (real characters decoded with the wrong
    encoding) elsewhere in a document, which IS recoverable -- verified
    against the actual TNCDBR-2019 PDF that substantive regulatory content
    (numeric values, section numbers) extracts correctly even where
    decorative punctuation around it does not.
    """
    suffix = Path(filename).suffix.lower()
    if suffix == ".txt":
        return ftfy.fix_text(content.decode("utf-8", errors="replace"))
    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        return ftfy.fix_text("\n\n".join(pages))
    raise ValidationError(
        f"Unsupported file type '{suffix}'. Supported types: {sorted(SUPPORTED_EXTENSIONS)}"
    )


def _split_into_sections(text: str) -> list[tuple[str, str]]:
    """Split `text` into (section_reference, section_body) pairs.

    Falls back to a single ("General", text) section if no heading-like
    lines are found, so unstructured documents still ingest.
    """
    matches = list(_SECTION_HEADING_RE.finditer(text))
    if not matches:
        return [("General", text.strip())] if text.strip() else []

    sections: list[tuple[str, str]] = []
    # Text before the first heading (front-matter/preamble), if any.
    if matches[0].start() > 0:
        preamble = text[: matches[0].start()].strip()
        if preamble:
            sections.append(("Preamble", preamble))

    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if not body:
            continue
        heading_line = match.group(0).strip()
        sections.append((heading_line[:255], body))

    return sections


def _sliding_window(text: str, size: int, overlap: int) -> list[str]:
    """Split `text` into overlapping fixed-size windows as a last resort."""
    if len(text) <= size:
        return [text]
    windows: list[str] = []
    step = max(size - overlap, 1)
    for start in range(0, len(text), step):
        window = text[start : start + size]
        if window.strip():
            windows.append(window)
        if start + size >= len(text):
            break
    return windows


def chunk_text(text: str) -> list[tuple[str, str]]:
    """Chunk a document's full text into (section_reference, content) pairs."""
    settings = get_settings()
    chunks: list[tuple[str, str]] = []
    for section_reference, body in _split_into_sections(text):
        if len(body) <= settings.CODE_RAG_CHUNK_SIZE_CHARS:
            chunks.append((section_reference, body))
            continue
        for window in _sliding_window(
            body, settings.CODE_RAG_CHUNK_SIZE_CHARS, settings.CODE_RAG_CHUNK_OVERLAP_CHARS
        ):
            chunks.append((section_reference, window))
    return chunks


async def ingest_document(
    db: Session,
    *,
    uploader: User,
    title: str,
    source_type: CodeDocumentSourceType,
    jurisdiction: str,
    version: str,
    filename: str,
    content: bytes,
) -> CodeDocument:
    """Extract, chunk, embed, and store an uploaded code document.

    Embeddings are fetched *before* anything is flushed to the DB or
    written to disk, so a failed OpenAI call (e.g. bad API key, rate
    limit) never leaves an orphaned file or a half-written document row
    behind — either the whole ingestion succeeds, or nothing is persisted.
    """
    text = extract_text(filename, content)
    if not text.strip():
        raise ValidationError("No extractable text found in the uploaded document")

    pieces = chunk_text(text)
    if not pieces:
        raise ValidationError("Document produced no usable chunks after splitting")

    embeddings = await llm_service.create_embeddings_batch([body for _, body in pieces])

    settings = get_settings()
    upload_dir = Path(settings.CODE_DOCUMENT_UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    document = CodeDocument(
        title=title,
        source_type=source_type,
        jurisdiction=jurisdiction,
        version=version,
        uploaded_by=uploader.id,
        file_path="",  # set once we know the generated id-prefixed filename
    )
    db.add(document)
    db.flush()  # assigns document.id without committing

    safe_filename = f"{document.id}_{Path(filename).name}"
    file_path = upload_dir / safe_filename
    file_path.write_bytes(content)
    document.file_path = str(file_path)

    for (section_reference, body), embedding in zip(pieces, embeddings, strict=True):
        db.add(
            CodeChunk(
                document_id=document.id,
                section_reference=section_reference,
                content=body,
                embedding=embedding,
            )
        )

    db.commit()
    db.refresh(document)
    logger.info(
        "Ingested code document id=%s title=%r chunks=%d", document.id, title, len(pieces)
    )
    return document


def list_documents(db: Session) -> list[CodeDocument]:
    """Return all ingested `CodeDocument` rows, most recent first."""
    return db.query(CodeDocument).order_by(CodeDocument.created_at.desc()).all()


def delete_document(db: Session, document_id: int) -> None:
    """Delete a `CodeDocument`, cascading to its `CodeChunk`s, and remove its file."""
    document = db.query(CodeDocument).filter(CodeDocument.id == document_id).first()
    if document is None:
        raise NotFoundError("Code document")

    file_path = Path(document.file_path) if document.file_path else None
    db.delete(document)  # cascade="all, delete-orphan" removes chunks
    db.commit()

    if file_path is not None and file_path.exists():
        try:
            file_path.unlink()
        except OSError:
            logger.warning("Failed to remove code document file at %s", file_path, exc_info=True)


def similarity_search(
    db: Session, query_embedding: list[float], *, top_k: int, threshold: float
) -> list[tuple[CodeChunk, float]]:
    """Return up to `top_k` `CodeChunk`s whose cosine similarity clears `threshold`.

    Ordered by similarity descending (i.e. cosine distance ascending).
    """
    distance_expr = CodeChunk.embedding.cosine_distance(query_embedding)
    rows = (
        db.query(CodeChunk, distance_expr.label("distance"))
        .options(joinedload(CodeChunk.document))
        .order_by(distance_expr.asc())
        .limit(top_k)
        .all()
    )
    results: list[tuple[CodeChunk, float]] = []
    for chunk, distance in rows:
        similarity = 1.0 - float(distance)
        if similarity >= threshold:
            results.append((chunk, similarity))
    return results


_GROUNDED_ANSWER_SYSTEM_PROMPT = (
    "You are REVVY's Tamil Nadu Building Code (TNCDBR) compliance assistant. "
    "Every rule, threshold, ratio, or standard you use (FSI/FAR, setbacks, "
    "parking ratios, height limits, etc.) must come from the numbered "
    "excerpts below — never invent or estimate a value the excerpts don't "
    "state. Cite the excerpt's section reference inline, e.g. '(Section "
    "4.2)', for every rule you use.\n\n"
    "TNCDBR often has SEVERAL tables/sections covering the same kind of rule "
    "for different categories (e.g. separate FSI tables for Non-High-Rise "
    "vs. High-Rise buildings, or by road width, dwelling count, plot area). "
    "Before quoting any number, first work out — from what the user told "
    "you and what the excerpts say each table applies to — WHICH table or "
    "section actually governs this case, and say so explicitly (e.g. "
    "'this is a small residential plot, so the Non-High-Rise table in "
    "Section 35 applies, not the High-Rise table in Section 39'). Only then "
    "pull the number from that table. Do not default to the first "
    "FSI-shaped (or setback-shaped, etc.) number you see in the excerpts.\n\n"
    "If more than one table could plausibly apply and the excerpts don't "
    "let you tell which one governs from what's already been said (e.g. "
    "you don't know if it's residential or commercial, how many dwelling "
    "units, or the building height), don't guess — ask the user the "
    "specific clarifying question(s) you need answered to pick the right "
    "table, and stop there. Once you have enough to identify the correct "
    "table with confidence, proceed to apply it.\n\n"
    "Once you've identified the right rule: don't stop at restating it. If "
    "the user gave specific numbers (plot dimensions, road width, existing "
    "built-up area, etc.), apply the rule to those numbers and compute the "
    "actual answer, showing your arithmetic — e.g. work out plot area, look "
    "up the applicable FSI, and multiply them out into a permissible "
    "built-up area, rather than just quoting the FSI figure back. The "
    "rule/value must be grounded; the arithmetic applying it to the user's "
    "numbers is yours to do.\n\n"
    "If the excerpts don't contain the specific rule or value needed at "
    "all (not even after clarification), say so explicitly instead of "
    "guessing or using outside knowledge."
)


async def answer_query(
    db: Session,
    *,
    user: User,
    query: str,
    top_k: int | None = None,
    history: list[dict[str, str]] | None = None,
) -> CodeRagQueryResponse:
    """Embed `query`, retrieve grounding chunks, and produce a cited answer.

    `history` (optional): prior turns in this chat session, oldest first,
    as `{"role": "user"|"assistant", "content": ...}` dicts. Needed for a
    clarify-then-answer flow to actually work -- e.g. the user gives plot
    dimensions, REVVY asks whether it's residential or commercial, the user
    replies "residential" alone. Without history, that reply would be
    embedded and searched on its own (losing the plot/road-width context
    that made it relevant) and the answer LLM call wouldn't know what
    question "residential" was even answering. With it, both the retrieval
    query and the answer generation see the whole exchange.

    Logs every query (found or not) to `CodeQueryLog` with the cited chunk
    ids, per CLAUDE.md's Code-RAG module rule.
    """
    settings = get_settings()
    resolved_top_k = top_k or settings.CODE_RAG_TOP_K
    history = history or []

    # Retrieval uses the recent conversation too (not just this message) so
    # a short clarifying reply still surfaces the chunks the *original*
    # question needed -- similarity search on "residential" alone would
    # find something plausible-but-wrong rather than nothing.
    search_text = query
    if history:
        recent_turns = "\n".join(f"{turn['role']}: {turn['content']}" for turn in history[-6:])
        search_text = f"{recent_turns}\nuser: {query}"

    query_embedding = await llm_service.create_embedding(search_text)
    matches = similarity_search(
        db, query_embedding, top_k=resolved_top_k, threshold=settings.CODE_RAG_SIMILARITY_THRESHOLD
    )

    if not matches:
        answer = (
            "This question could not be answered from the ingested Tamil Nadu "
            "building code documents — no sufficiently relevant section was found. "
            "Try rephrasing, or ask an administrator to ingest the relevant code document."
        )
        db.add(CodeQueryLog(user_id=user.id, query=query, answer=answer, cited_chunks=[]))
        db.commit()
        return CodeRagQueryResponse(answer=answer, citations=[], found=False)

    excerpts = "\n\n".join(
        f"[{idx + 1}] (Section {chunk.section_reference}) {chunk.content}"
        for idx, (chunk, _similarity) in enumerate(matches)
    )
    messages = (
        [{"role": "system", "content": _GROUNDED_ANSWER_SYSTEM_PROMPT}]
        + history
        + [{"role": "user", "content": f"Excerpts:\n{excerpts}\n\nQuestion: {query}"}]
    )
    answer = await llm_service.chat_completion(messages)

    citations = [
        CodeRagCitation(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_title=chunk.document.title,
            section_reference=chunk.section_reference,
            content=chunk.content,
            similarity=round(similarity, 4),
        )
        for chunk, similarity in matches
    ]

    db.add(
        CodeQueryLog(
            user_id=user.id,
            query=query,
            answer=answer,
            cited_chunks=[c.chunk_id for c in citations],
        )
    )
    db.commit()

    return CodeRagQueryResponse(answer=answer, citations=citations, found=True)
