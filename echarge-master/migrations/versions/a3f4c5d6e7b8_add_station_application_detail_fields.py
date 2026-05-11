"""add station application detail fields for operator apply / admin audit

Revision ID: a3f4c5d6e7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-08 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a3f4c5d6e7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(inspector, table_name: str) -> set[str]:
    return {col["name"] for col in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    station_columns = _column_names(inspector, "eq_stations")
    additions = [
        ("parking_slot_count", sa.Column("parking_slot_count", sa.Integer(), nullable=True, comment="parking slot count")),
        (
            "service_radius_km",
            sa.Column("service_radius_km", sa.Numeric(10, 2), nullable=True, comment="service radius km"),
        ),
        ("site_owner", sa.Column("site_owner", sa.String(length=120), nullable=True, comment="site owner")),
        (
            "construction_phase",
            sa.Column("construction_phase", sa.String(length=100), nullable=True, comment="construction phase"),
        ),
        ("grid_capacity_remark", sa.Column("grid_capacity_remark", sa.Text(), nullable=True, comment="grid capacity")),
        (
            "support_vehicle_types_json",
            sa.Column("support_vehicle_types_json", sa.Text(), nullable=True, comment="support vehicle types json"),
        ),
        ("facility_tags_json", sa.Column("facility_tags_json", sa.Text(), nullable=True, comment="facility tags json")),
        ("safety_contact_name", sa.Column("safety_contact_name", sa.String(length=50), nullable=True, comment="safety contact")),
        (
            "safety_contact_phone",
            sa.Column("safety_contact_phone", sa.String(length=30), nullable=True, comment="safety contact phone"),
        ),
    ]
    for name, column in additions:
        if name not in station_columns:
            op.add_column("eq_stations", column)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    station_columns = _column_names(inspector, "eq_stations")
    for name in (
        "safety_contact_phone",
        "safety_contact_name",
        "facility_tags_json",
        "support_vehicle_types_json",
        "grid_capacity_remark",
        "construction_phase",
        "site_owner",
        "service_radius_km",
        "parking_slot_count",
    ):
        if name in station_columns:
            op.drop_column("eq_stations", name)
