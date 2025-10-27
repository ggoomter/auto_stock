import { ArrowUpCircle, ArrowDownCircle, Clock, TrendingUp, TrendingDown } from 'lucide-react';

interface Trade {
  entry_date: string;
  exit_date: string;
  entry_price: number;
  exit_price: number;
  entry_price_krw?: number;
  exit_price_krw?: number;
  shares: number;
  position_value: number;
  position_value_krw?: number;
  pnl: number;
  pnl_krw?: number;
  pnl_pct: number;
  holding_days: number;
  exit_reason: string;
  currency: string;
}

interface TradingTimelineProps {
  trades: Trade[];
  initialCapital: number;
  finalCapital: number;
  currency?: string;
}

export default function TradingTimeline({
  trades,
  initialCapital,
  finalCapital,
  currency = 'KRW'
}: TradingTimelineProps) {

  // 누적 자본 계산
  const calculateCumulativeCapital = () => {
    let capital = initialCapital;
    return trades.map((trade) => {
      const pnl = currency === 'KRW' ? trade.pnl_krw : trade.pnl;
      capital += pnl;
      return {
        ...trade,
        cumulativeCapital: capital
      };
    });
  };

  const tradesWithCapital = calculateCumulativeCapital();
  const totalReturn = ((finalCapital - initialCapital) / initialCapital) * 100;
  const winningTrades = trades.filter(t => (currency === 'KRW' ? t.pnl_krw : t.pnl) > 0);
  const losingTrades = trades.filter(t => (currency === 'KRW' ? t.pnl_krw : t.pnl) <= 0);

  const formatCurrency = (value: number) => {
    if (currency === 'KRW') {
      return `${Math.round(value).toLocaleString()}원`;
    } else {
      return `$${value.toFixed(2)}`;
    }
  };

  const formatPrice = (value: number) => {
    if (currency === 'KRW') {
      return `${Math.round(value).toLocaleString()}원`;
    } else {
      return `$${value.toFixed(2)}`;
    }
  };

  return (
    <div className="space-y-6">
      {/* 요약 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 border-2 border-blue-300 rounded-lg p-4">
          <div className="text-sm text-blue-700 font-medium mb-1">시작 자본</div>
          <div className="text-2xl font-bold text-blue-900">{formatCurrency(initialCapital)}</div>
        </div>

        <div className={`bg-gradient-to-br ${totalReturn >= 0 ? 'from-green-50 to-green-100 border-green-300' : 'from-red-50 to-red-100 border-red-300'} border-2 rounded-lg p-4`}>
          <div className={`text-sm ${totalReturn >= 0 ? 'text-green-700' : 'text-red-700'} font-medium mb-1`}>최종 자본</div>
          <div className={`text-2xl font-bold ${totalReturn >= 0 ? 'text-green-900' : 'text-red-900'}`}>
            {formatCurrency(finalCapital)}
          </div>
          <div className={`text-sm font-semibold mt-1 ${totalReturn >= 0 ? 'text-green-700' : 'text-red-700'}`}>
            {totalReturn >= 0 ? '+' : ''}{totalReturn.toFixed(2)}%
          </div>
        </div>

        <div className="bg-gradient-to-br from-purple-50 to-purple-100 border-2 border-purple-300 rounded-lg p-4">
          <div className="text-sm text-purple-700 font-medium mb-1">총 거래 횟수</div>
          <div className="text-2xl font-bold text-purple-900">{trades.length}회</div>
          <div className="text-xs text-purple-600 mt-1">
            승: {winningTrades.length} / 패: {losingTrades.length}
          </div>
        </div>

        <div className="bg-gradient-to-br from-amber-50 to-amber-100 border-2 border-amber-300 rounded-lg p-4">
          <div className="text-sm text-amber-700 font-medium mb-1">승률</div>
          <div className="text-2xl font-bold text-amber-900">
            {trades.length > 0 ? ((winningTrades.length / trades.length) * 100).toFixed(1) : '0.0'}%
          </div>
        </div>
      </div>

      {/* 타임라인 */}
      <div className="bg-white rounded-lg border-2 border-gray-200 p-6">
        <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
          <Clock className="w-5 h-5 text-blue-600" />
          거래 타임라인
        </h3>

        {trades.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p className="text-lg font-medium">거래 내역이 없습니다</p>
            <p className="text-sm mt-2">진입 조건을 만족하는 시점이 없었습니다</p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* 초기 자본 */}
            <div className="flex items-start gap-4 pb-4 border-b border-gray-200">
              <div className="flex-shrink-0 w-24 pt-1">
                <div className="text-sm text-gray-500">시작</div>
              </div>
              <div className="flex-shrink-0 pt-1">
                <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                  <div className="w-3 h-3 bg-white rounded-full"></div>
                </div>
              </div>
              <div className="flex-1 bg-blue-50 rounded-lg p-4 border-2 border-blue-200">
                <div className="text-sm text-blue-700 font-medium">초기 자본금</div>
                <div className="text-xl font-bold text-blue-900 mt-1">{formatCurrency(initialCapital)}</div>
              </div>
            </div>

            {/* 각 거래 */}
            {tradesWithCapital.map((trade, index) => {
              const isProfit = (currency === 'KRW' ? trade.pnl_krw || trade.pnl : trade.pnl) > 0;
              const entryPrice = currency === 'KRW' ? (trade.entry_price_krw || trade.entry_price) : trade.entry_price;
              const exitPrice = currency === 'KRW' ? (trade.exit_price_krw || trade.exit_price) : trade.exit_price;
              const positionValue = currency === 'KRW' ? (trade.position_value_krw || trade.position_value) : trade.position_value;
              const pnl = currency === 'KRW' ? (trade.pnl_krw || trade.pnl) : trade.pnl;

              return (
                <div key={index} className="flex items-start gap-4">
                  {/* 날짜 */}
                  <div className="flex-shrink-0 w-24 pt-1">
                    <div className="text-xs text-gray-500">{trade.entry_date}</div>
                    <div className="text-xs text-gray-400 mt-1">↓ {trade.holding_days}일</div>
                    <div className="text-xs text-gray-500 mt-1">{trade.exit_date}</div>
                  </div>

                  {/* 타임라인 도트 */}
                  <div className="flex-shrink-0 pt-1">
                    <div className={`w-8 h-8 ${isProfit ? 'bg-green-500' : 'bg-red-500'} rounded-full flex items-center justify-center`}>
                      {isProfit ? (
                        <TrendingUp className="w-4 h-4 text-white" />
                      ) : (
                        <TrendingDown className="w-4 h-4 text-white" />
                      )}
                    </div>
                    {index < trades.length - 1 && (
                      <div className="w-0.5 h-16 bg-gray-300 mx-auto mt-2"></div>
                    )}
                  </div>

                  {/* 거래 상세 */}
                  <div className="flex-1">
                    <div className={`rounded-lg border-2 ${isProfit ? 'bg-green-50 border-green-300' : 'bg-red-50 border-red-300'}`}>
                      {/* 매수 */}
                      <div className="p-4 border-b border-gray-200">
                        <div className="flex items-center gap-2 mb-2">
                          <ArrowUpCircle className="w-4 h-4 text-blue-600" />
                          <span className="text-sm font-bold text-blue-900">매수</span>
                        </div>
                        <div className="grid grid-cols-3 gap-2 text-sm">
                          <div>
                            <span className="text-gray-600">가격: </span>
                            <span className="font-semibold text-gray-900">{formatPrice(entryPrice)}</span>
                          </div>
                          <div>
                            <span className="text-gray-600">수량: </span>
                            <span className="font-semibold text-gray-900">{trade.shares.toFixed(4)}주</span>
                          </div>
                          <div>
                            <span className="text-gray-600">금액: </span>
                            <span className="font-semibold text-gray-900">{formatCurrency(positionValue)}</span>
                          </div>
                        </div>
                      </div>

                      {/* 매도 */}
                      <div className="p-4">
                        <div className="flex items-center gap-2 mb-2">
                          <ArrowDownCircle className="w-4 h-4 text-orange-600" />
                          <span className="text-sm font-bold text-orange-900">매도</span>
                          <span className="text-xs bg-gray-200 text-gray-700 px-2 py-0.5 rounded">
                            {trade.exit_reason}
                          </span>
                        </div>
                        <div className="grid grid-cols-3 gap-2 text-sm">
                          <div>
                            <span className="text-gray-600">가격: </span>
                            <span className="font-semibold text-gray-900">{formatPrice(exitPrice)}</span>
                          </div>
                          <div>
                            <span className="text-gray-600">수익률: </span>
                            <span className={`font-bold ${isProfit ? 'text-green-700' : 'text-red-700'}`}>
                              {isProfit ? '+' : ''}{trade.pnl_pct.toFixed(2)}%
                            </span>
                          </div>
                          <div>
                            <span className="text-gray-600">손익: </span>
                            <span className={`font-bold ${isProfit ? 'text-green-700' : 'text-red-700'}`}>
                              {isProfit ? '+' : ''}{formatCurrency(pnl)}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* 누적 자본 */}
                      <div className="bg-white bg-opacity-60 px-4 py-2 border-t border-gray-200">
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-700">누적 자본</span>
                          <span className="text-lg font-bold text-gray-900">
                            {formatCurrency(trade.cumulativeCapital)}
                          </span>
                          <span className={`text-sm font-semibold ${
                            ((trade.cumulativeCapital - initialCapital) / initialCapital) >= 0
                              ? 'text-green-700'
                              : 'text-red-700'
                          }`}>
                            {((trade.cumulativeCapital - initialCapital) / initialCapital) >= 0 ? '+' : ''}
                            {(((trade.cumulativeCapital - initialCapital) / initialCapital) * 100).toFixed(2)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
