import random
from datetime import datetime, timedelta
from app.db.database import SessionLocal
from app.models.models import Invoice, User, Operator

def seed_invoices():
    db = SessionLocal()
    try:
        user = db.query(User).first()
        operator = db.query(Operator).first()
        
        if not user or not operator:
            print("请先运行基础的 seed_data.py！")
            return

        now = datetime.now()
        emails = ["zhangsan@qq.com", "lisi@163.com", "wangwu@gmail.com", "finance@company.com"]
        
        # 生成 12 条发票数据 (包含待开票、已开票、驳回)
        for i in range(12):
            status = random.choice([0, 0, 0, 1, 1, 2]) # 0:申请中, 1:已开票, 2:已驳回 (增加待开票的概率)
            amount = round(random.uniform(50.0, 800.0), 2)
            created_at = now - timedelta(days=random.randint(0, 10), hours=random.randint(1, 12))
            
            invoice = Invoice(
                user_id=user.id,
                operator_id=operator.id,
                amount=amount,
                email=random.choice(emails),
                status=status,
                file_url="https://mock-invoice-url.com/inv.pdf" if status == 1 else None
            )
            # 为了让时间看起来分散，我们手动覆盖创建时间
            invoice.created_at = created_at
            db.add(invoice)
            
        db.commit()
        print("✅ 成功！模拟发票申请数据已入库！")
    except Exception as e:
        db.rollback()
        print(f"❌ 失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_invoices()