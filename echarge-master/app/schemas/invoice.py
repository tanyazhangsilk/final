from pydantic import BaseModel


class InvoiceBaseSchema(BaseModel):
    id: int
    user_id: int
    operator_id: int
    order_id: int | None = None
    invoice_title: str | None = None
    amount: float
    email: str
    status: int
    file_url: str | None = None
    uploaded_at: str | None = None
    remark: str | None = None
    created_at: str
    updated_at: str


class InvoiceDetailSchema(InvoiceBaseSchema):
    user_phone: str = ""
    order_no: str | None = None


class InvoiceApplySchema(BaseModel):
    user_id: int
    operator_id: int
    order_id: int | None = None
    invoice_title: str
    amount: float
    email: str
    remark: str = ""


class InvoiceProcessSchema(BaseModel):
    action: str
    file_url: str = ""
    remark: str = ""
