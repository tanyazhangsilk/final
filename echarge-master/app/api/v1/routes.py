import json
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import random

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session, joinedload, noload
from sqlalchemy import func, or_, update as sa_update
from sqlalchemy.exc import OperationalError, ProgrammingError
from app.db.database import get_db
from app.models.models import (
    Charger,
    Fleet,
    Invoice,
    Operator,
    OperatorBankCard,
    OperatorSettlementRecord,
    Order,
    PriceTemplate,
    SettlementRecord,
    Station,
    User,
)
from app.schemas import InvoiceApplySchema, InvoiceProcessSchema, OrderActionSchema
from app.services.order_service import (
    ORDER_STATUS_LABELS,
    finish_order,
    force_stop_order,
    get_abnormal_order_list,
    get_all_order_list,
    get_history_order_list,
    get_order_detail_data,
    get_order_page,
    get_order_source_text,
    get_order_stats,
    get_platform_overview_realtime_orders,
    get_platform_overview_summary,
    get_realtime_order_list,
    get_station_name,
    mark_order_abnormal,
    order_duration_minutes,
    recalculate_order_amounts,
    serialize_order,
)
from app.services.operator_demo_service import (
    ensure_operator_price_templates,
    serialize_price_template,
)
from app.services.station_service import (
    batch_create_station_chargers,
    charger_status_text,
    create_station_charger,
    dump_site_photos,
    get_admin_station_audit_page,
    get_charger_name,
    get_operator_station_options,
    get_operator_station_page,
    get_station_manageable_row,
    release_charger_sn_if_soft_deleted,
    serialize_charger_snapshot,
    serialize_operator_station_apply_light,
    serialize_station,
    serialize_station_row,
    station_status_text,
    validate_station_manageable_status,
    visibility_text,
)
from app.services.notification_service import send_invoice_email
from app.services.settlement_service import settle_t_plus_1_by_operator
from app.services.wallet_service import get_wallet_summary, get_wallet_transaction_list
from app.services.operator_audit_application_service import (
    create_operator_audit_application,
    list_operator_audit_applications,
    process_operator_audit_application as submit_operator_audit_application,
)


api_router = APIRouter()
@api_router.post("/mgr/login", tags=["auth"])
async def mgr_login(payload: dict, db: Session = Depends(get_db)):
    """管理端登录：支持 admin/operator 角色识别。"""
    account = (payload.get("account") or "").strip()
    password = (payload.get("password") or "").strip()
    if not account or not password:
        return {"code": 400, "message": "请输入账号和密码"}

    from app.api.v1.mini_routes import _resolve_login_account
    resolved = _resolve_login_account(account)
    from app.models.models import User, Operator
    user = db.query(User).filter(User.phone == resolved).first()
    if not user or user.password_hash != password:
        return {"code": 401, "message": "账号或密码不正确"}

    if user.role not in {"admin", "operator"}:
        return {"code": 403, "message": "该账号不是管理员或运营商账号"}

    op_id = None
    if user.role == "operator":
        op = db.query(Operator).filter(Operator.is_deleted.is_(False)).order_by(Operator.id.asc()).first()
        op_id = op.id if op else 1

        # 通过已审核的入驻申请找到该用户绑定的运营商
        from app.models.models import OperatorAuditApplication
        app_row = db.query(OperatorAuditApplication).filter(
            OperatorAuditApplication.phone == user.phone,
            OperatorAuditApplication.status == "approved",
            OperatorAuditApplication.is_deleted.is_(False),
        ).order_by(OperatorAuditApplication.submitted_at.desc()).first()
        if app_row and app_row.linked_operator_id:
            linked = db.query(Operator).filter(Operator.id == app_row.linked_operator_id).first()
            if linked:
                op_id = linked.id

    display_email = account if "@" in account else f"{user.phone}@mgr.echarge"
    return {"code": 200, "data": {
        "id": user.id,
        "nickname": user.nickname or f"用户{str(user.phone)[-4:]}",
        "phone": user.phone,
        "email": display_email,
        "role": user.role,
        "operator_id": op_id,
        "user_id": user.id,
    }}

logger = logging.getLogger(__name__)

DB_CONNECTION_ERROR_MESSAGE = (
    "数据库连接失败，请确认 MySQL 已启动，并检查 .env 中 "
    "MYSQL_HOST、MYSQL_PORT、MYSQL_USER、MYSQL_PASSWORD、MYSQL_DB 配置。"
)
DB_SCHEMA_ERROR_MESSAGE = "数据库表结构未同步，请先执行 python scripts/patch_demo_schema.py 后再重试。"


def friendly_db_error_message(exc: Exception) -> str:
    raw = str(exc)
    lowered = raw.lower()
    if isinstance(exc, (OperationalError, ProgrammingError)) and (
        "unknown column" in lowered
        or "doesn't exist" in lowered
        or "unknown table" in lowered
        or "no such column" in lowered
    ):
        return DB_SCHEMA_ERROR_MESSAGE
    if isinstance(exc, OperationalError) and (
        "can't connect" in lowered
        or "connection refused" in lowered
        or "lost connection" in lowered
        or "access denied" in lowered
    ):
        return DB_CONNECTION_ERROR_MESSAGE
    return f"数据库操作失败：{raw}"

operator_audit_store: dict[int, dict[str, Any]] = {}
marketing_audit_store: dict[int, dict[str, Any]] = {}
blacklist_store: set[int] = set()
system_param_store: dict[str, Any] = {
    "station_auto_publish": False,
    "operator_auto_approve": False,
    "station_public_requires_review": True,
    "invoice_auto_approve_limit": 300.0,
    "settlement_platform_rate": 10,
    "settlement_cycle_days": 1,
    "settlement_minimum_amount": 100.0,
    "abnormal_order_sla_minutes": 30,
    "user_refund_limit_per_day": 2,
    "support_email": "support@echarge.com",
    "support_phone": "400-800-1024",
    "notification_email_enabled": True,
    "notification_sms_enabled": True,
    "invoice_notice_enabled": True,
    "abnormal_order_notify_roles": "平台运营, 财务审核",
}
permission_settings_store: list[dict[str, Any]] = [
    {"module": "运营商管理", "view": True, "edit": True, "approve": True, "export": False},
    {"module": "电站管理", "view": True, "edit": True, "approve": True, "export": True},
    {"module": "订单管理", "view": True, "edit": True, "approve": False, "export": True},
    {"module": "财务管理", "view": True, "edit": True, "approve": True, "export": True},
    {"module": "用户管理", "view": True, "edit": True, "approve": False, "export": True},
    {"module": "营销管理", "view": True, "edit": False, "approve": True, "export": False},
    {"module": "系统设置", "view": True, "edit": True, "approve": False, "export": False},
]
template_store: list[dict[str, Any]] = []
tag_store: list[dict[str, Any]] = []
discount_campaign_store: list[dict[str, Any]] = []
coupon_campaign_store: list[dict[str, Any]] = []


class TemplatePayload(BaseModel):
    name: str
    peak_price: float
    flat_price: float
    valley_price: float
    service_price: float
    scope: str
    status: str = "active"


class FleetPayload(BaseModel):
    name: str
    is_whitelist: bool = False


class TagPayload(BaseModel):
    name: str
    color: str = "#409EFF"
    description: str = ""


class CampaignPayload(BaseModel):
    name: str
    campaign_type: str
    discount_value: float
    threshold: float = 0
    audience: str = "all"
    status: str = "draft"


class CouponDispatchPayload(BaseModel):
    dispatch_count: int = 100


class SettingsProfilePayload(BaseModel):
    name: str
    org_type: str
    contact_email: str
    contact_phone: str
    bank_account: str = ""


class SystemParamsPayload(BaseModel):
    station_auto_publish: bool
    operator_auto_approve: bool
    station_public_requires_review: bool
    invoice_auto_approve_limit: float
    settlement_platform_rate: int
    settlement_cycle_days: int
    settlement_minimum_amount: float
    abnormal_order_sla_minutes: int
    user_refund_limit_per_day: int
    support_email: str
    support_phone: str
    notification_email_enabled: bool
    notification_sms_enabled: bool
    invoice_notice_enabled: bool
    abnormal_order_notify_roles: str


class PermissionSettingsPayload(BaseModel):
    modules: list[dict[str, Any]]


class BankCardSubmitPayload(BaseModel):
    account_name: str
    bank_name: str
    bank_account: str
    is_default: bool = True


class StationVisibilityPayload(BaseModel):
    visibility: str


class BindTemplatePayload(BaseModel):
    template_id: int


class StationApplyPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    station_name: str
    province: str
    city: str
    district: str
    address: str
    longitude: float
    latitude: float
    contact_name: str
    contact_phone: str
    operation_hours: str = ""
    parking_fee_desc: str = ""
    station_remark: str = ""
    planned_charger_count: int = 0
    total_power_kw: float = 0
    cover_image: str = ""
    site_photos: list[str] | str | None = None
    qualification_remark: str = ""
    parking_slot_count: int | None = None
    service_radius_km: float | None = None
    site_owner: str = ""
    construction_phase: str = ""
    grid_capacity_remark: str = ""
    support_vehicle_types: list[str] | None = None
    facility_tags: list[str] | None = None
    safety_contact_name: str = ""
    safety_contact_phone: str = ""


class StationAuditProcessPayload(BaseModel):
    action: str
    remark: str = ""


class OperatorAdmissionAuditProcessPayload(BaseModel):
    action: str
    remark: str = ""


class OperatorAdmissionAuditCreatePayload(BaseModel):
    application_no: str
    operator_name: str
    company_name: str = ""
    contact_name: str
    phone: str
    email: str = ""
    region: str = ""
    address: str = ""
    credit_code: str
    founded_at: str | None = None
    station_count: int = 0
    charger_count: int = 0
    service_cities: list[str] = Field(default_factory=list)
    description: str = ""
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    submit_comment: str = ""
    linked_operator_id: int | None = None


class StationChargerCreatePayload(BaseModel):
    sn_code: str
    charger_name: str
    type: str
    power_kw: float
    status: int = 0


class StationChargerBatchCreatePayload(BaseModel):
    count: int
    type: str
    power_kw: float


class StationChargerUpdatePayload(BaseModel):
    charger_name: str | None = None
    status: int | None = None


class DemoStartOrderPayload(BaseModel):
    user_id: int | None = None
    station_id: int | None = None
    charger_id: int | None = None
    source_type: str = "manual_demo"


class RoleContext(BaseModel):
    role: str
    operator_id: int | None = None


def _parse_operator_id(raw: Any) -> int | None:
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    value = str(raw).strip()
    if not value:
        return None
    if value.isdigit():
        return int(value)
    digits = "".join(ch for ch in value if ch.isdigit())
    if digits:
        return int(digits)
    return None


def get_current_operator(db: Session) -> Operator | None:
    return db.query(Operator).options(noload("*")).order_by(Operator.id.asc()).first()


def get_role_context(
    role: str | None = None,
    operator_id: int | None = None,
    x_role: str | None = Header(default=None, alias="x-role"),
    x_operator_id: str | None = Header(default=None, alias="x-operator-id"),
) -> RoleContext:
    resolved_role = (x_role or role or "operator").strip().lower()
    if resolved_role not in {"admin", "operator"}:
        resolved_role = "operator"

    resolved_operator_id = operator_id if operator_id is not None else _parse_operator_id(x_operator_id)

    if resolved_role == "operator":
        if resolved_operator_id is None:
            resolved_operator_id = 1
    return RoleContext(role=resolved_role, operator_id=resolved_operator_id)


def require_admin_context(context: RoleContext = Depends(get_role_context)) -> RoleContext:
    if context.role != "admin":
        raise HTTPException(status_code=403, detail="admin role required")
    return context


def require_operator_context(context: RoleContext = Depends(get_role_context)) -> RoleContext:
    if context.role != "operator":
        raise HTTPException(status_code=403, detail="operator role required")
    return context


def scoped_operator_id(context: RoleContext) -> int | None:
    return None if context.role == "admin" else context.operator_id


def get_operator_by_context(db: Session, context: RoleContext) -> Operator | None:
    if context.operator_id is not None:
        operator = db.query(Operator).options(noload("*")).filter(Operator.id == context.operator_id).first()
        if operator:
            return operator
    return get_current_operator(db)


def resolve_operator_id(db: Session, context: RoleContext) -> int:
    if context.operator_id is not None:
        row = db.query(Operator.id).filter(Operator.id == context.operator_id).first()
        if row:
            return row[0]

    fallback = db.query(Operator.id).order_by(Operator.id.asc()).first()
    if not fallback:
        raise HTTPException(status_code=404, detail="运营商不存在")
    return fallback[0]


def get_operator_basic_info(db: Session, operator_id: int) -> dict[str, Any] | None:
    row = (
        db.query(
            Operator.id.label("id"),
            Operator.name.label("name"),
            Operator.is_verified.label("is_verified"),
        )
        .filter(Operator.id == operator_id)
        .first()
    )
    if not row:
        return None
    return {
        "id": row.id,
        "name": row.name,
        "is_verified": bool(row.is_verified),
    }


def get_or_create_demo_user(db: Session) -> User:
    user = db.query(User).options(noload("*")).order_by(User.id.asc()).first()
    if user:
        return user

    user = User(
        phone="13800138000",
        nickname="演示车主",
        password_hash="demo-password",
        vin_code="DEMOEV20260001",
        status=0,
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def generate_demo_order_no(db: Session) -> str:
    while True:
        order_no = f"EC{datetime.now():%Y%m%d%H%M%S}{random.randint(1000, 9999)}"
        exists = db.query(Order.id).filter(Order.order_no == order_no).first()
        if not exists:
            return order_no


def user_display_name(user: User) -> str:
    return user.nickname or f"鐢ㄦ埛{str(user.phone)[-4:]}"


SETTLEMENT_STATUS_TEXT = {
    0: "待打款",
    1: "已打款",
    2: "挂起待补资料",
}

INVOICE_STATUS_TEXT = {
    0: "待开票",
    1: "已开票",
    2: "已驳回",
}

BANK_CARD_STATUS_TEXT = {
    0: "待审核",
    1: "已通过",
    2: "已驳回",
}


def mask_bank_account(bank_account: str | None) -> str:
    if not bank_account:
        return ""
    digits = bank_account.replace(" ", "")
    if len(digits) < 8:
        return digits
    return f"{digits[:4]} **** **** {digits[-4:]}"


def serialize_bank_card(card: OperatorBankCard) -> dict:
    return {
        "id": card.id,
        "operator_id": card.operator_id,
        "account_name": card.account_name,
        "bank_name": card.bank_name,
        "bank_account": card.bank_account,
        "bank_account_masked": mask_bank_account(card.bank_account),
        "is_default": bool(card.is_default),
        "bind_status": card.bind_status,
        "bind_status_text": BANK_CARD_STATUS_TEXT.get(card.bind_status, "未知状态"),
        "created_at": card.created_at.strftime("%Y-%m-%d %H:%M:%S") if card.created_at else "",
        "updated_at": card.updated_at.strftime("%Y-%m-%d %H:%M:%S") if card.updated_at else "",
    }


def resolve_bank_card_audit_status(cards: list[OperatorBankCard]) -> tuple[str, str]:
    if not cards:
        return "unbound", "未绑定"
    if any(card.bind_status == 1 for card in cards):
        return "approved", "已通过"
    if any(card.bind_status == 0 for card in cards):
        return "pending", "待审核"
    return "rejected", "已驳回"


def resolve_settlement_qualification(operator: Operator | None, cards: list[OperatorBankCard]) -> tuple[bool, str]:
    is_verified = bool(operator and operator.is_verified)
    approved_default_card = next((card for card in cards if card.is_default and card.bind_status == 1), None)
    if is_verified and approved_default_card:
        return True, "已具备 T+1 清分资格"

    missing_parts: list[str] = []
    if not is_verified:
        missing_parts.append("运营商未认证")
    if not approved_default_card:
        missing_parts.append("未配置默认且审核通过的收款卡")
    return False, "，".join(missing_parts) if missing_parts else "暂不具备清分资格"


def resolve_settlement_qualification_from_flag(is_verified: bool, cards: list[OperatorBankCard]) -> tuple[bool, str]:
    approved_default_card = next((card for card in cards if card.is_default and card.bind_status == 1), None)
    if is_verified and approved_default_card:
        return True, "已具备 T+1 清分资格"

    missing_parts: list[str] = []
    if not is_verified:
        missing_parts.append("运营商未认证")
    if not approved_default_card:
        missing_parts.append("未配置默认且审核通过的收款卡")
    return False, "，".join(missing_parts) if missing_parts else "暂不具备清分资格"


def serialize_operator_settlement(record: OperatorSettlementRecord) -> dict:
    return {
        "id": record.id,
        "settle_date": str(record.settle_date),
        "operator_id": record.operator_id,
        "operator_name": record.operator.name if record.operator else "",
        "order_count": record.order_count,
        "total_amount": float(record.total_amount),
        "platform_rate": float(record.platform_rate),
        "platform_fee": float(record.platform_fee),
        "settle_amount": float(record.settle_amount),
        "status": record.status,
        "status_text": SETTLEMENT_STATUS_TEXT.get(record.status, "未知"),
        "can_payout": record.status == 0,
        "hold_reason": record.hold_reason,
        "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S") if record.created_at else "",
        "updated_at": record.updated_at.strftime("%Y-%m-%d %H:%M:%S") if record.updated_at else "",
    }


def serialize_operator_settlement_row(row: Any) -> dict:
    return {
        "id": row.id,
        "settle_date": str(row.settle_date),
        "operator_id": row.operator_id,
        "operator_name": row.operator_name or "",
        "order_count": int(row.order_count or 0),
        "total_amount": float(row.total_amount or 0),
        "platform_rate": float(row.platform_rate or 0),
        "platform_fee": float(row.platform_fee or 0),
        "settle_amount": float(row.settle_amount or 0),
        "status": row.status,
        "status_text": SETTLEMENT_STATUS_TEXT.get(row.status, "未知"),
        "can_payout": row.status == 0,
        "hold_reason": row.hold_reason,
        "created_at": row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else "",
        "updated_at": row.updated_at.strftime("%Y-%m-%d %H:%M:%S") if row.updated_at else "",
    }


def serialize_invoice_record(invoice: Invoice, can_process: bool) -> dict:
    invoice_no = f"INV{invoice.created_at.strftime('%Y%m%d')}{str(invoice.id).zfill(4)}"
    return {
        "id": invoice.id,
        "invoice_no": invoice_no,
        "user_id": invoice.user_id,
        "user_phone": invoice.user.phone if invoice.user else "",
        "operator_id": invoice.operator_id,
        "operator_name": invoice.operator.name if invoice.operator else "",
        "order_id": invoice.order_id,
        "order_no": invoice.related_order.order_no if invoice.related_order else None,
        "invoice_title": invoice.invoice_title,
        "amount": float(invoice.amount or 0),
        "email": invoice.email,
        "status": invoice.status,
        "status_text": INVOICE_STATUS_TEXT.get(invoice.status, "未知状态"),
        "file_url": invoice.file_url,
        "remark": invoice.remark,
        "created_at": invoice.created_at.strftime("%Y-%m-%d %H:%M:%S") if invoice.created_at else "",
        "uploaded_at": invoice.uploaded_at.strftime("%Y-%m-%d %H:%M:%S") if invoice.uploaded_at else None,
        "updated_at": invoice.updated_at.strftime("%Y-%m-%d %H:%M:%S") if invoice.updated_at else "",
        "can_process": can_process,
    }


def serialize_invoice_row(row: Any, *, can_process: bool) -> dict:
    invoice_no = f"INV{row.created_at.strftime('%Y%m%d')}{str(row.id).zfill(4)}"
    return {
        "id": row.id,
        "invoice_no": invoice_no,
        "user_id": row.user_id,
        "user_phone": row.user_phone or "",
        "operator_id": row.operator_id,
        "operator_name": row.operator_name or "",
        "order_id": row.order_id,
        "order_no": row.order_no,
        "invoice_title": row.invoice_title,
        "amount": float(row.amount or 0),
        "email": row.email,
        "status": row.status,
        "status_text": INVOICE_STATUS_TEXT.get(row.status, "未知状态"),
        "file_url": row.file_url,
        "remark": row.remark,
        "created_at": row.created_at.strftime("%Y-%m-%d %H:%M:%S") if row.created_at else "",
        "uploaded_at": row.uploaded_at.strftime("%Y-%m-%d %H:%M:%S") if row.uploaded_at else None,
        "updated_at": row.updated_at.strftime("%Y-%m-%d %H:%M:%S") if row.updated_at else "",
        "can_process": can_process,
    }


def get_station_snapshot_data(db: Session, station_id: int) -> dict[str, Any] | None:
    row = (
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
            Operator.name.label("operator_name"),
            PriceTemplate.name.label("price_template_name"),
        )
        .select_from(Station)
        .join(Operator, Station.operator_id == Operator.id)
        .outerjoin(PriceTemplate, Station.template_id == PriceTemplate.id)
        .filter(Station.id == station_id, Station.is_deleted.is_(False))
        .first()
    )
    if not row:
        return None
    charger_count = (
        db.query(func.count(Charger.id))
        .filter(Charger.station_id == station_id, Charger.is_deleted.is_(False))
        .scalar()
        or 0
    )
    row_dict = row._asdict() if hasattr(row, "_asdict") else dict(row)
    row_dict["charger_count"] = int(charger_count)
    return serialize_station_row(type("StationRow", (), row_dict)())


def get_invoice_snapshot_data(db: Session, invoice_id: int, *, can_process: bool) -> dict[str, Any] | None:
    row = (
        db.query(
            Invoice.id.label("id"),
            Invoice.user_id.label("user_id"),
            Invoice.operator_id.label("operator_id"),
            Invoice.order_id.label("order_id"),
            Invoice.invoice_title.label("invoice_title"),
            Invoice.amount.label("amount"),
            Invoice.email.label("email"),
            Invoice.status.label("status"),
            Invoice.file_url.label("file_url"),
            Invoice.remark.label("remark"),
            Invoice.created_at.label("created_at"),
            Invoice.uploaded_at.label("uploaded_at"),
            Invoice.updated_at.label("updated_at"),
            User.phone.label("user_phone"),
            Operator.name.label("operator_name"),
            Order.order_no.label("order_no"),
        )
        .select_from(Invoice)
        .outerjoin(User, Invoice.user_id == User.id)
        .outerjoin(Operator, Invoice.operator_id == Operator.id)
        .outerjoin(Order, Invoice.order_id == Order.id)
        .filter(Invoice.id == invoice_id)
        .first()
    )
    return serialize_invoice_row(row, can_process=can_process) if row else None


def seed_runtime_data(db: Session) -> None:
    operator = get_current_operator(db)
    operator_id = operator.id if operator else 0

    if not template_store:
        template_store.extend(
            [
                {
                    "id": 1,
                    "name": "城市快充标准模板",
                    "peak_price": 1.88,
                    "flat_price": 1.34,
                    "valley_price": 0.76,
                    "service_price": 0.8,
                    "scope": "全站",
                    "status": "active",
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
                {
                    "id": 2,
                    "name": "园区夜充模板",
                    "peak_price": 1.56,
                    "flat_price": 1.12,
                    "valley_price": 0.58,
                    "service_price": 0.65,
                    "scope": "指定站点",
                    "status": "draft",
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
            ]
        )

    if not tag_store:
        tag_store.extend(
            [
                {"id": 1, "name": "高频通勤", "color": "#409EFF", "description": "近30天充电20次以上", "user_count": 86},
                {"id": 2, "name": "夜间充电", "color": "#67C23A", "description": "夜间活跃用户", "user_count": 43},
                {"id": 3, "name": "待召回", "color": "#E6A23C", "description": "近14天未复购", "user_count": 27},
            ]
        )

    if not discount_campaign_store:
        discount_campaign_store.extend(
            [
                {
                    "id": 1,
                    "name": "工作日午间充电折扣",
                    "campaign_type": "满减",
                    "discount_value": 8.8,
                    "threshold": 30,
                    "audience": "企业车队",
                    "status": "active",
                    "redeem_count": 326,
                    "conversion_rate": 24.5,
                },
                {
                    "id": 2,
                    "name": "新用户首充礼",
                    "campaign_type": "立减",
                    "discount_value": 12,
                    "threshold": 0,
                    "audience": "新用户",
                    "status": "draft",
                    "redeem_count": 0,
                    "conversion_rate": 0,
                },
            ]
        )

    if not coupon_campaign_store:
        coupon_campaign_store.extend(
            [
                {
                    "id": 1,
                    "name": "春季园区通勤券",
                    "discount_value": 10,
                    "inventory": 1000,
                    "dispatched": 640,
                    "used": 381,
                    "status": "active",
                },
                {
                    "id": 2,
                    "name": "夜充满减券",
                    "discount_value": 15,
                    "inventory": 500,
                    "dispatched": 120,
                    "used": 39,
                    "status": "paused",
                },
            ]
        )

    operators = db.query(Operator).order_by(Operator.created_at.desc()).all()
    if not operator_audit_store:
        for item in operators:
            operator_audit_store[item.id] = {
                "status": "approved" if item.is_verified else "pending",
                "remark": "",
                "contact_email": f"bd{item.id}@echarge.com",
                "contact_phone": f"1380000{str(item.id).zfill(4)}",
            }

    if not marketing_audit_store:
        for item in discount_campaign_store:
            marketing_audit_store[item["id"]] = {
                "status": "approved" if item["status"] == "active" else "pending",
                "remark": "",
            }


@api_router.get("/health", tags=["system"])
async def health_check() -> dict:
    return {"status": "ok"}

@api_router.get("/overview/summary", tags=["overview"])
def get_overview_summary(db: Session = Depends(get_db)) -> dict:
    return get_platform_overview_summary(db)

@api_router.get("/overview/realtime-orders", tags=["overview"])
def get_realtime_orders(db: Session = Depends(get_db)) -> list[dict]:
    return get_platform_overview_realtime_orders(db, limit=5)

class ManualSettleRequest(BaseModel):
    date: date

@api_router.post("/settlements/manual_settle", tags=["settlements"])
def manual_settle(payload: ManualSettleRequest, db: Session = Depends(get_db)) -> dict:
    try:
        detail = settle_t_plus_1_by_operator(
            payload.date,
            db=db,
            platform_rate_percent=system_param_store.get("settlement_platform_rate", 10),
        )
        logger.info(
            "manual_settle",
            extra={
                "date": str(payload.date),
                "processed": detail["processed_order_count"],
                "operator_count": detail["processed_operator_count"],
            },
        )
        return {
            "code": 0,
            "processed": detail["processed_order_count"],
            "operator_count": detail["processed_operator_count"],
            "data": detail,
        }
    except Exception as e:
        logger.exception("manual_settle_failed", extra={"date": str(payload.date)})
        return {"code": 500, "processed": 0, "message": friendly_db_error_message(e), "data": None}

@api_router.get("/finance/settlements", tags=["finance"])
async def get_settlements(
    context: RoleContext = Depends(get_role_context),
    db: Session = Depends(get_db),
):
    operator_id = resolve_operator_id(db, context) if context.role == "operator" else None
    query = (
        db.query(
            OperatorSettlementRecord.id.label("id"),
            OperatorSettlementRecord.settle_date.label("settle_date"),
            OperatorSettlementRecord.operator_id.label("operator_id"),
            OperatorSettlementRecord.order_count.label("order_count"),
            OperatorSettlementRecord.total_amount.label("total_amount"),
            OperatorSettlementRecord.platform_rate.label("platform_rate"),
            OperatorSettlementRecord.platform_fee.label("platform_fee"),
            OperatorSettlementRecord.settle_amount.label("settle_amount"),
            OperatorSettlementRecord.status.label("status"),
            OperatorSettlementRecord.hold_reason.label("hold_reason"),
            OperatorSettlementRecord.created_at.label("created_at"),
            OperatorSettlementRecord.updated_at.label("updated_at"),
            Operator.name.label("operator_name"),
        )
        .select_from(OperatorSettlementRecord)
        .outerjoin(Operator, OperatorSettlementRecord.operator_id == Operator.id)
        .order_by(OperatorSettlementRecord.settle_date.desc(), OperatorSettlementRecord.operator_id.asc())
    )
    if operator_id is not None:
        query = query.filter(OperatorSettlementRecord.operator_id == operator_id)

    records = query.all()
    if records:
        data = [serialize_operator_settlement_row(r) for r in records]
        return {
            "code": 200,
            "data": data,
            "summary": {
                "order_count": sum(item["order_count"] for item in data),
                "total_amount": round(sum(item["total_amount"] for item in data), 2),
                "platform_fee": round(sum(item["platform_fee"] for item in data), 2),
                "settle_amount": round(sum(item["settle_amount"] for item in data), 2),
            },
        }

    legacy_records = db.query(SettlementRecord).order_by(SettlementRecord.settle_date.desc()).all()
    legacy_data = [
        {
            "settle_date": str(r.settle_date),
            "order_count": r.order_count,
            "total_amount": float(r.total_amount),
            "platform_fee": float(r.platform_fee),
            "settle_amount": float(r.settle_amount),
            "status": r.status,
            "status_text": SETTLEMENT_STATUS_TEXT.get(r.status, "未知"),
            "operator_id": None,
            "operator_name": "全网汇总",
            "platform_rate": None,
            "can_payout": None,
            "hold_reason": None,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
            "updated_at": r.updated_at.strftime("%Y-%m-%d %H:%M:%S") if r.updated_at else "",
        }
        for r in legacy_records
    ]
    return {"code": 200, "data": legacy_data}


@api_router.post("/finance/settle", tags=["finance"])
async def trigger_settle(db: Session = Depends(get_db)):
    target = date.today() - timedelta(days=1)
    try:
        detail = settle_t_plus_1_by_operator(
            target,
            db=db,
            platform_rate_percent=system_param_store.get("settlement_platform_rate", 10),
        )
        return {
            "code": 200,
            "message": (
                f"清分完成：处理订单 {detail['processed_order_count']} 笔，"
                f"覆盖运营商 {detail['processed_operator_count']} 个，"
                f"跳过已存在批次 {detail['skipped_operator_count']} 个"
            ),
            "processed": detail["processed_order_count"],
            "operator_count": detail["processed_operator_count"],
            "skipped_operator_count": detail["skipped_operator_count"],
            "data": detail,
        }
    except Exception as e:
        logger.exception("finance_settle_failed", extra={"date": str(target)})
        return {"code": 500, "message": friendly_db_error_message(e), "processed": 0, "data": None}


@api_router.get("/orders/all", tags=["orders"])
async def get_orders_all(
    context: RoleContext = Depends(get_role_context),
    db: Session = Depends(get_db),
):
    return {
        "code": 200,
        "data": get_all_order_list(db, limit=200, operator_id=scoped_operator_id(context)),
    }


@api_router.get("/orders/realtime", tags=["orders"])
async def get_orders_realtime_api(
    context: RoleContext = Depends(get_role_context),
    db: Session = Depends(get_db),
):
    return {
        "code": 200,
        "data": get_realtime_order_list(db, limit=50, operator_id=scoped_operator_id(context)),
    }


@api_router.get("/orders/abnormal", tags=["orders"])
async def get_orders_abnormal_api(
    context: RoleContext = Depends(get_role_context),
    db: Session = Depends(get_db),
):
    return {
        "code": 200,
        "data": get_abnormal_order_list(db, limit=50, operator_id=scoped_operator_id(context)),
    }


@api_router.get("/orders/history", tags=["orders"])
async def get_orders_history_api(
    context: RoleContext = Depends(get_role_context),
    db: Session = Depends(get_db),
):
    return {
        "code": 200,
        "data": get_history_order_list(db, limit=100, operator_id=scoped_operator_id(context)),
    }


@api_router.get("/orders/stats", tags=["orders"])
async def get_order_stats_api(
    context: RoleContext = Depends(get_role_context),
    db: Session = Depends(get_db),
):
    return {
        "code": 200,
        "data": get_order_stats(db, operator_id=scoped_operator_id(context)),
    }


@api_router.get("/wallet/summary", tags=["wallet"])
async def get_wallet_summary_api(user_id: int = 1, db: Session = Depends(get_db)):
    return {
        "code": 200,
        "data": get_wallet_summary(db, user_id=user_id, limit=10),
    }


@api_router.get("/wallet/transactions", tags=["wallet"])
async def get_wallet_transactions_api(user_id: int = 1, limit: int = 50, db: Session = Depends(get_db)):
    return {
        "code": 200,
        "data": get_wallet_transaction_list(db, user_id=user_id, limit=limit),
    }


@api_router.get("/orders/{order_id}", tags=["orders"])
async def get_order_detail(
    order_id: int,
    context: RoleContext = Depends(get_role_context),
    db: Session = Depends(get_db),
):
    order_data = get_order_detail_data(db, order_id, operator_id=scoped_operator_id(context))
    if not order_data:
        return {"code": 404, "message": "订单不存在或无权限访问"}

    return {
        "code": 200,
        "data": order_data,
    }


@api_router.post("/orders/{order_id}/force-stop", tags=["orders"])
async def force_stop_order_api(
    order_id: int,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    result = force_stop_order(db, order_id, operator_id=context.operator_id)
    if not result:
        return {"code": 400, "message": "订单不存在、无权限或当前非充电中状态"}

    return {
        "code": 200,
        "message": "订单已强制停止",
        "data": serialize_order(result.order),
    }


@api_router.post("/orders/{order_id}/mark-abnormal", tags=["orders"])
async def mark_order_abnormal_api(
    order_id: int,
    payload: OrderActionSchema,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    order = mark_order_abnormal(db, order_id, payload.abnormal_reason, operator_id=context.operator_id)
    if not order:
        return {"code": 400, "message": "订单不存在、无权限或当前非充电中状态"}

    return {
        "code": 200,
        "message": "订单已标记异常",
        "data": serialize_order(order),
    }


@api_router.get("/admin/orders", tags=["orders", "admin"])
async def get_admin_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    keyword: str | None = None,
    status: int | None = None,
    station_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    _context: RoleContext = Depends(require_admin_context),
    db: Session = Depends(get_db),
):
    return {
        "code": 200,
        "data": get_order_page(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            status=status,
            station_id=station_id,
            start_date=start_date,
            end_date=end_date,
        ),
    }


@api_router.get("/admin/orders/abnormal", tags=["orders", "admin"])
async def get_admin_abnormal_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    keyword: str | None = None,
    status: int | None = None,
    station_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    abnormal_reason: str | None = None,
    _context: RoleContext = Depends(require_admin_context),
    db: Session = Depends(get_db),
):
    return {
        "code": 200,
        "data": get_order_page(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            status=status,
            station_id=station_id,
            start_date=start_date,
            end_date=end_date,
            abnormal_reason=abnormal_reason,
            default_status=2,
        ),
    }


@api_router.get("/admin/orders/{order_id}", tags=["orders", "admin"])
async def get_admin_order_detail(
    order_id: int,
    _context: RoleContext = Depends(require_admin_context),
    db: Session = Depends(get_db),
):
    order_data = get_order_detail_data(db, order_id)
    if not order_data:
        return {"code": 404, "message": "订单不存在"}
    return {"code": 200, "data": order_data}


@api_router.post("/admin/orders/{order_id}/mark-abnormal", tags=["orders", "admin"])
async def admin_mark_order_abnormal(
    order_id: int,
    payload: OrderActionSchema,
    _context: RoleContext = Depends(require_admin_context),
    db: Session = Depends(get_db),
):
    """平台管理员：将充电中订单标记为异常（不限运营商）。"""
    order = mark_order_abnormal(db, order_id, payload.abnormal_reason, operator_id=None)
    if not order:
        return {"code": 400, "message": "订单不存在或当前非充电中状态，无法标记异常"}
    return {
        "code": 200,
        "message": "订单已标记异常",
        "data": {
            "id": order.id,
            "order_no": order.order_no,
            "status": order.status,
            "abnormal_reason": order.abnormal_reason,
        },
    }


@api_router.get("/operator/stations", tags=["operator"])
async def get_operator_stations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    keyword: str | None = None,
    status: int | None = None,
    visibility: str | None = None,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator = get_operator_by_context(db, context)
    if not operator:
        return {"code": 404, "message": "当前运营商未找到，请先入驻"}
    operator_id = operator.id

    return {
        "code": 200,
        "data": get_operator_station_page(
            db,
            operator_id=operator_id,
            page=page,
            page_size=page_size,
            keyword=keyword,
            status=status,
            visibility=visibility,
        ),
    }


@api_router.get("/operator/stations/options", tags=["operator"])
async def get_operator_station_option_list(
    keyword: str | None = None,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator = get_operator_by_context(db, context)
    if not operator:
        return {"code": 404, "message": "当前运营商未找到，请先入驻"}
    operator_id = operator.id
    return {
        "code": 200,
        "data": get_operator_station_options(db, operator_id=operator_id, keyword=keyword),
    }


@api_router.post("/operator/stations/apply", tags=["operator"])
def operator_apply_station(
    payload: StationApplyPayload,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator = get_operator_by_context(db, context)
    if not operator:
        return {"code": 404, "message": "当前运营商未找到，请先入驻"}

    station_name = payload.station_name.strip()
    if not station_name:
        return {"code": 400, "message": "请填写电站名称"}

    support_types = [str(x).strip() for x in (payload.support_vehicle_types or []) if str(x).strip()]
    facility_tags = [str(x).strip() for x in (payload.facility_tags or []) if str(x).strip()]

    new_station = Station(
        operator_id=operator.id,
        name=station_name,
        province=payload.province.strip(),
        city=payload.city.strip(),
        district=payload.district.strip(),
        address=payload.address.strip(),
        longitude=Decimal(str(payload.longitude)),
        latitude=Decimal(str(payload.latitude)),
        contact_name=payload.contact_name.strip(),
        contact_phone=payload.contact_phone.strip(),
        operation_hours=payload.operation_hours.strip(),
        parking_fee_desc=payload.parking_fee_desc.strip(),
        station_remark=payload.station_remark.strip(),
        planned_charger_count=max(int(payload.planned_charger_count or 0), 0),
        total_power_kw=Decimal(str(payload.total_power_kw or 0)),
        cover_image=payload.cover_image.strip(),
        site_photos_json=dump_site_photos(payload.site_photos),
        qualification_remark=payload.qualification_remark.strip(),
        parking_slot_count=int(payload.parking_slot_count) if payload.parking_slot_count is not None else None,
        service_radius_km=Decimal(str(payload.service_radius_km))
        if payload.service_radius_km is not None
        else None,
        site_owner=payload.site_owner.strip(),
        construction_phase=payload.construction_phase.strip(),
        grid_capacity_remark=payload.grid_capacity_remark.strip(),
        support_vehicle_types_json=json.dumps(support_types, ensure_ascii=False) if support_types else None,
        facility_tags_json=json.dumps(facility_tags, ensure_ascii=False) if facility_tags else None,
        safety_contact_name=payload.safety_contact_name.strip(),
        safety_contact_phone=payload.safety_contact_phone.strip(),
        audit_remark="待管理员审核",
        status=3,
        visibility="private",
    )
    db.add(new_station)
    db.commit()

    snap = (
        db.query(
            Station.id,
            Station.name,
            Station.province,
            Station.city,
            Station.district,
            Station.address,
            Station.contact_name,
            Station.contact_phone,
            Station.status,
            Station.visibility,
            Station.planned_charger_count,
            Station.total_power_kw,
            Station.created_at,
            Station.updated_at,
        )
        .filter(Station.id == new_station.id)
        .first()
    )
    if not snap:
        return {"code": 500, "message": "申请已提交但读取站点信息失败，请刷新列表"}

    data = serialize_operator_station_apply_light(
        station_id=int(snap.id),
        station_name=str(snap.name or station_name),
        province=str(snap.province or ""),
        city=str(snap.city or ""),
        district=str(snap.district or ""),
        address=str(snap.address or ""),
        contact_name=str(snap.contact_name or ""),
        contact_phone=str(snap.contact_phone or ""),
        operator_id=int(operator.id),
        status=int(snap.status),
        visibility=str(snap.visibility or "private"),
        planned_charger_count=int(snap.planned_charger_count or 0),
        total_power_kw=snap.total_power_kw,
        created_at=snap.created_at,
        updated_at=snap.updated_at,
    )

    return {
        "code": 200,
        "message": "电站申请已提交，等待管理员审核",
        "data": data,
    }


@api_router.get("/operator/stations/{station_id}/chargers", tags=["operator"])
def get_operator_station_chargers(
    station_id: int,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator = get_operator_by_context(db, context)
    if not operator:
        return {"code": 404, "message": "当前运营商未找到，请先入驻"}
    operator_id = operator.id

    station = (
        db.query(Station.id.label("id"), Station.name.label("station_name"))
        .filter(Station.id == station_id, Station.operator_id == operator_id, Station.is_deleted.is_(False))
        .first()
    )
    if not station:
        return {"code": 404, "message": "电站不存在或无权限访问"}

    chargers = (
        db.query(
            Charger.id.label("id"),
            Charger.sn_code.label("sn_code"),
            Charger.name.label("charger_name"),
            Charger.type.label("type"),
            Charger.power_kw.label("power_kw"),
            Charger.status.label("status"),
            Charger.updated_at.label("updated_at"),
        )
        .filter(Charger.station_id == station_id, Charger.is_deleted.is_(False))
        .order_by(Charger.created_at.asc(), Charger.id.asc())
        .all()
    )

    return {
        "code": 200,
        "data": [
            {
                "id": row.id,
                "sn_code": row.sn_code,
                "charger_name": row.charger_name or f"{station.station_name[:10]}-{index:02d}号桩",
                "type": row.type,
                "power_kw": float(row.power_kw or 0),
                "status": row.status,
                "status_text": charger_status_text(row.status),
                "station_id": station.id,
                "station_name": station.station_name,
                "updated_at": row.updated_at.strftime("%Y-%m-%d %H:%M:%S") if row.updated_at else "",
            }
            for index, row in enumerate(chargers, start=1)
        ],
    }


@api_router.post("/operator/stations/{station_id}/chargers", tags=["operator"])
def create_operator_station_charger(
    station_id: int,
    payload: StationChargerCreatePayload,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator_id = resolve_operator_id(db, context)
    station = get_station_manageable_row(db, station_id=station_id, operator_id=operator_id)
    if not station:
        return {"code": 404, "message": "电站不存在或无权限访问"}

    manageable, message = validate_station_manageable_status(station.status)
    if not manageable:
        return {"code": 400, "message": message}

    sn_code = payload.sn_code.strip().upper()
    if not sn_code:
        return {"code": 400, "message": "请输入电桩编号"}
    sn_err = release_charger_sn_if_soft_deleted(db, sn_code)
    if sn_err:
        return {"code": 400, "message": sn_err}

    charger_type = (payload.type or "").strip().upper()
    if charger_type not in {"AC", "DC"}:
        return {"code": 400, "message": "电桩类型仅支持 AC/DC"}

    status = int(payload.status)
    if status not in {0, 1, 2, 3}:
        return {"code": 400, "message": "电桩状态不合法"}

    existing = (
        db.query(func.count(Charger.id))
        .filter(Charger.station_id == station.id, Charger.is_deleted.is_(False))
        .scalar()
        or 0
    )
    default_name = f"{station.name[:10]}-{existing + 1:02d}号桩"
    display_name = (payload.charger_name or "").strip() or default_name

    charger = create_station_charger(
        db,
        station_id=station.id,
        station_name=station.name,
        planned_charger_count=station.planned_charger_count,
        total_power_kw=station.total_power_kw,
        sn_code=sn_code,
        charger_name=display_name,
        charger_type=charger_type,
        power_kw=Decimal(str(payload.power_kw)),
        status=status,
    )
    row = (
        db.query(
            Charger.id,
            Charger.sn_code,
            Charger.name,
            Charger.type,
            Charger.power_kw,
            Charger.status,
            Charger.updated_at,
        )
        .filter(Charger.id == charger.id)
        .first()
    )
    if not row:
        return {"code": 500, "message": "电桩已写入但读取失败，请刷新列表"}
    data = serialize_charger_snapshot(
        charger_id=int(row.id),
        sn_code=str(row.sn_code or ""),
        name=row.name,
        type_value=str(row.type or ""),
        power_kw=row.power_kw,
        status=int(row.status or 0),
        station_id=int(station.id),
        station_name=str(station.name or ""),
        updated_at=row.updated_at,
    )
    return {"code": 200, "message": "电桩新增成功", "data": data}


@api_router.post("/operator/stations/{station_id}/chargers/batch-create", tags=["operator"])
def batch_create_operator_station_chargers(
    station_id: int,
    payload: StationChargerBatchCreatePayload,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator_id = resolve_operator_id(db, context)
    station = get_station_manageable_row(db, station_id=station_id, operator_id=operator_id)
    if not station:
        return {"code": 404, "message": "电站不存在或无权限访问"}

    manageable, message = validate_station_manageable_status(station.status)
    if not manageable:
        return {"code": 400, "message": message}

    count = int(payload.count or 0)
    if count < 1 or count > 50:
        return {"code": 400, "message": "批量生成数量需在 1-50 之间"}

    charger_type = (payload.type or "").strip().upper()
    if charger_type not in {"AC", "DC"}:
        return {"code": 400, "message": "电桩类型仅支持 AC/DC"}

    created = batch_create_station_chargers(
        db,
        station_id=station.id,
        station_name=station.name,
        planned_charger_count=station.planned_charger_count,
        total_power_kw=station.total_power_kw,
        count=count,
        charger_type=charger_type,
        power_kw=Decimal(str(payload.power_kw)),
    )
    ids = [c.id for c in created if getattr(c, "id", None)]
    if not ids:
        return {"code": 500, "message": "批量写入失败，请重试"}
    rows = (
        db.query(
            Charger.id,
            Charger.sn_code,
            Charger.name,
            Charger.type,
            Charger.power_kw,
            Charger.status,
            Charger.updated_at,
        )
        .filter(Charger.id.in_(ids))
        .order_by(Charger.id.asc())
        .all()
    )
    station_name = str(station.name or "")
    sid = int(station.id)
    data = [
        serialize_charger_snapshot(
            charger_id=int(r.id),
            sn_code=str(r.sn_code or ""),
            name=r.name,
            type_value=str(r.type or ""),
            power_kw=r.power_kw,
            status=int(r.status or 0),
            station_id=sid,
            station_name=station_name,
            updated_at=r.updated_at,
        )
        for r in rows
    ]
    return {
        "code": 200,
        "message": f"已批量生成 {len(data)} 个电桩",
        "data": data,
    }


@api_router.patch("/operator/stations/{station_id}/chargers/{charger_id}", tags=["operator"])
def update_operator_station_charger(
    station_id: int,
    charger_id: int,
    payload: StationChargerUpdatePayload,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator = get_operator_by_context(db, context)
    if not operator:
        return {"code": 404, "message": "当前运营商未找到，请先入驻"}
    operator_id = operator.id

    station_row = (
        db.query(Station.id, Station.name)
        .filter(Station.id == station_id, Station.operator_id == operator_id, Station.is_deleted.is_(False))
        .first()
    )
    if not station_row:
        return {"code": 404, "message": "电站不存在或无权限访问"}

    charger_row = (
        db.query(
            Charger.id,
            Charger.sn_code,
            Charger.name,
            Charger.type,
            Charger.power_kw,
            Charger.status,
            Charger.updated_at,
        )
        .filter(
            Charger.id == charger_id,
            Charger.station_id == station_id,
            Charger.is_deleted.is_(False),
        )
        .first()
    )
    if not charger_row:
        return {"code": 404, "message": "电桩不存在或无权操作"}

    if payload.status is not None and int(payload.status) not in {0, 1, 2, 3}:
        return {"code": 400, "message": "电桩状态不合法"}

    values: dict[str, Any] = {}
    if payload.charger_name is not None:
        stripped = payload.charger_name.strip()
        values["name"] = stripped or charger_row.name
    if payload.status is not None:
        values["status"] = int(payload.status)

    if values:
        values["updated_at"] = datetime.now()
        db.execute(
            sa_update(Charger)
            .where(
                Charger.id == charger_id,
                Charger.station_id == station_id,
                Charger.is_deleted.is_(False),
            )
            .values(**values)
        )
        db.commit()

    fresh = (
        db.query(
            Charger.id,
            Charger.sn_code,
            Charger.name,
            Charger.type,
            Charger.power_kw,
            Charger.status,
            Charger.updated_at,
        )
        .filter(Charger.id == charger_id)
        .first()
    )
    if not fresh:
        return {"code": 404, "message": "电桩不存在或无权操作"}

    data = serialize_charger_snapshot(
        charger_id=int(fresh.id),
        sn_code=str(fresh.sn_code or ""),
        name=fresh.name,
        type_value=str(fresh.type or ""),
        power_kw=fresh.power_kw,
        status=int(fresh.status or 0),
        station_id=int(station_row.id),
        station_name=str(station_row.name or ""),
        updated_at=fresh.updated_at,
    )
    return {"code": 200, "message": "电桩配置已更新", "data": data}


@api_router.post("/operator/stations/{station_id}/visibility", tags=["operator"])
def update_operator_station_visibility(
    station_id: int,
    payload: StationVisibilityPayload,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator_id = resolve_operator_id(db, context)
    station = (
        db.query(Station)
        .filter(Station.id == station_id, Station.operator_id == operator_id, Station.is_deleted.is_(False))
        .first()
    )
    if not station:
        return {"code": 404, "message": "电站不存在或无权限访问"}

    visibility = (payload.visibility or "").strip().lower()
    if visibility not in {"public", "private"}:
        return {"code": 400, "message": "visibility 仅支持 public/private"}
    if visibility == "public" and station.status != 0:
        return {"code": 400, "message": "电站未审核通过，不能设置为公开站点"}

    station.visibility = visibility
    db.commit()
    return {
        "code": 200,
        "message": "电站可见性已更新",
        "data": {
            "id": station.id,
            "visibility": station.visibility,
            "visibility_text": visibility_text(station.visibility),
            "status": station.status,
            "status_text": station_status_text(station.status),
        },
    }


@api_router.post("/operator/stations/{station_id}/bind-template", tags=["operator"])
def bind_operator_station_template(
    station_id: int,
    payload: BindTemplatePayload,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator_id = resolve_operator_id(db, context)

    station_row = (
        db.query(Station.id, Station.status, Station.visibility)
        .filter(Station.id == station_id, Station.operator_id == operator_id, Station.is_deleted.is_(False))
        .first()
    )
    if not station_row:
        return {"code": 404, "message": "电站不存在或无权限访问"}
    if station_row.status is None or int(station_row.status) != 0:
        return {"code": 400, "message": "电站审核通过后才允许绑定模板"}

    template = (
        db.query(PriceTemplate.id, PriceTemplate.name)
        .filter(
            PriceTemplate.id == payload.template_id,
            PriceTemplate.operator_id == operator_id,
            PriceTemplate.is_deleted.is_(False),
        )
        .first()
    )
    if not template:
        return {"code": 404, "message": "电价模板不存在"}

    res = db.execute(
        sa_update(Station)
        .where(
            Station.id == station_id,
            Station.operator_id == operator_id,
            Station.is_deleted.is_(False),
            Station.status == 0,
        )
        .values(template_id=template.id)
    )
    if not res.rowcount:
        return {"code": 400, "message": "模板绑定失败，请刷新后重试"}
    db.commit()
    return {
        "code": 200,
        "message": "模板绑定成功",
        "data": {
            "id": station_row.id,
            "price_template_id": template.id,
            "price_template_name": template.name,
            "status": station_row.status,
            "visibility": station_row.visibility,
        },
    }


@api_router.get("/operator/pricing/templates", tags=["operator"])
async def get_operator_pricing_templates(
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator_id = resolve_operator_id(db, context)

    templates = (
        db.query(PriceTemplate)
        .options(noload("*"))
        .filter(PriceTemplate.operator_id == operator_id, PriceTemplate.is_deleted.is_(False))
        .order_by(PriceTemplate.updated_at.desc(), PriceTemplate.id.desc())
        .all()
    )
    if not templates:
        operator = get_operator_by_context(db, context)
        if operator:
            templates = ensure_operator_price_templates(db, operator)
    return {"code": 200, "data": [serialize_price_template(item) for item in templates]}


@api_router.post("/operator/billing/templates", tags=["operator"])
def create_operator_billing_template(
    payload: TemplatePayload,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator_id = resolve_operator_id(db, context)
    name = payload.name.strip()
    if not name:
        return {"code": 400, "message": "请填写模板名称"}

    rules = {
        "peak_price": float(payload.peak_price or 1.68),
        "flat_price": float(payload.flat_price or 1.18),
        "valley_price": float(payload.valley_price or 0.68),
        "service_price": float(payload.service_price or 0.72),
        "scope": payload.scope or "全站",
        "status": payload.status or "active",
    }

    template = PriceTemplate(
        operator_id=operator_id,
        name=name,
        rules_json=json.dumps(rules, ensure_ascii=False),
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return {"code": 200, "message": "计费模板创建成功", "data": serialize_price_template(template)}


@api_router.put("/operator/billing/templates/{template_id}", tags=["operator"])
def update_operator_billing_template(
    template_id: int,
    payload: TemplatePayload,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator_id = resolve_operator_id(db, context)
    template = (
        db.query(PriceTemplate)
        .options(noload("*"))
        .filter(PriceTemplate.id == template_id, PriceTemplate.operator_id == operator_id, PriceTemplate.is_deleted.is_(False))
        .first()
    )
    if not template:
        return {"code": 404, "message": "计费模板不存在"}

    name = payload.name.strip()
    if not name:
        return {"code": 400, "message": "请填写模板名称"}

    rules = {
        "peak_price": float(payload.peak_price or 1.68),
        "flat_price": float(payload.flat_price or 1.18),
        "valley_price": float(payload.valley_price or 0.68),
        "service_price": float(payload.service_price or 0.72),
        "scope": payload.scope or "全站",
        "status": payload.status or "active",
    }
    template.name = name
    template.rules_json = json.dumps(rules, ensure_ascii=False)
    db.commit()
    db.refresh(template)
    return {"code": 200, "message": "计费模板更新成功", "data": serialize_price_template(template)}


@api_router.delete("/operator/billing/templates/{template_id}", tags=["operator"])
def delete_operator_billing_template(
    template_id: int,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator_id = resolve_operator_id(db, context)
    template = (
        db.query(PriceTemplate)
        .options(noload("*"))
        .filter(PriceTemplate.id == template_id, PriceTemplate.operator_id == operator_id, PriceTemplate.is_deleted.is_(False))
        .first()
    )
    if not template:
        return {"code": 404, "message": "计费模板不存在"}

    stations_using = (
        db.query(func.count(Station.id))
        .filter(Station.template_id == template_id, Station.is_deleted.is_(False))
        .scalar()
        or 0
    )
    if stations_using > 0:
        return {"code": 400, "message": f"该模板已被 {stations_using} 个电站使用，请先解绑后再删除"}

    template.is_deleted = True
    db.commit()
    return {"code": 200, "message": "计费模板已删除"}


@api_router.get("/operator/orders/start-options", tags=["orders", "operator"])
async def get_operator_order_start_options(
    station_id: int | None = None,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator = get_operator_by_context(db, context)
    if not operator:
        return {"code": 404, "message": "运营商不存在"}

    demo_user = get_or_create_demo_user(db)
    stations = get_operator_station_page(
        db,
        operator_id=operator.id,
        page=1,
        page_size=100,
    )
    # 创建演示订单仅允许「已审核通过」电站，避免误选待审核/驳回站点
    station_items_all = stations["items"]
    station_items = [s for s in station_items_all if int(s.get("status", -1)) == 0]

    selected_station = None
    if station_id is not None:
        sid = int(station_id)
        selected_station = next((item for item in station_items if int(item["id"]) == sid), None)
    if selected_station is None and station_items:
        selected_station = next(
            (item for item in station_items if int(item.get("charger_count") or 0) > 0),
            station_items[0],
        )

    selected_station_id = selected_station["id"] if selected_station else None
    charger_rows = []
    if selected_station_id is not None and selected_station and int(selected_station.get("status", -1)) == 0:
        charger_rows = (
            db.query(
                Charger.id.label("id"),
                Charger.sn_code.label("sn_code"),
                Charger.name.label("charger_name"),
                Charger.type.label("type"),
                Charger.power_kw.label("power_kw"),
                Charger.status.label("status"),
                Charger.updated_at.label("updated_at"),
                Station.id.label("station_id"),
                Station.name.label("station_name"),
            )
            .join(Station, Charger.station_id == Station.id)
            .filter(
                Station.operator_id == operator.id,
                Station.id == selected_station_id,
                Station.status == 0,
                Station.is_deleted.is_(False),
                Charger.is_deleted.is_(False),
                Charger.status == 0,
            )
            .order_by(Charger.created_at.asc(), Charger.id.asc())
            .all()
        )

    return {
        "code": 200,
        "data": {
            "users": [
                {
                    "id": demo_user.id,
                    "nickname": demo_user.nickname or user_display_name(demo_user),
                    "phone": demo_user.phone,
                    "vin": demo_user.vin_code,
                    "is_default": True,
                }
            ],
            "stations": station_items,
            "stations_all_count": len(station_items_all),
            "chargers": [
                {
                    "id": row.id,
                    "sn_code": row.sn_code,
                    "charger_name": row.charger_name or f"{row.station_name[:10]}-{index:02d}号桩",
                    "type": row.type,
                    "power_kw": float(row.power_kw or 0),
                    "status": row.status,
                    "status_text": charger_status_text(row.status),
                    "station_id": row.station_id,
                    "station_name": row.station_name,
                    "updated_at": row.updated_at.strftime("%Y-%m-%d %H:%M:%S") if row.updated_at else "",
                }
                for index, row in enumerate(charger_rows, start=1)
            ],
            "default_user_id": demo_user.id,
            "default_station_id": selected_station_id,
        },
    }


@api_router.post("/operator/orders/demo-start", tags=["orders", "operator"])
def operator_demo_start_order(
    payload: DemoStartOrderPayload,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator = get_operator_by_context(db, context)
    if not operator:
        return {"code": 404, "message": "运营商不存在"}
    source_type = (payload.source_type or "manual_demo").strip() or "manual_demo"
    if source_type not in {"manual_demo", "qr_code", "mini_program"}:
        return {"code": 400, "message": "订单来源不合法"}

    base_station_query = (
        db.query(Station)
        .options(joinedload(Station.price_template), noload(Station.operator), noload(Station.chargers))
        .filter(Station.operator_id == operator.id, Station.is_deleted.is_(False))
    )
    if payload.station_id:
        station = base_station_query.filter(Station.id == payload.station_id).first()
    else:
        station = base_station_query.order_by(Station.status.asc(), Station.id.asc()).first()
    if not station:
        return {"code": 400, "message": "当前运营商暂无可用电站"}
    if station.status != 0:
        return {"code": 400, "message": "请选择已审核通过的电站发起充电"}

    if payload.charger_id:
        charger = (
            db.query(Charger)
            .options(noload("*"))
            .filter(
                Charger.id == payload.charger_id,
                Charger.station_id == station.id,
                Charger.is_deleted.is_(False),
            )
            .first()
        )
        if not charger:
            return {"code": 404, "message": "电桩不存在或不属于当前电站"}
        if charger.status != 0:
            return {"code": 400, "message": "当前电桩不是空闲状态，请选择其他电桩"}
        active_order_exists = (
            db.query(Order.id)
            .filter(Order.charger_id == charger.id, Order.status == 0)
            .first()
        )
        if active_order_exists:
            return {"code": 400, "message": "当前电桩已有进行中的订单，请选择其他电桩"}
    else:
        charger_candidates = (
            db.query(Charger)
            .options(noload("*"))
            .filter(
                Charger.station_id == station.id,
                Charger.is_deleted.is_(False),
                Charger.status == 0,
            )
            .order_by(Charger.created_at.asc(), Charger.id.asc())
            .all()
        )
        if not charger_candidates:
            return {"code": 400, "message": "当前电站暂无可用空闲电桩"}
        active_charger_ids = {
            item[0]
            for item in db.query(Order.charger_id)
            .filter(Order.status == 0, Order.charger_id.in_([item.id for item in charger_candidates]))
            .all()
        }
        charger = next((item for item in charger_candidates if item.id not in active_charger_ids), None)
        if charger is None:
            return {"code": 400, "message": "当前电站暂无可用空闲电桩"}

    user = (
        db.query(User).options(noload("*")).filter(User.id == payload.user_id).first()
        if payload.user_id
        else get_or_create_demo_user(db)
    )
    if not user:
        user = get_or_create_demo_user(db)

    start_time = datetime.now() - timedelta(minutes=random.randint(12, 45))
    order = Order(
        order_no=generate_demo_order_no(db),
        user_id=user.id,
        operator_id=operator.id,
        station_id=station.id,
        charger_id=charger.id,
        vin=user.vin_code or f"VIN{user.id:08d}",
        start_time=start_time,
        source_type=source_type,
        pay_status=0,
        status=0,
        abnormal_reason=None,
        settle_status=0,
    )
    order.charger = charger
    order.station = station
    db.add(order)
    recalculate_order_amounts(order, minimum_charge_kwh=Decimal(str(random.randint(8, 36))))
    charger.status = 1
    db.commit()
    user_phone = user.phone or ""
    user_nickname = (user.nickname or "").strip() or (f"用户{str(user_phone)[-4:]}" if user_phone else "")
    return {
        "code": 200,
        "message": "已创建实时订单",
        "data": {
            "id": order.id,
            "order_no": order.order_no,
            "status": order.status,
            "station_id": order.station_id,
            "charger_id": order.charger_id,
            "start_time": order.start_time.strftime("%Y-%m-%d %H:%M:%S") if order.start_time else "",
            "charge_amount": float(order.total_kwh or 0),
            "total_amount": float(order.total_fee or 0),
            "station_name": station.name or "",
            "charger_name": get_charger_name(charger),
            "user_nickname": user_nickname,
            "user_phone": user_phone,
            "source_type": source_type,
            "source_type_text": get_order_source_text(source_type),
        },
    }


@api_router.get("/operator/orders/history", tags=["orders", "operator"])
async def get_operator_history_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    keyword: str | None = None,
    status: int | None = None,
    station_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator_id = resolve_operator_id(db, context)
    return {
        "code": 200,
        "data": get_order_page(
            db,
            operator_id=operator_id,
            page=page,
            page_size=page_size,
            keyword=keyword,
            status=status,
            station_id=station_id,
            start_date=start_date,
            end_date=end_date,
            default_status=1,
        ),
    }


@api_router.get("/operator/orders/realtime", tags=["orders", "operator"])
async def get_operator_realtime_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    keyword: str | None = None,
    status: int | None = None,
    station_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator_id = resolve_operator_id(db, context)
    return {
        "code": 200,
        "data": get_order_page(
            db,
            operator_id=operator_id,
            page=page,
            page_size=page_size,
            keyword=keyword,
            status=status,
            station_id=station_id,
            start_date=start_date,
            end_date=end_date,
            default_status=0,
        ),
    }


@api_router.get("/operator/orders/abnormal", tags=["orders", "operator"])
async def get_operator_abnormal_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    keyword: str | None = None,
    status: int | None = None,
    station_id: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    abnormal_reason: str | None = None,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator_id = resolve_operator_id(db, context)
    return {
        "code": 200,
        "data": get_order_page(
            db,
            operator_id=operator_id,
            page=page,
            page_size=page_size,
            keyword=keyword,
            status=status,
            station_id=station_id,
            start_date=start_date,
            end_date=end_date,
            abnormal_reason=abnormal_reason,
            default_status=2,
        ),
    }


@api_router.get("/operator/orders/{order_id}", tags=["orders", "operator"])
async def get_operator_order_detail(
    order_id: int,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator = get_operator_by_context(db, context)
    if not operator:
        return {"code": 404, "message": "当前运营商未找到，请先入驻"}
    order_data = get_order_detail_data(db, order_id, operator_id=operator.id)
    if not order_data:
        return {"code": 404, "message": "订单不存在或无权限访问"}
    return {"code": 200, "data": order_data}


@api_router.post("/operator/orders/{order_id}/finish", tags=["orders", "operator"])
def operator_finish_order(
    order_id: int,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator_id = resolve_operator_id(db, context)
    result = finish_order(db, order_id, operator_id=operator_id)
    if not result:
        return {"code": 400, "message": "订单不存在、无权限或当前非充电中状态"}
    order = result.order
    return {
        "code": 200,
        "message": "订单已完成并转入历史订单，电桩已恢复空闲，钱包已扣费入账",
        "data": {
            "id": order.id,
            "order_no": order.order_no,
            "status": order.status,
            "pay_status": order.pay_status,
            "settle_status": order.settle_status,
            "total_fee": float(order.total_fee or 0),
            "wallet_transaction_id": result.wallet_transaction_id,
            "wallet_balance_after": result.wallet_balance_after,
        },
    }


@api_router.post("/operator/orders/{order_id}/force-stop", tags=["orders", "operator"])
def operator_force_stop_order(
    order_id: int,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator_id = resolve_operator_id(db, context)
    result = force_stop_order(db, order_id, operator_id=operator_id)
    if not result:
        return {"code": 400, "message": "订单不存在、无权限或当前非充电中状态"}
    order = result.order
    return {
        "code": 200,
        "message": "订单已强制停止",
        "data": {
            "id": order.id,
            "order_no": order.order_no,
            "status": order.status,
        },
    }


@api_router.post("/operator/orders/{order_id}/mark-abnormal", tags=["orders", "operator"])
def operator_mark_order_abnormal(
    order_id: int,
    payload: OrderActionSchema,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator_id = resolve_operator_id(db, context)
    order = mark_order_abnormal(db, order_id, payload.abnormal_reason, operator_id=operator_id)
    if not order:
        return {"code": 400, "message": "订单不存在、无权限或当前非充电中状态"}
    return {
        "code": 200,
        "message": "订单已标记异常并转入异常订单",
        "data": {
            "id": order.id,
            "order_no": order.order_no,
            "status": order.status,
            "abnormal_reason": order.abnormal_reason,
        },
    }


@api_router.get("/finance/cards", tags=["finance"])
async def get_operator_bank_cards(
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator_id = resolve_operator_id(db, context)
    operator = get_operator_basic_info(db, operator_id)
    if not operator:
        return {"code": 404, "message": "运营商不存在"}

    cards = (
        db.query(OperatorBankCard)
        .filter(OperatorBankCard.operator_id == operator_id)
        .order_by(OperatorBankCard.is_default.desc(), OperatorBankCard.created_at.desc())
        .all()
    )

    audit_status, audit_status_text = resolve_bank_card_audit_status(cards)
    settlement_eligible, settlement_tip = resolve_settlement_qualification_from_flag(operator["is_verified"], cards)

    default_card_raw = next((card for card in cards if card.is_default and card.bind_status == 1), None)
    if default_card_raw is None:
        default_card_raw = next((card for card in cards if card.bind_status == 1), None)

    return {
        "code": 200,
        "data": {
            "operator_id": operator["id"],
            "operator_name": operator["name"],
            "operator_verified": operator["is_verified"],
            "audit_status": audit_status,
            "audit_status_text": audit_status_text,
            "cards": [serialize_bank_card(card) for card in cards],
            "default_card": serialize_bank_card(default_card_raw) if default_card_raw else None,
            "settlement_eligible": settlement_eligible,
            "settlement_tip": settlement_tip,
            "settlement_notice": "绑卡审核通过后才可启动 T+1 清分；如遇法定节假日，打款按清算规则顺延至下一工作日。",
        },
    }


@api_router.post("/finance/cards", tags=["finance"])
def submit_operator_bank_card(
    payload: BankCardSubmitPayload,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator_id = resolve_operator_id(db, context)
    operator = get_operator_basic_info(db, operator_id)
    if not operator:
        return {"code": 404, "message": "运营商不存在"}

    account_name = payload.account_name.strip()
    bank_name = payload.bank_name.strip()
    bank_account = payload.bank_account.replace(" ", "").strip()

    if not account_name or not bank_name or len(bank_account) < 8:
        return {"code": 400, "message": "请填写完整且有效的绑卡信息"}

    existing_cards = (
        db.query(OperatorBankCard)
        .filter(OperatorBankCard.operator_id == operator_id)
        .order_by(OperatorBankCard.created_at.desc())
        .all()
    )

    is_default = bool(payload.is_default or not existing_cards)
    if is_default:
        for card in existing_cards:
            card.is_default = False

    card = OperatorBankCard(
        operator_id=operator_id,
        account_name=account_name,
        bank_name=bank_name,
        bank_account=bank_account,
        is_default=is_default,
        bind_status=0,
    )

    db.add(card)
    db.commit()

    return {
        "code": 200,
        "message": "绑卡资料已提交，等待平台审核",
        "data": {
            "card": serialize_bank_card(card),
            "audit_status": "pending",
            "audit_status_text": "待审核",
        },
    }


@api_router.get("/finance/cards/audit-status", tags=["finance"])
async def get_operator_bank_card_audit_status(
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    operator_id = resolve_operator_id(db, context)
    operator = get_operator_basic_info(db, operator_id)
    if not operator:
        return {"code": 404, "message": "运营商不存在"}

    cards = (
        db.query(OperatorBankCard)
        .filter(OperatorBankCard.operator_id == operator_id)
        .order_by(OperatorBankCard.created_at.desc())
        .all()
    )
    audit_status, audit_status_text = resolve_bank_card_audit_status(cards)
    settlement_eligible, settlement_tip = resolve_settlement_qualification_from_flag(operator["is_verified"], cards)

    return {
        "code": 200,
        "data": {
            "audit_status": audit_status,
            "audit_status_text": audit_status_text,
            "operator_verified": operator["is_verified"],
            "settlement_eligible": settlement_eligible,
            "settlement_tip": settlement_tip,
        },
    }


@api_router.get("/finance/invoices", tags=["finance"])
async def get_invoices(
    status: int | None = None,
    keyword: str | None = None,
    context: RoleContext = Depends(get_role_context),
    db: Session = Depends(get_db),
):
    operator_id = resolve_operator_id(db, context) if context.role == "operator" else None
    query = (
        db.query(
            Invoice.id.label("id"),
            Invoice.user_id.label("user_id"),
            Invoice.operator_id.label("operator_id"),
            Invoice.order_id.label("order_id"),
            Invoice.invoice_title.label("invoice_title"),
            Invoice.amount.label("amount"),
            Invoice.email.label("email"),
            Invoice.status.label("status"),
            Invoice.file_url.label("file_url"),
            Invoice.remark.label("remark"),
            Invoice.created_at.label("created_at"),
            Invoice.uploaded_at.label("uploaded_at"),
            Invoice.updated_at.label("updated_at"),
            User.phone.label("user_phone"),
            Operator.name.label("operator_name"),
            Order.order_no.label("order_no"),
        )
        .select_from(Invoice)
        .outerjoin(User, Invoice.user_id == User.id)
        .outerjoin(Operator, Invoice.operator_id == Operator.id)
        .outerjoin(Order, Invoice.order_id == Order.id)
        .order_by(Invoice.created_at.desc())
    )

    if operator_id is not None:
        query = query.filter(Invoice.operator_id == operator_id)

    if status in (0, 1, 2):
        query = query.filter(Invoice.status == status)

    if keyword and keyword.strip():
        kw = f"%{keyword.strip()}%"
        query = query.filter(or_(User.phone.like(kw), Invoice.email.like(kw), Invoice.invoice_title.like(kw)))

    invoices = query.all()
    data = [
        serialize_invoice_row(
            inv,
            can_process=(context.role == "operator" and inv.operator_id == operator_id and inv.status == 0),
        )
        for inv in invoices
    ]

    return {
        "code": 200,
        "data": data,
        "summary": {
            "pending_count": sum(1 for item in data if item["status"] == 0),
            "issued_count": sum(1 for item in data if item["status"] == 1),
            "rejected_count": sum(1 for item in data if item["status"] == 2),
            "issued_amount": round(sum(item["amount"] for item in data if item["status"] == 1), 2),
        },
        "scope": context.role,
    }


@api_router.post("/finance/invoices/apply", tags=["finance"])
async def apply_invoice(payload: InvoiceApplySchema, db: Session = Depends(get_db)):
    operator = db.query(Operator).options(noload("*")).filter(Operator.id == payload.operator_id).first()
    if not operator:
        return {"code": 404, "message": "运营商不存在"}

    if payload.order_id:
        order = (
            db.query(Order)
            .options(noload("*"))
            .filter(Order.id == payload.order_id)
            .first()
        )
        if not order:
            return {"code": 404, "message": "订单不存在"}
        if order.operator_id != payload.operator_id:
            return {"code": 400, "message": "订单与运营商不匹配"}
        if order.status != 1 or order.pay_status != 1:
            return {"code": 400, "message": "仅已完成且已支付的订单可申请发票"}

    invoice = Invoice(
        user_id=payload.user_id,
        operator_id=payload.operator_id,
        order_id=payload.order_id,
        invoice_title=(payload.invoice_title or "个人")[:100],
        amount=Decimal(str(payload.amount)),
        email=payload.email,
        status=0,
        remark=payload.remark or None,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    return {
        "code": 200,
        "message": "发票申请已提交",
        "data": {"id": invoice.id},
    }


@api_router.get("/finance/invoices/{invoice_id}", tags=["finance"])
async def get_invoice_detail(
    invoice_id: int,
    context: RoleContext = Depends(get_role_context),
    db: Session = Depends(get_db),
):
    operator_id = resolve_operator_id(db, context) if context.role == "operator" else None
    inv = (
        db.query(Invoice)
        .options(joinedload(Invoice.user), joinedload(Invoice.operator), joinedload(Invoice.related_order))
        .filter(Invoice.id == invoice_id)
        .first()
    )
    if not inv:
        return {"code": 404, "message": "发票申请不存在"}

    if operator_id is not None and inv.operator_id != operator_id:
        return {"code": 403, "message": "无权限查看该发票"}

    return {
        "code": 200,
        "data": serialize_invoice_record(
            inv,
            can_process=(operator_id is not None and inv.operator_id == operator_id and inv.status == 0),
        ),
    }


@api_router.post("/finance/invoices/{invoice_id}/process", tags=["finance"])
def process_invoice(
    invoice_id: int,
    payload: InvoiceProcessSchema,
    context: RoleContext = Depends(require_operator_context),
    db: Session = Depends(get_db),
):
    action = (payload.action or "").strip().lower()
    if action not in {"approve", "reject"}:
        return {"code": 400, "message": "不支持的处理动作"}

    operator_id = resolve_operator_id(db, context)
    invoice = (
        db.query(Invoice)
        .options(noload("*"))
        .filter(Invoice.id == invoice_id, Invoice.operator_id == operator_id)
        .first()
    )
    if not invoice:
        return {"code": 404, "message": "发票申请不存在或无权限处理"}

    if invoice.status != 0:
        return {"code": 400, "message": "该发票申请已处理，请勿重复操作"}

    now = datetime.now()
    if action == "approve":
        file_url = (payload.file_url or "").strip()
        if not file_url:
            return {"code": 400, "message": "请上传发票文件后再提交"}
        invoice.status = 1
        invoice.file_url = file_url
        invoice.uploaded_at = now
        invoice.remark = payload.remark or "运营商已开票"
        notify_status = "已开票"
    else:
        invoice.status = 2
        invoice.remark = payload.remark or "运营商驳回"
        notify_status = "已驳回"

    db.commit()

    try:
        send_invoice_email(
            to_email=invoice.email,
            invoice_no=f"INV{invoice.created_at.strftime('%Y%m%d')}{str(invoice.id).zfill(4)}",
            status=notify_status,
            operator_name=f"运营商#{invoice.operator_id}",
            amount=float(invoice.amount or 0),
            file_url=invoice.file_url,
            remark=invoice.remark,
        )
    except Exception:
        logger.info("invoice notification skipped", extra={"invoice_id": invoice.id})

    return {
        "code": 200,
        "message": f"发票申请处理成功（{notify_status}），已触发邮件通知",
        "data": {
            "id": invoice.id,
            "status": invoice.status,
            "status_text": notify_status,
            "file_url": invoice.file_url,
            "remark": invoice.remark,
            "uploaded_at": invoice.uploaded_at.strftime("%Y-%m-%d %H:%M:%S") if invoice.uploaded_at else None,
        },
    }


@api_router.get("/admin/finance/settlements", tags=["admin"])
async def admin_get_settlements(db: Session = Depends(get_db)):
    records = (
        db.query(
            OperatorSettlementRecord.id.label("id"),
            OperatorSettlementRecord.settle_date.label("settle_date"),
            OperatorSettlementRecord.operator_id.label("operator_id"),
            OperatorSettlementRecord.order_count.label("order_count"),
            OperatorSettlementRecord.total_amount.label("total_amount"),
            OperatorSettlementRecord.platform_rate.label("platform_rate"),
            OperatorSettlementRecord.platform_fee.label("platform_fee"),
            OperatorSettlementRecord.settle_amount.label("settle_amount"),
            OperatorSettlementRecord.status.label("status"),
            OperatorSettlementRecord.hold_reason.label("hold_reason"),
            OperatorSettlementRecord.created_at.label("created_at"),
            OperatorSettlementRecord.updated_at.label("updated_at"),
            Operator.name.label("operator_name"),
        )
        .select_from(OperatorSettlementRecord)
        .outerjoin(Operator, OperatorSettlementRecord.operator_id == Operator.id)
        .order_by(OperatorSettlementRecord.settle_date.desc(), OperatorSettlementRecord.operator_id.asc())
        .all()
    )

    if not records:
        legacy = db.query(SettlementRecord).order_by(SettlementRecord.settle_date.desc()).all()
        return {
            "code": 200,
            "data": [
                {
                    "id": r.id,
                    "settle_date": str(r.settle_date),
                    "order_count": r.order_count,
                    "total_amount": float(r.total_amount),
                    "platform_fee": float(r.platform_fee),
                    "settle_amount": float(r.settle_amount),
                    "status": r.status,
                    "status_text": SETTLEMENT_STATUS_TEXT.get(r.status, "未知"),
                    "operator_count": None,
                    "ready_count": None,
                    "hold_count": None,
                }
                for r in legacy
            ],
            "operator_records": [],
        }

    operator_data = [serialize_operator_settlement_row(r) for r in records]
    daily_map: dict[str, dict] = {}
    for item in operator_data:
        day_key = item["settle_date"]
        if day_key not in daily_map:
            daily_map[day_key] = {
                "settle_date": day_key,
                "order_count": 0,
                "total_amount": 0.0,
                "platform_fee": 0.0,
                "settle_amount": 0.0,
                "operator_count": 0,
                "ready_count": 0,
                "hold_count": 0,
                "status": 0,
                "status_text": "待打款",
            }
        day = daily_map[day_key]
        day["order_count"] += item["order_count"]
        day["total_amount"] += item["total_amount"]
        day["platform_fee"] += item["platform_fee"]
        day["settle_amount"] += item["settle_amount"]
        day["operator_count"] += 1
        if item["status"] == 2:
            day["hold_count"] += 1
        else:
            day["ready_count"] += 1

    data = sorted(daily_map.values(), key=lambda row: row["settle_date"], reverse=True)
    for row in data:
        row["total_amount"] = round(row["total_amount"], 2)
        row["platform_fee"] = round(row["platform_fee"], 2)
        row["settle_amount"] = round(row["settle_amount"], 2)
        if row["hold_count"] > 0:
            row["status"] = 2
            row["status_text"] = "部分挂起待补资料"
        else:
            row["status"] = 0
            row["status_text"] = "待打款"

    return {"code": 200, "data": data, "operator_records": operator_data}


@api_router.post("/admin/finance/settle", tags=["admin"])
async def admin_trigger_settle(payload: dict, db: Session = Depends(get_db)):
    """管理员手动触发某日清分。"""
    target_date_str = payload.get("date")
    if target_date_str:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
    else:
        target_date = datetime.now().date() - timedelta(days=1)

    try:
        detail = settle_t_plus_1_by_operator(
            target_date,
            db=db,
            platform_rate_percent=system_param_store.get("settlement_platform_rate", 10),
        )
        if detail["processed_order_count"] == 0:
            return {
                "code": 200,
                "message": f"{target_date} 没有可清分订单，或该日运营商批次已全部生成。",
                "processed": 0,
                "operator_count": 0,
                "data": detail,
            }

        return {
            "code": 200,
            "message": (
                f"清分成功：处理订单 {detail['processed_order_count']} 笔，"
                f"覆盖运营商 {detail['processed_operator_count']} 个。"
            ),
            "processed": detail["processed_order_count"],
            "operator_count": detail["processed_operator_count"],
            "skipped_operator_count": detail["skipped_operator_count"],
            "data": detail,
        }
    except Exception as e:
        return {"code": 500, "message": friendly_db_error_message(e), "data": None}


@api_router.get("/admin/audit/stations", tags=["admin"])
async def get_station_audits(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    keyword: str | None = None,
    status: int | None = None,
    _context: RoleContext = Depends(require_admin_context),
    db: Session = Depends(get_db),
):
    return {
        "code": 200,
        "data": get_admin_station_audit_page(
            db,
            page=page,
            page_size=page_size,
            keyword=keyword,
            status=status,
        ),
    }


@api_router.get("/admin/audit/operator-applications", tags=["admin"])
async def get_operator_audit_applications(
    _context: RoleContext = Depends(require_admin_context),
    db: Session = Depends(get_db),
):
    return {"code": 200, "data": {"records": list_operator_audit_applications(db)}}


@api_router.post("/admin/audit/operator-applications", tags=["admin"])
async def create_operator_admission_audit(
    payload: OperatorAdmissionAuditCreatePayload,
    _context: RoleContext = Depends(require_admin_context),
    db: Session = Depends(get_db),
):
    result = create_operator_audit_application(db, data=payload.model_dump())
    if result.get("error") == "duplicate":
        return {"code": 409, "message": result.get("message", "申请编号已存在"), "data": None}
    if result.get("error"):
        return {"code": 400, "message": result.get("message", "无效请求"), "data": None}
    return {"code": 200, "message": "申请已入库", "data": {"record": result["record"]}}


@api_router.post("/admin/audit/operator-applications/{application_id}/process", tags=["admin"])
async def process_operator_admission_audit(
    application_id: int,
    payload: OperatorAdmissionAuditProcessPayload,
    _context: RoleContext = Depends(require_admin_context),
    db: Session = Depends(get_db),
):
    import logging
    logger = logging.getLogger(__name__)
    try:
        result = submit_operator_audit_application(
            db,
            application_id=application_id,
            action=payload.action,
            remark=payload.remark or "",
        )
    except Exception as exc:
        logger.exception("运营商审核处理异常")
        db.rollback()
        return {"code": 500, "message": f"审核处理异常: {exc}", "data": None}
    if result is None:
        return {"code": 404, "message": "申请不存在", "data": None}
    if result.get("error"):
        return {"code": 400, "message": result.get("message", "无法处理"), "data": None}
    return {"code": 200, "message": "审核已保存", "data": result.get("record")}


@api_router.get("/admin/stations/options", tags=["admin"])
async def get_admin_station_options(
    keyword: str | None = None,
    _context: RoleContext = Depends(require_admin_context),
    db: Session = Depends(get_db),
):
    query = (
        db.query(
            Station.id.label("id"),
            Station.name.label("station_name"),
        )
        .filter(Station.is_deleted.is_(False))
        .order_by(Station.updated_at.desc(), Station.id.desc())
    )

    if keyword and keyword.strip():
        query = query.filter(Station.name.like(f"%{keyword.strip()}%"))

    return {
        "code": 200,
        "data": [{"id": row.id, "station_name": row.station_name} for row in query.all()],
    }


@api_router.get("/admin/settings/permissions", tags=["admin"])
async def get_admin_permission_settings(_context: RoleContext = Depends(require_admin_context)):
    return {"code": 200, "data": {"modules": permission_settings_store}}


@api_router.put("/admin/settings/permissions", tags=["admin"])
async def update_admin_permission_settings(
    payload: PermissionSettingsPayload,
    _context: RoleContext = Depends(require_admin_context),
):
    permission_settings_store.clear()
    permission_settings_store.extend(payload.modules)
    return {"code": 200, "message": "权限配置已保存", "data": {"modules": permission_settings_store}}


@api_router.get("/admin/settings/params", tags=["admin"])
async def get_admin_system_params(_context: RoleContext = Depends(require_admin_context)):
    return {"code": 200, "data": system_param_store}


@api_router.put("/admin/settings/params", tags=["admin"])
async def update_admin_system_params(
    payload: SystemParamsPayload,
    _context: RoleContext = Depends(require_admin_context),
):
    system_param_store.update(payload.model_dump())
    return {"code": 200, "message": "系统参数已保存", "data": system_param_store}


@api_router.post("/admin/audit/stations/{station_id}/process", tags=["admin"])
async def process_station_audit(
    station_id: int,
    payload: StationAuditProcessPayload,
    _context: RoleContext = Depends(require_admin_context),
    db: Session = Depends(get_db),
):
    action = (payload.action or "").strip().lower()
    remark = (payload.remark or "").strip()

    station = db.query(Station).options(noload("*")).filter(Station.id == station_id).first()
    if not station:
        return {"code": 404, "message": "站点不存在"}

    if int(station.status) != 3:
        return {"code": 400, "message": "该电站不在待审核状态，无法重复审核"}

    if action == "approve":
        station.status = 0
        station.visibility = "public"
        station.audit_remark = remark or "审核通过，可继续配置电桩并绑定模板"
    elif action == "reject":
        if not remark:
            return {"code": 400, "message": "驳回时请填写原因"}
        station.status = 4
        station.visibility = "private"
        station.audit_remark = remark
    else:
        return {"code": 400, "message": "action 仅支持 approve/reject"}

    db.commit()
    return {
        "code": 200,
        "message": "电站审核处理成功",
        "data": {
            "id": station.id,
            "status": station.status,
            "status_text": station_status_text(station.status),
            "visibility": station.visibility,
            "visibility_text": visibility_text(station.visibility),
            "audit_remark": station.audit_remark,
        },
    }
