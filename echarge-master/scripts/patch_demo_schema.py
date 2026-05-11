from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.database import SessionLocal, engine
from app.models.models import Base


MYSQL_CONFIG_HINT = (
    "数据库连接失败，请确认 MySQL 已启动，并检查 .env 中 "
    "MYSQL_HOST、MYSQL_PORT、MYSQL_USER、MYSQL_PASSWORD、MYSQL_DB 配置。"
)


TABLE_COLUMNS: dict[str, dict[str, str]] = {
    "trade_orders": {
        "pay_status": (
            "ALTER TABLE trade_orders "
            "ADD COLUMN pay_status INT NOT NULL DEFAULT 0 COMMENT '支付状态：0待支付，1已支付，2已退款' "
            "AFTER source_type"
        ),
        "settle_status": (
            "ALTER TABLE trade_orders "
            "ADD COLUMN settle_status INT NOT NULL DEFAULT 0 COMMENT '清分状态：0未清分，1已清分' "
            "AFTER abnormal_reason"
        ),
        "charge_duration": (
            "ALTER TABLE trade_orders "
            "ADD COLUMN charge_duration INT NULL COMMENT '充电时长分钟' "
            "AFTER end_time"
        ),
    },
    "trade_wallet_transactions": {
        "id": "ALTER TABLE trade_wallet_transactions ADD COLUMN id INT NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST",
        "user_id": "ALTER TABLE trade_wallet_transactions ADD COLUMN user_id INT NOT NULL COMMENT '用户ID' AFTER id",
        "transaction_type": (
            "ALTER TABLE trade_wallet_transactions "
            "ADD COLUMN transaction_type VARCHAR(20) NOT NULL DEFAULT 'consume' COMMENT '流水类型' AFTER user_id"
        ),
        "amount": (
            "ALTER TABLE trade_wallet_transactions "
            "ADD COLUMN amount DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '流水金额' AFTER transaction_type"
        ),
        "balance_after": (
            "ALTER TABLE trade_wallet_transactions "
            "ADD COLUMN balance_after DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '交易后余额' AFTER amount"
        ),
        "remark": "ALTER TABLE trade_wallet_transactions ADD COLUMN remark VARCHAR(255) NULL COMMENT '备注' AFTER balance_after",
        "related_order_id": (
            "ALTER TABLE trade_wallet_transactions "
            "ADD COLUMN related_order_id INT NULL COMMENT '关联订单ID' AFTER remark"
        ),
        "created_at": (
            "ALTER TABLE trade_wallet_transactions "
            "ADD COLUMN created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间' AFTER related_order_id"
        ),
    },
    "trade_invoices": {
        "id": "ALTER TABLE trade_invoices ADD COLUMN id INT NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST",
        "user_id": "ALTER TABLE trade_invoices ADD COLUMN user_id INT NOT NULL DEFAULT 0 COMMENT '用户ID' AFTER id",
        "operator_id": "ALTER TABLE trade_invoices ADD COLUMN operator_id INT NOT NULL DEFAULT 0 COMMENT '运营商ID' AFTER user_id",
        "order_id": "ALTER TABLE trade_invoices ADD COLUMN order_id INT NULL COMMENT '订单ID' AFTER operator_id",
        "invoice_title": "ALTER TABLE trade_invoices ADD COLUMN invoice_title VARCHAR(100) NULL COMMENT '发票抬头' AFTER order_id",
        "amount": "ALTER TABLE trade_invoices ADD COLUMN amount DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '发票金额' AFTER invoice_title",
        "email": "ALTER TABLE trade_invoices ADD COLUMN email VARCHAR(100) NOT NULL DEFAULT '' COMMENT '接收邮箱' AFTER amount",
        "status": "ALTER TABLE trade_invoices ADD COLUMN status INT NOT NULL DEFAULT 0 COMMENT '发票状态' AFTER email",
        "file_url": "ALTER TABLE trade_invoices ADD COLUMN file_url VARCHAR(255) NULL COMMENT '发票文件地址' AFTER status",
        "uploaded_at": "ALTER TABLE trade_invoices ADD COLUMN uploaded_at DATETIME NULL COMMENT '上传时间' AFTER file_url",
        "remark": "ALTER TABLE trade_invoices ADD COLUMN remark VARCHAR(255) NULL COMMENT '备注' AFTER uploaded_at",
        "created_at": "ALTER TABLE trade_invoices ADD COLUMN created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间' AFTER remark",
        "updated_at": "ALTER TABLE trade_invoices ADD COLUMN updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间' AFTER created_at",
        "is_deleted": "ALTER TABLE trade_invoices ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0 COMMENT '软删除' AFTER updated_at",
    },
    "trade_operator_settlements": {
        "id": "ALTER TABLE trade_operator_settlements ADD COLUMN id INT NOT NULL AUTO_INCREMENT PRIMARY KEY FIRST",
        "settle_date": "ALTER TABLE trade_operator_settlements ADD COLUMN settle_date DATE NOT NULL COMMENT '清分日期' AFTER id",
        "operator_id": "ALTER TABLE trade_operator_settlements ADD COLUMN operator_id INT NOT NULL DEFAULT 0 COMMENT '运营商ID' AFTER settle_date",
        "order_count": "ALTER TABLE trade_operator_settlements ADD COLUMN order_count INT NOT NULL DEFAULT 0 COMMENT '订单数' AFTER operator_id",
        "total_amount": "ALTER TABLE trade_operator_settlements ADD COLUMN total_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00 COMMENT '订单总额' AFTER order_count",
        "platform_rate": "ALTER TABLE trade_operator_settlements ADD COLUMN platform_rate DECIMAL(5,4) NOT NULL DEFAULT 0.1000 COMMENT '平台费率' AFTER total_amount",
        "platform_fee": "ALTER TABLE trade_operator_settlements ADD COLUMN platform_fee DECIMAL(12,2) NOT NULL DEFAULT 0.00 COMMENT '平台服务费' AFTER platform_rate",
        "settle_amount": "ALTER TABLE trade_operator_settlements ADD COLUMN settle_amount DECIMAL(12,2) NOT NULL DEFAULT 0.00 COMMENT '应结算金额' AFTER platform_fee",
        "status": "ALTER TABLE trade_operator_settlements ADD COLUMN status INT NOT NULL DEFAULT 0 COMMENT '清分状态' AFTER settle_amount",
        "hold_reason": "ALTER TABLE trade_operator_settlements ADD COLUMN hold_reason VARCHAR(255) NULL COMMENT '挂起原因' AFTER status",
        "created_at": "ALTER TABLE trade_operator_settlements ADD COLUMN created_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间' AFTER hold_reason",
        "updated_at": "ALTER TABLE trade_operator_settlements ADD COLUMN updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间' AFTER created_at",
    },
}


def _table_exists(conn, table_name: str) -> bool:
    return bool(
        conn.execute(
            text(
                """
                SELECT 1
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = :table_name
                LIMIT 1
                """
            ),
            {"table_name": table_name},
        ).first()
    )


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    return bool(
        conn.execute(
            text(
                """
                SELECT 1
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = :table_name
                  AND COLUMN_NAME = :column_name
                LIMIT 1
                """
            ),
            {"table_name": table_name, "column_name": column_name},
        ).first()
    )


def _ensure_columns(conn, table_name: str, columns: dict[str, str], messages: list[str]) -> None:
    if not _table_exists(conn, table_name):
        messages.append(f"{table_name} 表不存在，已由 SQLAlchemy create_all 尝试创建")
        return

    for column_name, ddl in columns.items():
        if _column_exists(conn, table_name, column_name):
            messages.append(f"{table_name}.{column_name} 已确认")
            continue
        conn.execute(text(ddl))
        messages.append(f"{table_name}.{column_name} 已补齐")


def ensure_demo_schema() -> list[str]:
    messages: list[str] = []
    try:
        Base.metadata.create_all(bind=engine)
        with engine.begin() as conn:
            for table_name, columns in TABLE_COLUMNS.items():
                _ensure_columns(conn, table_name, columns, messages)

            conn.execute(text("UPDATE trade_orders SET pay_status = 1 WHERE status = 1 AND pay_status = 0"))
            conn.execute(text("UPDATE trade_orders SET settle_status = 0 WHERE settle_status IS NULL"))
            messages.append("旧订单支付状态和清分状态已修复")

        from app.services.operator_audit_application_service import ensure_operator_audit_seed_rows

        db = SessionLocal()
        try:
            inserted = ensure_operator_audit_seed_rows(db)
            if inserted:
                messages.append(f"运营商入驻审核表 busi_operator_audit_applications 已写入 {inserted} 条演示申请")
            else:
                with engine.connect() as chk:
                    if _table_exists(chk, "busi_operator_audit_applications"):
                        messages.append("运营商入驻审核表已存在数据，跳过演示种子")
        finally:
            db.close()
    except OperationalError as exc:
        raise RuntimeError(MYSQL_CONFIG_HINT) from exc
    except SQLAlchemyError as exc:
        raise RuntimeError(f"数据库表结构修复失败：{exc}") from exc

    return messages


def main() -> None:
    try:
        messages = ensure_demo_schema()
    except RuntimeError as exc:
        print(str(exc))
        raise

    print("数据库结构检查完成")
    for message in messages:
        print(message)
    print("钱包、发票、清分表结构已确认")


if __name__ == "__main__":
    main()
