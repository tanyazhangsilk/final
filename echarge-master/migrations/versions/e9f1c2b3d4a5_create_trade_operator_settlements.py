"""create trade_operator_settlements

Revision ID: e9f1c2b3d4a5
Revises: d4e6f8a9b1c2
Create Date: 2026-04-02 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e9f1c2b3d4a5"
down_revision: Union[str, None] = "d4e6f8a9b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "trade_operator_settlements" in inspector.get_table_names():
        return

    op.create_table(
        "trade_operator_settlements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("settle_date", sa.Date(), nullable=False, comment="清分归属日期"),
        sa.Column("operator_id", sa.Integer(), nullable=False, comment="运营商ID"),
        sa.Column("order_count", sa.Integer(), nullable=False, server_default="0", comment="订单数量"),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00", comment="订单总金额"),
        sa.Column("platform_rate", sa.Numeric(precision=5, scale=4), nullable=False, server_default="0.1000", comment="平台抽成比例"),
        sa.Column("platform_fee", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00", comment="平台抽成金额"),
        sa.Column("settle_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00", comment="应结算金额"),
        sa.Column("status", sa.Integer(), nullable=False, server_default="0", comment="打款状态(0-待打款 1-已打款 2-挂起待补资料)"),
        sa.Column("hold_reason", sa.String(length=255), nullable=True, comment="挂起原因"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="最后更新时间"),
        sa.ForeignKeyConstraint(["operator_id"], ["sys_operators.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("settle_date", "operator_id", name="uq_trade_operator_settlements_date_operator"),
    )
    op.create_index(
        "ix_trade_operator_settlements_settle_date",
        "trade_operator_settlements",
        ["settle_date"],
        unique=False,
    )
    op.create_index(
        "ix_trade_operator_settlements_operator_id",
        "trade_operator_settlements",
        ["operator_id"],
        unique=False,
    )
    op.create_index(
        "ix_trade_operator_settlements_status",
        "trade_operator_settlements",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "trade_operator_settlements" not in inspector.get_table_names():
        return

    op.drop_index("ix_trade_operator_settlements_status", table_name="trade_operator_settlements")
    op.drop_index("ix_trade_operator_settlements_operator_id", table_name="trade_operator_settlements")
    op.drop_index("ix_trade_operator_settlements_settle_date", table_name="trade_operator_settlements")
    op.drop_table("trade_operator_settlements")
