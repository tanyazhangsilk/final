"""运营商入驻审核申请：列表、详情序列化、审核处理。"""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import engine
from app.models.models import Base, Operator, OperatorAuditApplication, User


def _loads_json(raw: str | None, default: Any) -> Any:
    if not raw or not str(raw).strip():
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def _dt_fmt(value: datetime | None) -> str:
    if not value:
        return ""
    return value.strftime("%Y-%m-%d %H:%M")


def serialize_operator_audit_application(app: OperatorAuditApplication) -> dict[str, Any]:
    """转为前端 OperatorAuditRecord 形状（camelCase + 嵌套数组）。"""
    return {
        "id": str(app.id),
        "applicationNo": app.application_no,
        "operatorName": app.operator_name,
        "companyName": app.company_name,
        "contactName": app.contact_name,
        "phone": app.phone,
        "email": app.email,
        "region": app.region,
        "address": app.address,
        "creditCode": app.credit_code,
        "foundedAt": app.founded_at or "",
        "stationCount": int(app.station_count or 0),
        "chargerCount": int(app.charger_count or 0),
        "serviceCities": _loads_json(app.service_cities_json, []),
        "description": app.description or "",
        "attachments": _loads_json(app.attachments_json, []),
        "status": app.status,
        "submittedAt": _dt_fmt(app.submitted_at),
        "reviewedBy": app.reviewed_by or "",
        "reviewedAt": _dt_fmt(app.reviewed_at) if app.reviewed_at else "",
        "reviewComment": app.review_comment or "",
        "lastProcessedBy": app.last_processed_by or "",
        "lastProcessedAt": _dt_fmt(app.last_processed_at) if app.last_processed_at else "",
        "auditTimeline": _loads_json(app.audit_timeline_json, []),
    }


def _missing_operator_audit_table(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "busi_operator_audit_applications" in msg and (
        "doesn't exist" in msg or "1146" in msg or "不存在" in msg or "no such table" in msg
    )


def _fetch_audit_rows(db: Session) -> list[OperatorAuditApplication]:
    return (
        db.query(OperatorAuditApplication)
        .filter(OperatorAuditApplication.is_deleted.is_(False))
        .order_by(OperatorAuditApplication.submitted_at.desc(), OperatorAuditApplication.id.desc())
        .all()
    )


def list_operator_audit_applications(db: Session) -> list[dict[str, Any]]:
    """列表；表不存在时尝试建表，空表时写入种子数据（与迁移 / patch_demo_schema 一致）。"""
    try:
        rows = _fetch_audit_rows(db)
    except SQLAlchemyError as exc:
        if not _missing_operator_audit_table(exc):
            raise
        db.rollback()
        Base.metadata.create_all(bind=engine, tables=[OperatorAuditApplication.__table__])
        rows = _fetch_audit_rows(db)

    result = [serialize_operator_audit_application(r) for r in rows]
    if not result:
        ensure_operator_audit_seed_rows(db)
        rows = _fetch_audit_rows(db)
        result = [serialize_operator_audit_application(r) for r in rows]
    return result


def process_operator_audit_application(
    db: Session,
    *,
    application_id: int,
    action: str,
    remark: str,
    reviewer_label: str = "平台管理员 / 当前登录账号",
) -> dict[str, Any] | None:
    action = (action or "").strip().lower()
    if action not in {"approve", "reject"}:
        return None

    app = (
        db.query(OperatorAuditApplication)
        .filter(OperatorAuditApplication.id == application_id, OperatorAuditApplication.is_deleted.is_(False))
        .first()
    )
    if not app:
        return None

    if app.status != "pending":
        return {"error": "not_pending", "message": "该申请不在待审核状态，无法重复审核"}

    timeline: list[dict[str, Any]] = _loads_json(app.audit_timeline_json, [])
    # 去掉历史「终审」节点，与前端替换逻辑一致
    timeline = [n for n in timeline if n.get("status") not in {"approved", "rejected"}]

    reviewed_at = datetime.now()
    reviewed_at_ui = reviewed_at.strftime("%Y-%m-%d %H:%M")
    new_status = "approved" if action == "approve" else "rejected"
    node = {
        "id": f"timeline-{application_id}-{int(time.time() * 1000)}",
        "title": "审核通过" if action == "approve" else "审核驳回",
        "time": reviewed_at_ui,
        "operator": reviewer_label,
        "status": new_status,
        "comment": (remark or "").strip(),
    }
    timeline.append(node)

    app.status = new_status
    app.reviewed_by = reviewer_label
    app.reviewed_at = reviewed_at
    app.review_comment = (remark or "").strip()
    app.last_processed_by = reviewer_label
    app.last_processed_at = reviewed_at
    app.audit_timeline_json = json.dumps(timeline, ensure_ascii=False)

    if action == "approve":
        try:
            # 1. 查找或创建对应的运营商主体
            op = None
            if app.linked_operator_id:
                op = db.query(Operator).filter(Operator.id == app.linked_operator_id).first()
            if not op:
                op = Operator(
                    name=app.operator_name or app.company_name or app.contact_name,
                    org_type="enterprise",
                    is_verified=True,
                    bank_account="",
                )
                db.add(op)
                db.flush()
                app.linked_operator_id = op.id
            else:
                op.is_verified = True

            # 2. 查找或创建申请用户
            phone = (app.phone or "").strip()
            if not phone:
                return {"error": "invalid", "message": "申请手机号为空，无法创建用户"}
            user = db.query(User).filter(User.phone == phone).first()
            if not user:
                # 检查是否有已删除的同号码用户
                deleted_user = db.query(User).filter(
                    User.phone == phone, User.is_deleted.is_(True)
                ).first()
                if deleted_user:
                    deleted_user.is_deleted = False
                    deleted_user.role = "operator"
                    deleted_user.password_hash = "123456"
                    user = deleted_user
                else:
                    user = User(
                        phone=phone,
                        nickname=app.contact_name or app.operator_name or f"运营商{phone[-4:]}",
                        password_hash="123456",
                        role="operator",
                        vin_code=f"OP{phone[-4:]}{int(time.time()) % 100000}",
                    )
                    db.add(user)
                db.flush()
            elif user.role != "admin":
                if user.is_deleted:
                    user.is_deleted = False
                user.role = "operator"

            # 3. 确保运营商名称来自用户
            if not op.name or op.name == phone:
                op.name = user.nickname or f"运营商{phone[-4:]}"
        except SQLAlchemyError as exc:
            db.rollback()
            return {"error": "db_error", "message": f"数据库操作失败: {exc}"}

    db.add(app)
    db.commit()
    db.refresh(app)
    return {"record": serialize_operator_audit_application(app)}


def create_operator_audit_application(db: Session, *, data: dict[str, Any]) -> dict[str, Any]:
    """新建一条待审核申请。返回 {\"record\": ...} 或 {\"error\": \"...\", \"message\": \"...\"}。"""
    application_no = (data.get("application_no") or "").strip()
    if not application_no:
        return {"error": "invalid", "message": "申请编号 application_no 不能为空"}
    dup = (
        db.query(OperatorAuditApplication)
        .filter(
            OperatorAuditApplication.application_no == application_no,
            OperatorAuditApplication.is_deleted.is_(False),
        )
        .first()
    )
    if dup:
        return {"error": "duplicate", "message": "申请编号已存在"}

    contact_name = (data.get("contact_name") or "").strip()
    operator_name = (data.get("operator_name") or "").strip()
    submitted_at = datetime.now()
    submitted_ui = submitted_at.strftime("%Y-%m-%d %H:%M")
    timeline = [
        {
            "id": f"timeline-new-{int(time.time() * 1000)}",
            "title": "提交申请",
            "time": submitted_ui,
            "operator": f"{contact_name} / {operator_name}".strip(" /"),
            "status": "pending",
            "comment": (data.get("submit_comment") or "提交运营商入驻申请。").strip(),
        }
    ]
    service_cities = data.get("service_cities") or []
    attachments = data.get("attachments") or []

    app = OperatorAuditApplication(
        application_no=application_no,
        operator_name=operator_name or data.get("company_name") or application_no,
        company_name=(data.get("company_name") or operator_name or application_no).strip(),
        contact_name=contact_name,
        phone=(data.get("phone") or "").strip(),
        email=(data.get("email") or "").strip(),
        region=(data.get("region") or "").strip(),
        address=(data.get("address") or "").strip(),
        credit_code=(data.get("credit_code") or "").strip(),
        founded_at=(data.get("founded_at") or None),
        station_count=int(data.get("station_count") or 0),
        charger_count=int(data.get("charger_count") or 0),
        service_cities_json=json.dumps(service_cities, ensure_ascii=False),
        description=(data.get("description") or "").strip(),
        attachments_json=json.dumps(attachments, ensure_ascii=False),
        audit_timeline_json=json.dumps(timeline, ensure_ascii=False),
        status="pending",
        submitted_at=submitted_at,
        reviewed_by=None,
        reviewed_at=None,
        review_comment=None,
        last_processed_by="系统",
        last_processed_at=submitted_at,
        linked_operator_id=data.get("linked_operator_id"),
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return {"record": serialize_operator_audit_application(app)}


def ensure_operator_audit_seed_rows(db: Session) -> int:
    """若表为空则写入默认演示数据（迁移已插入时可跳过）。返回新增条数。"""
    from app.data.operator_audit_application_seed import OPERATOR_AUDIT_APPLICATION_SEED

    existing = db.query(OperatorAuditApplication).filter(OperatorAuditApplication.is_deleted.is_(False)).count()
    if existing:
        return 0

    inserted = 0
    for row in OPERATOR_AUDIT_APPLICATION_SEED:
        submitted_at = datetime.strptime(str(row["submitted_at"]), "%Y-%m-%d %H:%M:%S")
        reviewed_at = None
        if row.get("reviewed_at"):
            reviewed_at = datetime.strptime(str(row["reviewed_at"]), "%Y-%m-%d %H:%M:%S")
        last_processed_at = None
        if row.get("last_processed_at"):
            last_processed_at = datetime.strptime(str(row["last_processed_at"]), "%Y-%m-%d %H:%M:%S")

        app = OperatorAuditApplication(
            application_no=row["application_no"],
            operator_name=row["operator_name"],
            company_name=row["company_name"],
            contact_name=row["contact_name"],
            phone=row["phone"],
            email=row["email"],
            region=row["region"],
            address=row["address"],
            credit_code=row["credit_code"],
            founded_at=row.get("founded_at"),
            station_count=int(row.get("station_count") or 0),
            charger_count=int(row.get("charger_count") or 0),
            service_cities_json=json.dumps(row.get("service_cities") or [], ensure_ascii=False),
            description=row.get("description") or "",
            attachments_json=json.dumps(row.get("attachments") or [], ensure_ascii=False),
            audit_timeline_json=json.dumps(row.get("audit_timeline") or [], ensure_ascii=False),
            status=row.get("status") or "pending",
            submitted_at=submitted_at,
            reviewed_by=(row.get("reviewed_by") or None) or None,
            reviewed_at=reviewed_at,
            review_comment=(row.get("review_comment") or None) or None,
            last_processed_by=(row.get("last_processed_by") or None) or None,
            last_processed_at=last_processed_at,
            linked_operator_id=row.get("linked_operator_id"),
        )
        db.add(app)
        inserted += 1
    if inserted:
        db.commit()
    return inserted
