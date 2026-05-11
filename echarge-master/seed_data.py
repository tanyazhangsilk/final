import random
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from faker import Faker

from app.db.database import SessionLocal, engine
from app.models.models import Base, Charger, Invoice, Operator, Order, SettlementRecord, Station, User, WalletTransaction
from app.services.settlement_service import settle_t_plus_1

fake = Faker("zh_CN")


def generate_seed_data():
    db = SessionLocal()

    try:
        print("清理旧数据并重建表...")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        print("1. 生成运营商...")
        operators = []
        for _ in range(3):
            op = Operator(
                name=f"{fake.company()}新能源科技有限公司",
                org_type="enterprise",
                is_verified=True,
            )
            db.add(op)
            operators.append(op)
        db.commit()

        print("2. 生成充电站和充电桩...")
        chargers = []
        for i in range(15):
            op = random.choice(operators)
            if i < 10:
                status = 0
            elif i < 13:
                status = 3
            else:
                status = 4

            station = Station(
                operator_id=op.id,
                name=f"{fake.city()}{fake.street_name()}超级充电站",
                longitude=fake.longitude(),
                latitude=fake.latitude(),
                status=status,
            )
            db.add(station)
            db.flush()

            if status == 0:
                for _ in range(5):
                    charger = Charger(
                        station_id=station.id,
                        sn_code=f"SN{fake.random_number(digits=8, fix_len=True)}",
                        type=random.choice(["DC", "AC"]),
                        status=0,
                    )
                    db.add(charger)
                    chargers.append(charger)
        db.commit()

        print("3. 生成用户...")
        users = []
        for _ in range(100):
            user = User(
                phone=fake.unique.phone_number(),
                nickname=fake.name(),
                password_hash="mock_hash_123",
                vin_code=fake.bothify(text="LFM?????###########"),
                role="user",
            )
            db.add(user)
            users.append(user)
        db.commit()

        print("4. 生成订单（历史 / 实时 / 异常）...")
        now = datetime.now()

        for _ in range(200):
            user = random.choice(users)
            charger = random.choice(chargers)
            start_time = fake.date_time_between(start_date="-30d", end_date="now")
            end_time = start_time + timedelta(minutes=random.randint(20, 120))
            kwh = round(random.uniform(10.0, 60.0), 2)
            ele_fee = round(kwh * 0.95, 2)
            service_fee = round(kwh * 0.55, 2)

            order = Order(
                order_no=str(uuid.uuid4()).replace("-", ""),
                user_id=user.id,
                operator_id=charger.station.operator_id,
                station_id=charger.station_id,
                charger_id=charger.id,
                vin=user.vin_code,
                start_time=start_time,
                end_time=end_time,
                charge_duration=int((end_time - start_time).total_seconds() / 60),
                total_kwh=kwh,
                ele_fee=ele_fee,
                service_fee=service_fee,
                total_fee=round(ele_fee + service_fee, 2),
                pay_status=1,
                status=1,
                settle_status=random.choice([0, 1]),
            )
            db.add(order)

        for _ in range(10):
            user = random.choice(users)
            charger = random.choice(chargers)
            charger.status = 1
            start_time = now - timedelta(minutes=random.randint(1, 60))
            kwh = round(random.uniform(1.0, 20.0), 2)
            ele_fee = round(kwh * 0.9, 2)
            service_fee = round(kwh * 0.5, 2)

            order = Order(
                order_no=str(uuid.uuid4()).replace("-", ""),
                user_id=user.id,
                operator_id=charger.station.operator_id,
                station_id=charger.station_id,
                charger_id=charger.id,
                vin=user.vin_code,
                start_time=start_time,
                charge_duration=random.randint(1, 60),
                total_kwh=kwh,
                ele_fee=ele_fee,
                service_fee=service_fee,
                total_fee=round(ele_fee + service_fee, 2),
                pay_status=0,
                status=0,
                settle_status=0,
            )
            db.add(order)

        for _ in range(12):
            user = random.choice(users)
            charger = random.choice(chargers)
            start_time = fake.date_time_between(start_date="-15d", end_date="-1d")
            end_time = start_time + timedelta(minutes=random.randint(3, 20))
            kwh = round(random.uniform(0.5, 5.0), 2)
            ele_fee = round(kwh * 0.9, 2)
            service_fee = round(kwh * 0.4, 2)

            order = Order(
                order_no=f"ABN{uuid.uuid4().hex[:16].upper()}",
                user_id=user.id,
                operator_id=charger.station.operator_id,
                station_id=charger.station_id,
                charger_id=charger.id,
                vin=user.vin_code,
                start_time=start_time,
                end_time=end_time,
                charge_duration=int((end_time - start_time).total_seconds() / 60),
                total_kwh=kwh,
                ele_fee=ele_fee,
                service_fee=service_fee,
                total_fee=round(ele_fee + service_fee, 2),
                pay_status=0,
                status=2,
                abnormal_reason=random.choice(["设备离线断电", "通讯心跳超时", "结算扣款失败"]),
                settle_status=0,
            )
            db.add(order)

        db.flush()

        print("5. 生成钱包流水...")
        transaction_templates = [
            ("recharge", 200.00, "钱包充值"),
            ("pay", -36.80, "订单支付"),
            ("pay", -24.50, "订单支付"),
            ("refund", 12.00, "异常订单退款"),
        ]
        completed_orders = db.query(Order).filter(Order.status == 1).order_by(Order.created_at.asc()).limit(2).all()
        abnormal_order = db.query(Order).filter(Order.status == 2).order_by(Order.created_at.asc()).first()

        for index, user in enumerate(users[:8]):
            balance = Decimal("0.00")
            for tx_index, (tx_type, amount, remark) in enumerate(transaction_templates):
                order_ref = None
                if tx_type == "pay" and completed_orders:
                    order_ref = completed_orders[min(tx_index - 1, len(completed_orders) - 1)]
                elif tx_type == "refund":
                    order_ref = abnormal_order

                balance += Decimal(str(amount))
                wallet_tx = WalletTransaction(
                    user_id=user.id,
                    transaction_type=tx_type,
                    amount=Decimal(str(amount)),
                    balance_after=balance,
                    remark=f"{remark}{index + 1}",
                    related_order_id=order_ref.id if order_ref else None,
                    created_at=now - timedelta(days=max(0, 6 - index), hours=tx_index),
                )
                db.add(wallet_tx)

        print("6. 生成发票记录...")
        invoice_orders = db.query(Order).filter(Order.status == 1).order_by(Order.created_at.desc()).limit(6).all()
        for idx, order in enumerate(invoice_orders):
            invoice = Invoice(
                user_id=order.user_id,
                operator_id=order.operator_id,
                order_id=order.id,
                invoice_title=f"{users[idx % len(users)].nickname or '个人用户'}",
                amount=order.total_fee,
                email=f"user{idx + 1}@echarge.com",
                status=1 if idx < 3 else 0,
                file_url=f"https://static.echarge.local/invoices/invoice_{idx + 1}.pdf" if idx < 3 else None,
                remark="演示发票记录",
                uploaded_at=now - timedelta(days=idx) if idx < 3 else None,
            )
            db.add(invoice)

        db.commit()
        print("订单演示数据生成完成")

    except Exception as e:
        print(f"生成失败: {e}")
        db.rollback()
    finally:
        db.close()


def generate_wealth_data():
    db = SessionLocal()
    yesterday = date.today() - timedelta(days=1)

    print(f"正在为 {yesterday} 生成 100 笔完成订单...")

    try:
        users = db.query(User).all()
        chargers = db.query(Charger).all()

        if not users or not chargers:
            print("错误：数据库中没有用户或充电桩，请先运行基础种子")
            return

        for i in range(100):
            user = random.choice(users)
            charger = random.choice(chargers)
            random_hour = random.randint(0, 23)
            random_minute = random.randint(0, 59)
            start_time = datetime.combine(yesterday, time(random_hour, random_minute))
            duration = random.randint(30, 90)
            end_time = start_time + timedelta(minutes=duration)

            kwh = round(random.uniform(20.0, 80.0), 2)
            ele_fee = round(kwh * 1.2, 2)
            service_fee = round(kwh * 0.6, 2)

            new_order = Order(
                order_no=f"E{yesterday.strftime('%Y%m%d')}{i:04d}{random.randint(10, 99)}",
                user_id=user.id,
                operator_id=charger.station.operator_id,
                station_id=charger.station_id,
                charger_id=charger.id,
                vin=user.vin_code,
                start_time=start_time,
                end_time=end_time,
                charge_duration=duration,
                total_kwh=kwh,
                ele_fee=ele_fee,
                service_fee=service_fee,
                total_fee=ele_fee + service_fee,
                pay_status=1,
                status=1,
                settle_status=0,
            )
            db.add(new_order)

        db.commit()
        print("昨日完成订单已入库")

        processed = settle_t_plus_1(yesterday, db=db)
        record = db.query(SettlementRecord).filter(SettlementRecord.settle_date == yesterday).first()
        print(f"清分已执行：处理 {processed} 笔订单")
        if record:
            print(
                f"结算记录：date={record.settle_date}, order_count={record.order_count}, "
                f"total_amount={record.total_amount}, platform_fee={record.platform_fee}, "
                f"settle_amount={record.settle_amount}"
            )

    except Exception as e:
        db.rollback()
        print(f"生成失败: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    generate_seed_data()
    generate_wealth_data()
