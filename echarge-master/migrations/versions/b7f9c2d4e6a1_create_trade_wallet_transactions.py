"""create trade_wallet_transactions

Revision ID: b7f9c2d4e6a1
Revises: ae8d07e02c9b
Create Date: 2026-04-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7f9c2d4e6a1"
down_revision: Union[str, None] = "ae8d07e02c9b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "trade_wallet_transactions" in inspector.get_table_names():
        return

    op.create_table(
        "trade_wallet_transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="用户ID"),
        sa.Column("transaction_type", sa.String(length=20), nullable=False, comment="流水类型"),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False, comment="变动金额"),
        sa.Column("balance_after", sa.Numeric(precision=10, scale=2), nullable=False, comment="变动后余额"),
        sa.Column("remark", sa.String(length=255), nullable=True, comment="备注"),
        sa.Column("related_order_id", sa.Integer(), nullable=True, comment="关联订单ID"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.ForeignKeyConstraint(["related_order_id"], ["trade_orders.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["sys_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trade_wallet_transactions_user_id", "trade_wallet_transactions", ["user_id"], unique=False)
    op.create_index("ix_trade_wallet_transactions_created_at", "trade_wallet_transactions", ["created_at"], unique=False)
    op.create_index(
        "ix_trade_wallet_transactions_transaction_type",
        "trade_wallet_transactions",
        ["transaction_type"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "trade_wallet_transactions" not in inspector.get_table_names():
        return

    op.drop_index("ix_trade_wallet_transactions_transaction_type", table_name="trade_wallet_transactions")
    op.drop_index("ix_trade_wallet_transactions_created_at", table_name="trade_wallet_transactions")
    op.drop_index("ix_trade_wallet_transactions_user_id", table_name="trade_wallet_transactions")
    op.drop_table("trade_wallet_transactions")
