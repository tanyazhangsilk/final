"""
WeChat 小程序（C 端）聚合接口：路径与 E-mini-main 中 services/api 约定一致，
数据与演示订单 / 电站 / 钱包等业务表打通，不改变现有运营端 Vue 页面与路由。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload, noload

from app.db.database import get_db
from app.models.models import Charger, Coupon, Invoice, OperatorAuditApplication, Order, Station, User, UserCoupon
from app.services.order_service import recalculate_order_amounts, serialize_order
from app.services.station_service import (
    charger_status_text,
    compose_station_address,
    parse_price_template_rules,
    serialize_charger,
)
from app.services.wallet_flow_service import create_wallet_consume_record, create_wallet_recharge_record
from app.services.wallet_service import get_wallet_summary, get_wallet_transaction_list

from app.api.v1.demo_routes import (
    _commit,
    _generate_demo_order_no,
    _load_order,
    _serialize_invoice,
    fail,
    ok,
)

mini_api_router = APIRouter(tags=["mini"])

# 与 scripts/init_demo_data.py 中演示车主一致：小程序「邮箱登录」填 user@echarge.com 时映射到该账号
DEMO_DRIVER_PHONE = "13800138000"
DEMO_EMAIL_ALIASES: dict[str, str] = {
    "user@echarge.com": DEMO_DRIVER_PHONE,
}


def _ok_response(data: Any = None, message: str = "success") -> dict[str, Any]:
    return ok(data, message=message)


def _fail_response(message: str, code: int = 400) -> dict[str, Any]:
    return fail(message, code=code)


def _parse_user_id_header(x_mini_user_id: str | None) -> int | None:
    if not x_mini_user_id or not str(x_mini_user_id).strip():
        return None
    text = str(x_mini_user_id).strip()
    if text.isdigit():
        return int(text)
    return None


def _resolve_login_account(account: str) -> str:
    acc = (account or "").strip()
    if not acc:
        return acc
    lower = acc.lower()
    return DEMO_EMAIL_ALIASES.get(lower, acc)


class MiniLoginPayload(BaseModel):
    phone: str | None = None
    password: str = ""
    # 小程序登录页字段名
    account: str | None = None


class MiniOrderStartBody(BaseModel):
    sn_code: str | None = None
    pileId: str | None = None
    station_id: str | int | None = None


class MiniOrderEndBody(BaseModel):
    order_id: str | int


class MiniInvoiceApplyBody(BaseModel):
    order_id: str | int
    title: str = "个人"
    email: str
    note: str | None = None
    type: str | None = None


class MiniWalletRechargeBody(BaseModel):
    amount: float


def _charger_counts(station: Station) -> tuple[int, int, int, int]:
    chargers = [c for c in (station.chargers or []) if not c.is_deleted]
    total = len(chargers)
    available = sum(1 for c in chargers if c.status == 0)
    fast = sum(1 for c in chargers if (c.type or "").upper() == "DC")
    slow = sum(1 for c in chargers if (c.type or "").upper() == "AC")
    return total, available, fast, slow


def _serialize_station_list_item(station: Station) -> dict[str, Any]:
    rules = parse_price_template_rules(station.price_template)
    flat = float(rules.get("flat_price") or 0)
    total, available, fast_count, slow_count = _charger_counts(station)
    return {
        "id": station.id,
        "station_id": station.id,
        "station_name": station.name,
        "name": station.name,
        "operator_name": station.operator.name if station.operator else "",
        "operator": station.operator.name if station.operator else "",
        "address": compose_station_address(station),
        "detail_address": compose_station_address(station),
        "full_address": compose_station_address(station),
        "available_chargers": available,
        "available_count": available,
        "idle_piles": available,
        "total_chargers": total,
        "total_piles": total,
        "total": total,
        "current_price": flat,
        "fee_per_kwh": flat,
        "business_hours": station.operation_hours or "00:00-24:00",
        "businessHours": station.operation_hours or "00:00-24:00",
        "parking_tips": station.parking_fee_desc or "",
        "parkingTips": station.parking_fee_desc or "",
        "operation_hours": station.operation_hours or "",
        "fast_count": fast_count,
        "slow_count": slow_count,
        "distance_km": 0,
        "distance": 0,
        "status_text": "营业中" if station.status == 0 else "",
        "chargers": [serialize_charger(c) for c in (station.chargers or []) if not c.is_deleted],
    }



@mini_api_router.post("/auth/login")
async def mini_login(payload: MiniLoginPayload, db: Session = Depends(get_db)) -> dict[str, Any]:
    raw_account = (payload.phone or payload.account or "").strip()
    password = (payload.password or "").strip()
    if not raw_account or not password:
        return _fail_response("请输入账号和密码")

    account = _resolve_login_account(raw_account)
    user = db.query(User).options(noload("*")).filter(User.phone == account).first()
    if not user or user.password_hash != password:
        return _fail_response("账号或密码不正确", code=401)

    display_email = raw_account if "@" in raw_account else f"{user.phone}@mini.echarge"
    return _ok_response(
        {
            "id": user.id,
            "user_id": user.id,
            "nickname": user.nickname or f"用户{str(user.phone)[-4:]}",
            "phone": user.phone,
            "email": display_email,
            "role": user.role,
        },
        message="登录成功",
    )


@mini_api_router.get("/stations")
async def mini_station_list(db: Session = Depends(get_db)) -> dict[str, Any]:
    rows = (
        db.query(Station)
        .options(
            joinedload(Station.operator),
            joinedload(Station.price_template),
            joinedload(Station.chargers),
        )
        .filter(Station.is_deleted.is_(False), Station.status == 0, Station.visibility == "public")
        .order_by(Station.id.asc())
        .all()
    )
    return _ok_response([_serialize_station_list_item(s) for s in rows])


@mini_api_router.get("/stations/recommend")
async def mini_station_recommend(db: Session = Depends(get_db)) -> dict[str, Any]:
    rows = (
        db.query(Station)
        .options(
            joinedload(Station.operator),
            joinedload(Station.price_template),
            joinedload(Station.chargers),
        )
        .filter(Station.is_deleted.is_(False), Station.status == 0, Station.visibility == "public")
        .order_by(Station.id.asc())
        .limit(8)
        .all()
    )
    return _ok_response([_serialize_station_list_item(s) for s in rows])


@mini_api_router.get("/stations/{station_id}")
async def mini_station_detail(station_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    station = (
        db.query(Station)
        .options(
            joinedload(Station.operator),
            joinedload(Station.price_template),
            joinedload(Station.chargers),
        )
        .filter(Station.id == station_id, Station.is_deleted.is_(False))
        .first()
    )
    if not station:
        return _fail_response("电站不存在", code=404)
    if station.visibility != "public" or station.status != 0:
        return _fail_response("电站不可访问", code=404)
    return _ok_response(_serialize_station_list_item(station))


@mini_api_router.get("/chargers/by-sn")
async def mini_charger_by_sn(sn_code: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    code = (sn_code or "").strip().upper()
    if not code:
        return _fail_response("请提供 sn_code")

    charger = (
        db.query(Charger)
        .options(joinedload(Charger.station).joinedload(Station.operator))
        .filter(Charger.sn_code == code, Charger.is_deleted.is_(False))
        .first()
    )
    if not charger or not charger.station:
        return _fail_response("电桩不存在", code=404)

    st = charger.station
    available = charger.status == 0 and st.status == 0
    return _ok_response(
        {
            "charger": {
                "id": charger.id,
                "sn_code": charger.sn_code,
                "pile_no": charger.sn_code,
                "station_id": charger.station_id,
                "station_name": st.name,
                "status": charger.status,
                "status_text": charger_status_text(charger.status),
                "power_kw": float(charger.power_kw or 0),
                "type": charger.type,
                "available": available,
                "is_available": available,
            },
            "station": {"id": st.id, "station_name": st.name, "name": st.name},
        }
    )


@mini_api_router.post("/orders/start")
async def mini_order_start(
    payload: MiniOrderStartBody,
    db: Session = Depends(get_db),
    x_mini_user_id: str | None = Header(default=None, alias="X-Mini-User-Id"),
) -> dict[str, Any]:
    user_id = _parse_user_id_header(x_mini_user_id)
    if user_id is None:
        return fail("请先登录", code=401)

    sn = (payload.sn_code or payload.pileId or "").strip().upper()
    if not sn:
        return _fail_response("sn_code 与 pileId 至少传一个")

    user = db.query(User).options(noload("*")).filter(User.id == user_id).first()
    if not user:
        return _fail_response("用户不存在", code=404)

    charger = (
        db.query(Charger)
        .options(joinedload(Charger.station).joinedload(Station.price_template))
        .filter(Charger.is_deleted.is_(False), Charger.sn_code == sn)
        .first()
    )
    if not charger:
        return _fail_response("电桩不存在", code=404)
    if charger.status != 0:
        return _fail_response("当前电桩不是空闲状态，无法发起充电")
    if not charger.station:
        return _fail_response("电桩未绑定电站")
    if charger.station.status != 0:
        return _fail_response("电站未审核通过，无法发起充电")

    active = (
        db.query(Order.id).filter(Order.charger_id == charger.id, Order.status == 0).first()
    )
    if active:
        return _fail_response("当前电桩已有进行中的订单")

    # 检查余额：低于 5 元时不允许充电
    from app.services.wallet_flow_service import get_user_balance
    balance = get_user_balance(db, user.id)
    if balance < Decimal("5.00"):
        return _fail_response(f"钱包余额不足（当前 {float(balance):.2f} 元），请先充值", code=402)

    order = Order(
        order_no=_generate_demo_order_no(db),
        user_id=user.id,
        operator_id=charger.station.operator_id,
        station_id=charger.station_id,
        charger_id=charger.id,
        vin=user.vin_code or f"VIN{user.id:08d}",
        start_time=datetime.now(),
        source_type="mini_program",
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
        return _fail_response(str(exc), code=500)

    saved = _load_order(db, order.id)
    return _ok_response(serialize_order(saved), message="订单创建成功")


@mini_api_router.post("/orders/end")
async def mini_order_end(
    payload: MiniOrderEndBody,
    db: Session = Depends(get_db),
    x_mini_user_id: str | None = Header(default=None, alias="X-Mini-User-Id"),
) -> dict[str, Any]:
    user_id = _parse_user_id_header(x_mini_user_id)
    if user_id is None:
        return fail("请先登录", code=401)

    oid = int(payload.order_id)
    order = _load_order(db, oid)
    if not order:
        return _fail_response("订单不存在", code=404)
    if order.user_id != user_id:
        return _fail_response("无权操作该订单", code=403)
    if order.status != 0:
        return _fail_response("只有进行中的订单才能结束")

    now = datetime.now()
    order.end_time = now
    # 最小充电时间 1 分钟
    if order.start_time and (now - order.start_time).total_seconds() < 60:
        order.end_time = order.start_time + timedelta(minutes=1)
        recalculate_order_amounts(order, now=order.end_time)
    else:
        # 充电模拟已经在轮询中更新了费用数据，直接使用，不再 recalculate
        # 只更新 charge_duration 字段
        if order.start_time:
            order.charge_duration = max(int((order.end_time - order.start_time).total_seconds() / 60), 1)
        else:
            order.charge_duration = 1
    order.status = 1
    order.pay_status = 1
    order.settle_status = 0

    if order.charger:
        order.charger.status = 0

    from app.services.discount_service import apply_discount_to_order
    apply_discount_to_order(db, order)
    create_wallet_consume_record(db, order.user_id, order.id, Decimal(str(order.total_fee or 0)))

    try:
        _commit(db)
    except RuntimeError as exc:
        return _fail_response(str(exc), code=500)

    refreshed = _load_order(db, oid)
    return _ok_response(serialize_order(refreshed), message="订单已结束并完成计费")


@mini_api_router.get("/orders/my")
async def mini_orders_my(
    db: Session = Depends(get_db),
    x_mini_user_id: str | None = Header(default=None, alias="X-Mini-User-Id"),
) -> dict[str, Any]:
    user_id = _parse_user_id_header(x_mini_user_id)
    if user_id is None:
        return fail("请先登录", code=401)

    rows = (
        db.query(Order)
        .options(
            joinedload(Order.user),
            joinedload(Order.operator),
            joinedload(Order.station).joinedload(Station.price_template),
            joinedload(Order.charger).joinedload(Charger.station),
        )
        .filter(Order.user_id == user_id)
        .order_by(Order.start_time.desc(), Order.id.desc())
        .limit(100)
        .all()
    )
    return _ok_response([serialize_order(o) for o in rows])



@mini_api_router.get("/orders/stats")
async def mini_orders_stats(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    from app.services.order_service import get_order_stats
    return {"code": 200, "data": get_order_stats(db, operator_id=None)}

@mini_api_router.get("/orders/{order_id}")
async def mini_order_detail(
    order_id: int,
    db: Session = Depends(get_db),
    x_mini_user_id: str | None = Header(default=None, alias="X-Mini-User-Id"),
) -> dict[str, Any]:
    user_id = _parse_user_id_header(x_mini_user_id)
    if user_id is None:
        return fail("请先登录", code=401)

    order = _load_order(db, order_id)
    if not order:
        return _fail_response("订单不存在", code=404)
    if order.user_id != user_id:
        return _fail_response("无权查看该订单", code=403)
    return _ok_response(serialize_order(order))


@mini_api_router.get("/wallet")
async def mini_wallet(
    db: Session = Depends(get_db),
    x_mini_user_id: str | None = Header(default=None, alias="X-Mini-User-Id"),
) -> dict[str, Any]:
    user_id = _parse_user_id_header(x_mini_user_id)
    if user_id is None:
        return fail("请先登录", code=401)

    summary = get_wallet_summary(db, user_id=user_id, limit=20)
    return _ok_response(
        {
            "balance": summary.get("balance", 0),
            "available_balance": summary.get("balance", 0),
            "coupon_count": 0,
            "recent_transactions": summary.get("recent_transactions", []),
        }
    )


@mini_api_router.get("/wallet/transactions")
async def mini_wallet_transactions(
    db: Session = Depends(get_db),
    x_mini_user_id: str | None = Header(default=None, alias="X-Mini-User-Id"),
) -> dict[str, Any]:
    user_id = _parse_user_id_header(x_mini_user_id)
    if user_id is None:
        return fail("请先登录", code=401)

    rows = get_wallet_transaction_list(db, user_id=user_id, limit=50)
    return _ok_response(rows)


@mini_api_router.post("/wallet/recharge")
async def mini_wallet_recharge(
    payload: MiniWalletRechargeBody,
    db: Session = Depends(get_db),
    x_mini_user_id: str | None = Header(default=None, alias="X-Mini-User-Id"),
) -> dict[str, Any]:
    user_id = _parse_user_id_header(x_mini_user_id)
    if user_id is None:
        return fail("请先登录", code=401)

    try:
        amt = Decimal(str(payload.amount)).quantize(Decimal("0.01"))
    except Exception:
        return _fail_response("充值金额格式不正确")

    if amt <= 0:
        return _fail_response("充值金额必须大于 0")
    if amt > Decimal("50000"):
        return _fail_response("单笔充值金额过大")

    user = db.query(User).options(noload("*")).filter(User.id == user_id).first()
    if not user:
        return _fail_response("用户不存在", code=404)

    create_wallet_recharge_record(db, user_id, amt)
    try:
        _commit(db)
    except RuntimeError as exc:
        return _fail_response(str(exc), code=500)

    summary = get_wallet_summary(db, user_id=user_id, limit=20)
    return _ok_response(
        {
            "balance": summary.get("balance", 0),
            "available_balance": summary.get("balance", 0),
            "coupon_count": 0,
            "recent_transactions": summary.get("recent_transactions", []),
        },
        message="充值成功",
    )


@mini_api_router.post("/invoices/apply")
async def mini_invoice_apply(
    payload: MiniInvoiceApplyBody,
    db: Session = Depends(get_db),
    x_mini_user_id: str | None = Header(default=None, alias="X-Mini-User-Id"),
) -> dict[str, Any]:
    user_id = _parse_user_id_header(x_mini_user_id)
    if user_id is None:
        return fail("请先登录", code=401)

    oid = int(payload.order_id)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return _fail_response("用户不存在", code=404)

    order = _load_order(db, oid)
    if not order:
        return _fail_response("订单不存在", code=404)
    if order.user_id != user_id:
        return _fail_response("订单与用户不匹配")
    if order.status != 1 or order.pay_status != 1:
        return _fail_response("订单必须已完成且已支付后才能申请发票")

    title = (payload.title or "个人").strip()[:100]
    email = payload.email.strip()
    if not email:
        return _fail_response("请填写接收邮箱")

    existing = (
        db.query(Invoice)
        .filter(Invoice.order_id == order.id, Invoice.user_id == user.id)
        .order_by(Invoice.id.desc())
        .first()
    )

    def _money(v: Any) -> Decimal:
        return Decimal(str(v or 0)).quantize(Decimal("0.01"))

    if existing:
        existing.invoice_title = title
        existing.email = email
        existing.amount = _money(order.total_fee)
        existing.status = 0
        existing.remark = "小程序重复申请已重置为待开票"
        existing.file_url = None
        existing.uploaded_at = None
        invoice = existing
        message = "已更新原有发票申请并重置为待开票"
    else:
        invoice = Invoice(
            user_id=user.id,
            operator_id=order.operator_id,
            order_id=order.id,
            invoice_title=title,
            amount=_money(order.total_fee),
            email=email,
            status=0,
            remark="小程序发票申请",
        )
        db.add(invoice)
        message = "发票申请已提交"

    try:
        _commit(db)
    except RuntimeError as exc:
        return _fail_response(str(exc), code=500)

    return _ok_response(
        {
            "id": invoice.id,
            "invoice_id": invoice.id,
            "order_id": invoice.order_id,
            "invoice_title": invoice.invoice_title,
            "title": invoice.invoice_title,
            "email": invoice.email,
            "amount": float(invoice.amount or 0),
            "status": invoice.status,
            "created_at": invoice.created_at.strftime("%Y-%m-%d %H:%M:%S") if invoice.created_at else "",
        },
        message=message,
    )


@mini_api_router.get("/invoices")
async def mini_invoice_list(
    db: Session = Depends(get_db),
    x_mini_user_id: str | None = Header(default=None, alias="X-Mini-User-Id"),
) -> dict[str, Any]:
    user_id = _parse_user_id_header(x_mini_user_id)
    if user_id is None:
        return fail("请先登录", code=401)

    rows = (
        db.query(Invoice)
        .options(joinedload(Invoice.user), joinedload(Invoice.operator), joinedload(Invoice.related_order))
        .filter(Invoice.user_id == user_id)
        .order_by(Invoice.created_at.desc(), Invoice.id.desc())
        .limit(100)
        .all()
    )
    return _ok_response([_serialize_invoice(item) for item in rows])


@mini_api_router.get("/coupons")
async def mini_coupons_list(
    db: Session = Depends(get_db),
    x_mini_user_id: str | None = Header(default=None, alias="X-Mini-User-Id"),
) -> dict[str, Any]:
    user_id = _parse_user_id_header(x_mini_user_id)
    
    # 公开可领优惠券
    available_coupons = (
        db.query(Coupon)
        .options(joinedload(Coupon.operator))
        .filter(Coupon.is_deleted.is_(False))
        .order_by(Coupon.id.desc())
        .limit(50)
        .all()
    )
    
    # 用户已领取的 coupon id set
    received_ids: set[int] = set()
    if user_id is not None:
        received = (
            db.query(UserCoupon.coupon_id)
            .filter(UserCoupon.user_id == user_id)
            .all()
        )
        received_ids = {r[0] for r in received}
    
    base_discounts = [
        {"id": "promo-01", "title": "首充礼包已到账", "desc": "钱包首次充值满 100 元，可领取 12 元充电券，适用于合作快充站点。", "tag": "新人福利", "coupon_value": "￥12", "expire_text": "有效期至月底", "received": False},
        {"id": "promo-02", "title": "夜间充电服务费 8 折", "desc": "20:00 后生效，夜间补能更划算。", "tag": "限时优惠", "coupon_value": "8折", "expire_text": "每周末可用", "received": False},
        {"id": "promo-03", "title": "常用站点满减券", "desc": "近30天累计充电3次可领专属满减权益。", "tag": "会员权益", "coupon_value": "满30减6", "expire_text": "自动发放", "received": False},
    ]
    
    for item in base_discounts:
        cid = item["id"]
        item["received"] = cid in [f"promo-{rid}" for rid in received_ids] if received_ids else False
    
    coupon_list: list[dict[str, Any]] = []
    for cp in available_coupons:
        cp_id_str = str(cp.id)
        coupon_list.append({
            "id": cp_id_str,
            "title": cp.name or f"{cp.operator.name}优惠券" if cp.operator else "优惠券",
            "desc": f"充电满减 {float(cp.discount_val or 0):.0f} 元",
            "tag": "运营商券",
            "coupon_value": f"￥{float(cp.discount_val or 0):.0f}",
            "expire_text": "详见规则",
            "received": cp_id_str in [f"promo-{rid}" for rid in received_ids] if received_ids else False,
        })
    
    # 合并内置优惠 + 数据库优惠券
    merged: list[dict[str, Any]] = []
    seen_ids = set()
    for item in coupon_list:
        merged.append(item)
        seen_ids.add(item["id"])
    for item in base_discounts:
        if item["id"] not in seen_ids:
            merged.append(item)
            seen_ids.add(item["id"])
    
    return _ok_response(merged)


@mini_api_router.post("/coupons/{coupon_id}/receive")
async def mini_coupon_receive(
    coupon_id: str,
    db: Session = Depends(get_db),
    x_mini_user_id: str | None = Header(default=None, alias="X-Mini-User-Id"),
) -> dict[str, Any]:
    user_id = _parse_user_id_header(x_mini_user_id)
    if user_id is None:
        return fail("请先登录", code=401)
    
    try:
        real_id = int(coupon_id)
        coupon = db.query(Coupon).filter(Coupon.id == real_id, Coupon.is_deleted.is_(False)).first()
        if coupon:
            existing = db.query(UserCoupon).filter(
                UserCoupon.user_id == user_id,
                UserCoupon.coupon_id == real_id,
            ).first()
            if not existing:
                uc = UserCoupon(user_id=user_id, coupon_id=real_id, status=0)
                db.add(uc)
                db.commit()
            return _ok_response(
                {
                    "id": coupon_id,
                    "title": f"{coupon.type}优惠券" if coupon.type else "优惠券",
                    "received": True,
                },
                message="领取成功",
            )
    except ValueError:
        pass
    
    # 内置优惠：直接标记已领取（本地存储由前端处理）
    return _ok_response(
        {
            "id": coupon_id,
            "title": "演示优惠券",
            "received": True,
        },
        message="领取成功",
    )


# ===== 运营商入驻申请（小程序端） =====


class MiniOperatorApplyPayload(BaseModel):
    operator_name: str
    contact_name: str
    phone: str
    company_name: str = ""
    email: str = ""
    region: str = ""
    address: str = ""
    credit_code: str = ""
    description: str = ""
    station_count: int = 0
    charger_count: int = 0


@mini_api_router.post("/operator/apply")
async def mini_operator_apply(
    payload: MiniOperatorApplyPayload,
    db: Session = Depends(get_db),
    x_mini_user_id: str | None = Header(default=None, alias="X-Mini-User-Id"),
) -> dict[str, Any]:
    """小程序用户提交运营商入驻申请。"""
    user_id = _parse_user_id_header(x_mini_user_id)
    if user_id is None:
        return fail("请先登录", code=401)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return fail("用户不存在", code=404)
    if user.role == "operator":
        return fail("您已经是运营商用户", code=400)

    # 检查是否已有待审核申请
    existing_app = (
        db.query(OperatorAuditApplication)
        .filter(
            OperatorAuditApplication.phone == (payload.phone or user.phone),
            OperatorAuditApplication.status == "pending",
            OperatorAuditApplication.is_deleted.is_(False),
        )
        .first()
    )
    if existing_app:
        return fail("您已提交过入驻申请，请耐心等待审核", code=400)

    # 构建申请数据
    from app.services.operator_audit_application_service import create_operator_audit_application
    from datetime import datetime
    import random

    application_no = f"APP{datetime.now():%Y%m%d%H%M%S}{random.randint(100,999)}"

    result = create_operator_audit_application(db, data={
        "application_no": application_no,
        "operator_name": payload.operator_name,
        "company_name": payload.company_name or payload.operator_name,
        "contact_name": payload.contact_name,
        "phone": payload.phone or user.phone,
        "email": payload.email,
        "region": payload.region,
        "address": payload.address,
        "credit_code": payload.credit_code,
        "description": payload.description,
        "station_count": payload.station_count,
        "charger_count": payload.charger_count,
        "linked_operator_id": None,
        "submit_comment": f"小程序用户 {user.nickname or user.phone} 提交的入驻申请",
    })

    if result.get("error"):
        return fail(result.get("message", "提交失败"), code=400)

    return _ok_response(result.get("record"), message="入驻申请已提交，请等待管理员审核")


@mini_api_router.get("/operator/apply/status")
async def mini_operator_apply_status(
    db: Session = Depends(get_db),
    x_mini_user_id: str | None = Header(default=None, alias="X-Mini-User-Id"),
) -> dict[str, Any]:
    """查询当前用户的入驻申请状态。"""
    user_id = _parse_user_id_header(x_mini_user_id)
    if user_id is None:
        return fail("请先登录", code=401)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return fail("用户不存在", code=404)

    # 查找该用户的申请记录（通过手机号匹配）
    apps = (
        db.query(OperatorAuditApplication)
        .filter(
            OperatorAuditApplication.phone == user.phone,
            OperatorAuditApplication.is_deleted.is_(False),
        )
        .order_by(OperatorAuditApplication.submitted_at.desc())
        .all()
    )

    if user.role == "operator":
        return _ok_response({
            "is_operator": True,
            "message": "您已是运营商用户，请使用账号登录管理端",
            "applications": [],
        })

    if not apps:
        return _ok_response({
            "is_operator": False,
            "has_application": False,
            "message": "您尚未提交入驻申请",
            "applications": [],
        })

    latest = apps[0]
    return _ok_response({
        "is_operator": False,
        "has_application": True,
        "status": latest.status,
        "status_text": {"pending": "待审核", "approved": "已通过", "rejected": "已驳回"}.get(latest.status, "未知"),
        "application_no": latest.application_no,
        "submitted_at": latest.submitted_at.strftime("%Y-%m-%d %H:%M") if latest.submitted_at else "",
        "review_comment": latest.review_comment or "",
        "message": [
            "您的入驻申请正在审核中，请耐心等待",
            "恭喜！您的入驻申请已通过，请使用账号登录管理端",
            f"很抱歉，您的申请已被驳回（{latest.review_comment or '无备注'}）",
        ].get({"pending": 0, "approved": 1, "rejected": 2}.get(latest.status, 0), ""),
        "applications": [{
            "id": a.id,
            "status": a.status,
            "operator_name": a.operator_name,
            "submitted_at": a.submitted_at.strftime("%Y-%m-%d %H:%M") if a.submitted_at else "",
        } for a in apps],
    })
