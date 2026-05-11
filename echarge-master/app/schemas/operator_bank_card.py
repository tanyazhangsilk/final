from pydantic import BaseModel


class OperatorBankCardSchema(BaseModel):
    id: int
    operator_id: int
    account_name: str
    bank_name: str
    bank_account: str
    is_default: bool
    bind_status: int
    created_at: str
    updated_at: str
