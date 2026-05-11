"""composite index for latest wallet row per user (finish order hot path)

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-05-08 14:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "trade_wallet_transactions" not in insp.get_table_names():
        return
    existing = {idx["name"] for idx in insp.get_indexes("trade_wallet_transactions")}
    if "ix_trade_wallet_transactions_user_id_id" in existing:
        return
    op.create_index(
        "ix_trade_wallet_transactions_user_id_id",
        "trade_wallet_transactions",
        ["user_id", "id"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    if "trade_wallet_transactions" not in insp.get_table_names():
        return
    existing = {idx["name"] for idx in insp.get_indexes("trade_wallet_transactions")}
    if "ix_trade_wallet_transactions_user_id_id" not in existing:
        return
    op.drop_index("ix_trade_wallet_transactions_user_id_id", table_name="trade_wallet_transactions")
