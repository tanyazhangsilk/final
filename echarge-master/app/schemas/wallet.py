from pydantic import BaseModel


class WalletTransactionSchema(BaseModel):
    id: int
    user_id: int
    transaction_type: str
    transaction_type_label: str
    amount: float
    balance_after: float
    remark: str = ""
    related_order_id: int | None = None
    related_order_no: str | None = None
    created_at: str


class WalletSummarySchema(BaseModel):
    user_id: int
    balance: float
    transaction_count: int
    recent_transactions: list[WalletTransactionSchema]
