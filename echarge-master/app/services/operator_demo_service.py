from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session, noload

from app.models.models import Charger, Operator, PriceTemplate, Station


STATION_STATUS_TEXT = {
    0: "已上线",
    1: "停用",
    2: "维护中",
    3: "待审核",
    4: "已驳回",
}

VISIBILITY_TEXT = {
    "public": "公开站点",
    "private": "私有站点",
}

CHARGER_STATUS_TEXT = {
    0: "空闲",
    1: "充电中",
    2: "故障",
}

DEFAULT_TEMPLATE_PRESETS = [
    {
        "name": "城市快充标准模板",
        "peak_price": 1.88,
        "flat_price": 1.34,
        "valley_price": 0.76,
        "service_price": 0.80,
        "scope": "全站",
        "status": "active",
    },
    {
        "name": "园区夜充模板",
        "peak_price": 1.56,
        "flat_price": 1.12,
        "valley_price": 0.58,
        "service_price": 0.65,
        "scope": "指定站点",
        "status": "active",
    },
    {
        "name": "公交车队专属模板",
        "peak_price": 1.68,
        "flat_price": 1.18,
        "valley_price": 0.62,
        "service_price": 0.72,
        "scope": "车队站点",
        "status": "draft",
    },
]


def _now_text(value: datetime | None) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else ""


def _normalize_page(page: int | None, page_size: int | None, *, default_size: int = 10, max_size: int = 100) -> tuple[int, int]:
    safe_page = max(int(page or 1), 1)
    safe_page_size = max(int(page_size or default_size), 1)
    return safe_page, min(safe_page_size, max_size)


def _looks_like_mojibake(value: str | None) -> bool:
    if not value:
        return False
    return any(flag in value for flag in ("鍩", "鍥", "绔", "妯", "鍏", "绀"))


def station_status_text(status: int) -> str:
    return STATION_STATUS_TEXT.get(status, "未知状态")


def visibility_text(visibility: str | None) -> str:
    return VISIBILITY_TEXT.get((visibility or "").lower(), "未知可见性")


def charger_status_text(status: int) -> str:
    return CHARGER_STATUS_TEXT.get(status, "未知状态")


def infer_station_address(station: Station) -> str:
    districts = ["南山区", "福田区", "宝安区", "龙华区", "龙岗区"]
    district = districts[station.id % len(districts)]
    return f"深圳市{district}示范路{station.id}号 · {station.name}"


def infer_charger_power_kw(charger: Charger) -> int:
    charger_type = (charger.type or "").upper()
    if "AC" in charger_type:
        return 7
    if "DC" in charger_type:
        return 120 if charger.id % 2 == 0 else 90
    return 60


def infer_charger_name(charger: Charger) -> str:
    station_name = charger.station.name[:8] if charger.station and charger.station.name else "示范电站"
    suffix = charger.sn_code[-4:] if charger.sn_code else f"{charger.id:04d}"
    return f"{station_name}-{suffix}号桩"


def parse_price_template_rules(template: PriceTemplate | None) -> dict[str, Any]:
    defaults = {
        "peak_price": 1.68,
        "flat_price": 1.18,
        "valley_price": 0.68,
        "service_price": 0.72,
        "scope": "全站",
        "status": "active",
    }
    if not template or not template.rules_json:
        return defaults

    try:
        data = json.loads(template.rules_json)
    except Exception:
        return defaults

    return {
        "peak_price": float(data.get("peak_price", defaults["peak_price"])),
        "flat_price": float(data.get("flat_price", defaults["flat_price"])),
        "valley_price": float(data.get("valley_price", defaults["valley_price"])),
        "service_price": float(data.get("service_price", defaults["service_price"])),
        "scope": data.get("scope", defaults["scope"]),
        "status": data.get("status", defaults["status"]),
    }


def ensure_operator_price_templates(db: Session, operator: Operator) -> list[PriceTemplate]:
    templates = (
        db.query(PriceTemplate)
        .options(noload("*"))
        .filter(PriceTemplate.operator_id == operator.id, PriceTemplate.is_deleted.is_(False))
        .order_by(PriceTemplate.updated_at.desc(), PriceTemplate.id.desc())
        .all()
    )
    if templates:
        dirty = False
        for index, item in enumerate(reversed(templates)):
            preset = DEFAULT_TEMPLATE_PRESETS[min(index, len(DEFAULT_TEMPLATE_PRESETS) - 1)]
            if _looks_like_mojibake(item.name):
                item.name = preset["name"]
                dirty = True
            if not item.rules_json or _looks_like_mojibake(item.rules_json):
                item.rules_json = json.dumps(preset, ensure_ascii=False)
                dirty = True
        if dirty:
            db.commit()
            for item in templates:
                db.refresh(item)
        return templates

    created: list[PriceTemplate] = []
    for preset in DEFAULT_TEMPLATE_PRESETS:
        template = PriceTemplate(
            operator_id=operator.id,
            name=preset["name"],
            rules_json=json.dumps(preset, ensure_ascii=False),
        )
        db.add(template)
        created.append(template)

    db.commit()
    for item in created:
        db.refresh(item)
    return created


def ensure_station_chargers(db: Session, station: Station, count: int = 4) -> list[Charger]:
    if station.chargers:
        return station.chargers

    created: list[Charger] = []
    for index in range(count):
        charger = Charger(
            station_id=station.id,
            sn_code=f"ST{station.id:03d}CH{index + 1:02d}",
            type="DC" if index % 2 == 0 else "AC",
            status=0,
        )
        db.add(charger)
        created.append(charger)

    db.commit()
    db.refresh(station)
    return station.chargers


def ensure_operator_demo_assets(db: Session, operator: Operator) -> dict[str, Any]:
    templates = ensure_operator_price_templates(db, operator)
    stations = (
        db.query(Station)
        .options(noload("*"))
        .filter(Station.operator_id == operator.id, Station.is_deleted.is_(False))
        .order_by(Station.created_at.asc())
        .all()
    )

    if not stations:
        seeds = [
            ("科技园旗舰站", 0, "public"),
            ("湾区综合补能站", 3, "private"),
            ("城际枢纽示范站", 4, "private"),
        ]
        stations = []
        for index, (name, status, visibility) in enumerate(seeds, start=1):
            station = Station(
                operator_id=operator.id,
                template_id=templates[0].id if status == 0 else None,
                name=f"{operator.name[:6]}{name}",
                longitude=Decimal(f"113.9{index}1234"),
                latitude=Decimal(f"22.5{index}1234"),
                status=status,
                visibility=visibility,
            )
            db.add(station)
            stations.append(station)
        db.commit()
        for item in stations:
            db.refresh(item)
    else:
        dirty = False
        rename_presets = ["科技园旗舰站", "湾区综合补能站", "城际枢纽示范站"]
        for index, station in enumerate(stations):
            if _looks_like_mojibake(station.name):
                preset_name = rename_presets[min(index, len(rename_presets) - 1)]
                station.name = f"{operator.name[:6]}{preset_name}"
                dirty = True
        if dirty:
            db.commit()
            for item in stations:
                db.refresh(item)

    station_ids = [station.id for station in stations]
    if station_ids:
        charger_count_map = {
            row.station_id: int(row.charger_count or 0)
            for row in (
                db.query(
                    Charger.station_id.label("station_id"),
                    func.count(Charger.id).label("charger_count"),
                )
                .filter(Charger.station_id.in_(station_ids), Charger.is_deleted.is_(False))
                .group_by(Charger.station_id)
                .all()
            )
        }
        created_missing = False
        for station in stations:
            if charger_count_map.get(station.id, 0) > 0:
                continue
            created_missing = True
            for index in range(4):
                db.add(
                    Charger(
                        station_id=station.id,
                        sn_code=f"ST{station.id:03d}CH{index + 1:02d}",
                        type="DC" if index % 2 == 0 else "AC",
                        status=0,
                    )
                )
        if created_missing:
            db.commit()

    return {"stations": stations, "templates": templates}


def ensure_all_operators_demo_assets(db: Session) -> None:
    """应用启动时执行一次：为每个运营商补齐演示模板/电站/电桩，热点接口内不再调用。"""
    operators = db.query(Operator).options(noload("*")).order_by(Operator.id.asc()).all()
    for op in operators:
        ensure_operator_demo_assets(db, op)


def serialize_price_template(template: PriceTemplate) -> dict[str, Any]:
    rules = parse_price_template_rules(template)
    return {
        "id": template.id,
        "name": template.name,
        "peak_price": rules["peak_price"],
        "flat_price": rules["flat_price"],
        "valley_price": rules["valley_price"],
        "service_price": rules["service_price"],
        "scope": rules["scope"],
        "status": rules["status"],
        "updated_at": _now_text(template.updated_at or template.created_at),
    }


def serialize_operator_station(
    station: Station,
    charger_count: int | None = None,
    operator_name: str | None = None,
    price_template_name: str | None = None,
) -> dict[str, Any]:
    resolved_charger_count = charger_count if charger_count is not None else len(station.chargers or [])
    # 未审核通过的电站不允许以公开状态展示
    resolved_visibility = station.visibility
    if station.status != 0 and resolved_visibility == "public":
        resolved_visibility = "private"
    return {
        "id": station.id,
        "station_name": station.name,
        "operator_name": operator_name if operator_name is not None else (station.operator.name if station.operator else ""),
        "address": infer_station_address(station),
        "status": station.status,
        "status_text": station_status_text(station.status),
        "visibility": resolved_visibility,
        "visibility_text": visibility_text(resolved_visibility),
        "charger_count": int(resolved_charger_count),
        "price_template_id": station.template_id,
        "price_template_name": (
            price_template_name
            if price_template_name is not None
            else (station.price_template.name if station.price_template else "未绑定模板")
        ),
        "created_at": _now_text(station.created_at),
        "updated_at": _now_text(station.updated_at),
    }


def serialize_operator_charger(charger: Charger) -> dict[str, Any]:
    return {
        "id": charger.id,
        "sn_code": charger.sn_code,
        "charger_name": infer_charger_name(charger),
        "type": charger.type,
        "power_kw": infer_charger_power_kw(charger),
        "status": charger.status,
        "status_text": charger_status_text(charger.status),
        "station_id": charger.station_id,
        "station_name": charger.station.name if charger.station else "",
        "updated_at": _now_text(charger.updated_at),
    }


def get_operator_station_page(
    db: Session,
    *,
    operator_id: int,
    page: int = 1,
    page_size: int = 10,
    keyword: str | None = None,
    status: int | None = None,
    visibility: str | None = None,
) -> dict[str, Any]:
    safe_page, safe_page_size = _normalize_page(page, page_size)
    charger_count_subquery = (
        db.query(
            Charger.station_id.label("station_id"),
            func.count(Charger.id).label("charger_count"),
        )
        .group_by(Charger.station_id)
        .subquery()
    )

    query = (
        db.query(
            Station,
            func.coalesce(charger_count_subquery.c.charger_count, 0).label("charger_count"),
            Operator.name.label("operator_name"),
            PriceTemplate.name.label("template_name"),
        )
        .join(Operator, Station.operator_id == Operator.id)
        .outerjoin(PriceTemplate, Station.template_id == PriceTemplate.id)
        .outerjoin(charger_count_subquery, charger_count_subquery.c.station_id == Station.id)
        .filter(Station.operator_id == operator_id, Station.is_deleted.is_(False))
    )

    if keyword and keyword.strip():
        search = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                Station.name.like(search),
                Operator.name.like(search),
                PriceTemplate.name.like(search),
            )
        )

    if status is not None:
        query = query.filter(Station.status == status)

    if visibility and visibility.strip():
        normalized_visibility = visibility.strip().lower()
        query = query.filter(Station.visibility == normalized_visibility)
        if normalized_visibility == "public":
            query = query.filter(Station.status == 0)

    total = query.order_by(None).count()
    rows = (
        query.order_by(Station.updated_at.desc(), Station.id.desc())
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )

    summary_row = (
        db.query(
            func.count(Station.id),
            func.coalesce(func.sum(case((Station.status == 0, 1), else_=0)), 0),
            func.coalesce(func.sum(case((Station.status == 3, 1), else_=0)), 0),
            func.coalesce(func.sum(case((Station.visibility == "private", 1), else_=0)), 0),
        )
        .filter(Station.operator_id == operator_id, Station.is_deleted.is_(False))
        .one()
    )

    items = []
    for base_station, charger_count, operator_name, template_name in rows:
        items.append(
            serialize_operator_station(
                base_station,
                charger_count=int(charger_count or 0),
                operator_name=operator_name or "",
                price_template_name=template_name or "未绑定模板",
            )
        )

    return {
        "items": items,
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
        "summary": {
            "total_count": int(summary_row[0] or 0),
            "online_count": int(summary_row[1] or 0),
            "pending_count": int(summary_row[2] or 0),
            "private_count": int(summary_row[3] or 0),
        },
    }


def _station_address_text(station_id: int, station_name: str) -> str:
    districts = ["南山区", "福田区", "宝安区", "龙华区", "龙岗区"]
    district = districts[station_id % len(districts)]
    return f"深圳市{district}示范路{station_id}号 · {station_name}"


def get_operator_station_page_fast(
    db: Session,
    *,
    operator_id: int,
    page: int = 1,
    page_size: int = 10,
    keyword: str | None = None,
    status: int | None = None,
    visibility: str | None = None,
) -> dict[str, Any]:
    safe_page, safe_page_size = _normalize_page(page, page_size)
    charger_count_subquery = (
        db.query(
            Charger.station_id.label("station_id"),
            func.count(Charger.id).label("charger_count"),
        )
        .group_by(Charger.station_id)
        .subquery()
    )

    query = (
        db.query(
            Station.id.label("station_id"),
            Station.name.label("station_name"),
            Station.status.label("station_status"),
            Station.visibility.label("station_visibility"),
            Station.template_id.label("price_template_id"),
            Station.created_at.label("created_at"),
            Station.updated_at.label("updated_at"),
            func.coalesce(charger_count_subquery.c.charger_count, 0).label("charger_count"),
            Operator.name.label("operator_name"),
            PriceTemplate.name.label("template_name"),
        )
        .join(Operator, Station.operator_id == Operator.id)
        .outerjoin(PriceTemplate, Station.template_id == PriceTemplate.id)
        .outerjoin(charger_count_subquery, charger_count_subquery.c.station_id == Station.id)
        .filter(Station.operator_id == operator_id, Station.is_deleted.is_(False))
    )

    if keyword and keyword.strip():
        search = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                Station.name.like(search),
                Operator.name.like(search),
                PriceTemplate.name.like(search),
            )
        )

    if status is not None:
        query = query.filter(Station.status == status)

    if visibility and visibility.strip():
        normalized_visibility = visibility.strip().lower()
        query = query.filter(Station.visibility == normalized_visibility)
        if normalized_visibility == "public":
            query = query.filter(Station.status == 0)

    total = query.order_by(None).count()
    rows = (
        query.order_by(Station.updated_at.desc(), Station.id.desc())
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )

    summary_row = (
        db.query(
            func.count(Station.id),
            func.coalesce(func.sum(case((Station.status == 0, 1), else_=0)), 0),
            func.coalesce(func.sum(case((Station.status == 3, 1), else_=0)), 0),
            func.coalesce(func.sum(case((Station.visibility == "private", 1), else_=0)), 0),
        )
        .filter(Station.operator_id == operator_id, Station.is_deleted.is_(False))
        .one()
    )

    items = []
    for row in rows:
        resolved_visibility = row.station_visibility
        if row.station_status != 0 and resolved_visibility == "public":
            resolved_visibility = "private"

        items.append(
            {
                "id": row.station_id,
                "station_name": row.station_name,
                "operator_name": row.operator_name or "",
                "address": _station_address_text(row.station_id, row.station_name),
                "status": row.station_status,
                "status_text": station_status_text(row.station_status),
                "visibility": resolved_visibility,
                "visibility_text": visibility_text(resolved_visibility),
                "charger_count": int(row.charger_count or 0),
                "price_template_id": row.price_template_id,
                "price_template_name": row.template_name or "未绑定模板",
                "created_at": _now_text(row.created_at),
                "updated_at": _now_text(row.updated_at),
            }
        )

    return {
        "items": items,
        "total": int(total),
        "page": safe_page,
        "page_size": safe_page_size,
        "summary": {
            "total_count": int(summary_row[0] or 0),
            "online_count": int(summary_row[1] or 0),
            "pending_count": int(summary_row[2] or 0),
            "private_count": int(summary_row[3] or 0),
        },
    }


def get_operator_station_options(
    db: Session,
    *,
    operator_id: int,
    keyword: str | None = None,
) -> list[dict[str, Any]]:
    query = (
        db.query(
            Station.id.label("id"),
            Station.name.label("station_name"),
        )
        .filter(Station.operator_id == operator_id, Station.is_deleted.is_(False))
        .order_by(Station.updated_at.desc(), Station.id.desc())
    )

    if keyword and keyword.strip():
        query = query.filter(Station.name.like(f"%{keyword.strip()}%"))

    return [{"id": row.id, "station_name": row.station_name} for row in query.all()]
