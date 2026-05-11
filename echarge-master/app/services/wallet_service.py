from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.crud.wallet_crud import count_wallet_transactions, list_wallet_transactions
from app.models.models import WalletTransaction
from app.services.wallet_flow_service import get_user_balance


TRANSACTION_TYPE_LABELS = {
    "recharge": "充值",
    "consume": "消费",
    "pay": "支付",
    "refund": "退款",
}


def serialize_wallet_transaction(item: WalletTransaction) -> dict[str, Any]:
    return {
        "id": item.id,
        "user_id": item.user_id,
        "transaction_type": item.transaction_type,
        "transaction_type_label": TRANSACTION_TYPE_LABELS.get(item.transaction_type, item.transaction_type),
        "amount": float(Decimal(str(item.amount))),
        "balance_after": float(Decimal(str(item.balance_after))),
        "remark": item.remark or "",
        "related_order_id": item.related_order_id,
        "related_order_no": item.related_order.order_no if item.related_order else None,
        "created_at": item.created_at.strftime("%Y-%m-%d %H:%M:%S") if item.created_at else "",
    }


def get_wallet_transaction_list(db: Session, user_id: int, limit: int = 50) -> list[dict[str, Any]]:
    return [serialize_wallet_transaction(item) for item in list_wallet_transactions(db, user_id=user_id, limit=limit)]


def get_wallet_summary(db: Session, user_id: int, limit: int = 20) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "balance": float(get_user_balance(db, user_id=user_id)),
        "transaction_count": count_wallet_transactions(db, user_id=user_id),
        "recent_transactions": get_wallet_transaction_list(db, user_id=user_id, limit=limit),
    }
