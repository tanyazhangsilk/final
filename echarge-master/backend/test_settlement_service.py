import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.models import Base, Charger, Operator, Order, SettlementRecord, Station, User
from app.services.settlement_service import settle_t_plus_1


class SettlementServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autocommit=False, autoflush=False, future=True)

        self.db = self.Session()

        op = Operator(name="测试运营商", org_type="enterprise", is_verified=True)
        self.db.add(op)
        self.db.flush()

        station = Station(
            operator_id=op.id,
            template_id=None,
            name="测试电站",
            longitude=Decimal("113.0000000"),
            latitude=Decimal("22.0000000"),
            status=0,
            visibility="public",
        )
        self.db.add(station)
        self.db.flush()

        charger = Charger(
            station_id=station.id,
            sn_code="SN00000001",
            type="DC",
            status=0,
        )
        self.db.add(charger)
        self.db.flush()

        user = User(phone="13800138000", nickname="张三", password_hash="x", role="user")
        self.db.add(user)
        self.db.flush()

        self.operator_id = op.id
        self.station_id = station.id
        self.charger_id = charger.id
        self.user_id = user.id

        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def _create_completed_order(self, start_time: datetime, total_fee: Decimal, settle_status: int = 0) -> None:
        order = Order(
            order_no=f"ORD-{start_time.timestamp()}",
            user_id=self.user_id,
            charger_id=self.charger_id,
            operator_id=self.operator_id,
            start_time=start_time,
            end_time=start_time + timedelta(minutes=30),
            total_kwh=Decimal("10.00"),
            ele_fee=Decimal("10.00"),
            service_fee=Decimal("2.00"),
            total_fee=total_fee,
            status=1,
            settle_status=settle_status,
        )
        self.db.add(order)

    def test_settle_no_orders(self):
        target = date(2026, 3, 1)
        processed = settle_t_plus_1(target, db=self.db)
        self.assertEqual(processed, 0)
        self.assertEqual(self.db.query(SettlementRecord).count(), 0)

    def test_settle_creates_record_and_updates_orders(self):
        target = date(2026, 3, 1)
        self._create_completed_order(datetime(2026, 3, 1, 1, 0, 0), Decimal("100.00"))
        self._create_completed_order(datetime(2026, 3, 1, 12, 0, 0), Decimal("50.00"))
        self._create_completed_order(datetime(2026, 3, 1, 23, 59, 59), Decimal("25.50"))
        self.db.commit()

        processed = settle_t_plus_1(target, db=self.db)
        self.assertEqual(processed, 3)

        record = self.db.query(SettlementRecord).filter(SettlementRecord.settle_date == target).one()
        self.assertEqual(record.order_count, 3)
        self.assertEqual(Decimal(str(record.total_amount)), Decimal("175.50"))
        self.assertEqual(Decimal(str(record.platform_fee)), Decimal("17.55"))
        self.assertEqual(Decimal(str(record.settle_amount)), Decimal("157.95"))
        self.assertEqual(record.status, 0)

        unsettled = self.db.query(Order).filter(Order.settle_status == 0).count()
        self.assertEqual(unsettled, 0)

    def test_settle_is_idempotent(self):
        target = date(2026, 3, 1)
        self._create_completed_order(datetime(2026, 3, 1, 1, 0, 0), Decimal("100.00"))
        self.db.commit()

        processed1 = settle_t_plus_1(target, db=self.db)
        processed2 = settle_t_plus_1(target, db=self.db)

        self.assertEqual(processed1, 1)
        self.assertEqual(processed2, 0)
        self.assertEqual(self.db.query(SettlementRecord).count(), 1)


if __name__ == "__main__":
    unittest.main()

