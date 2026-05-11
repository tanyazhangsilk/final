"""
充电状态实时模拟模块。
供小程序充电监控页面轮询，模拟充电进度（电量、功率、时间、费用）。
每 3 秒调用一次，返回当前充电订单的实时状态快照。
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.db.database import get_db
from app.models.models import Charger, Order, Station
from app.services.order_service import (
    get_station_name,
    order_duration_minutes,
    serialize_order,
)
from app.services.wallet_flow_service import get_user_balance
from app.services.wallet_flow_service import create_wallet_consume_record

sim_api_router = APIRouter(tags=["charging-sim"])

# 充电进度缓存：order_id -> progress dict
_charging_progress: dict[int, dict[str, Any]] = {}

# 每 3 秒轮询，60/3 = 20 次 = 每分钟增长 1 分钟
# 所以每个 step 按 0.05 分钟模拟
STEP_MINUTES = 0.05


def _get_or_init_progress(order_id: int, order: Order) -> dict[str, Any]:
    if order_id in _charging_progress:
        return _charging_progress[order_id]

    start_soc = random.randint(15, 35)
    target_soc = random.randint(85, 98)
    battery_capacity_kwh = 60.0  # 典型电动汽车电池容量 (kWh)

    max_power_kw = 60.0
    if order.charger and order.charger.power_kw:
        max_power_kw = float(order.charger.power_kw) * 0.85
    if max_power_kw < 10:
        max_power_kw = 60.0

    # 从订单已有数据初始化
    initial_kwh = max(float(order.total_kwh or 0), 1.0)
    init_soc = min(start_soc + int(initial_kwh / battery_capacity_kwh * 100), target_soc)

    prog = {
        "current_soc": max(start_soc, init_soc),
        "target_soc": target_soc,
        "max_power_kw": max_power_kw,
        "current_power_kw": min(max_power_kw, 40 + random.random() * (max_power_kw - 40)),
        "battery_capacity_kwh": battery_capacity_kwh,
        "start_soc": start_soc,
        "sim_start": datetime.now(),
        "accumulated_minutes": 0.0,          # 模拟累计充电时长
        "current_energy_kwh": initial_kwh,   # 当前累计电量
        "flat_price": 1.18,                   # 电价
        "service_price": 0.72,                # 服务费
    }

    # 从模板解析价格
    if order.station and order.station.price_template:
        try:
            import json
            rules = json.loads(order.station.price_template.rules_json)
            avg = (float(rules.get("flat_price", 1.18)) + float(rules.get("valley_price", 0.68))) / 2
            srv = float(rules.get("service_price", 0.72))
            prog["flat_price"] = avg
            prog["service_price"] = srv
        except Exception:
            pass

    _charging_progress[order_id] = prog
    return prog


def _clear_progress(order_id: int):
    _charging_progress.pop(order_id, None)


@sim_api_router.get("/charging/status/{order_id}")
async def get_charging_status(
    order_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """充电监控轮询接口：返回实时充电状态。每次调用推进 ~0.05 分钟的模拟进度。"""
    order = (
        db.query(Order)
        .options(
            joinedload(Order.user),
            joinedload(Order.operator),
            joinedload(Order.station).joinedload(Station.price_template),
            joinedload(Order.charger),
        )
        .filter(Order.id == order_id)
        .first()
    )

    if not order:
        return {"code": 404, "message": "订单不存在", "data": None}

    if order.status == 1:
        _clear_progress(order_id)
        return {
            "code": 200, "message": "充电已完成",
            "data": {"charging": False, "finished": True, "order": serialize_order(order)},
        }
    elif order.status == 2:
        _clear_progress(order_id)
        return {
            "code": 200, "message": "充电异常结束",
            "data": {"charging": False, "finished": True, "abnormal": True, "order": serialize_order(order)},
        }

    if order.status != 0:
        return {"code": 200, "message": "订单未在充电中", "data": {"charging": False, "finished": False}}

    # ---------- 充电中状态 - 模拟实时进度 ----------
    prog = _get_or_init_progress(order_id, order)

    # 推进模拟累积时间（每次轮询 +STEP_MINUTES）
    prog["accumulated_minutes"] += STEP_MINUTES

    # 电池容量参数
    bat_cap = prog["battery_capacity_kwh"]
    start_soc = prog["start_soc"]
    target_soc = prog["target_soc"]
    max_power = prog["max_power_kw"]

    # 计算当前 SOC 和能量
    # 可用总能量 = 电池容量 * (target_soc - start_soc) / 100
    total_usable_kwh = bat_cap * (target_soc - start_soc) / 100.0

    # 充电速率：前 80% 满速，后 20% 线性衰减
    charged_fraction = min(prog["accumulated_minutes"] / (total_usable_kwh / (max_power * 0.55) * 60), 1.0)
    if charged_fraction < 0.8:
        power_factor = 1.0
    else:
        power_factor = max(1.0 - (charged_fraction - 0.8) / 0.2 * 0.6, 0.3)

    current_power = max_power * 0.55 * power_factor

    # 累计电量 = 电池容量 * 充电比例
    current_energy_kwh = total_usable_kwh * charged_fraction
    current_soc = start_soc + int((target_soc - start_soc) * min(charged_fraction, 1.0))
    current_soc = min(current_soc, target_soc)

    # 费用计算
    flat_price = prog["flat_price"]
    service_price = prog["service_price"]
    ele_fee = current_energy_kwh * flat_price
    service_fee = current_energy_kwh * service_price
    total_fee = ele_fee + service_fee

    # 每次轮询都刷新数据库（管理面板实时看到充电进度）
    order.total_kwh = Decimal(str(round(current_energy_kwh, 2)))
    order.ele_fee = Decimal(str(round(ele_fee, 2)))
    order.service_fee = Decimal(str(round(service_fee, 2)))
    order.total_fee = Decimal(str(round(total_fee, 2)))
    db.commit()

    # 检查余额：余额不足且累计消费 >= 余额时自动结束充电
    if order.user_id:
        balance = get_user_balance(db, order.user_id)
        min_balance = Decimal("5.00")  # 低于 5 元视为余额不足
        if balance < min_balance and Decimal(str(total_fee)) >= balance:
            # 余额不足，自动结束充电
            now = datetime.now()
            order.end_time = now
            order.status = 1
            order.pay_status = 1
            order.abnormal_reason = "余额不足自动结束"
            if order.charger:
                order.charger.status = 0
            create_wallet_consume_record(db, order.user_id, order.id, Decimal(str(total_fee)))
            db.commit()
            _clear_progress(order_id)
            return {
                "code": 200, "message": "余额不足，充电已自动结束",
                "data": {"charging": False, "finished": True, "auto_end": True, "reason": "余额不足"},
            }

    # 充电完成（SOC 达到目标）-> 自动结束
    if current_soc >= target_soc or charged_fraction >= 1.0:
        now = datetime.now()
        order.end_time = now
        order.status = 1
        order.pay_status = 1
        if order.charger:
            order.charger.status = 0
        create_wallet_consume_record(db, order.user_id, order.id, Decimal(str(total_fee)))
        db.commit()
        _clear_progress(order_id)
        return {
            "code": 200, "message": "充电完成",
            "data": {"charging": False, "finished": True, "auto_end": True, "reason": "充电完成"},
        }

    return {
        "code": 200,
        "message": "充电中",
        "data": {
            "charging": True,
            "finished": False,
            "order_id": order.id,
            "order_no": order.order_no,
            "station_name": get_station_name(order),
            "pile_no": order.charger.sn_code if order.charger else "",
            "start_time": order.start_time.strftime("%Y-%m-%d %H:%M:%S") if order.start_time else "",
            "elapsed_minutes": max(1, int(prog["accumulated_minutes"])),  # 未满 1 分钟按 1 分钟算
            "current_soc": current_soc,
            "current_power_kw": round(current_power, 1),
            "total_kwh": round(current_energy_kwh, 2),
            "electricity_fee": round(ele_fee, 2),
            "service_fee": round(service_fee, 2),
            "total_fee": round(total_fee, 2),
            "status": 0,
            "status_text": "充电中",
        },
    }


@sim_api_router.post("/charging/reset/{order_id}")
async def reset_charging_sim(
    order_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _clear_progress(order_id)
    return {"code": 200, "message": "充电模拟已重置"}
