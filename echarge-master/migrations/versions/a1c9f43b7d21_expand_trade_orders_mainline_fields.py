"""expand trade_orders mainline fields

Revision ID: a1c9f43b7d21
Revises: 5677157129a0
Create Date: 2026-04-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1c9f43b7d21"
down_revision: Union[str, None] = "5677157129a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("trade_orders")}
    indexes = {idx["name"] for idx in inspector.get_indexes("trade_orders")}
    foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("trade_orders")}

    if "station_id" not in columns:
        op.add_column(
            "trade_orders",
            sa.Column("station_id", sa.Integer(), nullable=True, comment="电站ID"),
        )
    if "vin" not in columns:
        op.add_column(
            "trade_orders",
            sa.Column("vin", sa.String(length=50), nullable=True, comment="车辆VIN"),
        )
    if "charge_duration" not in columns:
        op.add_column(
            "trade_orders",
            sa.Column("charge_duration", sa.Integer(), nullable=True, comment="充电时长(分钟)"),
        )
    if "pay_status" not in columns:
        op.add_column(
            "trade_orders",
            sa.Column(
                "pay_status",
                sa.Integer(),
                nullable=False,
                server_default="0",
                comment="支付状态",
            ),
        )
    if "abnormal_reason" not in columns:
        op.add_column(
            "trade_orders",
            sa.Column("abnormal_reason", sa.String(length=255), nullable=True, comment="异常原因"),
        )

    op.execute(
        sa.text(
            """
            UPDATE trade_orders o
            JOIN eq_chargers c ON c.id = o.charger_id
            SET o.station_id = c.station_id
            WHERE o.station_id IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE trade_orders o
            JOIN sys_users u ON u.id = o.user_id
            SET o.vin = u.vin_code
            WHERE o.vin IS NULL AND u.vin_code IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE trade_orders
            SET charge_duration = TIMESTAMPDIFF(MINUTE, start_time, end_time)
            WHERE charge_duration IS NULL
              AND start_time IS NOT NULL
              AND end_time IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE trade_orders
            SET pay_status = CASE WHEN status = 1 THEN 1 ELSE 0 END
            WHERE pay_status IS NULL OR pay_status = 0
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE trade_orders
            SET abnormal_reason = '系统标记异常'
            WHERE status = 2 AND (abnormal_reason IS NULL OR abnormal_reason = '')
            """
        )
    )

    if "ix_trade_orders_station_id" not in indexes:
        op.create_index("ix_trade_orders_station_id", "trade_orders", ["station_id"], unique=False)
    if "ix_trade_orders_status" not in indexes:
        op.create_index("ix_trade_orders_status", "trade_orders", ["status"], unique=False)
    if "ix_trade_orders_created_at" not in indexes:
        op.create_index("ix_trade_orders_created_at", "trade_orders", ["created_at"], unique=False)
    if "fk_trade_orders_station_id_eq_stations" not in foreign_keys:
        op.create_foreign_key(
            "fk_trade_orders_station_id_eq_stations",
            "trade_orders",
            "eq_stations",
            ["station_id"],
            ["id"],
        )

    if "pay_status" in {col["name"] for col in inspector.get_columns("trade_orders")}:
        op.alter_column("trade_orders", "pay_status", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {idx["name"] for idx in inspector.get_indexes("trade_orders")}
    foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("trade_orders")}
    columns = {col["name"] for col in inspector.get_columns("trade_orders")}

    if "fk_trade_orders_station_id_eq_stations" in foreign_keys:
        op.drop_constraint("fk_trade_orders_station_id_eq_stations", "trade_orders", type_="foreignkey")
    if "ix_trade_orders_created_at" in indexes:
        op.drop_index("ix_trade_orders_created_at", table_name="trade_orders")
    if "ix_trade_orders_status" in indexes:
        op.drop_index("ix_trade_orders_status", table_name="trade_orders")
    if "ix_trade_orders_station_id" in indexes:
        op.drop_index("ix_trade_orders_station_id", table_name="trade_orders")
    if "abnormal_reason" in columns:
        op.drop_column("trade_orders", "abnormal_reason")
    if "pay_status" in columns:
        op.drop_column("trade_orders", "pay_status")
    if "charge_duration" in columns:
        op.drop_column("trade_orders", "charge_duration")
    if "vin" in columns:
        op.drop_column("trade_orders", "vin")
    if "station_id" in columns:
        op.drop_column("trade_orders", "station_id")
