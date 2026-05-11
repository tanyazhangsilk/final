from __future__ import annotations

import random
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.exc import OperationalError, ProgrammingError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload, noload

from app.db.database import get_db
from app.models.models import (
    Charger,
    Invoice,
    Operator,
    OperatorBankCard,
    OperatorSettlementRecord,
    Order,
    PriceTemplate,
    Station,
    User,
)
from app.services.notification_service import send_invoice_email
from app.services.order_service import recalculate_order_amounts, serialize_order
from app.services.settlement_service import settle_t_plus_1_by_operator
from app.services.station_service import dump_site_photos, release_charger_sn_if_soft_deleted, serialize_charger, serialize_station
from app.services.wallet_flow_service import create_wallet_consume_record


demo_api_router = APIRouter(tags=["demo"])

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

DB_CONNECTION_ERROR_MESSAGE = (
    "数据库连接失败，请确认 MySQL 已启动，并检查 .env 中 "
    "MYSQL_HOST、MYSQL_PORT、MYSQL_USER、MYSQL_PASSWORD、MYSQL_DB 配置。"
)
DB_SCHEMA_ERROR_MESSAGE = "数据库表结构未同步，请先执行 python scripts/patch_demo_schema.py 后再重试。"


class DemoOrderStartPayload(BaseModel):
    user_id: int
    charger_id: int | None = None
    sn_code: str | None = None
    source_type: str = "manual_demo"


class DemoOrderAbnormalPayload(BaseModel):
    reason: str


class DemoStationApplyPayload(BaseModel):
    station_name: str
    province: str = "广东省"
    city: str = "深圳市"
    district: str = "南山区"
    address: str
    longitude: float = 113.9434
    latitude: float = 22.5405
    contact_name: str = "演示联系人"
    contact_phone: str = "13800138000"
    operation_hours: str = "00:00-24:00"
    parking_fee_desc: str = ""
    station_remark: str = ""
    planned_charger_count: int = 4
    total_power_kw: float = 240
    cover_image: str = ""
    site_photos: list[str] | str | None = None
    qualification_remark: str = ""
    operator_id: int | None = None


class DemoStationAuditPayload(BaseModel):
    audit_remark: str = ""


class DemoStationChargerPayload(BaseModel):
    sn_code: str
    charger_name: str = ""
    type: str = "DC"
    power_kw: float = 120
    status: int = 0


class DemoBindTemplatePayload(BaseModel):
    template_id: int


class DemoSettlementRunPayload(BaseModel):
    date: date


class DemoInvoiceApplyPayload(BaseModel):
    user_id: int
    order_id: int
    invoice_title: str = "个人"
    email: str


class DemoInvoiceProcessPayload(BaseModel):
    action: str
    file_url: str = ""
    remark: str = ""


def ok(data: Any = None, message: str = "success", **extra: Any) -> dict[str, Any]:
    response = {"code": 200, "message": message, "data": data}
    response.update(extra)
    return response


def fail(message: str, code: int = 400, data: Any = None, **extra: Any) -> dict[str, Any]:
    response = {"code": code, "message": message, "data": data}
    response.update(extra)
    return response


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


def _parse_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else None


def _to_money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _commit(db: Session) -> None:
    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise RuntimeError(f"数据库提交失败：{exc}") from exc


def _first_operator(db: Session) -> Operator | None:
    return db.query(Operator).options(noload("*")).order_by(Operator.id.asc()).first()


def _resolve_operator(
    db: Session,
    *,
    operator_id: int | None = None,
    header_operator_id: str | None = None,
) -> Operator | None:
    resolved_id = operator_id or _parse_int(header_operator_id)
    if resolved_id is not None:
        operator = db.query(Operator).options(noload("*")).filter(Operator.id == resolved_id).first()
        if operator:
            return operator
    return _first_operator(db)


def _load_station(db: Session, station_id: int) -> Station | None:
    return (
        db.query(Station)
        .options(
            joinedload(Station.operator),
            joinedload(Station.price_template),
            joinedload(Station.chargers),
        )
        .filter(Station.id == station_id, Station.is_deleted.is_(False))
        .first()
    )


def _load_order(db: Session, order_id: int) -> Order | None:
    return (
        db.query(Order)
        .options(
            joinedload(Order.user),
            joinedload(Order.operator),
            joinedload(Order.station).joinedload(Station.price_template),
            joinedload(Order.charger).joinedload(Charger.station),
        )
        .filter(Order.id == order_id)
        .first()
    )


def _load_invoice(db: Session, invoice_id: int) -> Invoice | None:
    return (
        db.query(Invoice)
        .options(
            joinedload(Invoice.user),
            joinedload(Invoice.operator),
            joinedload(Invoice.related_order),
        )
        .filter(Invoice.id == invoice_id)
        .first()
    )


def _generate_demo_order_no(db: Session) -> str:
    while True:
        order_no = f"DEMO{datetime.now():%Y%m%d%H%M%S}{random.randint(1000, 9999)}"
        exists = db.query(Order.id).filter(Order.order_no == order_no).first()
        if not exists:
            return order_no


def _serialize_settlement(record: OperatorSettlementRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "settle_date": str(record.settle_date),
        "operator_id": record.operator_id,
        "operator_name": record.operator.name if record.operator else "",
        "order_count": int(record.order_count or 0),
        "total_amount": float(record.total_amount or 0),
        "platform_rate": float(record.platform_rate or 0),
        "platform_fee": float(record.platform_fee or 0),
        "settle_amount": float(record.settle_amount or 0),
        "status": record.status,
        "status_text": SETTLEMENT_STATUS_TEXT.get(record.status, "未知状态"),
        "can_payout": record.status != 2,
        "hold_reason": record.hold_reason,
        "created_at": record.created_at.strftime("%Y-%m-%d %H:%M:%S") if record.created_at else "",
        "updated_at": record.updated_at.strftime("%Y-%m-%d %H:%M:%S") if record.updated_at else "",
    }


def _serialize_invoice(invoice: Invoice) -> dict[str, Any]:
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
    }


@demo_api_router.get("/demo/flow/health")
async def demo_flow_health(db: Session = Depends(get_db)) -> dict[str, Any]:
    bank_card_ready = False
    operator_row = (
        db.query(Operator.id, Operator.is_verified)
        .order_by(Operator.id.asc())
        .first()
    )
    if operator_row:
        card = (
            db.query(OperatorBankCard.id)
            .filter(
                OperatorBankCard.operator_id == operator_row.id,
                OperatorBankCard.is_default.is_(True),
                OperatorBankCard.bind_status == 1,
            )
            .first()
        )
        bank_card_ready = bool(operator_row.is_verified and card)

    unsettled_order_count = (
        db.query(Order.id)
        .filter(Order.status == 1, Order.pay_status == 1, Order.settle_status == 0)
        .count()
    )
    return ok(
        {
            "user_count": db.query(User.id).count(),
            "operator_count": db.query(Operator.id).count(),
            "station_count": db.query(Station.id).filter(Station.is_deleted.is_(False)).count(),
            "charger_count": db.query(Charger.id).filter(Charger.is_deleted.is_(False)).count(),
            "order_count": db.query(Order.id).count(),
            "unsettled_order_count": unsettled_order_count,
            "bank_card_ready": bank_card_ready,
        }
    )


@demo_api_router.post("/demo/orders/start")
async def demo_start_order(payload: DemoOrderStartPayload, db: Session = Depends(get_db)) -> dict[str, Any]:
    if not payload.charger_id and not (payload.sn_code or "").strip():
        return fail("charger_id 与 sn_code 至少传一个")

    user = db.query(User).options(noload("*")).filter(User.id == payload.user_id).first()
    if not user:
        return fail("用户不存在", code=404)

    charger_query = (
        db.query(Charger)
        .options(joinedload(Charger.station).joinedload(Station.price_template))
        .filter(Charger.is_deleted.is_(False))
    )
    if payload.charger_id:
        charger_query = charger_query.filter(Charger.id == payload.charger_id)
    else:
        charger_query = charger_query.filter(Charger.sn_code == payload.sn_code.strip().upper())
    charger = charger_query.first()
    if not charger:
        return fail("电桩不存在", code=404)

    if charger.status != 0:
        return fail("当前电桩不是空闲状态，无法发起演示订单")
    if not charger.station:
        return fail("电桩未绑定电站")
    if charger.station.status != 0:
        return fail("电站未审核通过，无法发起演示订单")

    active_order = (
        db.query(Order.id)
        .filter(Order.charger_id == charger.id, Order.status == 0)
        .first()
    )
    if active_order:
        return fail("当前电桩已有进行中的订单")

    source_type = (payload.source_type or "manual_demo").strip() or "manual_demo"
    if source_type not in {"manual_demo", "mini_program", "qr_code"}:
        return fail("source_type 不合法")

    order = Order(
        order_no=_generate_demo_order_no(db),
        user_id=user.id,
        operator_id=charger.station.operator_id,
        station_id=charger.station_id,
        charger_id=charger.id,
        vin=user.vin_code or f"VIN{user.id:08d}",
        start_time=datetime.now(),
        source_type=source_type,
        pay_status=0,
        status=0,
        settle_status=0,
    )
    db.add(order)
    recalculate_order_amounts(order, minimum_charge_kwh=Decimal("1.20"))
    charger.status = 1

    try:
        _commit(db)
    except RuntimeError as exc:
        return fail(str(exc), code=500)

    saved_order = _load_order(db, order.id)
    return ok(
        {
            "id": saved_order.id,
            "order_no": saved_order.order_no,
            "status": saved_order.status,
            "charger_id": saved_order.charger_id,
            "station_id": saved_order.station_id,
        },
        message="演示订单创建成功",
    )


@demo_api_router.post("/demo/orders/{order_id}/finish")
async def demo_finish_order(order_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    order = _load_order(db, order_id)
    if not order:
        return fail("订单不存在", code=404)
    if order.status != 0:
        return fail("只有进行中的订单才能结束")

    now = datetime.now()
    order.end_time = now
    recalculate_order_amounts(order, now=now)
    order.status = 1
    order.pay_status = 1
    order.settle_status = 0

    if order.charger:
        order.charger.status = 0

    create_wallet_consume_record(
        db, order.user_id, order.id, _to_money(order.total_fee), order_no=order.order_no
    )

    try:
        _commit(db)
    except RuntimeError as exc:
        return fail(str(exc), code=500)

    return ok(
        {
            "id": order.id,
            "order_no": order.order_no,
            "status": order.status,
            "pay_status": order.pay_status,
            "settle_status": order.settle_status,
        },
        message="订单已结束并完成计费",
    )


@demo_api_router.post("/demo/orders/{order_id}/abnormal")
async def demo_abnormal_order(
    order_id: int,
    payload: DemoOrderAbnormalPayload,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    order = _load_order(db, order_id)
    if not order:
        return fail("订单不存在", code=404)
    if order.status != 0:
        return fail("只有进行中的订单才能标记异常")

    now = datetime.now()
    order.end_time = now
    recalculate_order_amounts(order, now=now)
    order.status = 2
    order.abnormal_reason = (payload.reason or "").strip() or "设备连接中断"

    if order.charger:
        order.charger.status = 2

    try:
        _commit(db)
    except RuntimeError as exc:
        return fail(str(exc), code=500)

    return ok(
        {
            "id": order.id,
            "order_no": order.order_no,
            "status": order.status,
            "abnormal_reason": order.abnormal_reason,
        },
        message="订单已标记为异常",
    )


@demo_api_router.get("/demo/orders/{order_id}")
async def demo_order_detail(order_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    order = _load_order(db, order_id)
    if not order:
        return fail("订单不存在", code=404)
    return ok(serialize_order(order))


@demo_api_router.post("/demo/stations/apply")
async def demo_apply_station(
    payload: DemoStationApplyPayload,
    db: Session = Depends(get_db),
    x_operator_id: str | None = Header(default=None, alias="x-operator-id"),
) -> dict[str, Any]:
    operator = _resolve_operator(
        db,
        operator_id=payload.operator_id,
        header_operator_id=x_operator_id,
    )
    if not operator:
        return fail("运营商不存在，请先初始化演示数据", code=404)

    station_name = payload.station_name.strip()
    if not station_name:
        return fail("请填写电站名称")

    station = Station(
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
        audit_remark="待管理员审核",
        status=3,
        visibility="private",
    )
    db.add(station)

    try:
        _commit(db)
    except RuntimeError as exc:
        return fail(str(exc), code=500)

    saved_station = _load_station(db, station.id)
    return ok(serialize_station(saved_station), message="电站申请已提交，当前状态为待审核")


@demo_api_router.post("/demo/stations/{station_id}/approve")
async def demo_approve_station(
    station_id: int,
    payload: DemoStationAuditPayload,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    station = _load_station(db, station_id)
    if not station:
        return fail("电站不存在", code=404)
    if station.status not in {3, 4}:
        return fail("只有待审核或已驳回的电站才能审核通过")

    station.status = 0
    station.visibility = "public"
    station.audit_remark = (payload.audit_remark or "").strip() or "审核通过，可公开展示并继续配置电桩"

    try:
        _commit(db)
    except RuntimeError as exc:
        return fail(str(exc), code=500)

    return ok({"id": station.id, "status": station.status, "visibility": station.visibility}, message="电站审核通过")


@demo_api_router.post("/demo/stations/{station_id}/reject")
async def demo_reject_station(
    station_id: int,
    payload: DemoStationAuditPayload,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    station = _load_station(db, station_id)
    if not station:
        return fail("电站不存在", code=404)

    station.status = 4
    station.visibility = "private"
    station.audit_remark = (payload.audit_remark or "").strip() or "资料待补充，请修改后重新提交"

    try:
        _commit(db)
    except RuntimeError as exc:
        return fail(str(exc), code=500)

    return ok({"id": station.id, "status": station.status, "visibility": station.visibility}, message="电站已驳回")


@demo_api_router.post("/demo/stations/{station_id}/chargers")
async def demo_add_station_charger(
    station_id: int,
    payload: DemoStationChargerPayload,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    station = _load_station(db, station_id)
    if not station:
        return fail("电站不存在", code=404)
    if station.status != 0:
        return fail("只有已审核通过的电站才能添加电桩")

    sn_code = (payload.sn_code or "").strip().upper()
    if not sn_code:
        return fail("请输入电桩编号")
    sn_err = release_charger_sn_if_soft_deleted(db, sn_code)
    if sn_err:
        return fail(sn_err)

    charger_type = (payload.type or "").strip().upper()
    if charger_type not in {"AC", "DC"}:
        return fail("电桩类型仅支持 AC 或 DC")
    if int(payload.status) not in {0, 1, 2, 3}:
        return fail("电桩状态不合法")

    charger = Charger(
        station_id=station.id,
        sn_code=sn_code,
        name=(payload.charger_name or "").strip() or f"{station.name[:10]}-{sn_code[-4:]}号桩",
        type=charger_type,
        power_kw=Decimal(str(payload.power_kw)),
        status=int(payload.status),
    )
    db.add(charger)

    try:
        _commit(db)
    except RuntimeError as exc:
        return fail(str(exc), code=500)

    saved_station = _load_station(db, station.id)
    saved_charger = next((item for item in saved_station.chargers if item.id == charger.id), None)
    return ok(serialize_charger(saved_charger or charger), message="电桩新增成功")


@demo_api_router.post("/demo/stations/{station_id}/bind-template")
async def demo_bind_station_template(
    station_id: int,
    payload: DemoBindTemplatePayload,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    station = _load_station(db, station_id)
    if not station:
        return fail("电站不存在", code=404)
    if station.status != 0:
        return fail("只有已审核通过的电站才能绑定模板")

    template = (
        db.query(PriceTemplate)
        .filter(
            PriceTemplate.id == payload.template_id,
            PriceTemplate.operator_id == station.operator_id,
            PriceTemplate.is_deleted.is_(False),
        )
        .first()
    )
    if not template:
        return fail("电价模板不存在或不属于当前运营商", code=404)

    station.template_id = template.id

    try:
        _commit(db)
    except RuntimeError as exc:
        return fail(str(exc), code=500)

    return ok(
        {
            "id": station.id,
            "template_id": station.template_id,
            "price_template_name": template.name,
        },
        message="计费模板绑定成功",
    )


@demo_api_router.post("/demo/settlements/run")
async def demo_run_settlement(
    payload: DemoSettlementRunPayload,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        result = settle_t_plus_1_by_operator(payload.date, db=db)
    except Exception as exc:
        return fail(friendly_db_error_message(exc), code=500)

    operator_ids = [item.get("operator_id") for item in result.get("operator_results", []) if item.get("operator_id")]
    operator_map = (
        {item.id: item.name for item in db.query(Operator).filter(Operator.id.in_(operator_ids)).all()}
        if operator_ids
        else {}
    )

    operator_results = []
    for item in result.get("operator_results", []):
        operator_results.append(
            {
                **item,
                "operator_name": operator_map.get(item.get("operator_id"), f"运营商#{item.get('operator_id')}"),
            }
        )

    message = (
        "该日期暂无符合条件的已完成未清分订单。"
        if int(result.get("processed_order_count", 0) or 0) == 0
        else "T+1 清分执行完成"
    )
    return ok(
        {
            "settle_date": result.get("settle_date"),
            "processed_order_count": result.get("processed_order_count", 0),
            "processed_operator_count": result.get("processed_operator_count", 0),
            "skipped_operator_count": result.get("skipped_operator_count", 0),
            "operator_results": operator_results,
        },
        message=message,
    )


@demo_api_router.get("/demo/settlements")
async def demo_settlement_list(
    db: Session = Depends(get_db),
    x_role: str | None = Header(default=None, alias="x-role"),
    x_operator_id: str | None = Header(default=None, alias="x-operator-id"),
) -> dict[str, Any]:
    query = (
        db.query(OperatorSettlementRecord)
        .options(joinedload(OperatorSettlementRecord.operator))
        .order_by(OperatorSettlementRecord.settle_date.desc(), OperatorSettlementRecord.operator_id.asc())
    )

    if (x_role or "").strip().lower() == "operator":
        operator_id = _parse_int(x_operator_id)
        if operator_id is not None:
            query = query.filter(OperatorSettlementRecord.operator_id == operator_id)

    rows = query.all()
    return ok([_serialize_settlement(item) for item in rows])


@demo_api_router.post("/demo/invoices/apply")
async def demo_apply_invoice(
    payload: DemoInvoiceApplyPayload,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        return fail("用户不存在", code=404)

    order = _load_order(db, payload.order_id)
    if not order:
        return fail("订单不存在", code=404)
    if order.user_id != payload.user_id:
        return fail("订单与用户不匹配")
    if order.status != 1 or order.pay_status != 1:
        return fail("订单必须已完成且已支付后才能申请发票")

    existing = (
        db.query(Invoice)
        .filter(Invoice.order_id == order.id, Invoice.user_id == user.id)
        .order_by(Invoice.id.desc())
        .first()
    )
    if existing:
        existing.invoice_title = (payload.invoice_title or "个人").strip()[:100]
        existing.email = payload.email.strip()
        existing.amount = _to_money(order.total_fee)
        existing.status = 0
        existing.remark = "重复申请已重置为待开票"
        existing.file_url = None
        existing.uploaded_at = None
        invoice = existing
        message = "已更新原有发票申请并重置为待开票"
    else:
        invoice = Invoice(
            user_id=user.id,
            operator_id=order.operator_id,
            order_id=order.id,
            invoice_title=(payload.invoice_title or "个人").strip()[:100],
            amount=_to_money(order.total_fee),
            email=payload.email.strip(),
            status=0,
            remark="演示发票申请",
        )
        db.add(invoice)
        message = "发票申请已提交"

    try:
        _commit(db)
    except RuntimeError as exc:
        return fail(str(exc), code=500)

    return ok({"id": invoice.id, "status": invoice.status, "order_id": invoice.order_id}, message=message)


@demo_api_router.post("/demo/invoices/{invoice_id}/process")
async def demo_process_invoice(
    invoice_id: int,
    payload: DemoInvoiceProcessPayload,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    invoice = _load_invoice(db, invoice_id)
    if not invoice:
        return fail("发票申请不存在", code=404)

    action = (payload.action or "").strip().lower()
    if action in {"issue", "approve"}:
        invoice.status = 1
        invoice.file_url = (payload.file_url or "").strip() or f"https://example.com/invoices/demo-{invoice.id}.pdf"
        invoice.uploaded_at = datetime.now()
        invoice.remark = (payload.remark or "").strip() or "已开票"
        notify_status = "已开票"
        message = "发票已处理为已开票"
    elif action == "reject":
        invoice.status = 2
        invoice.remark = (payload.remark or "").strip() or "已驳回"
        notify_status = "已驳回"
        message = "发票申请已驳回"
    else:
        return fail("action 仅支持 issue/approve/reject")

    try:
        _commit(db)
    except RuntimeError as exc:
        return fail(str(exc), code=500)

    try:
        send_invoice_email(
            to_email=invoice.email,
            invoice_no=invoice.created_at.strftime("INV%Y%m%d") + str(invoice.id).zfill(4),
            status=notify_status,
            operator_name=invoice.operator.name if invoice.operator else f"运营商#{invoice.operator_id}",
            amount=float(invoice.amount or 0),
            file_url=invoice.file_url,
            remark=invoice.remark,
        )
    except Exception:
        pass

    return ok({"id": invoice.id, "status": invoice.status, "file_url": invoice.file_url}, message=message)


@demo_api_router.get("/demo/invoices")
async def demo_invoice_list(
    db: Session = Depends(get_db),
    x_role: str | None = Header(default=None, alias="x-role"),
    x_operator_id: str | None = Header(default=None, alias="x-operator-id"),
) -> dict[str, Any]:
    query = (
        db.query(Invoice)
        .options(
            joinedload(Invoice.user),
            joinedload(Invoice.operator),
            joinedload(Invoice.related_order),
        )
        .order_by(Invoice.created_at.desc(), Invoice.id.desc())
    )

    if (x_role or "").strip().lower() == "operator":
        operator_id = _parse_int(x_operator_id)
        if operator_id is not None:
            query = query.filter(Invoice.operator_id == operator_id)

    rows = query.all()
    return ok([_serialize_invoice(item) for item in rows])
