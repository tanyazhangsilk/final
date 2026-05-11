from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Fleet, Operator, Order, PriceTemplate, User

extra_api_router = APIRouter()

operator_audit_store: dict[int, dict[str, Any]] = {}
marketing_audit_store: dict[int, dict[str, Any]] = {}
blacklist_store: set[int] = set()
system_param_store: dict[str, Any] = {
    "station_auto_publish": False,
    "invoice_auto_approve_limit": 300.0,
    "settlement_platform_rate": 10,
    "abnormal_order_sla_minutes": 30,
    "user_refund_limit_per_day": 2,
    "support_email": "support@echarge.com",
}
template_store: list[dict[str, Any]] = []
tag_store: list[dict[str, Any]] = []
discount_campaign_store: list[dict[str, Any]] = []
coupon_campaign_store: list[dict[str, Any]] = []


class TemplatePayload(BaseModel):
    name: str
    peak_price: float
    flat_price: float
    valley_price: float
    service_price: float
    scope: str
    status: str = "active"


class FleetPayload(BaseModel):
    name: str
    is_whitelist: bool = False


class TagPayload(BaseModel):
    name: str
    color: str = "#409EFF"
    description: str = ""


class CampaignPayload(BaseModel):
    name: str
    campaign_type: str
    discount_value: float
    threshold: float = 0
    audience: str = "all"
    status: str = "draft"
    station_ids: list[int] = []
    station_names: str = "全部电站"


class CouponDispatchPayload(BaseModel):
    dispatch_count: int = 100


class SettingsProfilePayload(BaseModel):
    name: str
    org_type: str
    contact_email: str
    contact_phone: str
    bank_account: str = ""


class SystemParamsPayload(BaseModel):
    station_auto_publish: bool
    invoice_auto_approve_limit: float
    settlement_platform_rate: int
    abnormal_order_sla_minutes: int
    user_refund_limit_per_day: int
    support_email: str


def get_current_operator(db: Session) -> Operator | None:
    return db.query(Operator).order_by(Operator.id.asc()).first()


def user_display_name(user: User) -> str:
    return user.nickname or f"user-{str(user.phone)[-4:]}"


def seed_runtime_data(db: Session) -> None:
    operator = get_current_operator(db)
    operator_id = operator.id if operator else 0

    if not template_store:
        db_templates = (
            db.query(PriceTemplate)
            .filter(PriceTemplate.operator_id == operator_id)
            .order_by(PriceTemplate.created_at.desc())
            .all()
        )
        if db_templates:
            for item in db_templates:
                template_store.append(
                    {
                        "id": item.id,
                        "name": item.name,
                        "peak_price": 1.82,
                        "flat_price": 1.26,
                        "valley_price": 0.68,
                        "service_price": 0.8,
                        "scope": "all",
                        "status": "active",
                        "updated_at": item.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                    }
                )
        else:
            template_store.extend(
                [
                    {
                        "id": 1,
                        "name": "城市快充标准模板",
                        "peak_price": 1.88,
                        "flat_price": 1.34,
                        "valley_price": 0.76,
                        "service_price": 0.8,
                        "scope": "all",
                        "status": "active",
                        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    },
                    {
                        "id": 2,
                        "name": "园区夜充模板",
                        "peak_price": 1.56,
                        "flat_price": 1.12,
                        "valley_price": 0.58,
                        "service_price": 0.65,
                        "scope": "station",
                        "status": "draft",
                        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    },
                ]
            )

    if not tag_store:
        tag_store.extend(
            [
                {"id": 1, "name": "高频通勤", "color": "#409EFF", "description": "近30天充电6次以上", "user_count": 86},
                {"id": 2, "name": "夜间充电", "color": "#67C23A", "description": "夜间活跃用户", "user_count": 43},
                {"id": 3, "name": "待召回", "color": "#E6A23C", "description": "近14天未复购", "user_count": 27},
            ]
        )

    if not discount_campaign_store:
        discount_campaign_store.extend(
            [
                {
                    "id": 1,
                    "name": "工作日午间充电折扣",
                    "campaign_type": "满减",
                    "discount_value": 8.8,
                    "threshold": 30,
                    "audience": "fleet",
                    "status": "active",
                    "redeem_count": 326,
                    "conversion_rate": 24.5,
                },
                {
                    "id": 2,
                    "name": "新用户首充礼",
                    "campaign_type": "立减",
                    "discount_value": 12,
                    "threshold": 0,
                    "audience": "new",
                    "status": "draft",
                    "redeem_count": 0,
                    "conversion_rate": 0,
                },
            ]
        )

    if not coupon_campaign_store:
        coupon_campaign_store.extend(
            [
                {"id": 1, "name": "春季园区通勤券", "discount_value": 10, "inventory": 1000, "dispatched": 640, "used": 381, "status": "active"},
                {"id": 2, "name": "夜充满减券", "discount_value": 15, "inventory": 500, "dispatched": 120, "used": 39, "status": "paused"},
            ]
        )

    if not operator_audit_store:
        for item in db.query(Operator).order_by(Operator.created_at.desc()).all():
            operator_audit_store[item.id] = {
                "status": "approved" if item.is_verified else "pending",
                "remark": "",
                "contact_email": f"bd{item.id}@echarge.com",
                "contact_phone": f"1380000{str(item.id).zfill(4)}",
            }

    if not marketing_audit_store:
        for item in discount_campaign_store:
            marketing_audit_store[item["id"]] = {
                "status": "approved" if item["status"] == "active" else "pending",
                "remark": "",
            }


@extra_api_router.get("/admin/operators/audits", tags=["admin"])
async def get_operator_audits(db: Session = Depends(get_db)):
    seed_runtime_data(db)
    operators = db.query(Operator).order_by(Operator.created_at.desc()).all()
    rows = []
    for item in operators:
        runtime = operator_audit_store[item.id]
        rows.append(
            {
                "id": item.id,
                "name": item.name,
                "org_type": item.org_type,
                "status": runtime["status"],
                "license_url": item.license_url,
                "bank_account": item.bank_account,
                "contact_email": runtime["contact_email"],
                "contact_phone": runtime["contact_phone"],
                "station_count": len(item.stations),
                "fleet_count": len(item.fleets),
                "created_at": item.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "remark": runtime["remark"],
            }
        )
    return {
        "code": 200,
        "data": rows,
        "summary": {
            "pending_count": sum(1 for item in rows if item["status"] == "pending"),
            "approved_count": sum(1 for item in rows if item["status"] == "approved"),
            "rejected_count": sum(1 for item in rows if item["status"] == "rejected"),
        },
    }


@extra_api_router.post("/admin/operators/{operator_id}/process", tags=["admin"])
async def process_operator_audit(operator_id: int, payload: dict[str, Any], db: Session = Depends(get_db)):
    seed_runtime_data(db)
    operator = db.query(Operator).filter(Operator.id == operator_id).first()
    if not operator:
        return {"code": 404, "message": "operator not found"}
    runtime = operator_audit_store[operator_id]
    action = payload.get("action")
    if action == "approve":
        operator.is_verified = True
        runtime["status"] = "approved"
    elif action == "reject":
        operator.is_verified = False
        runtime["status"] = "rejected"
    runtime["remark"] = payload.get("remark", "")
    db.commit()
    return {"code": 200, "message": "audit updated"}


@extra_api_router.get("/admin/users", tags=["admin"])
async def get_admin_users(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    rows = []
    for item in users:
        total_spent = (
            db.query(func.coalesce(func.sum(Order.total_fee), 0))
            .filter(Order.user_id == item.id, Order.status == 1)
            .scalar()
        )
        rows.append(
            {
                "id": item.id,
                "name": user_display_name(item),
                "phone": item.phone,
                "status": "blacklisted" if item.id in blacklist_store or item.status == 1 else "active",
                "vin_code": item.vin_code or "-",
                "order_count": db.query(func.count(Order.id)).filter(Order.user_id == item.id).scalar(),
                "total_spent": float(total_spent or 0),
                "created_at": item.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return {
        "code": 200,
        "data": rows,
        "summary": {
            "total_users": len(rows),
            "blacklisted_users": sum(1 for item in rows if item["status"] == "blacklisted"),
            "active_users": sum(1 for item in rows if item["status"] == "active"),
        },
    }


@extra_api_router.post("/admin/users/{user_id}/toggle-blacklist", tags=["admin"])
async def toggle_user_blacklist(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"code": 404, "message": "user not found"}
    if user_id in blacklist_store:
        blacklist_store.remove(user_id)
        user.status = 0
        message = "removed"
    else:
        blacklist_store.add(user_id)
        user.status = 1
        message = "added"
    db.commit()
    return {"code": 200, "message": message}


@extra_api_router.get("/admin/users/blacklist", tags=["admin"])
async def get_blacklist_users(db: Session = Depends(get_db)):
    users = db.query(User).filter(User.id.in_(list(blacklist_store)) if blacklist_store else False).all()
    return {
        "code": 200,
        "data": [
            {
                "id": item.id,
                "name": user_display_name(item),
                "phone": item.phone,
                "reason": "risk_control",
                "created_at": item.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for item in users
        ],
    }


@extra_api_router.get("/admin/marketing/audits", tags=["admin"])
async def get_admin_marketing_audits(db: Session = Depends(get_db)):
    seed_runtime_data(db)
    operator = get_current_operator(db)
    return {
        "code": 200,
        "data": [
            {
                **item,
                "audit_status": marketing_audit_store[item["id"]]["status"],
                "remark": marketing_audit_store[item["id"]]["remark"],
                "operator_name": operator.name if operator else "unknown",
            }
            for item in discount_campaign_store
        ],
    }


@extra_api_router.post("/admin/marketing/audits/{campaign_id}/process", tags=["admin"])
async def process_admin_marketing_audit(campaign_id: int, payload: dict[str, Any], db: Session = Depends(get_db)):
    seed_runtime_data(db)
    audit = marketing_audit_store.get(campaign_id)
    if not audit:
        return {"code": 404, "message": "campaign not found"}
    audit["status"] = "approved" if payload.get("action") == "approve" else "rejected"
    audit["remark"] = payload.get("remark", "")
    return {"code": 200, "message": "audit updated"}


@extra_api_router.get("/admin/settings/params", tags=["admin"])
async def get_admin_system_params():
    return {"code": 200, "data": system_param_store}


@extra_api_router.put("/admin/settings/params", tags=["admin"])
async def update_admin_system_params(payload: SystemParamsPayload):
    system_param_store.update(payload.model_dump())
    return {"code": 200, "message": "saved", "data": system_param_store}


@extra_api_router.get("/operator/billing/templates", tags=["operator"])
async def get_operator_billing_templates(db: Session = Depends(get_db)):
    seed_runtime_data(db)
    return {"code": 200, "data": template_store}


@extra_api_router.post("/operator/billing/templates", tags=["operator"])
async def create_operator_billing_template(payload: TemplatePayload, db: Session = Depends(get_db)):
    seed_runtime_data(db)
    next_id = max((item["id"] for item in template_store), default=0) + 1
    record = payload.model_dump()
    record.update({"id": next_id, "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
    template_store.insert(0, record)
    return {"code": 200, "message": "created", "data": record}


@extra_api_router.put("/operator/billing/templates/{template_id}", tags=["operator"])
async def update_operator_billing_template(template_id: int, payload: TemplatePayload, db: Session = Depends(get_db)):
    seed_runtime_data(db)
    record = next((item for item in template_store if item["id"] == template_id), None)
    if not record:
        return {"code": 404, "message": "template not found"}
    record.update(payload.model_dump())
    record["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {"code": 200, "message": "updated", "data": record}


@extra_api_router.get("/operator/customers/overview", tags=["operator"])
async def get_operator_customers_overview(db: Session = Depends(get_db)):
    operator = get_current_operator(db)
    if not operator:
        return {"code": 200, "data": {"members": [], "summary": {}}}
    fleets = db.query(Fleet).filter(Fleet.operator_id == operator.id).all()
    members = []
    for fleet in fleets:
        for member in fleet.members:
            members.append(
                {
                    "id": member.id,
                    "name": user_display_name(member),
                    "phone": member.phone,
                    "fleet_name": fleet.name,
                    "is_whitelist": fleet.is_whitelist,
                    "status": "blacklisted" if member.id in blacklist_store else "active",
                }
            )
    return {
        "code": 200,
        "data": {
            "members": members,
            "summary": {
                "fleet_count": len(fleets),
                "whitelist_count": sum(1 for fleet in fleets if fleet.is_whitelist),
                "member_count": len(members),
            },
        },
    }


@extra_api_router.get("/operator/customers/fleets", tags=["operator"])
async def get_operator_fleets(db: Session = Depends(get_db)):
    operator = get_current_operator(db)
    if not operator:
        return {"code": 200, "data": []}
    fleets = db.query(Fleet).filter(Fleet.operator_id == operator.id).order_by(Fleet.created_at.desc()).all()
    return {
        "code": 200,
        "data": [
            {
                "id": fleet.id,
                "name": fleet.name,
                "is_whitelist": fleet.is_whitelist,
                "member_count": len(fleet.members),
                "created_at": fleet.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for fleet in fleets
        ],
    }


@extra_api_router.post("/operator/customers/fleets", tags=["operator"])
async def create_operator_fleet(payload: FleetPayload, db: Session = Depends(get_db)):
    operator = get_current_operator(db)
    if not operator:
        return {"code": 404, "message": "operator not found"}
    fleet = Fleet(operator_id=operator.id, name=payload.name, is_whitelist=payload.is_whitelist)
    db.add(fleet)
    db.commit()
    db.refresh(fleet)
    return {"code": 200, "message": "created", "data": {"id": fleet.id, "name": fleet.name}}


@extra_api_router.get("/operator/customers/tags", tags=["operator"])
async def get_operator_tags(db: Session = Depends(get_db)):
    seed_runtime_data(db)
    return {"code": 200, "data": tag_store}


@extra_api_router.post("/operator/customers/tags", tags=["operator"])
async def create_operator_tag(payload: TagPayload, db: Session = Depends(get_db)):
    seed_runtime_data(db)
    next_id = max((item["id"] for item in tag_store), default=0) + 1
    record = payload.model_dump()
    record.update({"id": next_id, "user_count": 0})
    tag_store.insert(0, record)
    return {"code": 200, "message": "created", "data": record}


@extra_api_router.get("/operator/marketing/discounts", tags=["operator"])
async def get_operator_discounts(db: Session = Depends(get_db)):
    seed_runtime_data(db)
    return {"code": 200, "data": discount_campaign_store}


@extra_api_router.post("/operator/marketing/discounts", tags=["operator"])
async def create_operator_discount(payload: CampaignPayload, db: Session = Depends(get_db)):
    seed_runtime_data(db)
    next_id = max((item["id"] for item in discount_campaign_store), default=0) + 1
    record = payload.model_dump()
    sids = record.pop("station_ids", [])
    record.update({
        "id": next_id,
        "redeem_count": 0,
        "conversion_rate": 0,
        "station_ids": sids if sids else [],
        "station_names": record.get("station_names", "全部电站") or "全部电站",
    })
    discount_campaign_store.insert(0, record)
    marketing_audit_store[next_id] = {"status": "pending", "remark": ""}
    return {"code": 200, "message": "created", "data": record}


@extra_api_router.get("/operator/marketing/coupons", tags=["operator"])
async def get_operator_coupons(db: Session = Depends(get_db)):
    seed_runtime_data(db)
    return {"code": 200, "data": coupon_campaign_store}


@extra_api_router.post("/operator/marketing/coupons", tags=["operator"])
async def create_operator_coupon(payload: CampaignPayload, db: Session = Depends(get_db)):
    seed_runtime_data(db)
    next_id = max((item["id"] for item in coupon_campaign_store), default=0) + 1
    record = {
        "id": next_id,
        "name": payload.name,
        "discount_value": payload.discount_value,
        "inventory": 1000,
        "dispatched": 0,
        "used": 0,
        "status": payload.status,
    }
    coupon_campaign_store.insert(0, record)
    return {"code": 200, "message": "created", "data": record}


@extra_api_router.post("/operator/marketing/coupons/{campaign_id}/dispatch", tags=["operator"])
async def dispatch_operator_coupon(campaign_id: int, payload: CouponDispatchPayload, db: Session = Depends(get_db)):
    seed_runtime_data(db)
    record = next((item for item in coupon_campaign_store if item["id"] == campaign_id), None)
    if not record:
        return {"code": 404, "message": "coupon not found"}
    record["dispatched"] = min(record["inventory"], record["dispatched"] + payload.dispatch_count)
    return {"code": 200, "message": "dispatched", "data": record}


@extra_api_router.get("/operator/settings/profile", tags=["operator"])
async def get_operator_settings_profile(db: Session = Depends(get_db)):
    operator = get_current_operator(db)
    if not operator:
        return {"code": 404, "message": "operator not found"}
    return {
        "code": 200,
        "data": {
            "id": operator.id,
            "name": operator.name,
            "org_type": operator.org_type,
            "contact_email": f"ops-{operator.id}@echarge.com",
            "contact_phone": f"1380000{str(operator.id).zfill(4)}",
            "bank_account": operator.bank_account or "",
            "verified": operator.is_verified,
            "station_count": len(operator.stations),
            "fleet_count": len(operator.fleets),
        },
    }


@extra_api_router.put("/operator/settings/profile", tags=["operator"])
async def update_operator_settings_profile(payload: SettingsProfilePayload, db: Session = Depends(get_db)):
    operator = get_current_operator(db)
    if not operator:
        return {"code": 404, "message": "operator not found"}
    operator.name = payload.name
    operator.org_type = payload.org_type
    operator.bank_account = payload.bank_account
    db.commit()
    return {"code": 200, "message": "saved"}
