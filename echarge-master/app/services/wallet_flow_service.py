from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.models.models import Order, WalletTransaction


DEFAULT_DEMO_BALANCE = Decimal("200.00")
MONEY_SCALE = Decimal("0.01")


def _to_money(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value or 0)).quantize(MONEY_SCALE, rounding=ROUND_HALF_UP)


def get_user_balance(db: Session, user_id: int) -> Decimal:
    """按主键 id 倒序取最新流水；与复合索引 (user_id, id) 对齐，避免按时间排序全表扫描。"""
    latest = (
        db.query(WalletTransaction.balance_after)
        .filter(WalletTransaction.user_id == user_id)
        .order_by(WalletTransaction.id.desc())
        .limit(1)
        .first()
    )
    if latest:
        return _to_money(latest[0])
    return DEFAULT_DEMO_BALANCE


def create_wallet_consume_record(
    db: Session,
    user_id: int,
    order_id: int,
    amount: Decimal | int | float | str,
    *,
    order_no: str | None = None,
) -> WalletTransaction:
    consume_amount = -abs(_to_money(amount))
    current_balance = get_user_balance(db, user_id)
    balance_after = _to_money(current_balance + consume_amount)
    if order_no is not None and str(order_no).strip():
        resolved_no = str(order_no).strip()
    else:
        order = db.query(Order.order_no).filter(Order.id == order_id).first()
        resolved_no = order[0] if order else f"#{order_id}"

    record = WalletTransaction(
        user_id=user_id,
        transaction_type="consume",
        amount=consume_amount,
        balance_after=balance_after,
        related_order_id=order_id,
        remark=f"订单消费，订单号={resolved_no}",
    )
    db.add(record)
    db.flush()
    return record


def create_wallet_recharge_record(
    db: Session,
    user_id: int,
    amount: Decimal | int | float | str,
) -> WalletTransaction:
    recharge_amount = abs(_to_money(amount))
    current_balance = get_user_balance(db, user_id)
    balance_after = _to_money(current_balance + recharge_amount)

    record = WalletTransaction(
        user_id=user_id,
        transaction_type="recharge",
        amount=recharge_amount,
        balance_after=balance_after,
        remark="演示钱包充值",
    )
    db.add(record)
    db.flush()
    return record
