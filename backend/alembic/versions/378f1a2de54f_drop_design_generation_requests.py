"""drop design generation requests

The Design Generation module (Generate pushbutton, backend LLM spec
parser, geometry validation, compliance gate against generated_spec) has
been removed in favor of driving model generation through Claude Desktop
over the RevitMCP connector instead. Drops the table and its now-unused
enum types created in the initial migration.

Revision ID: 378f1a2de54f
Revises: 82feb1c9bc25
Create Date: 2026-08-06 15:39:40.914122

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '378f1a2de54f'
down_revision: Union[str, Sequence[str], None] = '82feb1c9bc25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

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
    op.drop_index(
        op.f("ix_design_generation_requests_user_id"),
        table_name="design_generation_requests",
    )
    op.drop_index(
        op.f("ix_design_generation_requests_id"),
        table_name="design_generation_requests",
    )
    op.drop_table("design_generation_requests")
    design_generation_scope.drop(op.get_bind(), checkfirst=True)
    design_generation_compliance_status.drop(op.get_bind(), checkfirst=True)
    design_generation_status.drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    """Downgrade schema."""
    design_generation_scope.create(op.get_bind(), checkfirst=True)
    design_generation_compliance_status.create(op.get_bind(), checkfirst=True)
    design_generation_status.create(op.get_bind(), checkfirst=True)
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
