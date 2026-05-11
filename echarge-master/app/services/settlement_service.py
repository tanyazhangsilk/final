from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import logging

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.models.models import Operator, OperatorBankCard, OperatorSettlementRecord, Order, SettlementRecord

logger = logging.getLogger(__name__)

DEFAULT_PLATFORM_RATE_PERCENT = Decimal("10")
DEFAULT_PLATFORM_RATE = Decimal("0.10")
MONEY_SCALE = Decimal("0.01")
RATE_SCALE = Decimal("0.0001")

SETTLEMENT_STATUS_PENDING = 0
SETTLEMENT_STATUS_PAID = 1
SETTLEMENT_STATUS_HOLD = 2
VALID_BANK_CARD_STATUS = 1


def _quantize_money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value or 0)).quantize(MONEY_SCALE, rounding=ROUND_HALF_UP)


def _resolve_platform_rate(platform_rate_percent: Decimal | int | float | None) -> Decimal:
    raw_percent = DEFAULT_PLATFORM_RATE_PERCENT if platform_rate_percent is None else platform_rate_percent
    try:
        ratio = Decimal(str(raw_percent))
    except (InvalidOperation, TypeError, ValueError):
        logger.warning("invalid platform rate config, fallback to default", extra={"value": str(raw_percent)})
        return DEFAULT_PLATFORM_RATE

    if ratio > 1:
        ratio = ratio / Decimal("100")
    if ratio < 0 or ratio > 1:
        logger.warning("platform rate out of range, fallback to default", extra={"value": str(raw_percent)})
        return DEFAULT_PLATFORM_RATE
    return ratio.quantize(RATE_SCALE, rounding=ROUND_HALF_UP)


def _build_hold_reason(is_verified: bool, has_valid_bank_card: bool) -> str | None:
    reasons: list[str] = []
    if not is_verified:
        reasons.append("运营商资质未认证")
    if not has_valid_bank_card:
        reasons.append("缺少默认有效银行卡")
    return "；".join(reasons) if reasons else None


def _upsert_global_summary(db: Session, target_date: date) -> None:
    summary = (
        db.query(
            func.coalesce(func.sum(OperatorSettlementRecord.order_count), 0),
            func.coalesce(func.sum(OperatorSettlementRecord.total_amount), 0),
            func.coalesce(func.sum(OperatorSettlementRecord.platform_fee), 0),
            func.coalesce(func.sum(OperatorSettlementRecord.settle_amount), 0),
        )
        .filter(OperatorSettlementRecord.settle_date == target_date)
        .first()
    )

    if not summary:
        return

    order_count = int(summary[0] or 0)
    if order_count <= 0:
        return

    global_record = db.query(SettlementRecord).filter(SettlementRecord.settle_date == target_date).first()
    if not global_record:
        global_record = SettlementRecord(settle_date=target_date)
        db.add(global_record)

    global_record.order_count = order_count
    global_record.total_amount = _quantize_money(summary[1] or 0)
    global_record.platform_fee = _quantize_money(summary[2] or 0)
    global_record.settle_amount = _quantize_money(summary[3] or 0)
    global_record.status = SETTLEMENT_STATUS_PENDING


def settle_t_plus_1_by_operator(
    target_date: date,
    db: Session | None = None,
    platform_rate_percent: Decimal | int | float | None = None,
) -> dict:
    own_session = db is None
    if own_session:
        db = SessionLocal()

    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = day_start + timedelta(days=1)
    platform_rate = _resolve_platform_rate(platform_rate_percent)

    try:
        order_rows = (
            db.query(Order.id, Order.operator_id, Order.total_fee)
            .filter(
                Order.status == 1,          # 已完成
                Order.pay_status == 1,      # 已支付
                Order.settle_status == 0,   # 未清分
                Order.end_time.isnot(None), # 按 end_time 自然日归属
                Order.end_time >= day_start,
                Order.end_time < day_end,
            )
            .all()
        )

        if not order_rows:
            logger.info("no eligible orders for settlement", extra={"settle_date": str(target_date)})
            return {
                "settle_date": str(target_date),
                "platform_rate": float(platform_rate),
                "processed_order_count": 0,
                "processed_operator_count": 0,
                "skipped_operator_count": 0,
                "operator_results": [],
            }

        grouped_orders: dict[int, dict] = defaultdict(
            lambda: {"order_ids": [], "order_count": 0, "total_amount": Decimal("0.00")}
        )
        for order_id, operator_id, total_fee in order_rows:
            bucket = grouped_orders[operator_id]
            bucket["order_ids"].append(order_id)
            bucket["order_count"] += 1
            bucket["total_amount"] += Decimal(str(total_fee or 0))

        operator_ids = list(grouped_orders.keys())
        existing_operator_ids = {
            row[0]
            for row in (
                db.query(OperatorSettlementRecord.operator_id)
                .filter(
                    OperatorSettlementRecord.settle_date == target_date,
                    OperatorSettlementRecord.operator_id.in_(operator_ids),
                )
                .all()
            )
        }

        operator_rows = (
            db.query(Operator.id, Operator.is_verified)
            .filter(Operator.id.in_(operator_ids))
            .all()
        )
        verify_map = {row[0]: bool(row[1]) for row in operator_rows}

        valid_card_operator_ids = {
            row[0]
            for row in (
                db.query(OperatorBankCard.operator_id)
                .filter(
                    OperatorBankCard.operator_id.in_(operator_ids),
                    OperatorBankCard.is_default.is_(True),
                    OperatorBankCard.bind_status == VALID_BANK_CARD_STATUS,
                )
                .distinct()
                .all()
            )
        }

        operator_results: list[dict] = []
        processed_order_count = 0
        processed_operator_count = 0
        skipped_operator_count = 0

        for operator_id in sorted(operator_ids):
            bucket = grouped_orders[operator_id]

            if operator_id in existing_operator_ids:
                skipped_operator_count += 1
                operator_results.append(
                    {
                        "operator_id": operator_id,
                        "order_count": bucket["order_count"],
                        "total_amount": float(_quantize_money(bucket["total_amount"])),
                        "platform_fee": 0.0,
                        "settle_amount": 0.0,
                        "status": "skipped",
                        "status_code": None,
                        "can_payout": None,
                        "hold_reason": "该运营商该日已生成清分记录",
                        "updated_order_count": 0,
                    }
                )
                continue

            total_amount = _quantize_money(bucket["total_amount"])
            platform_fee = _quantize_money(total_amount * platform_rate)
            settle_amount = _quantize_money(total_amount - platform_fee)

            is_verified = verify_map.get(operator_id, False)
            has_valid_bank_card = operator_id in valid_card_operator_ids
            can_payout = is_verified and has_valid_bank_card
            hold_reason = _build_hold_reason(is_verified, has_valid_bank_card)
            record_status = SETTLEMENT_STATUS_PENDING if can_payout else SETTLEMENT_STATUS_HOLD

            record = OperatorSettlementRecord(
                settle_date=target_date,
                operator_id=operator_id,
                order_count=bucket["order_count"],
                total_amount=total_amount,
                platform_rate=platform_rate,
                platform_fee=platform_fee,
                settle_amount=settle_amount,
                status=record_status,
                hold_reason=hold_reason,
            )
            db.add(record)

            updated_order_count = (
                db.query(Order)
                .filter(Order.id.in_(bucket["order_ids"]))
                .update({"settle_status": 1}, synchronize_session=False)
            )

            processed_operator_count += 1
            processed_order_count += int(updated_order_count or 0)
            operator_results.append(
                {
                    "operator_id": operator_id,
                    "order_count": bucket["order_count"],
                    "total_amount": float(total_amount),
                    "platform_fee": float(platform_fee),
                    "settle_amount": float(settle_amount),
                    "status": "pending" if can_payout else "hold",
                    "status_code": record_status,
                    "can_payout": can_payout,
                    "hold_reason": hold_reason,
                    "updated_order_count": int(updated_order_count or 0),
                }
            )

        _upsert_global_summary(db, target_date)
        db.commit()

        logger.info(
            "operator settlement committed",
            extra={
                "settle_date": str(target_date),
                "processed_order_count": processed_order_count,
                "processed_operator_count": processed_operator_count,
                "skipped_operator_count": skipped_operator_count,
            },
        )
        return {
            "settle_date": str(target_date),
            "platform_rate": float(platform_rate),
            "processed_order_count": processed_order_count,
            "processed_operator_count": processed_operator_count,
            "skipped_operator_count": skipped_operator_count,
            "operator_results": operator_results,
        }
    except IntegrityError:
        db.rollback()
        logger.info("settlement unique conflict", extra={"settle_date": str(target_date)})
        return {
            "settle_date": str(target_date),
            "platform_rate": float(platform_rate),
            "processed_order_count": 0,
            "processed_operator_count": 0,
            "skipped_operator_count": 0,
            "operator_results": [],
        }
    except Exception:
        db.rollback()
        logger.exception("operator settlement failed", extra={"settle_date": str(target_date)})
        raise
    finally:
        if own_session:
            db.close()


def settle_t_plus_1(
    target_date: date,
    db: Session | None = None,
    platform_rate_percent: Decimal | int | float | None = None,
) -> int:
    result = settle_t_plus_1_by_operator(
        target_date=target_date,
        db=db,
        platform_rate_percent=platform_rate_percent,
    )
    return int(result.get("processed_order_count", 0))


def execute_t_plus_1_settlement(db: Session, target_date: date = None):
    t_day = target_date if target_date else (date.today() - timedelta(days=1))
    try:
        detail = settle_t_plus_1_by_operator(t_day, db=db)
        return {
            "status": "success",
            "msg": "清分完成",
            "processed_count": detail["processed_order_count"],
            "operator_batch_count": detail["processed_operator_count"],
            "detail": detail,
        }
    except Exception as e:
        return {"status": "error", "msg": str(e), "processed_count": 0, "operator_batch_count": 0}
