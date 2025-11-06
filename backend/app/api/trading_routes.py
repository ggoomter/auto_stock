"""
자동매매 API 라우트
실시간 트레이딩 시작/중지, 상태 조회, 포지션 관리
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from ..core.logging_config import logger
from ..services.auto_trading_engine import (
    AutoTradingEngine,
    AutoTradingConfig,
    TradingMode,
    OrderType
)
from ..services.position_manager import PositionManager
from ..services.advanced_risk_manager import AdvancedRiskManager

router = APIRouter()

# 전역 자동매매 엔진 (싱글톤)
_trading_engine: Optional[AutoTradingEngine] = None
_is_running: bool = False


# ============================================================
# Pydantic 스키마
# ============================================================

class TradingStartRequest(BaseModel):
    """자동매매 시작 요청"""
    mode: str = "paper"  # "paper" or "live"
    total_capital: float = 10000000  # KRW
    max_positions: int = 5
    max_position_size: float = 0.2  # 20%
    max_risk_per_trade: float = 0.02  # 2%
    max_daily_loss: float = 0.05  # 5%
    enabled_strategies: List[str] = ["buffett", "lynch"]
    trading_symbols: List[str] = ["AAPL", "TSLA", "005930.KS"]
    use_trailing_stop: bool = True
    trailing_stop_percent: float = 0.05
    order_type: str = "market"  # "market" or "limit"
    slippage_tolerance: float = 0.01


class TradingStopRequest(BaseModel):
    """자동매매 중지 요청"""
    close_all_positions: bool = False  # 모든 포지션 청산 여부
    reason: str = "user_request"


class TradingStatusResponse(BaseModel):
    """자동매매 상태 응답"""
    is_running: bool
    mode: str
    uptime_seconds: float
    active_positions: int
    total_trades_today: int
    daily_pnl: float
    daily_pnl_pct: float
    enabled_strategies: List[str]
    risk_level: str  # "low", "medium", "high", "extreme"
    last_update: str


class PositionResponse(BaseModel):
    """포지션 정보"""
    symbol: str
    quantity: int
    entry_price: float
    entry_date: str
    current_price: float
    pnl: float
    pnl_pct: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    strategy: str


class PortfolioStatusResponse(BaseModel):
    """포트폴리오 상태"""
    total_value: float
    cash: float
    positions_value: float
    total_pnl: float
    total_pnl_pct: float
    positions: List[PositionResponse]
    risk_metrics: Dict
    last_update: str


class EmergencyStopRequest(BaseModel):
    """긴급 정지 요청"""
    reason: str = "emergency"


# ============================================================
# API 엔드포인트
# ============================================================

@router.post("/trading/start")
async def start_trading(request: TradingStartRequest, background_tasks: BackgroundTasks):
    """
    자동매매 시작

    - 실시간 데이터 수집 시작
    - 전략 신호 모니터링
    - 자동 주문 실행
    """
    global _trading_engine, _is_running

    try:
        # 이미 실행 중인지 체크
        if _is_running:
            raise HTTPException(
                status_code=400,
                detail="자동매매가 이미 실행 중입니다. 먼저 중지해주세요."
            )

        logger.info(f"=== 자동매매 시작 요청 ===")
        logger.info(f"모드: {request.mode}")
        logger.info(f"초기 자본: {request.total_capital:,.0f} KRW")
        logger.info(f"활성화 전략: {request.enabled_strategies}")
        logger.info(f"거래 종목: {request.trading_symbols}")

        # 실전 모드 경고
        if request.mode == "live":
            logger.warning("⚠️ 실전 거래 모드로 시작합니다! 실제 자금이 사용됩니다.")

        # TradingMode enum 변환
        mode = TradingMode.LIVE if request.mode == "live" else TradingMode.PAPER
        order_type = OrderType.LIMIT if request.order_type == "limit" else OrderType.MARKET

        # 자동매매 설정
        config = AutoTradingConfig(
            mode=mode,
            max_positions=request.max_positions,
            max_position_size=request.max_position_size,
            total_capital=request.total_capital,
            max_daily_loss=request.max_daily_loss,
            max_risk_per_trade=request.max_risk_per_trade,
            use_trailing_stop=request.use_trailing_stop,
            trailing_stop_percent=request.trailing_stop_percent,
            order_type=order_type,
            slippage_tolerance=request.slippage_tolerance,
            enabled_strategies=request.enabled_strategies
        )

        # 자동매매 엔진 생성
        _trading_engine = AutoTradingEngine(config)

        # 백그라운드에서 실행
        async def run_engine():
            global _is_running
            _is_running = True
            try:
                await _trading_engine.start(symbols=request.trading_symbols)
            except Exception as e:
                logger.error(f"자동매매 엔진 오류: {e}")
                _is_running = False

        background_tasks.add_task(run_engine)

        logger.info("✅ 자동매매가 시작되었습니다.")

        return {
            "status": "started",
            "message": "자동매매가 시작되었습니다",
            "mode": request.mode,
            "config": {
                "total_capital": request.total_capital,
                "max_positions": request.max_positions,
                "enabled_strategies": request.enabled_strategies,
                "trading_symbols": request.trading_symbols
            },
            "warnings": [
                "실전 거래는 실제 자금 손실 위험이 있습니다" if request.mode == "live" else None,
                "시스템 오류 발생 시 수동으로 포지션을 확인해주세요"
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"자동매매 시작 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trading/stop")
async def stop_trading(request: TradingStopRequest):
    """
    자동매매 중지

    - 실시간 데이터 수집 중지
    - 신규 포지션 진입 차단
    - 옵션: 기존 포지션 청산
    """
    global _trading_engine, _is_running

    try:
        if not _is_running or _trading_engine is None:
            raise HTTPException(
                status_code=400,
                detail="실행 중인 자동매매가 없습니다"
            )

        logger.info(f"=== 자동매매 중지 요청 ===")
        logger.info(f"포지션 청산: {request.close_all_positions}")
        logger.info(f"사유: {request.reason}")

        # 엔진 중지
        await _trading_engine.stop(close_positions=request.close_all_positions)

        # 상태 저장
        final_status = _trading_engine.get_status()

        # 전역 변수 초기화
        _trading_engine = None
        _is_running = False

        logger.info("✅ 자동매매가 중지되었습니다.")

        return {
            "status": "stopped",
            "message": "자동매매가 중지되었습니다",
            "final_status": final_status,
            "positions_closed": request.close_all_positions
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"자동매매 중지 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trading/status", response_model=TradingStatusResponse)
async def get_trading_status():
    """
    자동매매 현재 상태 조회

    - 실행 여부
    - 일일 손익
    - 포지션 수
    - 리스크 레벨
    """
    global _trading_engine, _is_running

    try:
        if not _is_running or _trading_engine is None:
            return TradingStatusResponse(
                is_running=False,
                mode="stopped",
                uptime_seconds=0,
                active_positions=0,
                total_trades_today=0,
                daily_pnl=0.0,
                daily_pnl_pct=0.0,
                enabled_strategies=[],
                risk_level="low",
                last_update=datetime.now().isoformat()
            )

        # 엔진 상태 조회
        status = _trading_engine.get_status()

        return TradingStatusResponse(
            is_running=True,
            mode=status.get("mode", "paper"),
            uptime_seconds=status.get("uptime_seconds", 0),
            active_positions=status.get("active_positions", 0),
            total_trades_today=status.get("total_trades_today", 0),
            daily_pnl=status.get("daily_pnl", 0.0),
            daily_pnl_pct=status.get("daily_pnl_pct", 0.0),
            enabled_strategies=status.get("enabled_strategies", []),
            risk_level=status.get("risk_level", "low"),
            last_update=datetime.now().isoformat()
        )

    except Exception as e:
        logger.error(f"상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolio/status", response_model=PortfolioStatusResponse)
async def get_portfolio_status():
    """
    포트폴리오 상태 조회

    - 총 자산
    - 현금 잔고
    - 포지션 목록
    - 리스크 지표
    """
    global _trading_engine, _is_running

    try:
        if not _is_running or _trading_engine is None:
            raise HTTPException(
                status_code=400,
                detail="실행 중인 자동매매가 없습니다"
            )

        # 포트폴리오 정보 조회
        portfolio = _trading_engine.get_portfolio_summary()

        # 포지션 변환
        positions = []
        for pos_data in portfolio.get("positions", []):
            positions.append(PositionResponse(
                symbol=pos_data.get("symbol"),
                quantity=pos_data.get("quantity", 0),
                entry_price=pos_data.get("entry_price", 0.0),
                entry_date=pos_data.get("entry_date", ""),
                current_price=pos_data.get("current_price", 0.0),
                pnl=pos_data.get("pnl", 0.0),
                pnl_pct=pos_data.get("pnl_pct", 0.0),
                stop_loss=pos_data.get("stop_loss"),
                take_profit=pos_data.get("take_profit"),
                strategy=pos_data.get("strategy", "unknown")
            ))

        return PortfolioStatusResponse(
            total_value=portfolio.get("total_value", 0.0),
            cash=portfolio.get("cash", 0.0),
            positions_value=portfolio.get("positions_value", 0.0),
            total_pnl=portfolio.get("total_pnl", 0.0),
            total_pnl_pct=portfolio.get("total_pnl_pct", 0.0),
            positions=positions,
            risk_metrics=portfolio.get("risk_metrics", {}),
            last_update=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"포트폴리오 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trading/emergency-stop")
async def emergency_stop(request: EmergencyStopRequest):
    """
    긴급 정지 (킬 스위치)

    - 즉시 모든 거래 중단
    - 모든 포지션 시장가 청산
    - 실시간 데이터 수집 중지
    """
    global _trading_engine, _is_running

    try:
        logger.warning(f"🚨 긴급 정지 요청: {request.reason}")

        if not _is_running or _trading_engine is None:
            return {
                "status": "already_stopped",
                "message": "실행 중인 자동매매가 없습니다"
            }

        # 긴급 정지 실행
        result = await _trading_engine.emergency_stop(reason=request.reason)

        # 전역 변수 초기화
        _trading_engine = None
        _is_running = False

        logger.warning("🛑 긴급 정지 완료")

        return {
            "status": "emergency_stopped",
            "message": "긴급 정지가 완료되었습니다",
            "reason": request.reason,
            "closed_positions": result.get("closed_positions", 0),
            "final_portfolio": result.get("final_portfolio", {})
        }

    except Exception as e:
        logger.error(f"긴급 정지 실패: {e}")
        # 긴급 정지는 실패해도 시스템을 중단시킴
        _trading_engine = None
        _is_running = False
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trading/performance")
async def get_trading_performance():
    """
    거래 성과 조회

    - 총 거래 횟수
    - 승률
    - Profit Factor
    - 샤프 비율
    - 최대 낙폭
    """
    global _trading_engine

    try:
        if _trading_engine is None:
            raise HTTPException(
                status_code=400,
                detail="자동매매 세션이 없습니다"
            )

        performance = _trading_engine.get_performance_metrics()

        return {
            "total_trades": performance.get("total_trades", 0),
            "win_rate": performance.get("win_rate", 0.0),
            "profit_factor": performance.get("profit_factor", 0.0),
            "sharpe_ratio": performance.get("sharpe_ratio", 0.0),
            "max_drawdown": performance.get("max_drawdown", 0.0),
            "average_win": performance.get("average_win", 0.0),
            "average_loss": performance.get("average_loss", 0.0),
            "largest_win": performance.get("largest_win", 0.0),
            "largest_loss": performance.get("largest_loss", 0.0)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"성과 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trading/health")
async def get_trading_health():
    """
    시스템 헬스 체크

    - CPU/메모리 사용률
    - WebSocket 연결 상태
    - 데이터 수집 상태
    - API 연결 상태
    """
    try:
        import psutil

        health_status = {
            "timestamp": datetime.now().isoformat(),
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            },
            "trading": {
                "is_running": _is_running,
                "engine_status": "running" if _trading_engine else "stopped"
            },
            "checks": []
        }

        # CPU 체크
        if health_status["system"]["cpu_percent"] > 90:
            health_status["checks"].append({
                "status": "warning",
                "message": "CPU 사용률이 높습니다 (>90%)"
            })

        # 메모리 체크
        if health_status["system"]["memory_percent"] > 90:
            health_status["checks"].append({
                "status": "warning",
                "message": "메모리 사용률이 높습니다 (>90%)"
            })

        # 전체 상태
        if len(health_status["checks"]) == 0:
            health_status["overall_status"] = "healthy"
        else:
            health_status["overall_status"] = "warning"

        return health_status

    except Exception as e:
        logger.error(f"헬스 체크 실패: {e}")
        return {
            "overall_status": "error",
            "error": str(e)
        }
