"""initial

Creates every REVVY table (User, RefreshToken, ChatSession, ChatMessage,
CodeDocument, CodeChunk, CodeQueryLog, ModelQueryLog,
DesignGenerationRequest) and the `pgvector` Postgres extension required
by `CodeChunk.embedding`.

NOTE: this migration was hand-written (no reachable Postgres instance in
the sandbox that authored it) but was validated by importing every model
in `app/models/` through Alembic's `env.py` without error — only the DB
connection itself failed. Re-run `alembic upgrade head` against a real
Postgres+pgvector instance to confirm it applies cleanly, and consider
re-generating with `alembic revision --autogenerate` to double check for
drift once the DB is reachable.

Revision ID: 6ee5ae0e1446
Revises:
Create Date: 2026-07-28 22:37:05.052279

"""
from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6ee5ae0e1446"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIMENSIONS = 1536  # OpenAI text-embedding-3-small

chat_message_role = sa.Enum("user", "assistant", name="chat_message_role")
code_document_source_type = sa.Enum(
    "tncdbr", "municipal_amendment", name="code_document_source_type"
)
design_generation_scope = sa.Enum(
    "element", "full_layout", name="design_generation_scope"
)
design_generation_compliance_status = sa.Enum(
    "pending", "passed", "failed", "overridden",
    name="design_generation_compliance_status",
)
design_generation_status = sa.Enum(
    "previewed", "confirmed", "rejected", "applied",
    name="design_generation_status",
)


def upgrade() -> None:
    """Upgrade schema."""
    # pgvector must exist before any table declares a `Vector` column.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=512), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_refresh_tokens_id"), "refresh_tokens", ["id"], unique=False)
    op.create_index(
        op.f("ix_refresh_tokens_user_id"), "refresh_tokens", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_refresh_tokens_token"), "refresh_tokens", ["token"], unique=True
    )

    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("revit_project_name", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chat_sessions_id"), "chat_sessions", ["id"], unique=False)
    op.create_index(
        op.f("ix_chat_sessions_user_id"), "chat_sessions", ["user_id"], unique=False
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("role", chat_message_role, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["chat_sessions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_chat_messages_id"), "chat_messages", ["id"], unique=False)
    op.create_index(
        op.f("ix_chat_messages_session_id"), "chat_messages", ["session_id"], unique=False
    )

    op.create_table(
        "code_documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source_type", code_document_source_type, nullable=False),
        sa.Column("jurisdiction", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_code_documents_id"), "code_documents", ["id"], unique=False)
    op.create_index(
        op.f("ix_code_documents_uploaded_by"),
        "code_documents",
        ["uploaded_by"],
        unique=False,
    )

    op.create_table(
        "code_chunks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("section_reference", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["code_documents.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_code_chunks_id"), "code_chunks", ["id"], unique=False)
    op.create_index(
        op.f("ix_code_chunks_document_id"), "code_chunks", ["document_id"], unique=False
    )
    op.create_index(
        op.f("ix_code_chunks_section_reference"),
        "code_chunks",
        ["section_reference"],
        unique=False,
    )
    # HNSW index for cosine-similarity search over embeddings (pgvector >= 0.5.0).
    # Unlike ivfflat, hnsw does not require existing rows / ANALYZE to be useful.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_code_chunks_embedding_hnsw "
        "ON code_chunks USING hnsw (embedding vector_cosine_ops);"
    )

    op.create_table(
        "code_query_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column(
            "cited_chunks",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_code_query_logs_id"), "code_query_logs", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_code_query_logs_user_id"), "code_query_logs", ["user_id"], unique=False
    )

    op.create_table(
        "model_query_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("revit_project_name", sa.String(length=255), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("result_summary", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_model_query_logs_id"), "model_query_logs", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_model_query_logs_user_id"),
        "model_query_logs",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "design_generation_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("revit_project_name", sa.String(length=255), nullable=False),
        sa.Column("command_text", sa.Text(), nullable=False),
        sa.Column("scope", design_generation_scope, nullable=False),
        sa.Column(
            "generated_spec",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "compliance_status",
            design_generation_compliance_status,
            nullable=False,
        ),
        sa.Column(
            "compliance_report",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("status", design_generation_status, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_design_generation_requests_id"),
        "design_generation_requests",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_design_generation_requests_user_id"),
        "design_generation_requests",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_design_generation_requests_user_id"),
        table_name="design_generation_requests",
    )
    op.drop_index(
        op.f("ix_design_generation_requests_id"),
        table_name="design_generation_requests",
    )
    op.drop_table("design_generation_requests")

    op.drop_index(op.f("ix_model_query_logs_user_id"), table_name="model_query_logs")
    op.drop_index(op.f("ix_model_query_logs_id"), table_name="model_query_logs")
    op.drop_table("model_query_logs")

    op.drop_index(op.f("ix_code_query_logs_user_id"), table_name="code_query_logs")
    op.drop_index(op.f("ix_code_query_logs_id"), table_name="code_query_logs")
    op.drop_table("code_query_logs")

    op.execute("DROP INDEX IF EXISTS ix_code_chunks_embedding_hnsw;")
    op.drop_index(op.f("ix_code_chunks_section_reference"), table_name="code_chunks")
    op.drop_index(op.f("ix_code_chunks_document_id"), table_name="code_chunks")
    op.drop_index(op.f("ix_code_chunks_id"), table_name="code_chunks")
    op.drop_table("code_chunks")

    op.drop_index(op.f("ix_code_documents_uploaded_by"), table_name="code_documents")
    op.drop_index(op.f("ix_code_documents_id"), table_name="code_documents")
    op.drop_table("code_documents")

    op.drop_index(op.f("ix_chat_messages_session_id"), table_name="chat_messages")
    op.drop_index(op.f("ix_chat_messages_id"), table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index(op.f("ix_chat_sessions_user_id"), table_name="chat_sessions")
    op.drop_index(op.f("ix_chat_sessions_id"), table_name="chat_sessions")
    op.drop_table("chat_sessions")

    op.drop_index(op.f("ix_refresh_tokens_token"), table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_user_id"), table_name="refresh_tokens")
    op.drop_index(op.f("ix_refresh_tokens_id"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    design_generation_status.drop(bind, checkfirst=True)
    design_generation_compliance_status.drop(bind, checkfirst=True)
    design_generation_scope.drop(bind, checkfirst=True)
    code_document_source_type.drop(bind, checkfirst=True)
    chat_message_role.drop(bind, checkfirst=True)

    # Not dropping the `vector` extension on downgrade: other
    # objects/tables outside this migration may depend on it.
