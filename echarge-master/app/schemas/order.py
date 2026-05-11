from pydantic import BaseModel


class OrderBaseSchema(BaseModel):
    id: int
    order_no: str
    user_id: int
    operator_id: int
    station_id: int | None = None
    charger_id: int
    vin: str | None = None
    start_time: str
    end_time: str = ""
    charge_duration: int = 0
    charge_amount: float
    electricity_fee: float
    service_fee: float
    total_amount: float
    source_type: str = "mini_program"
    source_type_text: str = ""
    pay_status: int
    pay_status_label: str
    order_status: str
    order_status_code: int
    abnormal_reason: str | None = None
    settlement_status: int
    settlement_status_label: str
    created_at: str
    updated_at: str


class OrderDetailSchema(OrderBaseSchema):
    user_phone: str = ""
    operator_name: str = ""
    station_name: str = ""
    charger_sn: str = ""
    price_template_name: str = ""
    station_status_text: str = ""


class OrderActionSchema(BaseModel):
    abnormal_reason: str = ""


class OrderStatsSchema(BaseModel):
    charging_count: int
    today_completed_count: int
    today_charge_amount: float
    today_total_amount: float
    abnormal_count: int
