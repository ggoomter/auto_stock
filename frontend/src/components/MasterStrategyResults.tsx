import { TrendingUp, TrendingDown, Activity, Target, AlertCircle, BarChart3 } from 'lucide-react';
import type { MasterStrategyResponse } from '../services/api';
import TradingTimeline from './TradingTimeline';
import PortfolioChart from './PortfolioChart';

interface MasterStrategyResultsProps {
  results: MasterStrategyResponse;
}

export default function MasterStrategyResults({ results }: MasterStrategyResultsProps) {
  const { strategy_info, backtest, fundamental_screen, signal_examples, equity_curve, price_data, trade_history } = results;

  const formatPercent = (value: number) => `${(value * 100).toFixed(2)}%`;
  const formatNumber = (value: number) => value.toFixed(2);
  const formatRiskValue = (value?: number) =>
    value !== undefined ? `${(Math.abs(value) * 100).toFixed(2)}%` : '-';
  const formatSignedAmount = (value?: number) => {
    if (value === undefined) return '-';
    const sign = value >= 0 ? '+' : '-';
    return `${sign}${Math.abs(value).toLocaleString()}`;
  };



  // 한국 주식 여부 확인 (거래 내역에서)
  const isKoreanStock = trade_history && trade_history.length > 0 && trade_history[0].currency === 'KRW';

  // 가격 포맷 함수 (한국 주식은 정수, 외국 주식은 소수점 2자리)
  const formatPrice = (value: number, forceInteger = false) => {
    if (isKoreanStock || forceInteger) {
      return Math.round(value).toLocaleString();
    }
    return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  // 차트 생성 함수
  const createChart = () => {
    if (!price_data || !equity_curve || price_data.length === 0) return null;

    const width = 900;
    const height = 300;
    const padding = 40;

    // 데이터 범위 계산
    const priceValues = price_data.map(d => d.close);
    const minPrice = Math.min(...priceValues);
    const maxPrice = Math.max(...priceValues);
    const priceRange = maxPrice - minPrice;

    // X축 스케일
    const xScale = (index: number) => padding + (index / (price_data.length - 1)) * (width - 2 * padding);

    // Y축 스케일 (가격)
    const yScale = (price: number) => height - padding - ((price - minPrice) / priceRange) * (height - 2 * padding);

    // 가격 라인 경로 생성
    const pricePath = price_data.map((d, i) =>
      `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(d.close)}`
    ).join(' ');

    // 매수/매도 포인트
    const buyPoints = trade_history?.map(trade => {
      const dateIndex = price_data.findIndex(d => d.date === trade.entry_date);
      if (dateIndex === -1) return null;
      const price = trade.currency === 'KRW' ? trade.entry_price_krw! : trade.entry_price;
      return { x: xScale(dateIndex), y: yScale(price), date: trade.entry_date, price };
    }).filter(p => p !== null) || [];

    const sellPoints = trade_history?.map(trade => {
      const dateIndex = price_data.findIndex(d => d.date === trade.exit_date);
      if (dateIndex === -1) return null;
      const price = trade.currency === 'KRW' ? trade.exit_price_krw! : trade.exit_price;
      return { x: xScale(dateIndex), y: yScale(price), date: trade.exit_date, price };
    }).filter(p => p !== null) || [];

    return (
      <svg width={width} height={height} className="border border-gray-200 bg-white">
        {/* 가격 라인 */}
        <path d={pricePath} fill="none" stroke="#3b82f6" strokeWidth="2" />

        {/* 매수 포인트 (초록 화살표) */}
        {buyPoints.map((point, idx) => point && (
          <g key={`buy-${idx}`}>
            <circle cx={point.x} cy={point.y} r="5" fill="#10b981" stroke="white" strokeWidth="2" />
            <text x={point.x} y={point.y - 10} fontSize="10" fill="#10b981" textAnchor="middle">▲매수</text>
          </g>
        ))}

        {/* 매도 포인트 (빨강 화살표) */}
        {sellPoints.map((point, idx) => point && (
          <g key={`sell-${idx}`}>
            <circle cx={point.x} cy={point.y} r="5" fill="#ef4444" stroke="white" strokeWidth="2" />
            <text x={point.x} y={point.y + 20} fontSize="10" fill="#ef4444" textAnchor="middle">▼매도</text>
          </g>
        ))}

        {/* X축 */}
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#666" />
        {/* Y축 */}
        <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="#666" />

        {/* Y축 라벨 */}
        <text x="10" y={padding} fontSize="12" fill="#666">{formatPrice(maxPrice)}</text>
        <text x="10" y={height - padding} fontSize="12" fill="#666">{formatPrice(minPrice)}</text>

        {/* X축 라벨 */}
        <text x={padding} y={height - 20} fontSize="10" fill="#666">{price_data[0].date}</text>
        <text x={width - padding - 60} y={height - 20} fontSize="10" fill="#666">{price_data[price_data.length - 1].date}</text>
      </svg>
    );
  };

  // 대시보드 계산
  const initialCapitalDisplay = isKoreanStock ? results.initial_capital_krw! : results.initial_capital;
  const finalCapitalDisplay = isKoreanStock ? results.final_capital_krw! : results.final_capital!;
  const totalReturn = ((finalCapitalDisplay - initialCapitalDisplay) / initialCapitalDisplay) * 100;
  const totalPnL = finalCapitalDisplay - initialCapitalDisplay;
  const winningTrades = trade_history?.filter(t => t.pnl_pct > 0) || [];
  const losingTrades = trade_history?.filter(t => t.pnl_pct <= 0) || [];
  const winRate = trade_history && trade_history.length > 0 ? (winningTrades.length / trade_history.length) * 100 : 0;

  // 거래 0건 체크
  const hasNoTrades = !trade_history || trade_history.length === 0;

  // 디버깅: 거래 내역 확인
  console.log('[MasterStrategyResults] Debug Info:', {
    hasTradeHistory: !!trade_history,
    tradeCount: trade_history?.length || 0,
    trades: trade_history,
    totalReturn,
    hasNoTrades
  });

  return (
    <div className="space-y-6">
      {/* 전략 정보 */}
      <div className="card bg-gradient-to-r from-blue-50 to-purple-50">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          {strategy_info.name}
        </h3>
        <p className="text-gray-700 mb-4">{strategy_info.description}</p>

        <div className="flex gap-6 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-gray-600">보유 기간:</span>
            <span className="font-medium text-gray-900">{strategy_info.holding_period}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-600">리스크 프로필:</span>
            <span className="font-medium text-gray-900">{strategy_info.risk_profile}</span>
          </div>
        </div>
      </div>

      {/* 거래 0건일 때 경고 메시지 */}
      {hasNoTrades && (
        <div className="card bg-gradient-to-r from-red-50 to-orange-50 border-2 border-red-300">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0">
              <AlertCircle className="w-12 h-12 text-red-600" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-bold text-red-900 mb-3">
                ❌ 매수 조건 미충족 - 거래 0건
              </h3>
              <p className="text-red-800 mb-4">
                백테스트 기간 동안 <strong>{strategy_info.name}</strong> 전략의 진입 조건을 충족하는 시점이 <strong>단 한 번도 없었습니다.</strong>
              </p>

              {/* 조건 체크 상세 (있을 경우) */}
              {results.condition_checks && results.condition_checks.length > 0 ? (
                <div className="bg-white bg-opacity-90 rounded-lg p-4 mb-4">
                  <h4 className="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2">
                    <Target className="w-4 h-4 text-red-600" />
                    📊 현재 시점 조건 체크 (참고용)
                  </h4>
                  <div className="space-y-2">
                    {results.condition_checks.map((check, idx) => (
                      <div
                        key={idx}
                        className={`flex items-center justify-between p-3 rounded-lg border-2 ${
                          check.passed
                            ? 'bg-green-50 border-green-400'
                            : 'bg-red-50 border-red-400'
                        }`}
                      >
                        <div className="flex-1">
                          <div className="text-sm font-bold text-gray-900 mb-1">
                            {check.condition_name}
                            <span className="ml-2 text-xs text-gray-500">({check.condition_name_en})</span>
                          </div>
                          <div className="text-xs text-gray-700 flex items-center gap-2">
                            <span className="font-medium">필요:</span>
                            <span className="px-2 py-0.5 bg-blue-100 text-blue-900 rounded font-mono">{check.required_value}</span>
                            <span>→</span>
                            <span className="font-medium">실제:</span>
                            <span className={`px-2 py-0.5 rounded font-mono font-bold ${
                              check.passed
                                ? 'bg-green-100 text-green-900'
                                : 'bg-red-100 text-red-900'
                            }`}>
                              {check.actual_value || '데이터 없음'}
                            </span>
                          </div>
                        </div>
                        <div className={`ml-3 w-10 h-10 rounded-full flex items-center justify-center ${
                          check.passed ? 'bg-green-500' : 'bg-red-500'
                        }`}>
                          <span className="text-xl text-white font-bold">
                            {check.passed ? '✓' : '✗'}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-3 p-2 bg-blue-50 border border-blue-200 rounded text-xs text-blue-900">
                    <strong>📌 참고:</strong> 위 조건은 <strong>현재 시점</strong> 기준입니다. 백테스트 기간 중 이 조건들을 충족하는 시점이 한 번도 없었습니다.
                    <br />
                    <strong>통과율:</strong> {results.condition_checks.filter(c => c.passed).length} / {results.condition_checks.length}개 ({((results.condition_checks.filter(c => c.passed).length / results.condition_checks.length) * 100).toFixed(0)}%)
                  </div>
                </div>
              ) : (
                <div className="bg-white bg-opacity-70 rounded-lg p-3 text-sm text-amber-900">
                  <strong>💡 가능한 원인:</strong>
                  <ul className="list-disc list-inside mt-2 space-y-1">
                    <li>선택한 기간에 펀더멘털 조건을 충족하지 못함</li>
                    <li>기술적 지표(RSI, MACD 등)가 진입 신호를 발생시키지 않음</li>
                    <li>해당 종목이 이 전략에 적합하지 않을 수 있음</li>
                  </ul>
                </div>
              )}

              <div className="mt-3 p-3 bg-amber-50 border border-amber-300 rounded-lg text-sm text-amber-900">
                <strong>🔧 해결 방법:</strong>
                <ul className="list-disc list-inside mt-1 space-y-1">
                  <li><strong>다른 종목 선택:</strong> 이 전략에 더 적합한 종목을 찾아보세요</li>
                  <li><strong>백테스트 기간 조정:</strong> 더 긴 기간으로 설정하거나, 다른 시기를 선택해보세요</li>
                  <li><strong>다른 전략 시도:</strong> 해당 종목에 더 적합한 다른 대가의 전략을 시도해보세요</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 백테스트 요약 (거래가 있을 때만 표시) */}
      {!hasNoTrades && (
        <div className="card bg-gradient-to-br from-slate-50 to-slate-100 border-2 border-slate-300">
          <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
            💰 백테스트 요약
          </h3>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {/* 시작 자본 */}
            <div className="bg-white rounded-lg p-4 border-2 border-blue-200">
              <div className="text-xs text-blue-700 font-medium mb-1">시작 자본</div>
              <div className="text-2xl font-bold text-blue-900">
                {formatPrice(initialCapitalDisplay, isKoreanStock)}{isKoreanStock ? '원' : ''}
              </div>
            </div>

            {/* 최종 자본 */}
            <div className={`rounded-lg p-4 border-2 ${
              totalPnL === 0
                ? 'bg-white border-blue-200'
                : totalPnL > 0
                  ? 'bg-green-50 border-green-300'
                  : 'bg-red-50 border-red-300'
            }`}>
              <div className={`text-xs font-medium mb-1 ${
                totalPnL === 0
                  ? 'text-blue-700'
                  : totalPnL > 0
                    ? 'text-green-700'
                    : 'text-red-700'
              }`}>최종 자본</div>
              <div className={`text-2xl font-bold ${
                totalPnL === 0
                  ? 'text-blue-900'
                  : totalPnL > 0
                    ? 'text-green-900'
                    : 'text-red-900'
              }`}>
                {formatPrice(finalCapitalDisplay, isKoreanStock)}{isKoreanStock ? '원' : ''}
              </div>
            </div>

            {/* 총 손익 */}
            <div className={`rounded-lg p-4 border-2 ${totalPnL >= 0 ? 'bg-green-50 border-green-300' : 'bg-red-50 border-red-300'}`}>
              <div className={`text-xs font-medium mb-1 ${totalPnL >= 0 ? 'text-green-700' : 'text-red-700'}`}>총 손익</div>
              <div className={`text-2xl font-bold ${totalPnL >= 0 ? 'text-green-900' : 'text-red-900'}`}>
                {totalPnL >= 0 ? '+' : ''}{formatPrice(totalPnL, isKoreanStock)}{isKoreanStock ? '원' : ''}
              </div>
              <div className={`text-sm font-semibold mt-1 ${totalPnL >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                {totalReturn >= 0 ? '+' : ''}{totalReturn.toFixed(2)}%
              </div>
            </div>

            {/* 총 거래 횟수 & 승률 */}
            <div className="bg-white rounded-lg p-4 border-2 border-purple-200">
              <div className="text-xs text-purple-700 font-medium mb-1">거래 성과</div>
              <div className="text-2xl font-bold text-purple-900">
                {trade_history?.length || 0}회
              </div>
              <div className="text-sm text-purple-700 mt-1">
                승률 {winRate.toFixed(1)}% ({winningTrades.length}승 {losingTrades.length}패)
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 가격 차트 with 매수/매도 시점 (거래가 있을 때만 표시) */}
      {!hasNoTrades && price_data && price_data.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-primary-600" />
            📈 가격 차트 & 거래 시점
          </h3>
          <div className="overflow-x-auto">
            {createChart()}
          </div>
          <div className="mt-3 text-xs text-gray-600 flex gap-4">
            <div className="flex items-center gap-1">
              <span className="inline-block w-3 h-3 rounded-full bg-blue-500"></span>
              <span>주가</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="inline-block w-3 h-3 rounded-full bg-green-500"></span>
              <span>▲ 매수</span>
            </div>
            <div className="flex items-center gap-1">
              <span className="inline-block w-3 h-3 rounded-full bg-red-500"></span>
              <span>▼ 매도</span>
            </div>
          </div>
        </div>
      )}

      {/* 백테스트 성과 (거래가 있을 때만 표시) */}
      {!hasNoTrades && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-primary-600" />
            백테스트 상세 지표
          </h3>

          {/* 성과 지표 - 한 줄로 컴팩트하게 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <div className="bg-green-50 border border-green-200 rounded-lg p-3">
            <div className="text-xs text-green-700 mb-1">연간 수익률 (CAGR)</div>
            <div className={`text-lg font-bold ${backtest.metrics.CAGR >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {formatPercent(backtest.metrics.CAGR)}
            </div>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <div className="text-xs text-blue-700 mb-1">샤프 비율 (Sharpe)</div>
            <div className="text-lg font-bold text-blue-600">
              {formatNumber(backtest.metrics.Sharpe)}
            </div>
          </div>

          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <div className="text-xs text-red-700 mb-1">최대 손실 (MDD)</div>
            <div className="text-lg font-bold text-red-600">
              {formatPercent(backtest.metrics.MaxDD)}
            </div>
          </div>

          <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
            <div className="text-xs text-purple-700 mb-1">승률 (Win Rate)</div>
            <div className="text-lg font-bold text-purple-600">
              {formatPercent(backtest.metrics.HitRatio)}
            </div>
          </div>

          {backtest.metrics.AvgWin !== undefined && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-3">
              <div className="text-xs text-green-700 mb-1">평균 수익</div>
              <div className="text-lg font-bold text-green-600">
                {formatPercent(backtest.metrics.AvgWin)}
              </div>
            </div>
          )}

          {backtest.metrics.AvgLoss !== undefined && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <div className="text-xs text-red-700 mb-1">평균 손실</div>
              <div className="text-lg font-bold text-red-600">
                {formatPercent(backtest.metrics.AvgLoss)}
              </div>
            </div>
          )}

          {backtest.metrics.TotalTrades !== undefined && (
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
              <div className="text-xs text-gray-700 mb-1">총 거래</div>
              <div className="text-lg font-bold text-gray-900">
                {backtest.metrics.TotalTrades}회
              </div>
            </div>
          )}
        </div>

        {/* Risk Summary */}
        {backtest.risk_summary && (
          <div className="card bg-gradient-to-r from-rose-50 to-orange-50 border border-rose-200 mt-4">
            <h4 className="text-sm font-semibold text-rose-900 mb-3 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-rose-600" />
              Risk Guardrails
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              {backtest.risk_summary.max_drawdown_pct !== undefined && (
                <div className="bg-white border border-rose-200 rounded-lg p-3">
                  <div className="text-xs text-rose-600 mb-1">Max Drawdown</div>
                  <div className="text-base font-semibold text-rose-700">{formatRiskValue(backtest.risk_summary.max_drawdown_pct)}</div>
                </div>
              )}
              {backtest.risk_summary.max_daily_loss_pct !== undefined && (
                <div className="bg-white border border-amber-200 rounded-lg p-3">
                  <div className="text-xs text-amber-600 mb-1">Worst Day</div>
                  <div className="text-base font-semibold text-amber-700">{formatRiskValue(backtest.risk_summary.max_daily_loss_pct)}</div>
                </div>
              )}
            </div>
            {backtest.warnings && backtest.warnings.length > 0 && (
              <div className="mt-3 text-xs text-rose-700 bg-white border border-rose-100 rounded-lg p-3">
                <strong>Alerts:</strong>
                <ul className="list-disc pl-4 mt-1 space-y-1">
                  {backtest.warnings.map((warning, idx) => (
                    <li key={idx}>{warning}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}

{results.condition_checks && results.condition_checks.length > 0 && (
          <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Target className="w-4 h-4 text-blue-600" />
              매수 조건 상세 체크
            </h4>

            <div className="space-y-2">
              {results.condition_checks.map((check, idx) => (
                <div
                  key={idx}
                  className={`flex items-center justify-between p-2 rounded border ${
                    check.passed
                      ? 'bg-green-50 border-green-300'
                      : 'bg-red-50 border-red-300'
                  }`}
                >
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">
                      {check.condition_name}
                      <span className="ml-1 text-xs text-gray-500">({check.condition_name_en})</span>
                    </div>
                    <div className="text-xs text-gray-600">
                      필요: {check.required_value} → 실제: <span className="font-medium">{check.actual_value || '없음'}</span>
                    </div>
                  </div>
                  <div className={`ml-3 w-8 h-8 rounded-full flex items-center justify-center ${
                    check.passed ? 'bg-green-500' : 'bg-red-500'
                  }`}>
                    <span className="text-lg text-white">
                      {check.passed ? '✓' : '✗'}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-3 text-xs text-blue-800">
              💡 <strong>조건 통과:</strong> {results.condition_checks.filter(c => c.passed).length} / {results.condition_checks.length}개
              {results.condition_checks.filter(c => c.passed).length === 0 && (
                <span className="ml-2 text-red-600 font-medium">
                  (현재 시점 기준 - 과거 백테스트 기간 중 조건 충족 시점 존재 가능)
                </span>
              )}
            </div>
          </div>
        )}

        <div className="mt-4 p-2 bg-gray-50 rounded-lg">
          <div className="text-xs text-gray-600 flex gap-4">
            <div>
              <span className="font-medium">수수료:</span> {backtest.cost_assumptions_bps.fee}bps
            </div>
            <div>
              <span className="font-medium">슬리피지:</span> {backtest.cost_assumptions_bps.slippage}bps
            </div>
          </div>
        </div>
      </div>
      )}

      {/* 펀더멘털 스크리닝 결과 (거래가 있을 때만 표시) */}
      {!hasNoTrades && fundamental_screen && !fundamental_screen.error && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-primary-600" />
            펀더멘털 분석
          </h3>

          {fundamental_screen.criteria && (
            <div className="mb-4">
              <div className="flex items-center gap-3 mb-2">
                <div className="text-sm text-gray-600">투자 기준 통과율:</div>
                <div className="flex-1 bg-gray-200 rounded-full h-4">
                  <div
                    className={`h-4 rounded-full ${
                      fundamental_screen.criteria.pass_rate >= 0.7
                        ? 'bg-green-500'
                        : fundamental_screen.criteria.pass_rate >= 0.5
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                    }`}
                    style={{ width: `${fundamental_screen.criteria.pass_rate * 100}%` }}
                  ></div>
                </div>
                <div className="text-sm font-medium text-gray-900">
                  {formatPercent(fundamental_screen.criteria.pass_rate)} (
                  {fundamental_screen.criteria.passed_count}/{fundamental_screen.criteria.total_count})
                </div>
              </div>
            </div>
          )}

          {fundamental_screen.metrics && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Object.entries(fundamental_screen.metrics).map(([key, value]) => (
                value !== null && value !== undefined && (
                  <div key={key} className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                    <div className="text-xs text-gray-600 mb-1">{key}</div>
                    <div className="text-sm font-medium text-gray-900">
                      {typeof value === 'number' ? value.toFixed(2) : value}
                    </div>
                  </div>
                )
              ))}
            </div>
          )}

          <div className="mt-3 text-xs text-gray-500">
            💡 <strong>현재 시점</strong>의 재무 데이터입니다 (참고용).
            <br />
            백테스트는 각 시점별로 해당 날짜에 공개된 재무제표를 사용하여 매매 여부를 결정합니다.
            <br />
            <strong>통과율이 낮아도</strong> 과거 시점에는 기준을 충족했을 수 있으므로 백테스트 결과와 무관합니다.
          </div>
        </div>
      )}

      {!hasNoTrades && fundamental_screen?.error && (
        <div className="card bg-yellow-50 border-yellow-200">
          <div className="flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5" />
            <div>
              <div className="font-medium text-yellow-900 mb-1">펀더멘털 데이터 부족</div>
              <div className="text-sm text-yellow-700">{fundamental_screen.error}</div>
            </div>
          </div>
        </div>
      )}

      {/* 포트폴리오 차트 (거래가 있을 때만 표시) */}
      {!hasNoTrades && equity_curve && equity_curve.length > 0 && (
        <PortfolioChart
          equityCurve={equity_curve}
          priceData={price_data}
          trades={trade_history || []}
          initialCapital={isKoreanStock ? results.initial_capital_krw! : results.initial_capital}
          currency={isKoreanStock ? 'KRW' : 'USD'}
        />
      )}

      {/* 거래 타임라인 (거래가 있을 때만 표시) */}
      {!hasNoTrades && results.trade_history && results.trade_history.length > 0 && (
        <TradingTimeline
          trades={results.trade_history as any}
          initialCapital={isKoreanStock ? results.initial_capital_krw! : results.initial_capital}
          finalCapital={isKoreanStock ? results.final_capital_krw! : results.final_capital!}
          currency={isKoreanStock ? 'KRW' : 'USD'}
        />
      )}

      {/* 거래 내역 테이블 (상세) - 거래가 있을 때만 표시 */}
      {!hasNoTrades && results.trade_history && results.trade_history.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            📋 거래 내역 상세
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-100 border-b-2 border-gray-300">
                <tr>
                  <th className="px-3 py-2 text-left">매수일</th>
                  <th className="px-3 py-2 text-left">매도일</th>
                  <th className="px-3 py-2 text-right">매수가</th>
                  <th className="px-3 py-2 text-right">매도가</th>
                  <th className="px-3 py-2 text-right">수량</th>
                  <th className="px-3 py-2 text-right">매수금액</th>
                  <th className="px-3 py-2 text-right">손익</th>
                  <th className="px-3 py-2 text-right">수익률</th>
                  <th className="px-3 py-2 text-right bg-blue-50 border-l-2 border-blue-300">거래 후 잔고</th>
                  <th className="px-3 py-2 text-center">보유일</th>
                  <th className="px-3 py-2 text-center">청산사유</th>
                </tr>
              </thead>
              <tbody>
                {results.trade_history.map((trade, idx) => (
                  <tr key={idx} className="border-b border-gray-200 hover:bg-gray-50">
                    <td className="px-3 py-2">{trade.entry_date}</td>
                    <td className="px-3 py-2">{trade.exit_date}</td>
                    <td className="px-3 py-2 text-right text-sm">
                      {trade.currency === 'KRW' ? (
                        <>{formatPrice(trade.entry_price_krw!, true)}원</>
                      ) : (
                        <>${trade.entry_price.toFixed(2)}<br/><span className="text-xs text-gray-500">({formatPrice(trade.entry_price_krw!, true)}원)</span></>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right text-sm">
                      {trade.currency === 'KRW' ? (
                        <>{formatPrice(trade.exit_price_krw!, true)}원</>
                      ) : (
                        <>${trade.exit_price.toFixed(2)}<br/><span className="text-xs text-gray-500">({formatPrice(trade.exit_price_krw!, true)}원)</span></>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right font-medium">
                      {trade.currency === 'KRW' ? Math.round(trade.shares || 0).toLocaleString() : trade.shares?.toFixed(4)}
                    </td>
                    <td className="px-3 py-2 text-right font-medium text-sm">
                      {trade.currency === 'KRW' ? (
                        <>{formatPrice(trade.position_value_krw || 0, true)}원</>
                      ) : (
                        <>${(trade.position_value || 0).toLocaleString()}<br/><span className="text-xs text-gray-500">({formatPrice(trade.position_value_krw || 0, true)}원)</span></>
                      )}
                    </td>
                    <td className={`px-3 py-2 text-right font-bold text-sm ${trade.pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {trade.currency === 'KRW' ? (
                        <>{formatPrice(trade.pnl_krw!, true)}원</>
                      ) : (
                        <>${trade.pnl.toLocaleString()}<br/><span className="text-xs">({formatPrice(trade.pnl_krw!, true)}원)</span></>
                      )}
                    </td>
                    <td className={`px-3 py-2 text-right font-bold ${trade.pnl_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {trade.pnl_pct >= 0 ? '+' : ''}{trade.pnl_pct.toFixed(2)}%
                    </td>
                    <td className="px-3 py-2 text-right bg-blue-50 border-l-2 border-blue-300 font-bold text-blue-900 text-sm">
                      {trade.currency === 'KRW' ? (
                        <>{formatPrice((trade as any).balance_after_krw || 0, true)}원</>
                      ) : (
                        <>${((trade as any).balance_after || 0).toLocaleString()}<br/><span className="text-xs text-gray-500">({formatPrice((trade as any).balance_after_krw || 0, true)}원)</span></>
                      )}
                    </td>
                    <td className="px-3 py-2 text-center">{trade.holding_days}일</td>
                    <td className="px-3 py-2 text-center text-xs">
                      {trade.exit_reason === 'stop_loss' ? '🛑 손절' :
                       trade.exit_reason === 'take_profit' ? '🎯 익절' :
                       trade.exit_reason === 'exit_signal' ? '📤 시그널' : trade.exit_reason}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 실제 매수 시그널 (거래가 있을 때만 표시) */}
      {!hasNoTrades && signal_examples && signal_examples.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            📍 실제 매수 시그널 (최근 {signal_examples.length}건)
          </h3>
          <div className="space-y-2">
            {signal_examples.map((example, idx) => (
              <div key={idx} className="flex items-start gap-3 p-3 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 bg-green-500 text-white rounded-full flex items-center justify-center text-sm font-bold">
                    {idx + 1}
                  </div>
                </div>
                <div className="flex-1">
                  <div className="text-sm font-medium text-gray-900 mb-1">
                    {example.date} - {example.symbol}
                  </div>
                  <div className="text-xs text-gray-700 space-y-0.5">
                    {example.reason.map((r, ridx) => (
                      <div key={ridx}>• {r}</div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}


