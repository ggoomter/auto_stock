"""
FastAPI 메인 애플리케이션
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .core.config import settings
from .api.routes import router
from .api.websocket_api import router as websocket_router, register_websocket_callbacks
from .api.trading_routes import router as trading_router
from .routers.events import router as events_router
import traceback
import numpy as np
import sys


def convert_numpy_types(obj):
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.datetime64):
        return str(obj)
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(item) for item in obj]
    else:
        return obj


from fastapi.encoders import ENCODERS_BY_TYPE
ENCODERS_BY_TYPE[np.integer] = int
ENCODERS_BY_TYPE[np.floating] = float
ENCODERS_BY_TYPE[np.bool_] = bool
ENCODERS_BY_TYPE[np.ndarray] = lambda x: x.tolist()
ENCODERS_BY_TYPE[np.int64] = int
ENCODERS_BY_TYPE[np.int32] = int
ENCODERS_BY_TYPE[np.float64] = float
ENCODERS_BY_TYPE[np.float32] = float

# Python 3.13 호환성: numpy.bool은 deprecated되었지만 여전히 사용됨
try:
    ENCODERS_BY_TYPE[np.bool] = bool
except AttributeError:
    pass  # numpy.bool이 없는 경우 무시


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="투명한 확률 예측과 전략 시뮬레이션을 제공하는 금융 분석 플랫폼"
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    error_msg = f"\n{'='*80}\nGLOBAL EXCEPTION HANDLER CAUGHT:\nError: {str(exc)}\nTraceback:\n{tb}\n{'='*80}\n"

    sys.stderr.write(error_msg)
    sys.stderr.flush()

    try:
        with open("G:/ai_coding/auto_stock/error_traceback.txt", "a", encoding="utf-8") as f:
            f.write(error_msg)
    except Exception:
        pass

    return JSONResponse(status_code=500, content={"detail": str(exc)})


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=settings.API_V1_STR, tags=["analysis"])
app.include_router(events_router)
app.include_router(websocket_router, prefix=settings.API_V1_STR, tags=["websocket"])
app.include_router(trading_router, prefix=settings.API_V1_STR, tags=["trading"])


@app.on_event("startup")
async def startup_event():
    """앱 시작 시 실행"""
    register_websocket_callbacks()


@app.get("/")
async def root():
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health",
        "websocket": f"{settings.API_V1_STR}/ws/realtime"
    }
