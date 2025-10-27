import { useState, useEffect } from 'react';
import { Activity, TrendingUp, TrendingDown, Clock, RefreshCw } from 'lucide-react';
import { useWebSocket, type PriceUpdate } from '../hooks/useWebSocket';
import StockAutocomplete from '../components/StockAutocomplete';

export default function RealtimeMonitor() {
  const [watchlist, setWatchlist] = useState<string[]>(['AAPL', 'TSLA', 'NVDA']);
  const { isConnected, latestPrices, error, subscribe, unsubscribe } = useWebSocket(
    'ws://localhost:8000/api/v1/ws/realtime'
  );

  // 초기 구독
  useEffect(() => {
    if (isConnected && watchlist.length > 0) {
      subscribe(watchlist);
    }
  }, [isConnected]);

  const handleAddSymbol = (symbol: string) => {
    if (!watchlist.includes(symbol)) {
      setWatchlist([...watchlist, symbol]);
      if (isConnected) {
        subscribe([symbol]);
      }
    }
  };

  const handleRemoveSymbol = (symbol: string) => {
    setWatchlist(watchlist.filter(s => s !== symbol));
    if (isConnected) {
      unsubscribe([symbol]);
    }
  };

  const formatPrice = (price: number) => price.toFixed(2);
  const formatPercent = (change: number) => `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
  const formatTime = (timestamp?: string) => {
    if (!timestamp) return '-';
    const date = new Date(timestamp);
    return date.toLocaleTimeString('ko-KR');
  };

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="card bg-gradient-to-r from-green-50 to-blue-50 border-green-200">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center gap-3">
              <Activity className="w-8 h-8 text-green-600" />
              실시간 가격 모니터링
            </h1>
            <p className="text-gray-700">
              10분마다 자동으로 최신 가격을 업데이트합니다 (yfinance)
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className={`px-4 py-2 rounded-lg font-semibold ${
              isConnected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
            }`}>
              {isConnected ? '🟢 연결됨' : '🔴 연결 끊김'}
            </div>
          </div>
        </div>
      </div>

      {/* 오류 메시지 */}
      {error && (
        <div className="card bg-red-50 border-red-200">
          <p className="text-red-700 font-semibold">{error}</p>
        </div>
      )}

      {/* 종목 추가 */}
      <div className="card">
        <h2 className="text-xl font-bold text-gray-900 mb-4">관심종목 추가</h2>
        <StockAutocomplete
          value=""
          onChange={handleAddSymbol}
        />
        <div className="mt-4 flex gap-2 flex-wrap">
          {watchlist.map(symbol => (
            <div key={symbol} className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm flex items-center gap-2">
              {symbol}
              <button onClick={() => handleRemoveSymbol(symbol)} className="text-blue-600 hover:text-blue-800">✕</button>
            </div>
          ))}
        </div>
      </div>

      {/* 가격 테이블 */}
      <div className="card overflow-x-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-gray-900">실시간 가격</h2>
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <RefreshCw className="w-4 h-4 animate-spin" />
            10분마다 업데이트
          </div>
        </div>

        <table className="w-full text-sm">
          <thead className="bg-gray-100">
            <tr>
              <th className="px-4 py-3 text-left font-bold">종목</th>
              <th className="px-4 py-3 text-right font-bold">현재가</th>
              <th className="px-4 py-3 text-right font-bold">시가</th>
              <th className="px-4 py-3 text-right font-bold">고가</th>
              <th className="px-4 py-3 text-right font-bold">저가</th>
              <th className="px-4 py-3 text-right font-bold">변동률</th>
              <th className="px-4 py-3 text-right font-bold">거래량</th>
              <th className="px-4 py-3 text-right font-bold">업데이트</th>
            </tr>
          </thead>
          <tbody>
            {watchlist.map(symbol => {
              const price = latestPrices.get(symbol);
              if (!price) {
                return (
                  <tr key={symbol} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-3 font-bold">{symbol}</td>
                    <td colSpan={7} className="px-4 py-3 text-center text-gray-500">
                      데이터 로딩 중...
                    </td>
                  </tr>
                );
              }

              const change = ((price.close - price.open) / price.open) * 100;
              const isPositive = change >= 0;

              return (
                <tr key={symbol} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-3 font-bold">{symbol}</td>
                  <td className={`px-4 py-3 text-right font-bold text-lg ${
                    isPositive ? 'text-green-600' : 'text-red-600'
                  }`}>
                    ${formatPrice(price.current_price)}
                  </td>
                  <td className="px-4 py-3 text-right">${formatPrice(price.open)}</td>
                  <td className="px-4 py-3 text-right text-red-600">${formatPrice(price.high)}</td>
                  <td className="px-4 py-3 text-right text-blue-600">${formatPrice(price.low)}</td>
                  <td className={`px-4 py-3 text-right font-semibold ${
                    isPositive ? 'text-green-600' : 'text-red-600'
                  }`}>
                    <div className="flex items-center justify-end gap-1">
                      {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                      {formatPercent(change)}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">{price.volume.toLocaleString()}</td>
                  <td className="px-4 py-3 text-right text-gray-500 flex items-center justify-end gap-1">
                    <Clock className="w-3 h-3" />
                    {formatTime(price.last_update)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {watchlist.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            종목을 추가하여 실시간 가격을 모니터링하세요.
          </div>
        )}
      </div>

      {/* 가격 카드 (모바일 친화적) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 lg:hidden">
        {watchlist.map(symbol => {
          const price = latestPrices.get(symbol);
          if (!price) return null;

          const change = ((price.close - price.open) / price.open) * 100;
          const isPositive = change >= 0;

          return (
            <div key={symbol} className={`card border-2 ${
              isPositive ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
            }`}>
              <div className="flex items-center justify-between mb-2">
                <span className="font-bold text-lg">{symbol}</span>
                <button onClick={() => handleRemoveSymbol(symbol)} className="text-gray-400 hover:text-gray-600">✕</button>
              </div>
              <div className={`text-3xl font-bold mb-2 ${
                isPositive ? 'text-green-600' : 'text-red-600'
              }`}>
                ${formatPrice(price.current_price)}
              </div>
              <div className={`flex items-center gap-2 text-sm font-semibold ${
                isPositive ? 'text-green-700' : 'text-red-700'
              }`}>
                {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                {formatPercent(change)}
              </div>
              <div className="mt-3 text-xs text-gray-600 flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {formatTime(price.last_update)}
              </div>
            </div>
          );
        })}
      </div>

      {/* 설명 */}
      <div className="card bg-blue-50 border-blue-200">
        <h3 className="font-bold text-blue-900 mb-2">💡 사용 방법</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• 관심 종목을 추가하면 자동으로 구독됩니다</li>
          <li>• yfinance에서 10분마다 최신 가격을 가져옵니다</li>
          <li>• WebSocket으로 실시간 업데이트를 받습니다</li>
          <li>• 브라우저를 닫아도 백엔드는 계속 데이터를 수집합니다</li>
        </ul>
      </div>
    </div>
  );
}
