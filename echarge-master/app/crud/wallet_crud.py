from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.models import WalletTransaction


def list_wallet_transactions(db: Session, user_id: int, limit: int = 50) -> list[WalletTransaction]:
    return (
        db.query(WalletTransaction)
        .options(joinedload(WalletTransaction.related_order))
        .filter(WalletTransaction.user_id == user_id)
        .order_by(WalletTransaction.created_at.desc(), WalletTransaction.id.desc())
        .limit(limit)
        .all()
    )


def get_wallet_balance(db: Session, user_id: int) -> Decimal:
    latest = (
        db.query(WalletTransaction.balance_after)
        .filter(WalletTransaction.user_id == user_id)
        .order_by(WalletTransaction.created_at.desc(), WalletTransaction.id.desc())
        .first()
    )
    if latest:
        return Decimal(str(latest[0]))
    return Decimal("0.00")


def count_wallet_transactions(db: Session, user_id: int) -> int:
    return db.query(func.count(WalletTransaction.id)).filter(WalletTransaction.user_id == user_id).scalar() or 0
