"""TNCDBR compliance/Q&A check, used by the `ask_building_code` RevitMCP tool.

Given a natural-language question or design description, searches ingested
Tamil Nadu building code chunks (via `rag_service`) and produces a
`(status, report)` pair. Works for both open-ended code questions ("what's
the minimum setback for X") and compliance checks ("does a 2.1m-wide
bathroom comply with X") — the LLM verdict adapts to which kind of question
it was asked; `status` is only really meaningful for the compliance-check
case, but is always returned for a consistent tool contract.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.config import get_settings
from app.services import llm_service, rag_service

logger = logging.getLogger(__name__)

ComplianceStatus = Literal["passed", "failed", "unverified"]

_COMPLIANCE_SYSTEM_PROMPT = (
    "You are REVVY's Tamil Nadu Building Code (TNCDBR) assistant. You will be given "
    "a question or a proposed Revit design change, and numbered excerpts from the "
    "ingested building code. Answer or judge compliance using ONLY what the excerpts "
    "say — do not use outside knowledge, and do not guess at numeric thresholds "
    "(areas, widths, ratios, setbacks, etc.) that the excerpts don't actually state. "
    "TNCDBR often has several tables for the same kind of rule covering different "
    "categories (e.g. separate FSI tables for Non-High-Rise vs. High-Rise buildings). "
    "Before quoting a number, work out from what's given which table actually "
    "governs this case and say so in \"summary\" — don't default to the first "
    "FSI-shaped (or setback-shaped, etc.) number in the excerpts. If more than one "
    "table could plausibly apply and you can't tell which from what's already been "
    "said (building type, dwelling count, height, etc.), set \"passed\" to null and "
    "put the specific clarifying question you'd need answered in \"summary\", rather "
    "than guessing which table to use. "
    "Once the right rule is identified, don't stop at restating it: if the question "
    "gives specific numbers (plot dimensions, road width, existing built-up area, "
    "etc.), apply the rule to those numbers and compute the actual answer, showing "
    "your arithmetic in \"summary\" — e.g. work out plot area, look up the "
    "applicable FSI, and multiply them out into a permissible built-up area, rather "
    "than just quoting the FSI figure back. The rule/value must be grounded in "
    "the excerpts; the arithmetic applying it to the question's own numbers is "
    "yours to do. "
    "Respond with strict JSON only, no prose, no markdown fences, matching exactly "
    'this shape: {"passed": <true|false|null>, "summary": "<one paragraph>", '
    '"findings": [{"section_reference": "<string>", "issue": "<string>"}]}. Set '
    '"passed" to true only if you can point to a concrete requirement in the '
    "excerpts that the design/answer actually satisfies; false only if you can "
    "point to a concrete requirement it actually violates, quoting or citing the "
    'specific clause in "findings". If the excerpts are too vague, fragmentary, or '
    "don't give you enough to actually check or calculate (e.g. a bare section "
    'heading or checklist label with no numeric threshold), set "passed" to null '
    'and say so in "summary" rather than guessing a verdict — an unverifiable '
    "answer is far better than a confident wrong one. For a plain question (not a "
    'compliance check), set "passed" to null and just answer in "summary".'
)


def _parse_llm_verdict(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict) and "passed" in parsed:
            return parsed
    except json.JSONDecodeError:
        pass

    logger.warning(
        "Compliance LLM response was not valid JSON; treating as unverified: %r", raw
    )
    return {
        "passed": None,
        "summary": "Response could not be parsed; treating as unverified out of caution.",
        "findings": [{"section_reference": "N/A", "issue": raw[:500]}],
    }


async def run_compliance_check(
    db: Session, question: str
) -> tuple[ComplianceStatus, dict[str, Any]]:
    """Answer `question` (open code question or compliance check) against ingested TNCDBR.

    Returns `("unverified", report)` when nothing relevant enough was
    ingested, or when the LLM itself can't ground a concrete pass/fail
    verdict in what was found.
    """
    settings = get_settings()
    checked_at = datetime.now(UTC).isoformat()

    query_embedding = await llm_service.create_embedding(question)
    matches = rag_service.similarity_search(
        db,
        query_embedding,
        top_k=settings.CODE_RAG_COMPLIANCE_TOP_K,
        threshold=settings.CODE_RAG_COMPLIANCE_SIMILARITY_THRESHOLD,
    )

    if not matches:
        report = {
            "checked_at": checked_at,
            "summary": (
                "No ingested TNCDBR sections were relevant enough to answer this. "
                "Treat as unverified, not as approved or answered."
            ),
            "findings": [],
            "citations": [],
        }
        return "unverified", report

    excerpts = "\n\n".join(
        f"[{idx + 1}] (Section {chunk.section_reference}) {chunk.content}"
        for idx, (chunk, _similarity) in enumerate(matches)
    )

    messages = [
        {"role": "system", "content": _COMPLIANCE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"Excerpts:\n{excerpts}\n\nQuestion / proposed design:\n{question}",
        },
    ]

    raw_verdict = await llm_service.chat_completion(messages, temperature=0.0)
    verdict = _parse_llm_verdict(raw_verdict)

    citations = [
        {
            "chunk_id": chunk.id,
            "section_reference": chunk.section_reference,
            "similarity": round(similarity, 4),
        }
        for chunk, similarity in matches
    ]

    report = {
        "checked_at": checked_at,
        "summary": verdict.get("summary", ""),
        "findings": verdict.get("findings", []),
        "citations": citations,
    }

    passed = verdict.get("passed")
    if passed is True:
        status = "passed"
    elif passed is False:
        status = "failed"
    else:
        status = "unverified"

    return status, report
