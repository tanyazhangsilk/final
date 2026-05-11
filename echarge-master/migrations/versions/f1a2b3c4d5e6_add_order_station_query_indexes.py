"""add order and station query indexes

Revision ID: f1a2b3c4d5e6
Revises: e9f1c2b3d4a5
Create Date: 2026-04-15 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e9f1c2b3d4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_index_if_missing(table_name: str, index_name: str, columns: list[str]) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    index_names = {idx["name"] for idx in inspector.get_indexes(table_name)}
    if index_name in index_names:
        return
    op.create_index(index_name, table_name, columns, unique=False)


def _drop_index_if_exists(table_name: str, index_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    index_names = {idx["name"] for idx in inspector.get_indexes(table_name)}
    if index_name not in index_names:
        return
    op.drop_index(index_name, table_name=table_name)


def upgrade() -> None:
    _create_index_if_missing("trade_orders", "ix_trade_orders_operator_id", ["operator_id"])
    _create_index_if_missing("trade_orders", "ix_trade_orders_start_time", ["start_time"])
    _create_index_if_missing("trade_orders", "ix_trade_orders_end_time", ["end_time"])
    _create_index_if_missing(
        "trade_orders",
        "ix_trade_orders_operator_status_start_time",
        ["operator_id", "status", "start_time"],
    )

    _create_index_if_missing("eq_stations", "ix_eq_stations_operator_id", ["operator_id"])
    _create_index_if_missing("eq_stations", "ix_eq_stations_status", ["status"])
    _create_index_if_missing("eq_stations", "ix_eq_stations_visibility", ["visibility"])
    _create_index_if_missing(
        "eq_stations",
        "ix_eq_stations_operator_status_visibility",
        ["operator_id", "status", "visibility"],
    )

    _create_index_if_missing("eq_chargers", "ix_eq_chargers_station_id", ["station_id"])
    _create_index_if_missing("eq_chargers", "ix_eq_chargers_station_status", ["station_id", "status"])


def downgrade() -> None:
    _drop_index_if_exists("eq_chargers", "ix_eq_chargers_station_status")
    _drop_index_if_exists("eq_chargers", "ix_eq_chargers_station_id")

    _drop_index_if_exists("eq_stations", "ix_eq_stations_operator_status_visibility")
    _drop_index_if_exists("eq_stations", "ix_eq_stations_visibility")
    _drop_index_if_exists("eq_stations", "ix_eq_stations_status")
    _drop_index_if_exists("eq_stations", "ix_eq_stations_operator_id")

    _drop_index_if_exists("trade_orders", "ix_trade_orders_operator_status_start_time")
    _drop_index_if_exists("trade_orders", "ix_trade_orders_end_time")
    _drop_index_if_exists("trade_orders", "ix_trade_orders_start_time")
    _drop_index_if_exists("trade_orders", "ix_trade_orders_operator_id")
