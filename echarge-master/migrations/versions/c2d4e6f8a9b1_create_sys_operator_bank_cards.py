"""create sys_operator_bank_cards

Revision ID: c2d4e6f8a9b1
Revises: b7f9c2d4e6a1
Create Date: 2026-04-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2d4e6f8a9b1"
down_revision: Union[str, None] = "b7f9c2d4e6a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "sys_operator_bank_cards" in inspector.get_table_names():
        return

    op.create_table(
        "sys_operator_bank_cards",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("operator_id", sa.Integer(), nullable=False, comment="运营商ID"),
        sa.Column("account_name", sa.String(length=100), nullable=False, comment="开户名"),
        sa.Column("bank_name", sa.String(length=100), nullable=False, comment="银行名称"),
        sa.Column("bank_account", sa.String(length=100), nullable=False, comment="银行卡号"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0"), comment="是否默认卡"),
        sa.Column("bind_status", sa.Integer(), nullable=False, server_default="1", comment="绑卡状态"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="最后更新时间"),
        sa.ForeignKeyConstraint(["operator_id"], ["sys_operators.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sys_operator_bank_cards_operator_id", "sys_operator_bank_cards", ["operator_id"], unique=False)
    op.create_index("ix_sys_operator_bank_cards_bind_status", "sys_operator_bank_cards", ["bind_status"], unique=False)
    op.create_index("ix_sys_operator_bank_cards_is_default", "sys_operator_bank_cards", ["is_default"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "sys_operator_bank_cards" not in inspector.get_table_names():
        return

    op.drop_index("ix_sys_operator_bank_cards_is_default", table_name="sys_operator_bank_cards")
    op.drop_index("ix_sys_operator_bank_cards_bind_status", table_name="sys_operator_bank_cards")
    op.drop_index("ix_sys_operator_bank_cards_operator_id", table_name="sys_operator_bank_cards")
    op.drop_table("sys_operator_bank_cards")
