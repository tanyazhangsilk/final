import random
import uuid
from datetime import datetime, timedelta

from app.db.database import SessionLocal
from app.models.models import Charger, Operator, Order, User


def seed_extra():
    db = SessionLocal()
    try:
        user = db.query(User).first()
        charger = db.query(Charger).first()
        operator = db.query(Operator).first()

        if not all([user, charger, operator]):
            print("请先运行 seed_data.py 生成基础数据")
            return

        now = datetime.now()

        print("正在生成实时订单...")
        for _ in range(15):
            start = now - timedelta(minutes=random.randint(5, 120))
            total_kwh = round(random.uniform(5.0, 40.0), 2)
            ele_fee = round(random.uniform(10.0, 50.0), 2)
            service_fee = round(random.uniform(2.0, 15.0), 2)
            order = Order(
                order_no=f"RT{uuid.uuid4().hex[:12].upper()}",
                user_id=user.id,
                operator_id=operator.id,
                station_id=charger.station_id,
                charger_id=charger.id,
                vin=user.vin_code,
                start_time=start,
                charge_duration=random.randint(5, 120),
                total_kwh=total_kwh,
                ele_fee=ele_fee,
                service_fee=service_fee,
                total_fee=round(ele_fee + service_fee, 2),
                pay_status=0,
                status=0,
                settle_status=0,
            )
            db.add(order)

        print("正在生成异常订单...")
        for _ in range(10):
            start = now - timedelta(days=random.randint(1, 5), hours=random.randint(1, 10))
            end = start + timedelta(minutes=random.randint(1, 10))
            total_kwh = round(random.uniform(0.1, 2.0), 2)
            ele_fee = round(random.uniform(0.5, 3.0), 2)
            service_fee = round(random.uniform(0.2, 1.0), 2)
            order = Order(
                order_no=f"ERR{uuid.uuid4().hex[:12].upper()}",
                user_id=user.id,
                operator_id=operator.id,
                station_id=charger.station_id,
                charger_id=charger.id,
                vin=user.vin_code,
                start_time=start,
                end_time=end,
                charge_duration=int((end - start).total_seconds() / 60),
                total_kwh=total_kwh,
                ele_fee=ele_fee,
                service_fee=service_fee,
                total_fee=round(ele_fee + service_fee, 2),
                pay_status=0,
                status=2,
                abnormal_reason=random.choice(["设备离线断电", "用户账户余额不足", "枪头温度过高保护"]),
                settle_status=0,
            )
            db.add(order)

        db.commit()
        print("成功：实时订单与异常订单已入库")
    except Exception as e:
        db.rollback()
        print(f"失败: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_extra()
