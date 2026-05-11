"""expand station, charger and order mainline fields

Revision ID: b2c3d4e5f6a7
Revises: f1a2b3c4d5e6
Create Date: 2026-04-16 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(inspector, table_name: str) -> set[str]:
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    station_columns = _column_names(inspector, "eq_stations")
    station_additions = [
        ("province", sa.Column("province", sa.String(length=50), nullable=True, comment="province")),
        ("city", sa.Column("city", sa.String(length=50), nullable=True, comment="city")),
        ("district", sa.Column("district", sa.String(length=50), nullable=True, comment="district")),
        ("address", sa.Column("address", sa.String(length=255), nullable=True, comment="address")),
        ("contact_name", sa.Column("contact_name", sa.String(length=50), nullable=True, comment="contact name")),
        ("contact_phone", sa.Column("contact_phone", sa.String(length=30), nullable=True, comment="contact phone")),
        ("operation_hours", sa.Column("operation_hours", sa.String(length=100), nullable=True, comment="operation hours")),
        ("parking_fee_desc", sa.Column("parking_fee_desc", sa.String(length=255), nullable=True, comment="parking fee desc")),
        ("station_remark", sa.Column("station_remark", sa.Text(), nullable=True, comment="station remark")),
        ("planned_charger_count", sa.Column("planned_charger_count", sa.Integer(), nullable=True, comment="planned charger count")),
        ("total_power_kw", sa.Column("total_power_kw", sa.Numeric(10, 2), nullable=True, comment="planned total power")),
        ("cover_image", sa.Column("cover_image", sa.String(length=255), nullable=True, comment="cover image")),
        ("site_photos_json", sa.Column("site_photos_json", sa.Text(), nullable=True, comment="site photos json")),
        ("qualification_remark", sa.Column("qualification_remark", sa.Text(), nullable=True, comment="qualification remark")),
        ("audit_remark", sa.Column("audit_remark", sa.String(length=255), nullable=True, comment="audit remark")),
    ]
    for name, column in station_additions:
        if name not in station_columns:
            op.add_column("eq_stations", column)

    charger_columns = _column_names(inspector, "eq_chargers")
    charger_additions = [
        ("name", sa.Column("name", sa.String(length=100), nullable=True, comment="charger name")),
        ("power_kw", sa.Column("power_kw", sa.Numeric(10, 2), nullable=True, comment="charger power")),
    ]
    for name, column in charger_additions:
        if name not in charger_columns:
            op.add_column("eq_chargers", column)

    order_columns = _column_names(inspector, "trade_orders")
    if "source_type" not in order_columns:
        op.add_column(
            "trade_orders",
            sa.Column("source_type", sa.String(length=30), nullable=False, server_default="mini_program", comment="order source"),
        )
        op.alter_column("trade_orders", "source_type", server_default=None)

    op.execute(
        sa.text(
            """
            UPDATE eq_stations
            SET address = COALESCE(address, CONCAT('演示地址-', id, '号'))
            WHERE address IS NULL OR address = ''
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE eq_stations
            SET planned_charger_count = (
                SELECT COUNT(1) FROM eq_chargers c WHERE c.station_id = eq_stations.id
            )
            WHERE planned_charger_count IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE eq_stations
            SET total_power_kw = (
                SELECT COALESCE(SUM(
                    CASE
                        WHEN UPPER(c.type) = 'AC' THEN 7
                        WHEN UPPER(c.type) = 'DC' THEN 120
                        ELSE 60
                    END
                ), 0)
                FROM eq_chargers c
                WHERE c.station_id = eq_stations.id
            )
            WHERE total_power_kw IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE eq_chargers
            SET name = COALESCE(name, CONCAT('充电桩-', RIGHT(sn_code, 4)))
            WHERE name IS NULL OR name = ''
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE eq_chargers
            SET power_kw = CASE
                WHEN power_kw IS NOT NULL THEN power_kw
                WHEN UPPER(type) = 'AC' THEN 7
                WHEN UPPER(type) = 'DC' THEN 120
                ELSE 60
            END
            WHERE power_kw IS NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE trade_orders
            SET source_type = 'mini_program'
            WHERE source_type IS NULL OR source_type = ''
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    order_columns = _column_names(inspector, "trade_orders")
    if "source_type" in order_columns:
        op.drop_column("trade_orders", "source_type")

    charger_columns = _column_names(inspector, "eq_chargers")
    if "power_kw" in charger_columns:
        op.drop_column("eq_chargers", "power_kw")
    if "name" in charger_columns:
        op.drop_column("eq_chargers", "name")

    station_columns = _column_names(inspector, "eq_stations")
    for name in [
        "audit_remark",
        "qualification_remark",
        "site_photos_json",
        "cover_image",
        "total_power_kw",
        "planned_charger_count",
        "station_remark",
        "parking_fee_desc",
        "operation_hours",
        "contact_phone",
        "contact_name",
        "address",
        "district",
        "city",
        "province",
    ]:
        if name in station_columns:
            op.drop_column("eq_stations", name)
