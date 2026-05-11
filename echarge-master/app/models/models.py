import datetime
from decimal import Decimal
from typing import List

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class BaseModel:
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="primary key")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), comment="created at")
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        comment="updated at",
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True, comment="soft delete")


user_fleet_association = Table(
    "busi_user_fleet_association",
    Base.metadata,
    Column("user_id", ForeignKey("sys_users.id"), primary_key=True, comment="user id"),
    Column("fleet_id", ForeignKey("busi_fleets.id"), primary_key=True, comment="fleet id"),
)


class User(Base, BaseModel):
    __tablename__ = "sys_users"

    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True, comment="phone")
    nickname: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="nickname")
    password_hash: Mapped[str] = mapped_column(String(255), comment="password hash")
    vin_code: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True, comment="vin code")
    status: Mapped[int] = mapped_column(Integer, default=0, comment="user status")
    role: Mapped[str] = mapped_column(String(20), default="user", comment="user role")

    orders: Mapped[List["Order"]] = relationship("Order", back_populates="user")
    invoices: Mapped[List["Invoice"]] = relationship("Invoice", back_populates="user")
    wallet_transactions: Mapped[List["WalletTransaction"]] = relationship(
        "WalletTransaction",
        back_populates="user",
    )
    user_coupons: Mapped[List["UserCoupon"]] = relationship("UserCoupon", back_populates="user")
    member_of_fleets: Mapped[List["Fleet"]] = relationship(
        "Fleet",
        secondary=user_fleet_association,
        back_populates="members",
    )


class Operator(Base, BaseModel):
    __tablename__ = "sys_operators"

    name: Mapped[str] = mapped_column(String(100), comment="operator name")
    org_type: Mapped[str] = mapped_column(String(50), comment="org type")
    license_url: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="license url")
    bank_account: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="bank account")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, comment="verified")

    fleets: Mapped[List["Fleet"]] = relationship("Fleet", back_populates="operator")
    stations: Mapped[List["Station"]] = relationship("Station", back_populates="operator")
    price_templates: Mapped[List["PriceTemplate"]] = relationship(
        "PriceTemplate", back_populates="operator"
    )
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="operator")
    invoices: Mapped[List["Invoice"]] = relationship("Invoice", back_populates="operator")
    bank_cards: Mapped[List["OperatorBankCard"]] = relationship(
        "OperatorBankCard",
        back_populates="operator",
    )
    operator_settlements: Mapped[List["OperatorSettlementRecord"]] = relationship(
        "OperatorSettlementRecord",
        back_populates="operator",
    )
    coupons: Mapped[List["Coupon"]] = relationship("Coupon", back_populates="operator")


class OperatorAuditApplication(Base, BaseModel):
    """运营商入驻申请（管理员审核页数据源，持久化于 MySQL）。"""

    __tablename__ = "busi_operator_audit_applications"
    __table_args__ = (
        Index("ix_operator_audit_app_credit", "credit_code"),
        Index("ix_operator_audit_app_status", "status"),
        Index("ix_operator_audit_app_submitted", "submitted_at"),
        UniqueConstraint("application_no", name="uq_operator_audit_application_no"),
    )

    application_no: Mapped[str] = mapped_column(String(40), comment="application number")
    operator_name: Mapped[str] = mapped_column(String(200), comment="operator display name")
    company_name: Mapped[str] = mapped_column(String(200), comment="company legal name")
    contact_name: Mapped[str] = mapped_column(String(50), comment="contact name")
    phone: Mapped[str] = mapped_column(String(30), comment="contact phone")
    email: Mapped[str] = mapped_column(String(120), comment="contact email")
    region: Mapped[str] = mapped_column(String(200), comment="service region text")
    address: Mapped[str] = mapped_column(Text, comment="registered address")
    credit_code: Mapped[str] = mapped_column(String(30), comment="unified social credit code")
    founded_at: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="founded date text")
    station_count: Mapped[int] = mapped_column(Integer, default=0, comment="declared station count")
    charger_count: Mapped[int] = mapped_column(Integer, default=0, comment="declared gun count")
    service_cities_json: Mapped[str] = mapped_column(Text, comment="service cities json array")
    description: Mapped[str] = mapped_column(Text, comment="business description")
    attachments_json: Mapped[str] = mapped_column(Text, comment="attachments json")
    audit_timeline_json: Mapped[str] = mapped_column(Text, comment="audit timeline json")
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="pending approved rejected")
    submitted_at: Mapped[datetime.datetime] = mapped_column(DateTime, comment="submitted at")
    reviewed_by: Mapped[str | None] = mapped_column(String(120), nullable=True, comment="reviewer label")
    reviewed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True, comment="reviewed at")
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True, comment="review comment")
    last_processed_by: Mapped[str | None] = mapped_column(String(120), nullable=True, comment="last actor")
    last_processed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True, comment="last action time")
    linked_operator_id: Mapped[int | None] = mapped_column(
        ForeignKey("sys_operators.id"),
        nullable=True,
        index=True,
        comment="linked sys operator when applicable",
    )


class Fleet(Base, BaseModel):
    __tablename__ = "busi_fleets"

    operator_id: Mapped[int] = mapped_column(ForeignKey("sys_operators.id"), comment="operator id")
    name: Mapped[str] = mapped_column(String(100), comment="fleet name")
    is_whitelist: Mapped[bool] = mapped_column(Boolean, default=False, comment="whitelist flag")

    operator: Mapped["Operator"] = relationship("Operator", back_populates="fleets", lazy="joined")
    members: Mapped[List["User"]] = relationship(
        "User",
        secondary=user_fleet_association,
        back_populates="member_of_fleets",
    )


class Station(Base, BaseModel):
    __tablename__ = "eq_stations"
    __table_args__ = (
        Index("ix_eq_stations_operator_id", "operator_id"),
        Index("ix_eq_stations_status", "status"),
        Index("ix_eq_stations_visibility", "visibility"),
        Index("ix_eq_stations_operator_status_visibility", "operator_id", "status", "visibility"),
    )

    operator_id: Mapped[int] = mapped_column(ForeignKey("sys_operators.id"), comment="operator id")
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("busi_price_templates.id"),
        nullable=True,
        comment="price template id",
    )
    name: Mapped[str] = mapped_column(String(100), comment="station name")
    province: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="province")
    city: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="city")
    district: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="district")
    address: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="address")
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), comment="longitude")
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), comment="latitude")
    contact_name: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="contact name")
    contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True, comment="contact phone")
    operation_hours: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="operation hours")
    parking_fee_desc: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="parking fee description")
    station_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="station remark")
    planned_charger_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="planned charger count")
    total_power_kw: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True, comment="planned total power")
    cover_image: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="cover image")
    site_photos_json: Mapped[str | None] = mapped_column(Text, nullable=True, comment="site photos json")
    qualification_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="qualification remark")
    parking_slot_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="parking slot count")
    service_radius_km: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True, comment="service radius km")
    site_owner: Mapped[str | None] = mapped_column(String(120), nullable=True, comment="site owner")
    construction_phase: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="construction phase")
    grid_capacity_remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="grid capacity remark")
    support_vehicle_types_json: Mapped[str | None] = mapped_column(Text, nullable=True, comment="support vehicle types json")
    facility_tags_json: Mapped[str | None] = mapped_column(Text, nullable=True, comment="facility tags json")
    safety_contact_name: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="safety contact name")
    safety_contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True, comment="safety contact phone")
    audit_remark: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="audit remark")
    status: Mapped[int] = mapped_column(Integer, default=0, comment="station status")
    visibility: Mapped[str] = mapped_column(String(20), default="public", comment="visibility")

    operator: Mapped["Operator"] = relationship("Operator", back_populates="stations", lazy="joined")
    price_template: Mapped["PriceTemplate"] = relationship(
        "PriceTemplate", back_populates="stations", lazy="joined"
    )
    chargers: Mapped[List["Charger"]] = relationship("Charger", back_populates="station")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="station")


class Charger(Base, BaseModel):
    __tablename__ = "eq_chargers"
    __table_args__ = (
        Index("ix_eq_chargers_station_id", "station_id"),
        Index("ix_eq_chargers_station_status", "station_id", "status"),
    )

    station_id: Mapped[int] = mapped_column(ForeignKey("eq_stations.id"), comment="station id")
    sn_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment="charger sn")
    name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="charger name")
    type: Mapped[str] = mapped_column(String(20), comment="charger type")
    power_kw: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True, comment="power kw")
    status: Mapped[int] = mapped_column(Integer, default=0, comment="charger status")

    station: Mapped["Station"] = relationship("Station", back_populates="chargers", lazy="joined")
    orders: Mapped[List["Order"]] = relationship("Order", back_populates="charger")


class PriceTemplate(Base, BaseModel):
    __tablename__ = "busi_price_templates"

    operator_id: Mapped[int] = mapped_column(ForeignKey("sys_operators.id"), comment="operator id")
    name: Mapped[str] = mapped_column(String(100), comment="template name")
    rules_json: Mapped[str] = mapped_column(Text, comment="template rules json")

    operator: Mapped["Operator"] = relationship("Operator", back_populates="price_templates", lazy="joined")
    stations: Mapped[List["Station"]] = relationship("Station", back_populates="price_template")


class Order(Base, BaseModel):
    __tablename__ = "trade_orders"
    __table_args__ = (
        Index("ix_trade_orders_station_id", "station_id"),
        Index("ix_trade_orders_status", "status"),
        Index("ix_trade_orders_operator_id", "operator_id"),
        Index("ix_trade_orders_start_time", "start_time"),
        Index("ix_trade_orders_end_time", "end_time"),
        Index("ix_trade_orders_operator_status_start_time", "operator_id", "status", "start_time"),
        Index("ix_trade_orders_created_at", "created_at"),
    )

    order_no: Mapped[str] = mapped_column(String(64), unique=True, index=True, comment="order no")
    user_id: Mapped[int] = mapped_column(ForeignKey("sys_users.id"), comment="user id")
    operator_id: Mapped[int] = mapped_column(ForeignKey("sys_operators.id"), comment="operator id")
    station_id: Mapped[int | None] = mapped_column(ForeignKey("eq_stations.id"), nullable=True, comment="station id")
    charger_id: Mapped[int] = mapped_column(ForeignKey("eq_chargers.id"), comment="charger id")
    vin: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="vin")
    start_time: Mapped[datetime.datetime] = mapped_column(DateTime, comment="start time")
    end_time: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True, comment="end time")
    charge_duration: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="charge duration minutes")
    total_kwh: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), comment="charge amount")
    ele_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), comment="electricity fee")
    service_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), comment="service fee")
    total_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), comment="total fee")
    source_type: Mapped[str] = mapped_column(String(30), default="mini_program", comment="source type")
    pay_status: Mapped[int] = mapped_column(Integer, default=0, server_default="0", comment="pay status")
    status: Mapped[int] = mapped_column(Integer, default=0, comment="order status")
    abnormal_reason: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="abnormal reason")
    settle_status: Mapped[int] = mapped_column(Integer, default=0, comment="settlement status")

    user: Mapped["User"] = relationship("User", back_populates="orders", lazy="joined")
    operator: Mapped["Operator"] = relationship("Operator", back_populates="orders", lazy="joined")
    station: Mapped["Station | None"] = relationship("Station", back_populates="orders", lazy="joined")
    charger: Mapped["Charger"] = relationship("Charger", back_populates="orders", lazy="joined")
    invoices: Mapped[List["Invoice"]] = relationship("Invoice", back_populates="related_order")
    wallet_transactions: Mapped[List["WalletTransaction"]] = relationship(
        "WalletTransaction",
        back_populates="related_order",
    )

    @property
    def charge_amount(self) -> Decimal:
        return self.total_kwh

    @property
    def electricity_fee(self) -> Decimal:
        return self.ele_fee

    @property
    def total_amount(self) -> Decimal:
        return self.total_fee

    @property
    def order_status(self) -> str:
        return {0: "charging", 1: "completed", 2: "abnormal"}.get(self.status, "unknown")

    @property
    def settlement_status(self) -> int:
        return self.settle_status


class Invoice(Base, BaseModel):
    __tablename__ = "trade_invoices"
    __table_args__ = (
        Index("ix_trade_invoices_order_id", "order_id"),
        Index("ix_trade_invoices_status", "status"),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("sys_users.id"), comment="user id")
    operator_id: Mapped[int] = mapped_column(ForeignKey("sys_operators.id"), comment="operator id")
    order_id: Mapped[int | None] = mapped_column(ForeignKey("trade_orders.id"), nullable=True, comment="order id")
    invoice_title: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="invoice title")
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), comment="amount")
    email: Mapped[str] = mapped_column(String(100), comment="email")
    status: Mapped[int] = mapped_column(Integer, default=0, comment="invoice status")
    file_url: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="file url")
    uploaded_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True, comment="uploaded at")
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="remark")

    user: Mapped["User"] = relationship("User", back_populates="invoices", lazy="joined")
    operator: Mapped["Operator"] = relationship("Operator", back_populates="invoices", lazy="joined")
    related_order: Mapped["Order | None"] = relationship("Order", back_populates="invoices", lazy="joined")


class OperatorBankCard(Base):
    __tablename__ = "sys_operator_bank_cards"
    __table_args__ = (
        Index("ix_sys_operator_bank_cards_operator_id", "operator_id"),
        Index("ix_sys_operator_bank_cards_bind_status", "bind_status"),
        Index("ix_sys_operator_bank_cards_is_default", "is_default"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="primary key")
    operator_id: Mapped[int] = mapped_column(ForeignKey("sys_operators.id"), comment="operator id")
    account_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="account name")
    bank_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="bank name")
    bank_account: Mapped[str] = mapped_column(String(100), nullable=False, comment="bank account")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="default card")
    bind_status: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="bind status")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), comment="created at")
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        comment="updated at",
    )

    operator: Mapped["Operator"] = relationship("Operator", back_populates="bank_cards", lazy="joined")


class WalletTransaction(Base):
    __tablename__ = "trade_wallet_transactions"
    __table_args__ = (
        Index("ix_trade_wallet_transactions_user_id", "user_id"),
        Index("ix_trade_wallet_transactions_user_id_id", "user_id", "id"),
        Index("ix_trade_wallet_transactions_created_at", "created_at"),
        Index("ix_trade_wallet_transactions_transaction_type", "transaction_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="primary key")
    user_id: Mapped[int] = mapped_column(ForeignKey("sys_users.id"), comment="user id")
    transaction_type: Mapped[str] = mapped_column(String(20), comment="transaction type")
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="amount")
    balance_after: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="balance after")
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="remark")
    related_order_id: Mapped[int | None] = mapped_column(
        ForeignKey("trade_orders.id"),
        nullable=True,
        comment="related order id",
    )
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), comment="created at")

    user: Mapped["User"] = relationship("User", back_populates="wallet_transactions", lazy="joined")
    related_order: Mapped["Order | None"] = relationship("Order", back_populates="wallet_transactions", lazy="joined")


class Coupon(Base, BaseModel):
    __tablename__ = "mkt_coupons"

    operator_id: Mapped[int | None] = mapped_column(
        ForeignKey("sys_operators.id"),
        nullable=True,
        comment="operator id",
    )
    type: Mapped[str] = mapped_column(String(50), comment="coupon type")
    discount_val: Mapped[Decimal] = mapped_column(Numeric(10, 2), comment="discount value")

    operator: Mapped["Operator"] = relationship("Operator", back_populates="coupons", lazy="joined")
    user_coupons: Mapped[List["UserCoupon"]] = relationship("UserCoupon", back_populates="coupon")


class UserCoupon(Base, BaseModel):
    __tablename__ = "mkt_user_coupons"

    user_id: Mapped[int] = mapped_column(ForeignKey("sys_users.id"), comment="user id")
    coupon_id: Mapped[int] = mapped_column(ForeignKey("mkt_coupons.id"), comment="coupon id")
    status: Mapped[int] = mapped_column(Integer, default=0, comment="coupon status")

    user: Mapped["User"] = relationship("User", back_populates="user_coupons", lazy="joined")
    coupon: Mapped["Coupon"] = relationship("Coupon", back_populates="user_coupons", lazy="joined")


class OperatorSettlementRecord(Base):
    __tablename__ = "trade_operator_settlements"
    __table_args__ = (
        Index("ix_trade_operator_settlements_settle_date", "settle_date"),
        Index("ix_trade_operator_settlements_operator_id", "operator_id"),
        Index("ix_trade_operator_settlements_status", "status"),
        UniqueConstraint("settle_date", "operator_id", name="uq_trade_operator_settlements_date_operator"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="primary key")
    settle_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, comment="settlement date")
    operator_id: Mapped[int] = mapped_column(ForeignKey("sys_operators.id"), nullable=False, comment="operator id")
    order_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="order count")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False, comment="total amount")
    platform_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        default=Decimal("0.1000"),
        nullable=False,
        comment="platform rate",
    )
    platform_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="platform fee",
    )
    settle_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
        comment="settlement amount",
    )
    status: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="payout status")
    hold_reason: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="hold reason")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), comment="created at")
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        comment="updated at",
    )

    operator: Mapped["Operator"] = relationship("Operator", back_populates="operator_settlements", lazy="joined")


class SettlementRecord(Base):
    __tablename__ = "trade_settlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="primary key")
    settle_date: Mapped[datetime.date] = mapped_column(Date, nullable=False, index=True, unique=True, comment="settlement date")
    order_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="order count")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False, comment="total amount")
    platform_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False, comment="platform fee")
    settle_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False, comment="settlement amount")
    status: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="settlement status")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), comment="created at")
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        comment="updated at",
    )
