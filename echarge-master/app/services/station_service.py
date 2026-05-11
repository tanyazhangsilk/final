from __future__ import annotations

import datetime
import json
from decimal import Decimal
from typing import Any, NamedTuple

from sqlalchemy import case, func, or_, update as sa_update
from sqlalchemy.orm import Session, joinedload

from app.models.models import Charger, Operator, PriceTemplate, Station


STATION_STATUS_TEXT = {
    0: "已审核通过",
    1: "已停用",
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
    3: "停用",
}


def _normalize_page(page: int | None, page_size: int | None, *, default_size: int = 10, max_size: int = 100) -> tuple[int, int]:
    safe_page = max(int(page or 1), 1)
    safe_page_size = max(int(page_size or default_size), 1)
    return safe_page, min(safe_page_size, max_size)


def station_status_text(status: int) -> str:
    return STATION_STATUS_TEXT.get(status, "未知状态")


def visibility_text(visibility: str | None) -> str:
    return VISIBILITY_TEXT.get((visibility or "").lower(), "未知可见性")


def charger_status_text(status: int) -> str:
    return CHARGER_STATUS_TEXT.get(status, "未知状态")


def normalize_source_site_photos(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except Exception:
            pass
        return [item.strip() for item in stripped.replace("\r", "\n").split("\n") if item.strip()]
    return []


def dump_site_photos(value: Any) -> str:
    return json.dumps(normalize_source_site_photos(value), ensure_ascii=False)


def compose_station_address(station: Station) -> str:
    parts = [station.province, station.city, station.district, station.address]
    joined = "".join([part for part in parts if part])
    if joined:
        return joined
    return f"演示地址 {station.id} 号"


def serialize_operator_station_apply_light(
    *,
    station_id: int,
    station_name: str,
    province: str,
    city: str,
    district: str,
    address: str,
    contact_name: str,
    contact_phone: str,
    operator_id: int,
    status: int,
    visibility: str,
    planned_charger_count: int,
    total_power_kw: Decimal | float | int | None,
    created_at: datetime.datetime | None,
    updated_at: datetime.datetime | None,
) -> dict[str, Any]:
    """建站申请写入后返回列表行所需字段，避免 load Station.operator / price_template / chargers。"""
    resolved_visibility = visibility
    if status != 0 and resolved_visibility == "public":
        resolved_visibility = "private"
    parts = [province or "", city or "", district or "", address or ""]
    full_address = "".join(parts) or f"演示地址 {station_id} 号"
    return {
        "id": station_id,
        "station_name": station_name,
        "operator_id": operator_id,
        "full_address": full_address,
        "contact_name": (contact_name or "").strip(),
        "contact_phone": (contact_phone or "").strip(),
        "charger_count": 0,
        "planned_charger_count": int(planned_charger_count or 0),
        "status": status,
        "status_text": station_status_text(status),
        "visibility": resolved_visibility,
        "visibility_text": visibility_text(resolved_visibility),
        "planned_piles": int(planned_charger_count or 0),
        "total_power_kw": float(total_power_kw or 0),
        "total_power": float(total_power_kw or 0),
        "price_template_id": None,
        "price_template_name": "未绑定模板",
        "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S") if created_at else "",
        "updated_at": updated_at.strftime("%Y-%m-%d %H:%M:%S") if updated_at else "",
        "can_bind_template": status == 0,
        "can_manage_chargers": status == 0,
        "can_publish": status == 0,
    }


def infer_charger_power_kw_by_type(charger_type: str | None) -> Decimal:
    normalized = (charger_type or "").upper()
    if normalized == "AC":
        return Decimal("7")
    if normalized == "DC":
        return Decimal("120")
    return Decimal("60")


def get_charger_power_kw(charger: Charger) -> Decimal:
    if charger.power_kw is not None:
        return Decimal(str(charger.power_kw))
    return infer_charger_power_kw_by_type(charger.type)


def build_charger_name(station_name: str, sn_code: str | None, charger_id: int | None = None) -> str:
    if sn_code:
        suffix = sn_code[-4:]
    else:
        suffix = f"{charger_id or 0:04d}"
    return f"{station_name[:8] or '充电站'}-{suffix}号桩"


def get_charger_name(charger: Charger) -> str:
    if charger.name:
        return charger.name
    station_name = charger.station.name if charger.station else "充电站"
    return build_charger_name(station_name, charger.sn_code, charger.id)


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


def _row_json_string_list(row: Any, attr: str) -> list[str]:
    raw = getattr(row, attr, None)
    return normalize_source_site_photos(raw)


def serialize_station(station: Station, *, charger_count: int | None = None) -> dict[str, Any]:
    resolved_charger_count = charger_count if charger_count is not None else len(station.chargers or [])
    resolved_visibility = station.visibility
    if station.status != 0 and resolved_visibility == "public":
        resolved_visibility = "private"

    return {
        "id": station.id,
        "station_name": station.name,
        "operator_id": station.operator_id,
        "operator_name": station.operator.name if station.operator else "",
        "province": station.province or "",
        "city": station.city or "",
        "district": station.district or "",
        "address": station.address or "",
        "full_address": compose_station_address(station),
        "longitude": float(station.longitude or 0),
        "latitude": float(station.latitude or 0),
        "lng": float(station.longitude or 0),
        "lat": float(station.latitude or 0),
        "contact_name": station.contact_name or "",
        "contact_phone": station.contact_phone or "",
        "operation_hours": station.operation_hours or "",
        "parking_fee_desc": station.parking_fee_desc or "",
        "station_remark": station.station_remark or "",
        "planned_charger_count": int(station.planned_charger_count or 0),
        "planned_piles": int(station.planned_charger_count or 0),
        "total_power_kw": float(station.total_power_kw or 0),
        "total_power": float(station.total_power_kw or 0),
        "cover_image": station.cover_image or "",
        "site_photos": normalize_source_site_photos(station.site_photos_json),
        "qualification_remark": station.qualification_remark or "",
        "parking_slot_count": int(station.parking_slot_count) if station.parking_slot_count is not None else None,
        "service_radius_km": float(station.service_radius_km) if station.service_radius_km is not None else None,
        "site_owner": station.site_owner or "",
        "construction_phase": station.construction_phase or "",
        "grid_capacity_remark": station.grid_capacity_remark or "",
        "support_vehicle_types": normalize_source_site_photos(station.support_vehicle_types_json),
        "facility_tags": normalize_source_site_photos(station.facility_tags_json),
        "safety_contact_name": station.safety_contact_name or "",
        "safety_contact_phone": station.safety_contact_phone or "",
        "audit_remark": station.audit_remark or "",
        "status": station.status,
        "status_text": station_status_text(station.status),
        "visibility": resolved_visibility,
        "visibility_text": visibility_text(resolved_visibility),
        "charger_count": int(resolved_charger_count),
        "price_template_id": station.template_id,
        "price_template_name": station.price_template.name if station.price_template else "未绑定模板",
        "created_at": station.created_at.strftime("%Y-%m-%d %H:%M:%S") if station.created_at else "",
        "updated_at": station.updated_at.strftime("%Y-%m-%d %H:%M:%S") if station.updated_at else "",
        "can_bind_template": station.status == 0,
        "can_manage_chargers": station.status == 0,
        "can_publish": station.status == 0,
    }


def serialize_charger(charger: Charger) -> dict[str, Any]:
    return {
        "id": charger.id,
        "sn_code": charger.sn_code,
        "charger_name": get_charger_name(charger),
        "type": charger.type,
        "power_kw": float(get_charger_power_kw(charger)),
        "status": charger.status,
        "status_text": charger_status_text(charger.status),
        "station_id": charger.station_id,
        "station_name": charger.station.name if charger.station else "",
        "updated_at": charger.updated_at.strftime("%Y-%m-%d %H:%M:%S") if charger.updated_at else "",
    }


def serialize_charger_snapshot(
    *,
    charger_id: int,
    sn_code: str,
    name: str | None,
    type_value: str,
    power_kw: Decimal | float | int | None,
    status: int,
    station_id: int,
    station_name: str,
    updated_at: datetime.datetime | None,
) -> dict[str, Any]:
    """无 ORM 关系加载时的电桩序列化，供热点 PATCH 等接口直接返回。"""
    label = (name or "").strip() or f"{station_name[:10]}-{charger_id % 100:02d}号桩"
    return {
        "id": charger_id,
        "sn_code": sn_code,
        "charger_name": label,
        "type": type_value,
        "power_kw": float(power_kw or 0),
        "status": status,
        "status_text": charger_status_text(status),
        "station_id": station_id,
        "station_name": station_name,
        "updated_at": updated_at.strftime("%Y-%m-%d %H:%M:%S") if updated_at else "",
    }


def serialize_station_row(row: Any) -> dict[str, Any]:
    resolved_visibility = row.visibility
    if row.status != 0 and resolved_visibility == "public":
        resolved_visibility = "private"

    full_address = "".join([part for part in [row.province, row.city, row.district, row.address] if part]) or f"演示地址 {row.id} 号"
    return {
        "id": row.id,
        "station_name": row.station_name,
        "operator_id": row.operator_id,
        "operator_name": row.operator_name or "",
        "province": row.province or "",
        "city": row.city or "",
        "district": row.district or "",
        "address": row.address or "",
        "full_address": full_address,
        "longitude": float(row.longitude or 0),
        "latitude": float(row.latitude or 0),
        "lng": float(row.longitude or 0),
        "lat": float(row.latitude or 0),
        "contact_name": row.contact_name or "",
        "contact_phone": row.contact_phone or "",
        "operation_hours": row.operation_hours or "",
        "parking_fee_desc": row.parking_fee_desc or "",
        "station_remark": row.station_remark or "",
        "planned_charger_count": int(row.planned_charger_count or 0),
        "planned_piles": int(row.planned_charger_count or 0),
        "total_power_kw": float(row.total_power_kw or 0),
        "total_power": float(row.total_power_kw or 0),
        "cover_image": row.cover_image or "",
        "site_photos": normalize_source_site_photos(row.site_photos_json),
        "qualification_remark": row.qualification_remark or "",
        "parking_slot_count": int(row.parking_slot_count) if getattr(row, "parking_slot_count", None) is not None else None,
        "service_radius_km": float(row.service_radius_km) if getattr(row, "service_radius_km", None) is not None else None,
        "site_owner": getattr(row, "site_owner", None) or "",
        "construction_phase": getattr(row, "construction_phase", None) or "",
        "grid_capacity_remark": getattr(row, "grid_capacity_remark", None) or "",
        "support_vehicle_types": _row_json_string_list(row, "support_vehicle_types_json"),
        "facility_tags": _row_json_string_list(row, "facility_tags_json"),
        "safety_contact_name": getattr(row, "safety_contact_name", None) or "",
        "safety_contact_phone": getattr(row, "safety_contact_phone", None) or "",
        "audit_remark": row.audit_remark or "",
        "status": row.status,
        "status_text": station_status_text(row.status),
        "visibility": resolved_visibility,
        "visibility_text": visibility_text(resolved_visibility),
        "charger_count": int(row.charger_count or 0),
        "price_template_id": row.template_id,
        "price_template_name": row.price_template_name or "未绑定模板",
        "created_at": row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else "",
        "updated_at": row.updated_at.strftime("%Y-%m-%d %H:%M:%S") if row.updated_at else "",
        "can_bind_template": row.status == 0,
        "can_manage_chargers": row.status == 0,
        "can_publish": row.status == 0,
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
            Station.id.label("id"),
            Station.operator_id.label("operator_id"),
            Station.template_id.label("template_id"),
            Station.name.label("station_name"),
            Station.province.label("province"),
            Station.city.label("city"),
            Station.district.label("district"),
            Station.address.label("address"),
            Station.longitude.label("longitude"),
            Station.latitude.label("latitude"),
            Station.contact_name.label("contact_name"),
            Station.contact_phone.label("contact_phone"),
            Station.operation_hours.label("operation_hours"),
            Station.parking_fee_desc.label("parking_fee_desc"),
            Station.station_remark.label("station_remark"),
            Station.planned_charger_count.label("planned_charger_count"),
            Station.total_power_kw.label("total_power_kw"),
            Station.cover_image.label("cover_image"),
            Station.site_photos_json.label("site_photos_json"),
            Station.qualification_remark.label("qualification_remark"),
            Station.parking_slot_count.label("parking_slot_count"),
            Station.service_radius_km.label("service_radius_km"),
            Station.site_owner.label("site_owner"),
            Station.construction_phase.label("construction_phase"),
            Station.grid_capacity_remark.label("grid_capacity_remark"),
            Station.support_vehicle_types_json.label("support_vehicle_types_json"),
            Station.facility_tags_json.label("facility_tags_json"),
            Station.safety_contact_name.label("safety_contact_name"),
            Station.safety_contact_phone.label("safety_contact_phone"),
            Station.audit_remark.label("audit_remark"),
            Station.status.label("status"),
            Station.visibility.label("visibility"),
            Station.created_at.label("created_at"),
            Station.updated_at.label("updated_at"),
            func.coalesce(charger_count_subquery.c.charger_count, 0).label("charger_count"),
            Operator.name.label("operator_name"),
            PriceTemplate.name.label("price_template_name"),
        )
        .select_from(Station)
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
                Station.address.like(search),
                Station.province.like(search),
                Station.city.like(search),
                Station.district.like(search),
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

    return {
        "items": [serialize_station_row(row) for row in rows],
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


def get_admin_station_audit_page(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 10,
    keyword: str | None = None,
    status: int | None = None,
) -> dict[str, Any]:
    """平台管理员：电站审核列表（分页 + 汇总），与前端 StationAudit 约定字段一致。"""
    safe_page, safe_page_size = _normalize_page(page, page_size)
    charger_count_subquery = (
        db.query(
            Charger.station_id.label("station_id"),
            func.count(Charger.id).label("charger_count"),
        )
        .filter(Charger.is_deleted.is_(False))
        .group_by(Charger.station_id)
        .subquery()
    )

    query = (
        db.query(
            Station.id.label("id"),
            Station.operator_id.label("operator_id"),
            Station.template_id.label("template_id"),
            Station.name.label("station_name"),
            Station.province.label("province"),
            Station.city.label("city"),
            Station.district.label("district"),
            Station.address.label("address"),
            Station.longitude.label("longitude"),
            Station.latitude.label("latitude"),
            Station.contact_name.label("contact_name"),
            Station.contact_phone.label("contact_phone"),
            Station.operation_hours.label("operation_hours"),
            Station.parking_fee_desc.label("parking_fee_desc"),
            Station.station_remark.label("station_remark"),
            Station.planned_charger_count.label("planned_charger_count"),
            Station.total_power_kw.label("total_power_kw"),
            Station.cover_image.label("cover_image"),
            Station.site_photos_json.label("site_photos_json"),
            Station.qualification_remark.label("qualification_remark"),
            Station.parking_slot_count.label("parking_slot_count"),
            Station.service_radius_km.label("service_radius_km"),
            Station.site_owner.label("site_owner"),
            Station.construction_phase.label("construction_phase"),
            Station.grid_capacity_remark.label("grid_capacity_remark"),
            Station.support_vehicle_types_json.label("support_vehicle_types_json"),
            Station.facility_tags_json.label("facility_tags_json"),
            Station.safety_contact_name.label("safety_contact_name"),
            Station.safety_contact_phone.label("safety_contact_phone"),
            Station.audit_remark.label("audit_remark"),
            Station.status.label("status"),
            Station.visibility.label("visibility"),
            Station.created_at.label("created_at"),
            Station.updated_at.label("updated_at"),
            func.coalesce(charger_count_subquery.c.charger_count, 0).label("charger_count"),
            Operator.name.label("operator_name"),
            PriceTemplate.name.label("price_template_name"),
        )
        .select_from(Station)
        .join(Operator, Station.operator_id == Operator.id)
        .outerjoin(PriceTemplate, Station.template_id == PriceTemplate.id)
        .outerjoin(charger_count_subquery, charger_count_subquery.c.station_id == Station.id)
        .filter(Station.is_deleted.is_(False))
    )

    if keyword and keyword.strip():
        search = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                Station.name.like(search),
                Station.address.like(search),
                Station.province.like(search),
                Station.city.like(search),
                Station.district.like(search),
                Operator.name.like(search),
                Station.contact_name.like(search),
                Station.contact_phone.like(search),
            )
        )

    if status is not None:
        query = query.filter(Station.status == status)

    total = query.order_by(None).count()
    rows = (
        query.order_by(Station.created_at.desc(), Station.id.desc())
        .offset((safe_page - 1) * safe_page_size)
        .limit(safe_page_size)
        .all()
    )

    summary_row = (
        db.query(
            func.count(Station.id),
            func.coalesce(func.sum(case((Station.status == 3, 1), else_=0)), 0),
            func.coalesce(func.sum(case((Station.status == 0, 1), else_=0)), 0),
            func.coalesce(func.sum(case((Station.status == 4, 1), else_=0)), 0),
        )
        .filter(Station.is_deleted.is_(False))
        .one()
    )

    return {
        "items": [serialize_station_row(row) for row in rows],
        "total": int(total),
        "page": safe_page,
        "page_size": safe_page_size,
        "summary": {
            "total_count": int(summary_row[0] or 0),
            "pending_count": int(summary_row[1] or 0),
            "approved_count": int(summary_row[2] or 0),
            "rejected_count": int(summary_row[3] or 0),
        },
    }


class StationManageableRow(NamedTuple):
    """写电桩等接口用：仅标量列，不加载 price_template / operator / chargers。"""

    id: int
    name: str
    status: int
    planned_charger_count: int | None
    total_power_kw: Decimal | None


def get_station_manageable_row(
    db: Session,
    *,
    station_id: int,
    operator_id: int,
) -> StationManageableRow | None:
    row = (
        db.query(
            Station.id,
            Station.name,
            Station.status,
            Station.planned_charger_count,
            Station.total_power_kw,
        )
        .filter(
            Station.id == station_id,
            Station.operator_id == operator_id,
            Station.is_deleted.is_(False),
        )
        .first()
    )
    if not row:
        return None
    return StationManageableRow(
        id=int(row.id),
        name=str(row.name or ""),
        status=int(row.status),
        planned_charger_count=int(row.planned_charger_count) if row.planned_charger_count is not None else None,
        total_power_kw=row.total_power_kw if row.total_power_kw is not None else None,
    )


def validate_station_manageable_status(status: int) -> tuple[bool, str]:
    if status != 0:
        return False, "电站审核通过后才允许配置电桩和绑定模板"
    return True, ""


def get_operator_station_options(db: Session, *, operator_id: int, keyword: str | None = None) -> list[dict[str, Any]]:
    query = (
        db.query(
            Station.id.label("id"),
            Station.name.label("station_name"),
            Station.status.label("status"),
            PriceTemplate.name.label("price_template_name"),
        )
        .select_from(Station)
        .outerjoin(PriceTemplate, Station.template_id == PriceTemplate.id)
        .filter(Station.operator_id == operator_id, Station.is_deleted.is_(False))
        .order_by(Station.updated_at.desc(), Station.id.desc())
    )
    if keyword and keyword.strip():
        search = f"%{keyword.strip()}%"
        query = query.filter(or_(Station.name.like(search), Station.address.like(search)))

    return [
        {
            "id": station.id,
            "station_name": station.station_name,
            "status": station.status,
            "status_text": station_status_text(station.status),
            "price_template_name": station.price_template_name or "未绑定模板",
        }
        for station in query.all()
    ]


def release_charger_sn_if_soft_deleted(db: Session, sn_code: str) -> str | None:
    """
    sn_code 表上有全局唯一索引；软删除行仍会占位。
    若同号仅被软删除记录占用，则改写旧行 sn 以释放编号；若未删除记录占用则返回错误文案。
    """
    row = db.query(Charger).filter(Charger.sn_code == sn_code).first()
    if row is None:
        return None
    if not row.is_deleted:
        return "电桩编号已存在"
    row.sn_code = f"_DEL{row.id}_{sn_code}"[:50]
    db.flush()
    return None


def create_station_charger(
    db: Session,
    *,
    station_id: int,
    station_name: str,
    planned_charger_count: int | None,
    total_power_kw: Decimal | None,
    sn_code: str,
    charger_name: str,
    charger_type: str,
    power_kw: Decimal,
    status: int = 0,
) -> Charger:
    existing = (
        db.query(func.count(Charger.id))
        .filter(Charger.station_id == station_id, Charger.is_deleted.is_(False))
        .scalar()
        or 0
    )
    charger = Charger(
        station_id=station_id,
        sn_code=sn_code,
        name=charger_name,
        type=charger_type,
        power_kw=power_kw,
        status=status,
    )
    db.add(charger)
    new_planned = max(int(planned_charger_count or 0), existing + 1)
    new_total_kw = Decimal(str(total_power_kw or 0)) + Decimal(str(power_kw))
    db.execute(
        sa_update(Station)
        .where(Station.id == station_id, Station.is_deleted.is_(False))
        .values(planned_charger_count=new_planned, total_power_kw=new_total_kw, updated_at=func.now())
    )
    db.commit()
    return charger


def batch_create_station_chargers(
    db: Session,
    *,
    station_id: int,
    station_name: str,
    planned_charger_count: int | None,
    total_power_kw: Decimal | None,
    count: int,
    charger_type: str,
    power_kw: Decimal,
) -> list[Charger]:
    created: list[Charger] = []
    existing_count = (
        db.query(func.count(Charger.id))
        .filter(Charger.station_id == station_id, Charger.is_deleted.is_(False))
        .scalar()
        or 0
    )

    name_prefix = (station_name or "")[:10] or "电站"
    for index in range(count):
        sequence = existing_count + index + 1
        sn_code = f"ST{station_id:03d}{charger_type.upper()}{sequence:03d}"
        charger = Charger(
            station_id=station_id,
            sn_code=sn_code,
            name=f"{name_prefix}-{sequence:02d}号桩",
            type=charger_type,
            power_kw=power_kw,
            status=0,
        )
        db.add(charger)
        created.append(charger)

    new_planned = max(int(planned_charger_count or 0), existing_count + count)
    new_total_kw = Decimal(str(total_power_kw or 0)) + Decimal(str(power_kw)) * Decimal(str(count))
    db.execute(
        sa_update(Station)
        .where(Station.id == station_id, Station.is_deleted.is_(False))
        .values(planned_charger_count=new_planned, total_power_kw=new_total_kw, updated_at=func.now())
    )
    db.commit()
    return created


def update_station_charger(charger: Charger, *, charger_name: str | None = None, status: int | None = None) -> Charger:
    if charger_name is not None:
        charger.name = charger_name
    if status is not None:
        charger.status = status
    return charger
