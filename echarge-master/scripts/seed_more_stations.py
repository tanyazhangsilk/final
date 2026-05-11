"""
为充电聚合平台添加更多种子充电站/电桩数据。
在本项目中，通过 python scripts/seed_more_stations.py 执行。
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.database import SessionLocal
from app.models.models import Charger, Operator, PriceTemplate, Station
from sqlalchemy.orm import noload


OPERATOR_NAME = "毕业设计演示运营商"

STATIONS_DATA = [
    # (name, city, district, address, lng, lat, dc_count, ac_count, dc_power, ac_power, price)
    ("天府软件园综合充电站", "成都市", "高新区", "天府五街 200 号地下停车场 B1", 104.0621, 30.5442, 8, 4, 120, 7, 1.42),
    ("环球中心北广场充电站", "成都市", "高新区", "天府大道北段 1700 号 P2 停车区", 104.0678, 30.5730, 5, 3, 180, 7, 1.55),
    ("东客站出行服务充电站", "成都市", "成华区", "迎晖路 8 号东广场停车楼 1 层", 104.1456, 30.6368, 4, 6, 90, 7, 1.36),
    ("金融城商务区充电站", "成都市", "高新区", "交子大道 333 号 A 座地下停车场", 104.0708, 30.5500, 4, 2, 120, 60, 1.68),
    ("深圳科技园南充电站", "深圳市", "南山区", "科技南路 88 号地下停车场", 113.9530, 22.5370, 6, 4, 120, 7, 1.32),
    ("福田CBD卓悦中心充电站", "深圳市", "福田区", "福华一路 168 号卓悦中心 B2", 114.0695, 22.5380, 8, 2, 150, 7, 1.48),
    ("宝安中心区充电站", "深圳市", "宝安区", "创业一路 88 号宝安体育馆停车场", 113.8860, 22.5550, 4, 6, 90, 7, 1.22),
    ("广州天河城充电站", "广州市", "天河区", "天河路 188 号天河城 B3", 113.3300, 23.1320, 6, 4, 120, 7, 1.45),
    ("广州科学城充电站", "广州市", "黄埔区", "科学大道 288 号创新大厦停车场", 113.4670, 23.1780, 5, 3, 90, 7, 1.28),
    ("杭州西湖文化广场充电站", "杭州市", "下城区", "西湖文化广场地下停车场", 120.1670, 30.2830, 6, 2, 120, 7, 1.40),
    ("杭州滨江物联网街充电站", "杭州市", "滨江区", "江南大道 618 号停车场", 120.2120, 30.2070, 8, 2, 150, 7, 1.52),
    ("上海浦东陆家嘴充电站", "上海市", "浦东新区", "世纪大道 100 号地下停车场", 121.5050, 31.2400, 10, 4, 160, 7, 1.65),
    ("上海虹桥枢纽充电站", "上海市", "闵行区", "虹桥火车站 P9 停车场", 121.3350, 31.1950, 12, 4, 120, 7, 1.58),
    ("北京中关村充电站", "北京市", "海淀区", "中关村大街 66 号创新工场 B2", 116.3180, 39.9830, 6, 4, 120, 7, 1.50),
    ("北京望京商务区充电站", "北京市", "朝阳区", "望京 SOHO B1 停车场", 116.4800, 39.9960, 8, 4, 150, 7, 1.62),
]

# 电价模板规则 (同一运营商使用不同模板)
TEMPLATES = {
    "城市快充标准模板": {
        "peak_price": 1.88, "flat_price": 1.34, "valley_price": 0.76, "service_price": 0.80,
        "scope": "全站", "status": "active",
    },
    "园区夜充模板": {
        "peak_price": 1.56, "flat_price": 1.12, "valley_price": 0.58, "service_price": 0.65,
        "scope": "指定站点", "status": "active",
    },
    "商务区经济模板": {
        "peak_price": 1.72, "flat_price": 1.28, "valley_price": 0.68, "service_price": 0.72,
        "scope": "全站", "status": "active",
    },
}

# 模板名称到站点的映射（交替使用不同模板）
STATION_TEMPLATE_MAP = [
    "城市快充标准模板",
    "城市快充标准模板",
    "园区夜充模板",
    "商务区经济模板",
    "城市快充标准模板",
    "城市快充标准模板",
    "园区夜充模板",
    "商务区经济模板",
    "园区夜充模板",
    "城市快充标准模板",
    "城市快充标准模板",
    "商务区经济模板",
    "城市快充标准模板",
    "园区夜充模板",
    "商务区经济模板",
]


def main():
    db = SessionLocal()
    try:
        operator = db.query(Operator).options(noload("*")).filter(Operator.name == OPERATOR_NAME).first()
        if not operator:
            operator = Operator(name=OPERATOR_NAME, org_type="enterprise", is_verified=True)
            db.add(operator)
            db.flush()
            print(f"创建运营商: {operator.name} (id={operator.id})")
        else:
            print(f"使用已有运营商: {operator.name} (id={operator.id})")

        # 确保模板存在
        template_map = {}
        for tpl_name, tpl_rules in TEMPLATES.items():
            tpl = db.query(PriceTemplate).options(noload("*")).filter(
                PriceTemplate.operator_id == operator.id,
                PriceTemplate.name == tpl_name,
            ).first()
            if not tpl:
                import json
                tpl = PriceTemplate(
                    operator_id=operator.id,
                    name=tpl_name,
                    rules_json=json.dumps(tpl_rules, ensure_ascii=False),
                )
                db.add(tpl)
                db.flush()
                print(f"创建模板: {tpl_name}")
            template_map[tpl_name] = tpl

        # 创建充电站
        now = datetime.now()
        created_count = 0
        for idx, (name, city, district, address, lng, lat, dc_count, ac_count, dc_power, ac_power, price) in enumerate(STATIONS_DATA):
            existing = db.query(Station).options(noload("*")).filter(
                Station.name == name,
                Station.operator_id == operator.id,
                Station.is_deleted.is_(False),
            ).first()
            if existing:
                continue

            province = "广东省"
            for prov, city_list in [("四川省", ["成都市"]), ("广东省", ["深圳市", "广州市"]), ("浙江省", ["杭州市"]), ("上海市", ["上海市"]), ("北京市", ["北京市"])]:
                if city in city_list:
                    province = prov
                    break

            tpl_name = STATION_TEMPLATE_MAP[idx]
            tpl = template_map.get(tpl_name)

            station = Station(
                operator_id=operator.id,
                template_id=tpl.id if tpl else None,
                name=name,
                province=province,
                city=city,
                district=district,
                address=address,
                longitude=Decimal(str(lng)),
                latitude=Decimal(str(lat)),
                contact_name="站内客服",
                contact_phone="400-800-1024",
                operation_hours="00:00-24:00",
                parking_fee_desc="首小时免费，后续视商场规则",
                station_remark="聚合充电平台演示站点",
                planned_charger_count=dc_count + ac_count,
                total_power_kw=Decimal(str(dc_count * dc_power + ac_count * ac_power)),
                cover_image="",
                parking_slot_count=dc_count + ac_count + 2,
                service_radius_km=Decimal("3.00"),
                support_vehicle_types_json='["纯电动", "插电混动"]',
                facility_tags_json='["快充", "慢充", "24小时", "停车便利"]',
                status=0,
                visibility="public",
                audit_remark="自动审核通过",
            )
            db.add(station)
            db.flush()

            # 创建电桩
            for di in range(dc_count):
                sn = f"DC-{station.id:03d}-{di+1:03d}"
                charger = Charger(
                    station_id=station.id,
                    sn_code=sn,
                    name=f"{station.name[:10]}-{di+1:02d}号快充桩",
                    type="DC",
                    power_kw=Decimal(str(dc_power)),
                    status=0,
                )
                db.add(charger)

            for ai in range(ac_count):
                sn = f"AC-{station.id:03d}-{ai+1:03d}"
                charger = Charger(
                    station_id=station.id,
                    sn_code=sn,
                    name=f"{station.name[:10]}-{dc_count+ai+1:02d}号慢充桩",
                    type="AC",
                    power_kw=Decimal(str(ac_power)),
                    status=0 if ai < ac_count // 2 else 2,
                )
                db.add(charger)

            created_count += 1
            print(f"创建站点: {station.name} ({city}{district}) - {dc_count}直流+{ac_count}交流桩")

        db.commit()
        print(f"\n✅ 种子数据添加完成！")
        print(f"   新增站点: {created_count}")
        print(f"   总站点数: {db.query(Station).filter(Station.operator_id == operator.id, Station.is_deleted.is_(False)).count()}")
        total_chargers = db.query(Charger).filter(Charger.is_deleted.is_(False)).count()
        print(f"   总电桩数: {total_chargers}")
    except Exception as exc:
        db.rollback()
        print(f"❌ 失败: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
