from sqlalchemy.orm import Session, joinedload

from app.models.models import Invoice


def list_invoices(db: Session) -> list[Invoice]:
    return (
        db.query(Invoice)
        .options(joinedload(Invoice.user), joinedload(Invoice.related_order))
        .order_by(Invoice.created_at.desc())
        .all()
    )


def get_invoice_by_id(db: Session, invoice_id: int) -> Invoice | None:
    return (
        db.query(Invoice)
        .options(joinedload(Invoice.user), joinedload(Invoice.operator), joinedload(Invoice.related_order))
        .filter(Invoice.id == invoice_id)
        .first()
    )
