from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.models import Charger, Order


def _order_query(db: Session):
    return db.query(Order).options(
        joinedload(Order.user),
        joinedload(Order.operator),
        joinedload(Order.station),
        joinedload(Order.charger).joinedload(Charger.station),
    )


def _with_operator_scope(query, operator_id: int | None):
    if operator_id is None:
        return query
    return query.filter(Order.operator_id == operator_id)


def list_all_orders(db: Session, limit: int = 100, operator_id: int | None = None) -> list[Order]:
    query = _with_operator_scope(_order_query(db), operator_id)
    return query.order_by(Order.created_at.desc()).limit(limit).all()


def list_realtime_orders(db: Session, limit: int = 50, operator_id: int | None = None) -> list[Order]:
    query = _with_operator_scope(_order_query(db), operator_id)
    return (
        query
        .filter(Order.status == 0)
        .order_by(Order.start_time.desc())
        .limit(limit)
        .all()
    )


def list_history_orders(db: Session, limit: int = 100, operator_id: int | None = None) -> list[Order]:
    query = _with_operator_scope(_order_query(db), operator_id)
    return (
        query
        .filter(Order.status == 1)
        .order_by(Order.end_time.desc(), Order.created_at.desc())
        .limit(limit)
        .all()
    )


def list_abnormal_orders(db: Session, limit: int = 50, operator_id: int | None = None) -> list[Order]:
    query = _with_operator_scope(_order_query(db), operator_id)
    return (
        query
        .filter(Order.status == 2)
        .order_by(Order.start_time.desc())
        .limit(limit)
        .all()
    )


def get_order_by_id(db: Session, order_id: int, operator_id: int | None = None) -> Order | None:
    query = _with_operator_scope(_order_query(db), operator_id)
    return query.filter(Order.id == order_id).first()


def count_charging_orders(db: Session, operator_id: int | None = None) -> int:
    query = _with_operator_scope(db.query(func.count(Order.id)), operator_id)
    return query.filter(Order.status == 0).scalar() or 0


def count_abnormal_orders(db: Session, operator_id: int | None = None) -> int:
    query = _with_operator_scope(db.query(func.count(Order.id)), operator_id)
    return query.filter(Order.status == 2).scalar() or 0


def count_today_completed_orders(
    db: Session,
    today_start: datetime,
    today_end: datetime,
    operator_id: int | None = None,
) -> int:
    query = _with_operator_scope(db.query(func.count(Order.id)), operator_id)
    return (
        query
        .filter(Order.status == 1, Order.end_time >= today_start, Order.end_time < today_end)
        .scalar()
        or 0
    )


def sum_today_charge_amount(
    db: Session,
    today_start: datetime,
    today_end: datetime,
    operator_id: int | None = None,
) -> Decimal:
    query = _with_operator_scope(db.query(func.coalesce(func.sum(Order.total_kwh), 0)), operator_id)
    value = (
        query
        .filter(Order.status == 1, Order.end_time >= today_start, Order.end_time < today_end)
        .scalar()
    )
    return Decimal(str(value or 0))


def sum_today_total_amount(
    db: Session,
    today_start: datetime,
    today_end: datetime,
    operator_id: int | None = None,
) -> Decimal:
    query = _with_operator_scope(db.query(func.coalesce(func.sum(Order.total_fee), 0)), operator_id)
    value = (
        query
        .filter(Order.status == 1, Order.end_time >= today_start, Order.end_time < today_end)
        .scalar()
    )
    return Decimal(str(value or 0))
