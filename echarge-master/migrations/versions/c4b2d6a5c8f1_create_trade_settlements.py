"""create trade_settlements

Revision ID: c4b2d6a5c8f1
Revises: 981a6e580a29
Create Date: 2026-03-12 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4b2d6a5c8f1"
down_revision: Union[str, None] = "981a6e580a29"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "trade_settlements" in inspector.get_table_names():
        return

    op.create_table(
        "trade_settlements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("settle_date", sa.Date(), nullable=False, comment="结算日期 (即 T 日)"),
        sa.Column("order_count", sa.Integer(), nullable=False, server_default="0", comment="包含的订单笔数"),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00", comment="订单总额 (元)"),
        sa.Column("platform_fee", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00", comment="平台抽成 (元)"),
        sa.Column("settle_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00", comment="应结算金额 (元)"),
        sa.Column("status", sa.Integer(), nullable=False, server_default="0", comment="打款状态 (0-待打款, 1-已打款)"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
            server_onupdate=sa.text("CURRENT_TIMESTAMP"),
            comment="最后更新时间",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_trade_settlements_settle_date", "trade_settlements", ["settle_date"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "trade_settlements" not in inspector.get_table_names():
        return
    op.drop_index("uq_trade_settlements_settle_date", table_name="trade_settlements")
    op.drop_table("trade_settlements")
