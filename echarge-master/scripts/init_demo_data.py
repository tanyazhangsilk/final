from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.database import SessionLocal, engine
from app.models.models import (
    Base,
    Charger,
    Coupon,
    Invoice,
    Operator,
    OperatorBankCard,
    OperatorSettlementRecord,
    Order,
    PriceTemplate,
    Station,
    User,
    UserCoupon,
    WalletTransaction,
)
from sqlalchemy.orm import noload

from app.services.order_service import recalculate_order_amounts
from app.services.wallet_flow_service import create_wallet_consume_record, create_wallet_recharge_record
from scripts.patch_demo_schema import ensure_demo_schema


ADMIN_ACCOUNT = "admin@echarge.com"
OPERATOR_ACCOUNT = "operator@echarge.com"
DEMO_USER_PHONE = "13800138000"

DEMO_OPERATOR_NAME = "毕业设计演示运营商"
DEMO_BANK_ACCOUNT = "6222020000008888"

PENDING_STATION_NAME = "演示待审电站"
APPROVED_STATION_A_NAME = "演示已审核电站A"
APPROVED_STATION_B_NAME = "演示已审核电站B"

TEMPLATE_A_NAME = "演示城市快充模板"
TEMPLATE_B_NAME = "演示夜间优惠模板"

ORDER_NO_CHARGING = "DEMO-ORDER-CHARGING-001"
ORDER_NO_UNSETTLED = "DEMO-ORDER-COMPLETED-UNSETTLED-001"
ORDER_NO_SETTLED = "DEMO-ORDER-COMPLETED-SETTLED-001"
ORDER_NO_ABNORMAL = "DEMO-ORDER-ABNORMAL-001"


def _money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def upsert_user(
    db,
    *,
    phone: str,
    nickname: str,
    password: str,
    role: str,
    vin_code: str | None = None,
) -> User:
    user = db.query(User).options(noload("*")).filter(User.phone == phone).first()
    if not user:
        user = User(phone=phone, password_hash=password, nickname=nickname, role=role, status=0)
        db.add(user)
    user.nickname = nickname
    user.password_hash = password
    user.role = role
    user.status = 0
    user.vin_code = vin_code
    db.flush()
    return user


def upsert_operator(db) -> Operator:
    operator = db.query(Operator).options(noload("*")).filter(Operator.name == DEMO_OPERATOR_NAME).first()
    if not operator:
        operator = Operator(name=DEMO_OPERATOR_NAME, org_type="enterprise")
        db.add(operator)
    operator.org_type = "enterprise"
    operator.is_verified = True
    operator.bank_account = DEMO_BANK_ACCOUNT
    operator.license_url = "https://example.com/demo-operator-license.pdf"
    db.flush()
    return operator


def upsert_bank_card(db, operator: Operator) -> OperatorBankCard:
    cards = db.query(OperatorBankCard).options(noload("*")).filter(OperatorBankCard.operator_id == operator.id).all()
    for item in cards:
        item.is_default = False

    card = next((item for item in cards if item.bank_account == DEMO_BANK_ACCOUNT), None)
    if not card:
        card = OperatorBankCard(
            operator_id=operator.id,
            account_name=operator.name,
            bank_name="中国工商银行深圳科技园支行",
            bank_account=DEMO_BANK_ACCOUNT,
        )
        db.add(card)
    card.account_name = operator.name
    card.bank_name = "中国工商银行深圳科技园支行"
    card.bank_account = DEMO_BANK_ACCOUNT
    card.is_default = True
    card.bind_status = 1
    db.flush()
    return card


def upsert_price_template(db, operator: Operator, *, name: str, rules: dict) -> PriceTemplate:
    template = (
        db.query(PriceTemplate)
        .options(noload("*"))
        .filter(PriceTemplate.operator_id == operator.id, PriceTemplate.name == name)
        .first()
    )
    if not template:
        template = PriceTemplate(operator_id=operator.id, name=name, rules_json="")
        db.add(template)
    template.name = name
    template.rules_json = json.dumps(rules, ensure_ascii=False)
    db.flush()
    return template


def upsert_station(
    db,
    operator: Operator,
    *,
    name: str,
    template: PriceTemplate | None,
    status: int,
    visibility: str,
    district: str,
    address: str,
    longitude: str,
    latitude: str,
    audit_remark: str,
) -> Station:
    station = (
        db.query(Station)
        .options(noload("*"))
        .filter(Station.operator_id == operator.id, Station.name == name, Station.is_deleted.is_(False))
        .first()
    )
    if not station:
        station = Station(operator_id=operator.id, name=name, longitude=Decimal(longitude), latitude=Decimal(latitude))
        db.add(station)
    station.template_id = template.id if template else None
    station.name = name
    station.province = "广东省"
    station.city = "深圳市"
    station.district = district
    station.address = address
    station.longitude = Decimal(longitude)
    station.latitude = Decimal(latitude)
    station.contact_name = "演示联系人"
    station.contact_phone = "13800138000"
    station.operation_hours = "00:00-24:00"
    station.parking_fee_desc = "首小时免费，后续按商场规则收费"
    station.station_remark = "毕业设计演示数据"
    station.planned_charger_count = 4
    station.total_power_kw = Decimal("360.00")
    station.cover_image = "https://example.com/demo-station-cover.jpg"
    station.site_photos_json = json.dumps(["站点门头", "充电区域", "停车引导牌"], ensure_ascii=False)
    station.qualification_remark = "资料齐全，可用于答辩演示"
    station.audit_remark = audit_remark
    station.status = status
    station.visibility = visibility
    db.flush()
    return station


def upsert_charger(
    db,
    station: Station,
    *,
    sn_code: str,
    name: str,
    charger_type: str,
    power_kw: str,
    status: int,
) -> Charger:
    charger = db.query(Charger).options(noload("*")).filter(Charger.sn_code == sn_code).first()
    if not charger:
        charger = Charger(sn_code=sn_code, station_id=station.id, type=charger_type)
        db.add(charger)
    charger.station_id = station.id
    charger.sn_code = sn_code
    charger.name = name
    charger.type = charger_type
    charger.power_kw = Decimal(power_kw)
    charger.status = status
    db.flush()
    return charger


def upsert_order(
    db,
    *,
    order_no: str,
    user: User,
    operator: Operator,
    station: Station,
    charger: Charger,
    source_type: str,
    start_time: datetime,
    end_time: datetime | None,
    status: int,
    pay_status: int,
    settle_status: int,
    abnormal_reason: str | None = None,
    minimum_charge_kwh: Decimal | None = None,
) -> Order:
    order = db.query(Order).options(noload("*")).filter(Order.order_no == order_no).first()
    if not order:
        order = Order(
            order_no=order_no,
            user_id=user.id,
            operator_id=operator.id,
            station_id=station.id,
            charger_id=charger.id,
            start_time=start_time,
        )
        db.add(order)
    order.user_id = user.id
    order.operator_id = operator.id
    order.station_id = station.id
    order.charger_id = charger.id
    order.vin = user.vin_code or "LSVFA49J5N2000001"
    order.start_time = start_time
    order.end_time = end_time
    order.source_type = source_type
    order.pay_status = pay_status
    order.status = status
    order.abnormal_reason = abnormal_reason
    order.settle_status = settle_status
    order.user = user
    order.operator = operator
    order.station = station
    order.charger = charger
    recalculate_order_amounts(
        order,
        now=end_time or datetime.now(),
        minimum_charge_kwh=minimum_charge_kwh,
    )
    db.flush()
    return order


def ensure_wallet_transactions(db, demo_user: User, completed_orders: list[Order]) -> None:
    for item in db.query(WalletTransaction).options(noload("*")).filter(WalletTransaction.user_id == demo_user.id).all():
        db.delete(item)
    db.flush()

    create_wallet_recharge_record(db, demo_user.id, Decimal("300.00"))
    for order in completed_orders:
        create_wallet_consume_record(db, demo_user.id, order.id, order.total_fee)


def ensure_invoices(db, demo_user: User, unsettled_order: Order, settled_order: Order) -> None:
    existing = (
        db.query(Invoice)
        .options(noload("*"))
        .filter(Invoice.user_id == demo_user.id, Invoice.order_id.in_([unsettled_order.id, settled_order.id]))
        .all()
    )
    for item in existing:
        db.delete(item)
    db.flush()

    db.add(
        Invoice(
            user_id=demo_user.id,
            operator_id=unsettled_order.operator_id,
            order_id=unsettled_order.id,
            invoice_title="个人",
            amount=_money(unsettled_order.total_fee),
            email="user@example.com",
            status=0,
            remark="待开票演示申请",
        )
    )
    db.add(
        Invoice(
            user_id=demo_user.id,
            operator_id=settled_order.operator_id,
            order_id=settled_order.id,
            invoice_title="毕业设计演示用户",
            amount=_money(settled_order.total_fee),
            email="demo.invoice@example.com",
            status=1,
            file_url="https://example.com/invoice/demo-issued.pdf",
            uploaded_at=datetime.now() - timedelta(days=1),
            remark="已开票演示记录",
        )
    )
    db.flush()


def ensure_settlement_record(db, operator: Operator, settled_order: Order) -> None:
    settle_date = settled_order.end_time.date()
    record = (
        db.query(OperatorSettlementRecord)
        .options(noload("*"))
        .filter(
            OperatorSettlementRecord.operator_id == operator.id,
            OperatorSettlementRecord.settle_date == settle_date,
        )
        .first()
    )
    total_amount = _money(settled_order.total_fee)
    platform_rate = Decimal("0.1000")
    platform_fee = _money(total_amount * Decimal("0.10"))
    settle_amount = _money(total_amount - platform_fee)

    if not record:
        record = OperatorSettlementRecord(operator_id=operator.id, settle_date=settle_date)
        db.add(record)
    record.order_count = 1
    record.total_amount = total_amount
    record.platform_rate = platform_rate
    record.platform_fee = platform_fee
    record.settle_amount = settle_amount
    record.status = 1
    record.hold_reason = None
    db.flush()


def main() -> None:
    ensure_demo_schema()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        admin_user = upsert_user(
            db,
            phone=ADMIN_ACCOUNT,
            nickname="平台管理员",
            password="admin123",
            role="admin",
        )
        operator_user = upsert_user(
            db,
            phone=OPERATOR_ACCOUNT,
            nickname="演示运营商账号",
            password="operator123",
            role="operator",
        )
        demo_user = upsert_user(
            db,
            phone=DEMO_USER_PHONE,
            nickname="演示车主",
            password="123456",
            role="user",
            vin_code="LSVFA49J5N2000001",
        )

        operator = upsert_operator(db)
        upsert_bank_card(db, operator)

        template_a = upsert_price_template(
            db,
            operator,
            name=TEMPLATE_A_NAME,
            rules={
                "peak_price": 1.88,
                "flat_price": 1.34,
                "valley_price": 0.76,
                "service_price": 0.80,
                "scope": "全站",
                "status": "active",
            },
        )
        template_b = upsert_price_template(
            db,
            operator,
            name=TEMPLATE_B_NAME,
            rules={
                "peak_price": 1.56,
                "flat_price": 1.12,
                "valley_price": 0.58,
                "service_price": 0.65,
                "scope": "指定站点",
                "status": "active",
            },
        )

        pending_station = upsert_station(
            db,
            operator,
            name=PENDING_STATION_NAME,
            template=None,
            status=3,
            visibility="private",
            district="南山区",
            address="科技南十二路 88 号",
            longitude="113.9434000",
            latitude="22.5405000",
            audit_remark="待管理员审核",
        )
        approved_station_a = upsert_station(
            db,
            operator,
            name=APPROVED_STATION_A_NAME,
            template=template_a,
            status=0,
            visibility="public",
            district="福田区",
            address="深南大道 1008 号",
            longitude="114.0579000",
            latitude="22.5431000",
            audit_remark="审核通过，可公开展示",
        )
        approved_station_b = upsert_station(
            db,
            operator,
            name=APPROVED_STATION_B_NAME,
            template=template_b,
            status=0,
            visibility="public",
            district="宝安区",
            address="创业一路 66 号",
            longitude="113.8842000",
            latitude="22.5535000",
            audit_remark="审核通过，可公开展示",
        )

        chargers = {
            "idle_a_1": upsert_charger(db, approved_station_a, sn_code="DEMO-A-CH-001", name="A站 1号桩", charger_type="DC", power_kw="120.00", status=0),
            "charging_a_2": upsert_charger(db, approved_station_a, sn_code="DEMO-A-CH-002", name="A站 2号桩", charger_type="DC", power_kw="120.00", status=1),
            "fault_a_3": upsert_charger(db, approved_station_a, sn_code="DEMO-A-CH-003", name="A站 3号桩", charger_type="AC", power_kw="7.00", status=2),
            "idle_a_4": upsert_charger(db, approved_station_a, sn_code="DEMO-A-CH-004", name="A站 4号桩", charger_type="DC", power_kw="90.00", status=0),
            "idle_b_1": upsert_charger(db, approved_station_b, sn_code="DEMO-B-CH-001", name="B站 1号桩", charger_type="DC", power_kw="120.00", status=0),
            "fault_b_2": upsert_charger(db, approved_station_b, sn_code="DEMO-B-CH-002", name="B站 2号桩", charger_type="DC", power_kw="90.00", status=2),
            "idle_b_3": upsert_charger(db, approved_station_b, sn_code="DEMO-B-CH-003", name="B站 3号桩", charger_type="AC", power_kw="7.00", status=0),
            "idle_b_4": upsert_charger(db, approved_station_b, sn_code="DEMO-B-CH-004", name="B站 4号桩", charger_type="DC", power_kw="120.00", status=0),
        }

        now = datetime.now()
        charging_order = upsert_order(
            db,
            order_no=ORDER_NO_CHARGING,
            user=demo_user,
            operator=operator,
            station=approved_station_a,
            charger=chargers["charging_a_2"],
            source_type="manual_demo",
            start_time=now - timedelta(minutes=42),
            end_time=None,
            status=0,
            pay_status=0,
            settle_status=0,
            minimum_charge_kwh=Decimal("14.80"),
        )
        unsettled_order = upsert_order(
            db,
            order_no=ORDER_NO_UNSETTLED,
            user=demo_user,
            operator=operator,
            station=approved_station_a,
            charger=chargers["idle_a_1"],
            source_type="manual_demo",
            start_time=now - timedelta(days=1, hours=2),
            end_time=now - timedelta(days=1, hours=1, minutes=10),
            status=1,
            pay_status=1,
            settle_status=0,
            minimum_charge_kwh=Decimal("26.50"),
        )
        settled_order = upsert_order(
            db,
            order_no=ORDER_NO_SETTLED,
            user=demo_user,
            operator=operator,
            station=approved_station_b,
            charger=chargers["idle_b_1"],
            source_type="mini_program",
            start_time=now - timedelta(days=2, hours=3),
            end_time=now - timedelta(days=2, hours=2, minutes=5),
            status=1,
            pay_status=1,
            settle_status=1,
            minimum_charge_kwh=Decimal("31.20"),
        )
        abnormal_order = upsert_order(
            db,
            order_no=ORDER_NO_ABNORMAL,
            user=demo_user,
            operator=operator,
            station=approved_station_b,
            charger=chargers["fault_b_2"],
            source_type="manual_demo",
            start_time=now - timedelta(days=3, hours=1),
            end_time=now - timedelta(days=3, minutes=20),
            status=2,
            pay_status=0,
            settle_status=0,
            abnormal_reason="设备连接中断",
            minimum_charge_kwh=Decimal("4.60"),
        )

        chargers["charging_a_2"].status = 1
        chargers["idle_a_1"].status = 0
        chargers["idle_b_1"].status = 0
        chargers["fault_b_2"].status = 2

        ensure_wallet_transactions(db, demo_user, [settled_order, unsettled_order])
        ensure_invoices(db, demo_user, unsettled_order, settled_order)
        ensure_settlement_record(db, operator, settled_order)

        # === 种子优惠券数据 ===
        coupon_types = [
            ("discount", Decimal("10.00")),
            ("discount", Decimal("15.00")),
            ("flat", Decimal("5.00")),
            ("percentage", Decimal("8.00")),
            ("discount", Decimal("20.00")),
        ]
        existing_coupons = db.query(Coupon).filter(Coupon.operator_id == operator.id).count()
        if existing_coupons == 0:
            for ctype, cval in coupon_types:
                cp = Coupon(operator_id=operator.id, type=ctype, discount_val=cval)
                db.add(cp)
            db.flush()
            print(f"已添加 {len(coupon_types)} 个种子优惠券")

        # 为演示用户领取前两个优惠券
        seed_coupons = db.query(Coupon).filter(Coupon.operator_id == operator.id).limit(2).all()
        for sc in seed_coupons:
            has = db.query(UserCoupon).filter(
                UserCoupon.user_id == demo_user.id,
                UserCoupon.coupon_id == sc.id,
            ).first()
            if not has:
                db.add(UserCoupon(user_id=demo_user.id, coupon_id=sc.id, status=0))

        db.commit()

        print("演示数据初始化完成")
        print(f"operator_id: {operator.id}")
        print(f"pending_station_id: {pending_station.id}")
        print(f"approved_station_id: {approved_station_a.id}")
        print(f"charger_sn: {chargers['idle_a_4'].sn_code}")
        print(f"user_id: {demo_user.id}")
        print(
            "test_order_nos: "
            f"{charging_order.order_no}, "
            f"{unsettled_order.order_no}, "
            f"{settled_order.order_no}, "
            f"{abnormal_order.order_no}"
        )
        print(f"admin_login: {ADMIN_ACCOUNT} / admin123")
        print(f"operator_login: {OPERATOR_ACCOUNT} / operator123")
        print(f"user_login: {DEMO_USER_PHONE} / 123456")
        _ = admin_user, operator_user
    except Exception as exc:
        db.rollback()
        print(f"演示数据初始化失败: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
