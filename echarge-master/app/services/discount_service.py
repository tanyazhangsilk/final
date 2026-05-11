"""
折扣优惠模块：从 extra_routes 共享活动数据，订单结束自动计算折扣。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.api.v1.extra_routes import (
    discount_campaign_store,
    marketing_audit_store,
    seed_runtime_data,
)
from app.models.models import Order


def _ensure_seeded():
    if not discount_campaign_store:
        try:
            from app.db.database import SessionLocal
            db = SessionLocal()
            seed_runtime_data(db)
            db.close()
        except Exception:
            pass


def calculate_discount(order_total: Decimal, campaign: dict) -> Decimal:
    total = float(order_total or 0)
    ctype = campaign.get("campaign_type", "")
    value = float(campaign.get("discount_value", 0))
    threshold = float(campaign.get("threshold", 0))
    status = campaign.get("status", "")
    audit = marketing_audit_store.get(campaign.get("id"))
    audit_status = audit.get("status") if audit else "pending"

    if status != "active" or audit_status != "approved":
        return Decimal("0.00")
    if threshold > 0 and total < threshold:
        return Decimal("0.00")

    if ctype in ("满减", "立减"):
        return min(Decimal(str(value)), Decimal(str(total)))
    elif ctype == "折扣":
        rate = max(Decimal(str(value)), Decimal("0")) / Decimal("100")
        return (Decimal(str(total)) * (Decimal("1") - rate)).quantize(Decimal("0.01")) if rate < Decimal("1") else Decimal("0.00")
    return Decimal("0.00")


def apply_discount_to_order(db: Session, order: Order) -> tuple[Decimal, int | None]:
    _ensure_seeded()
    best_disc = Decimal("0.00")
    best_camp = None
    sid = order.station_id

    for camp in discount_campaign_store:
        if camp.get("status") != "active":
            continue
        audit = marketing_audit_store.get(camp.get("id"))
        if not audit or audit.get("status") != "approved":
            continue
        sids = camp.get("station_ids") or []
        if sids and sid not in sids:
            continue
        disc = calculate_discount(Decimal(str(order.total_fee or 0)), camp)
        if disc > best_disc:
            best_disc = disc
            best_camp = camp["id"]

    if best_disc > Decimal("0.00"):
        order.total_fee = Decimal(str(order.total_fee or 0)) - best_disc
        for c in discount_campaign_store:
            if c["id"] == best_camp:
                c["redeem_count"] = c.get("redeem_count", 0) + 1
                break

    return best_disc, best_camp
