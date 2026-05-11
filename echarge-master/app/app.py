import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.charging_sim import sim_api_router
from app.api.v1.demo_routes import demo_api_router
from app.api.v1.extra_routes import extra_api_router
from app.api.v1.mini_routes import mini_api_router
from app.api.v1.routes import api_router
from app.core.config import settings
from app.db.database import SessionLocal
from app.services.operator_demo_service import ensure_all_operators_demo_assets

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时一次性补齐演示运营商资产，避免在电桩列表/状态更新等热点接口内重复执行。"""
    db = SessionLocal()
    try:
        ensure_all_operators_demo_assets(db)
    except Exception:
        logger.exception("ensure_all_operators_demo_assets on startup failed")
    finally:
        db.close()
    yield


origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8001",
    "http://127.0.0.1:8001",
    "http://localhost",
    "http://127.0.0.1",
]
_extra = [o.strip() for o in settings.CORS_EXTRA_ORIGINS.split(",") if o.strip()]
origins = list(dict.fromkeys(origins + _extra))

app = FastAPI(title=settings.PROJECT_NAME, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 小程序路由必须优先注册，避免 /orders/my 被 /orders/{order_id} 截胡
app.include_router(mini_api_router, prefix=settings.API_V1_PREFIX)
app.include_router(sim_api_router, prefix=settings.API_V1_PREFIX)
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(extra_api_router, prefix=settings.API_V1_PREFIX)
app.include_router(demo_api_router, prefix=settings.API_V1_PREFIX)
