"""
WebSocket API 엔드포인트
실시간 데이터 스트리밍 및 자동매매 제어
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict
import json
import asyncio
from datetime import datetime

from ..core.logging_config import logger


router = APIRouter()

# 전역 인스턴스
trading_engine = None
data_collector = None

# WebSocket 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket 연결: {len(self.active_connections)}개 활성")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket 연결 해제: {len(self.active_connections)}개 남음")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        """모든 연결된 클라이언트에 메시지 전송"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)

        # 연결 끊긴 클라이언트 제거
        for conn in disconnected:
            self.active_connections.remove(conn)


manager = ConnectionManager()


def register_websocket_callbacks():
    """WebSocket 콜백 등록 (앱 시작 시)"""
    global trading_engine, data_collector

    try:
        from ..services.auto_trading_engine import AutoTradingEngine, AutoTradingConfig
        from ..services.realtime_data import RealtimeDataCollector

        data_collector = RealtimeDataCollector()
        logger.info("WebSocket 콜백 등록 완료")
    except ImportError as e:
        logger.warning(f"자동매매 모듈 로드 실패 (선택적): {e}")


@router.websocket("/ws/realtime")
async def websocket_realtime(websocket: WebSocket):
    """실시간 데이터 스트리밍 WebSocket"""
    await manager.connect(websocket)

    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_text()
            request = json.loads(data)

            if request['type'] == 'subscribe':
                # 종목 구독
                symbols = request.get('symbols', [])

                if data_collector:
                    for symbol in symbols:
                        data_collector.subscribe(symbol)

                await websocket.send_text(json.dumps({
                    'type': 'subscription_confirmed',
                    'symbols': symbols
                }))

            elif request['type'] == 'unsubscribe':
                # 구독 해제
                symbols = request.get('symbols', [])

                if data_collector:
                    for symbol in symbols:
                        data_collector.unsubscribe(symbol)

            elif request['type'] == 'get_status':
                # 현재 상태 요청
                if trading_engine:
                    from ..services.auto_trading_engine import AutoTradingEngine
                    status = trading_engine.get_status()
                    await websocket.send_text(json.dumps({
                        'type': 'status_update',
                        'status': status
                    }))
                else:
                    await websocket.send_text(json.dumps({
                        'type': 'status_update',
                        'status': {
                            'is_running': False,
                            'mode': 'paper',
                            'active_positions': 0
                        }
                    }))

            elif request['type'] == 'get_performance':
                # 성과 지표 요청
                if trading_engine:
                    from ..services.auto_trading_engine import AutoTradingEngine
                    metrics = trading_engine.get_performance_metrics()
                    await websocket.send_text(json.dumps({
                        'type': 'performance_update',
                        'metrics': metrics
                    }))

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket 오류: {e}")
        manager.disconnect(websocket)


@router.websocket("/ws/trading")
async def websocket_trading_control(websocket: WebSocket):
    """자동매매 제어 WebSocket"""
    await manager.connect(websocket)

    global trading_engine

    try:
        while True:
            data = await websocket.receive_text()
            command = json.loads(data)

            if command['type'] == 'start_trading':
                # 자동매매 시작
                try:
                    from ..services.auto_trading_engine import AutoTradingEngine, AutoTradingConfig

                    config = AutoTradingConfig(**command.get('config', {}))

                    if not trading_engine:
                        trading_engine = AutoTradingEngine(config)

                    if not trading_engine.is_running:
                        asyncio.create_task(trading_engine.start())

                        await websocket.send_text(json.dumps({
                            'type': 'trading_started',
                            'message': '자동매매가 시작되었습니다'
                        }))
                    else:
                        await websocket.send_text(json.dumps({
                            'type': 'error',
                            'message': '자동매매가 이미 실행 중입니다'
                        }))

                except ImportError:
                    await websocket.send_text(json.dumps({
                        'type': 'error',
                        'message': '자동매매 엔진이 설치되지 않았습니다'
                    }))

            elif command['type'] == 'stop_trading':
                # 자동매매 중지
                if trading_engine and trading_engine.is_running:
                    await trading_engine.stop()

                    await websocket.send_text(json.dumps({
                        'type': 'trading_stopped',
                        'message': '자동매매가 중지되었습니다'
                    }))
                else:
                    await websocket.send_text(json.dumps({
                        'type': 'error',
                        'message': '자동매매가 실행되고 있지 않습니다'
                    }))

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Trading WebSocket 오류: {e}")
        manager.disconnect(websocket)


@router.post("/trading/start")
async def start_trading(config: Dict = None):
    """자동매매 시작 (REST API)"""
    global trading_engine

    try:
        from ..services.auto_trading_engine import AutoTradingEngine, AutoTradingConfig

        if config:
            trading_config = AutoTradingConfig(**config)
        else:
            trading_config = AutoTradingConfig()

        if not trading_engine:
            trading_engine = AutoTradingEngine(trading_config)

        if not trading_engine.is_running:
            asyncio.create_task(trading_engine.start())
            return {"success": True, "message": "자동매매가 시작되었습니다"}
        else:
            return {"success": False, "message": "자동매매가 이미 실행 중입니다"}

    except ImportError:
        return {"success": False, "message": "자동매매 엔진이 설치되지 않았습니다"}
    except Exception as e:
        logger.error(f"자동매매 시작 오류: {e}")
        return {"success": False, "message": str(e)}


@router.post("/trading/stop")
async def stop_trading():
    """자동매매 중지 (REST API)"""
    global trading_engine

    try:
        if trading_engine and trading_engine.is_running:
            await trading_engine.stop()
            return {"success": True, "message": "자동매매가 중지되었습니다"}
        else:
            return {"success": False, "message": "자동매매가 실행되고 있지 않습니다"}

    except Exception as e:
        logger.error(f"자동매매 중지 오류: {e}")
        return {"success": False, "message": str(e)}


@router.get("/trading/status")
async def get_trading_status():
    """자동매매 상태 조회 (REST API)"""
    global trading_engine

    if trading_engine:
        try:
            return {
                "success": True,
                "status": trading_engine.get_status()
            }
        except:
            pass

    return {
        "success": True,
        "status": {
            "is_running": False,
            "mode": None,
            "active_positions": 0,
            "pending_orders": 0,
            "daily_pnl": 0
        }
    }


@router.get("/portfolio/status")
async def get_portfolio_status():
    """포트폴리오 상태 조회 (대시보드용)"""
    global trading_engine

    if trading_engine and hasattr(trading_engine, 'active_positions'):
        # 실제 포지션 데이터
        positions = []
        for symbol, pos in trading_engine.active_positions.items():
            # 현재가 조회 (임시로 entry_price * 1.05 사용)
            current_price = pos['entry_price'] * 1.05  # TODO: 실제 현재가 조회
            pnl = (current_price - pos['entry_price']) * pos['shares']
            pnl_percent = ((current_price / pos['entry_price']) - 1) * 100

            positions.append({
                'symbol': symbol,
                'shares': pos['shares'],
                'entryPrice': pos['entry_price'],
                'currentPrice': current_price,
                'stopLoss': pos['stop_loss'],
                'takeProfit': pos['take_profit'],
                'pnl': pnl,
                'pnlPercent': pnl_percent,
                'status': 'active',
                'strategy': pos['strategy']
            })

        # 리스크 지표 (간단 계산)
        risk_metrics = {
            'portfolioRisk': 0.05,  # TODO: 실제 계산
            'var95': -0.03,
            'sharpeRatio': 1.2,
            'maxDrawdown': -0.08,
            'riskLevel': 'medium'
        }

        return {
            'positions': positions,
            'riskMetrics': risk_metrics
        }
    else:
        # 데모 데이터
        return {
            'positions': [
                {
                    'symbol': 'AAPL',
                    'shares': 100,
                    'entryPrice': 170.00,
                    'currentPrice': 175.50,
                    'stopLoss': 165.00,
                    'takeProfit': 180.00,
                    'pnl': 550.00,
                    'pnlPercent': 3.24,
                    'status': 'active',
                    'strategy': 'buffett'
                },
                {
                    'symbol': '005930.KS',
                    'shares': 50,
                    'entryPrice': 68000,
                    'currentPrice': 67500,
                    'stopLoss': 65000,
                    'takeProfit': 72000,
                    'pnl': -25000,
                    'pnlPercent': -0.74,
                    'status': 'active',
                    'strategy': 'lynch'
                }
            ],
            'riskMetrics': {
                'portfolioRisk': 0.03,
                'var95': -0.02,
                'sharpeRatio': 1.5,
                'maxDrawdown': -0.05,
                'riskLevel': 'low'
            }
        }