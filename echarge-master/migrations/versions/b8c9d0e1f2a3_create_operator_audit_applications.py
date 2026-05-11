"""create busi_operator_audit_applications + seed demo rows

Revision ID: b8c9d0e1f2a3
Revises: a3f4c5d6e7b8
Create Date: 2026-05-08 12:00:00.000000
"""

from __future__ import annotations

import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.data.operator_audit_application_seed import OPERATOR_AUDIT_APPLICATION_SEED


revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "a3f4c5d6e7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "busi_operator_audit_applications" in inspector.get_table_names():
        return

    op.create_table(
        "busi_operator_audit_applications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="primary key"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="created at"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP"), comment="updated at"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0"), comment="soft delete"),
        sa.Column("application_no", sa.String(length=40), nullable=False, comment="application number"),
        sa.Column("operator_name", sa.String(length=200), nullable=False, comment="operator display name"),
        sa.Column("company_name", sa.String(length=200), nullable=False, comment="company legal name"),
        sa.Column("contact_name", sa.String(length=50), nullable=False, comment="contact name"),
        sa.Column("phone", sa.String(length=30), nullable=False, comment="contact phone"),
        sa.Column("email", sa.String(length=120), nullable=False, comment="contact email"),
        sa.Column("region", sa.String(length=200), nullable=False, comment="service region text"),
        sa.Column("address", sa.Text(), nullable=False, comment="registered address"),
        sa.Column("credit_code", sa.String(length=30), nullable=False, comment="unified social credit code"),
        sa.Column("founded_at", sa.String(length=20), nullable=True, comment="founded date text"),
        sa.Column("station_count", sa.Integer(), nullable=False, server_default="0", comment="declared station count"),
        sa.Column("charger_count", sa.Integer(), nullable=False, server_default="0", comment="declared gun count"),
        sa.Column("service_cities_json", sa.Text(), nullable=False, comment="service cities json array"),
        sa.Column("description", sa.Text(), nullable=False, comment="business description"),
        sa.Column("attachments_json", sa.Text(), nullable=False, comment="attachments json"),
        sa.Column("audit_timeline_json", sa.Text(), nullable=False, comment="audit timeline json"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending", comment="pending approved rejected"),
        sa.Column("submitted_at", sa.DateTime(), nullable=False, comment="submitted at"),
        sa.Column("reviewed_by", sa.String(length=120), nullable=True, comment="reviewer label"),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True, comment="reviewed at"),
        sa.Column("review_comment", sa.Text(), nullable=True, comment="review comment"),
        sa.Column("last_processed_by", sa.String(length=120), nullable=True, comment="last actor"),
        sa.Column("last_processed_at", sa.DateTime(), nullable=True, comment="last action time"),
        sa.Column("linked_operator_id", sa.Integer(), nullable=True, comment="linked sys operator when applicable"),
        sa.ForeignKeyConstraint(["linked_operator_id"], ["sys_operators.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("application_no", name="uq_operator_audit_application_no"),
    )
    op.create_index("ix_operator_audit_app_credit", "busi_operator_audit_applications", ["credit_code"], unique=False)
    op.create_index("ix_operator_audit_app_status", "busi_operator_audit_applications", ["status"], unique=False)
    op.create_index("ix_operator_audit_app_submitted", "busi_operator_audit_applications", ["submitted_at"], unique=False)
    op.create_index("ix_busi_operator_audit_applications_linked_operator_id", "busi_operator_audit_applications", ["linked_operator_id"], unique=False)

    conn = op.get_bind()
    for row in OPERATOR_AUDIT_APPLICATION_SEED:
        conn.execute(
            sa.text(
                """
                INSERT INTO busi_operator_audit_applications (
                    application_no, operator_name, company_name, contact_name, phone, email, region, address,
                    credit_code, founded_at, station_count, charger_count, service_cities_json, description,
                    attachments_json, audit_timeline_json, status, submitted_at, reviewed_by, reviewed_at,
                    review_comment, last_processed_by, last_processed_at, linked_operator_id, is_deleted
                ) VALUES (
                    :application_no, :operator_name, :company_name, :contact_name, :phone, :email, :region, :address,
                    :credit_code, :founded_at, :station_count, :charger_count, :service_cities_json, :description,
                    :attachments_json, :audit_timeline_json, :status, :submitted_at, :reviewed_by, :reviewed_at,
                    :review_comment, :last_processed_by, :last_processed_at, :linked_operator_id, 0
                )
                """
            ),
            {
                "application_no": row["application_no"],
                "operator_name": row["operator_name"],
                "company_name": row["company_name"],
                "contact_name": row["contact_name"],
                "phone": row["phone"],
                "email": row["email"],
                "region": row["region"],
                "address": row["address"],
                "credit_code": row["credit_code"],
                "founded_at": row.get("founded_at"),
                "station_count": int(row.get("station_count") or 0),
                "charger_count": int(row.get("charger_count") or 0),
                "service_cities_json": json.dumps(row.get("service_cities") or [], ensure_ascii=False),
                "description": row.get("description") or "",
                "attachments_json": json.dumps(row.get("attachments") or [], ensure_ascii=False),
                "audit_timeline_json": json.dumps(row.get("audit_timeline") or [], ensure_ascii=False),
                "status": row.get("status") or "pending",
                "submitted_at": row["submitted_at"],
                "reviewed_by": (row.get("reviewed_by") or None) or None,
                "reviewed_at": row.get("reviewed_at"),
                "review_comment": (row.get("review_comment") or None) or None,
                "last_processed_by": (row.get("last_processed_by") or None) or None,
                "last_processed_at": row.get("last_processed_at"),
                "linked_operator_id": row.get("linked_operator_id"),
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "busi_operator_audit_applications" not in inspector.get_table_names():
        return

    op.drop_index("ix_busi_operator_audit_applications_linked_operator_id", table_name="busi_operator_audit_applications")
    op.drop_index("ix_operator_audit_app_submitted", table_name="busi_operator_audit_applications")
    op.drop_index("ix_operator_audit_app_status", table_name="busi_operator_audit_applications")
    op.drop_index("ix_operator_audit_app_credit", table_name="busi_operator_audit_applications")
    op.drop_table("busi_operator_audit_applications")
