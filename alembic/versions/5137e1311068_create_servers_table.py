"""create servers table

Revision ID: 5137e1311068
Revises: 
Create Date: 2026-07-17 14:18:35.829044

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5137e1311068"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "servers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hostname", sa.String(), nullable=False),
        sa.Column("ip_address", sa.String(), nullable=False),
        sa.Column("operating_system", sa.String(), nullable=False),
        sa.Column("cpu_cores", sa.Integer(), nullable=False),
        sa.Column("memory_gb", sa.Float(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_servers_id"), "servers", ["id"], unique=False)
    op.create_index(op.f("ix_servers_hostname"), "servers", ["hostname"], unique=True)
    op.create_index(
        op.f("ix_servers_ip_address"), "servers", ["ip_address"], unique=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_servers_ip_address"), table_name="servers")
    op.drop_index(op.f("ix_servers_hostname"), table_name="servers")
    op.drop_index(op.f("ix_servers_id"), table_name="servers")
    op.drop_table("servers")
