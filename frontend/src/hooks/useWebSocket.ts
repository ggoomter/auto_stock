import { useEffect, useRef, useState } from 'react';

export interface PriceUpdate {
  symbol: string;
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  current_price: number;
  last_update?: string;
}

export interface WebSocketMessage {
  type: 'price_update' | 'signal' | 'subscribed' | 'unsubscribed' | 'error' | 'latest_prices';
  symbol?: string;
  data?: PriceUpdate | PriceUpdate[];
  symbols?: string[];
  message?: string;
}

export const useWebSocket = (url: string) => {
  const [isConnected, setIsConnected] = useState(false);
  const [latestPrices, setLatestPrices] = useState<Map<string, PriceUpdate>>(new Map());
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    const connect = () => {
      try {
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log('WebSocket 연결됨');
          setIsConnected(true);
          setError(null);
        };

        ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);

            if (message.type === 'price_update' && message.data) {
              const priceData = message.data as PriceUpdate;
              setLatestPrices(prev => {
                const newMap = new Map(prev);
                newMap.set(priceData.symbol, priceData);
                return newMap;
              });
            } else if (message.type === 'latest_prices' && Array.isArray(message.data)) {
              const prices = message.data as PriceUpdate[];
              setLatestPrices(prev => {
                const newMap = new Map(prev);
                prices.forEach(price => newMap.set(price.symbol, price));
                return newMap;
              });
            }
          } catch (err) {
            console.error('메시지 파싱 오류:', err);
          }
        };

        ws.onerror = (event) => {
          console.error('WebSocket 오류:', event);
          setError('WebSocket 연결 오류');
        };

        ws.onclose = () => {
          console.log('WebSocket 연결 끊김');
          setIsConnected(false);

          // 5초 후 재연결 시도
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('재연결 시도...');
            connect();
          }, 5000);
        };
      } catch (err) {
        console.error('WebSocket 연결 실패:', err);
        setError('연결 실패');
      }
    };

    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [url]);

  const subscribe = (symbols: string[]) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'subscribe',
        symbols
      }));
    }
  };

  const unsubscribe = (symbols: string[]) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'unsubscribe',
        symbols
      }));
    }
  };

  const getLatest = (symbols?: string[]) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        action: 'get_latest',
        symbols: symbols || []
      }));
    }
  };

  return {
    isConnected,
    latestPrices,
    error,
    subscribe,
    unsubscribe,
    getLatest
  };
};
