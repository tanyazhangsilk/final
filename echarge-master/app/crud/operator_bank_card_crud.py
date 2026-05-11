from sqlalchemy.orm import Session

from app.models.models import OperatorBankCard


def list_operator_bank_cards(db: Session, operator_id: int) -> list[OperatorBankCard]:
    return (
        db.query(OperatorBankCard)
        .filter(OperatorBankCard.operator_id == operator_id)
        .order_by(OperatorBankCard.is_default.desc(), OperatorBankCard.created_at.desc())
        .all()
    )


def get_default_operator_bank_card(db: Session, operator_id: int) -> OperatorBankCard | None:
    return (
        db.query(OperatorBankCard)
        .filter(OperatorBankCard.operator_id == operator_id, OperatorBankCard.is_default.is_(True))
        .order_by(OperatorBankCard.updated_at.desc())
        .first()
    )
