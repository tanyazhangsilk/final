import logging

logger = logging.getLogger(__name__)


def send_invoice_email(
    *,
    to_email: str,
    invoice_no: str,
    status: str,
    operator_name: str,
    amount: float,
    file_url: str | None = None,
    remark: str | None = None,
) -> bool:
    """模拟发票通知邮件发送（当前先日志输出，后续可接入真实 SMTP/消息服务）。"""
    logger.info(
        "invoice_email_notify",
        extra={
            "to_email": to_email,
            "invoice_no": invoice_no,
            "status": status,
            "operator_name": operator_name,
            "amount": amount,
            "file_url": file_url,
            "remark": remark,
        },
    )
    return True
