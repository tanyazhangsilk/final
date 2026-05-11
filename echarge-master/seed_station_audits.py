# seed_station_audits.py
import random
from datetime import datetime, timedelta
from app.db.database import SessionLocal
from app.models.models import Station, Operator

def seed_audits():
    db = SessionLocal()
    try:
        operator = db.query(Operator).first()
        if not operator:
            print("请先运行基础的 seed_data.py！")
            return

        now = datetime.now()
        
        # 模拟电站申请数据
        audit_data = [
            {"name": "南山科技园地下超充站", "status": 3, "days_ago": 0},
            {"name": "宝安中心区特惠充电站", "status": 3, "days_ago": 1},
            {"name": "福田高铁站临时配套站", "status": 4, "days_ago": 2}, # 4 表示已驳回
            {"name": "龙华大浪商业中心站", "status": 3, "days_ago": 0},
            {"name": "罗湖国贸大厦地面站", "status": 3, "days_ago": 3},
        ]
        
        print("正在生成电站审核工单...")
        for item in audit_data:
            created_at = now - timedelta(days=item["days_ago"], hours=random.randint(1, 12))
            
            station = Station(
                operator_id=operator.id,
                name=item["name"],
                longitude=round(random.uniform(113.8, 114.2), 6),
                latitude=round(random.uniform(22.5, 22.8), 6),
                status=item["status"], # 3:待审核, 4:已驳回
                visibility="private" # 审核通过前，对 C 端不可见
            )
            station.created_at = created_at
            db.add(station)
            
        db.commit()
        print("✅ 成功！待审核电站已入库！")
    except Exception as e:
        db.rollback()
        print(f"❌ 失败: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_audits()