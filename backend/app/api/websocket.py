"""
WebSocket 서버: 실시간 데이터 스트리밍
"""
from fastapi import WebSocket, WebSocketDisconnect, APIRouter
from typing import List, Set
import json
import asyncio
from ..core.logging_config import logger
from ..services.realtime_data import get_realtime_collector, get_signal_generator


router = APIRouter()


class ConnectionManager:
    """WebSocket 연결 관리자"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: dict[WebSocket, Set[str]] = {}  # 각 연결별 구독 종목

    async def connect(self, websocket: WebSocket):
        """새로운 연결 수락"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.subscriptions[websocket] = set()
        logger.info(f"WebSocket 연결: {websocket.client} (총 {len(self.active_connections)}개)")

    def disconnect(self, websocket: WebSocket):
        """연결 종료"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.subscriptions:
            del self.subscriptions[websocket]
        logger.info(f"WebSocket 연결 해제 (남은 연결: {len(self.active_connections)}개)")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """특정 클라이언트에게 메시지 전송"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"메시지 전송 오류: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        """모든 클라이언트에게 브로드캐스트"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"브로드캐스트 오류: {e}")
                disconnected.append(connection)

        # 끊어진 연결 제거
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_to_symbol_subscribers(self, symbol: str, message: dict):
        """특정 종목 구독자에게만 전송"""
        disconnected = []
        for connection in self.active_connections:
            if symbol in self.subscriptions.get(connection, set()):
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"메시지 전송 오류: {e}")
                    disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)


# 싱글톤 매니저
manager = ConnectionManager()


@router.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket):
    """
    실시간 데이터 스트리밍 WebSocket 엔드포인트

    클라이언트 → 서버 메시지 형식:
    {
        "action": "subscribe" | "unsubscribe" | "get_latest",
        "symbols": ["AAPL", "TSLA", ...]
    }

    서버 → 클라이언트 메시지 형식:
    {
        "type": "price_update" | "signal" | "error",
        "symbol": "AAPL",
        "timestamp": "2024-01-01T12:00:00",
        "data": {...}
    }
    """
    await manager.connect(websocket)
    collector = get_realtime_collector(update_interval=600)  # 10분

    # 실시간 데이터 수집 시작 (아직 시작 안 됐으면)
    if not collector.running:
        asyncio.create_task(collector.start())

    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_text()
            message = json.loads(data)

            action = message.get("action")
            symbols = message.get("symbols", [])

            if action == "subscribe":
                # 종목 구독
                for symbol in symbols:
                    collector.subscribe(symbol)
                    manager.subscriptions[websocket].add(symbol)

                # 즉시 최신 가격 전송
                for symbol in symbols:
                    latest_price = collector.get_latest_price(symbol)
                    if latest_price:
                        await manager.send_personal_message({
                            "type": "price_update",
                            "data": latest_price
                        }, websocket)

                await manager.send_personal_message({
                    "type": "subscribed",
                    "symbols": symbols,
                    "message": f"{len(symbols)}개 종목 구독 완료"
                }, websocket)

            elif action == "unsubscribe":
                # 종목 구독 해제
                for symbol in symbols:
                    collector.unsubscribe(symbol)
                    if websocket in manager.subscriptions:
                        manager.subscriptions[websocket].discard(symbol)

                await manager.send_personal_message({
                    "type": "unsubscribed",
                    "symbols": symbols
                }, websocket)

            elif action == "get_latest":
                # 최신 가격 조회
                if not symbols:
                    # 모든 구독 종목
                    all_prices = collector.get_all_latest_prices()
                    await manager.send_personal_message({
                        "type": "latest_prices",
                        "data": all_prices
                    }, websocket)
                else:
                    # 특정 종목만
                    for symbol in symbols:
                        latest_price = collector.get_latest_price(symbol)
                        if latest_price:
                            await manager.send_personal_message({
                                "type": "price_update",
                                "data": latest_price
                            }, websocket)

            elif action == "ping":
                # 연결 확인
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": logger.info(f"수신: {message}")
                }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket 연결 종료")
    except Exception as e:
        logger.error(f"WebSocket 오류: {e}")
        manager.disconnect(websocket)


# 데이터 업데이트 시 자동 브로드캐스트
async def broadcast_price_update(message: dict):
    """실시간 데이터 수집기에서 호출됨"""
    symbol = message.get("symbol")
    await manager.broadcast_to_symbol_subscribers(symbol, message)


# 실시간 데이터 수집기에 콜백 등록
def register_websocket_callbacks():
    """앱 시작 시 호출"""
    collector = get_realtime_collector()
    collector.register_callback(broadcast_price_update)
    logger.info("WebSocket 콜백 등록 완료")
