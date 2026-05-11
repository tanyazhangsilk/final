"""expand trade_invoices fields

Revision ID: d4e6f8a9b1c2
Revises: c2d4e6f8a9b1
Create Date: 2026-04-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e6f8a9b1c2"
down_revision: Union[str, None] = "c2d4e6f8a9b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("trade_invoices")}
    indexes = {idx["name"] for idx in inspector.get_indexes("trade_invoices")}
    foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("trade_invoices")}

    if "order_id" not in columns:
        op.add_column("trade_invoices", sa.Column("order_id", sa.Integer(), nullable=True, comment="关联订单ID"))
    if "invoice_title" not in columns:
        op.add_column("trade_invoices", sa.Column("invoice_title", sa.String(length=100), nullable=True, comment="发票抬头"))
    if "uploaded_at" not in columns:
        op.add_column("trade_invoices", sa.Column("uploaded_at", sa.DateTime(), nullable=True, comment="上传时间"))
    if "remark" not in columns:
        op.add_column("trade_invoices", sa.Column("remark", sa.String(length=255), nullable=True, comment="备注"))

    if "ix_trade_invoices_order_id" not in indexes:
        op.create_index("ix_trade_invoices_order_id", "trade_invoices", ["order_id"], unique=False)
    if "ix_trade_invoices_status" not in indexes:
        op.create_index("ix_trade_invoices_status", "trade_invoices", ["status"], unique=False)
    if "fk_trade_invoices_order_id_trade_orders" not in foreign_keys:
        op.create_foreign_key(
            "fk_trade_invoices_order_id_trade_orders",
            "trade_invoices",
            "trade_orders",
            ["order_id"],
            ["id"],
        )

    op.execute(
        sa.text(
            """
            UPDATE trade_invoices
            SET uploaded_at = updated_at
            WHERE file_url IS NOT NULL
              AND file_url <> ''
              AND uploaded_at IS NULL
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {idx["name"] for idx in inspector.get_indexes("trade_invoices")}
    foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("trade_invoices")}
    columns = {col["name"] for col in inspector.get_columns("trade_invoices")}

    if "fk_trade_invoices_order_id_trade_orders" in foreign_keys:
        op.drop_constraint("fk_trade_invoices_order_id_trade_orders", "trade_invoices", type_="foreignkey")
    if "ix_trade_invoices_status" in indexes:
        op.drop_index("ix_trade_invoices_status", table_name="trade_invoices")
    if "ix_trade_invoices_order_id" in indexes:
        op.drop_index("ix_trade_invoices_order_id", table_name="trade_invoices")
    if "remark" in columns:
        op.drop_column("trade_invoices", "remark")
    if "uploaded_at" in columns:
        op.drop_column("trade_invoices", "uploaded_at")
    if "invoice_title" in columns:
        op.drop_column("trade_invoices", "invoice_title")
    if "order_id" in columns:
        op.drop_column("trade_invoices", "order_id")
