import { useState } from 'react';
import { TrendingUp, TrendingDown, BarChart3, AlertCircle, Info, Activity, ChevronDown, ChevronUp } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';
import type { AnalysisResponse } from '../services/api';
import StockChart from './StockChart';

interface ResultsDisplayProps {
  results: AnalysisResponse;
  initialCapital?: number;
}

export default function ResultsDisplay({ results, initialCapital = 1000000 }: ResultsDisplayProps) {
  const { prediction, backtest, monte_carlo, signal_examples, limitations } = results;

  // 접기/펼치기 상태 - 거래 내역과 차트는 기본으로 펼침
  const [showTradeHistory, setShowTradeHistory] = useState(true);
  const [showChart, setShowChart] = useState(true);
  const [showDetailedStats, setShowDetailedStats] = useState(false);

  const riskSummary = backtest.risk_summary;
  const warnings = backtest.warnings ?? (riskSummary?.warnings ?? []);
  const tradeHistory = backtest.trade_history ?? [];

  // 디버깅: 거래 내역 확인
  console.log('[ResultsDisplay] Debug Info:', {
    hasTradeHistory: !!backtest.trade_history,
    tradeCount: tradeHistory.length,
    trades: tradeHistory,
    backtest,
    metrics: backtest.metrics
  });
  const formatRiskValue = (value: number) => `${(Math.abs(value) * 100).toFixed(2)}%`;
  const formatCurrency = (value: number, digits = 0) =>
    value.toLocaleString('ko-KR', { maximumFractionDigits: digits, minimumFractionDigits: digits });

  const formatSignedCurrency = (value: number) => {
    const sign = value >= 0 ? '+' : '-';
    return `${sign}${formatCurrency(Math.abs(value))}`;
  };
  const formatSignedPercent = (value: number) => {
    const sign = value >= 0 ? '+' : '-';
    return `${sign}${Math.abs(value).toFixed(2)}%`;
  };

  const calculatePortfolioValue = () => {
    const startDate = new Date(results.sample_info.period.start);
    const endDate = new Date(results.sample_info.period.end);
    const years = (endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24 * 365.25);

    // 거래가 0건이면 수익률 0%
    if (tradeHistory.length === 0) {
      console.log('[ResultsDisplay] 거래 0건 - 수익률 0%로 설정');
      return {
        finalValue: initialCapital,
        totalReturn: 0,
        totalReturnPct: 0,
        years
      };
    }

    // 백엔드에서 제공하는 ending_equity를 우선 사용
    let finalEquity = riskSummary?.ending_equity;

    // ending_equity가 없으면 거래 내역의 PnL 합계로 계산
    if (finalEquity === undefined || finalEquity === null) {
      const totalPnL = tradeHistory.reduce((sum, trade) => sum + (trade.pnl ?? 0), 0);
      finalEquity = initialCapital + totalPnL;
      console.log('[ResultsDisplay] ending_equity 없음, PnL 합계로 계산:', { totalPnL, finalEquity });
    }

    const totalReturn = finalEquity - initialCapital;
    const totalReturnPct = (totalReturn / initialCapital) * 100;

    console.log('[ResultsDisplay] 포트폴리오 계산:', {
      initialCapital,
      finalEquity,
      totalReturn,
      totalReturnPct,
      years,
      tradeCount: tradeHistory.length,
      ending_equity_from_backend: riskSummary?.ending_equity
    });

    return { finalValue: finalEquity, totalReturn, totalReturnPct, years };
  };

  const portfolio = calculatePortfolioValue();

  const isProfit = portfolio.totalReturn >= 0;

  return (
    <div className="space-y-6">
      {/* 🎯 히어로 섹션: 수익/손실 대형 표시 */}
      <div className={`relative overflow-hidden rounded-2xl shadow-2xl ${
        isProfit
          ? 'bg-gradient-to-br from-green-400 via-green-500 to-emerald-600'
          : 'bg-gradient-to-br from-red-400 via-red-500 to-rose-600'
      }`}>
        <div className="absolute inset-0 opacity-10">
          {isProfit ? (
            <div className="text-white text-[300px] font-black absolute -right-20 -top-20 rotate-12">💰</div>
          ) : (
            <div className="text-white text-[300px] font-black absolute -right-20 -top-20 rotate-12">📉</div>
          )}
        </div>

        <div className="relative z-10 p-8 md:p-12">
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-white/80 text-lg font-medium mb-1">
                {results.sample_info.period.start} ~ {results.sample_info.period.end} ({portfolio.years.toFixed(1)}년)
              </p>
              <h2 className="text-white text-4xl md:text-5xl font-black">
                {isProfit ? '💰 수익 발생!' : '📉 손실 발생'}
              </h2>
            </div>
          </div>

          <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* 수익률 */}
            <div className="bg-white/20 backdrop-blur-sm rounded-xl p-6 border-2 border-white/30">
              <p className="text-white/90 text-sm font-medium mb-2">수익률</p>
              <p className="text-white text-5xl md:text-6xl font-black">
                {portfolio.totalReturnPct >= 0 ? '+' : ''}{portfolio.totalReturnPct.toFixed(1)}%
              </p>
            </div>

            {/* 수익금 */}
            <div className="bg-white/20 backdrop-blur-sm rounded-xl p-6 border-2 border-white/30">
              <p className="text-white/90 text-sm font-medium mb-2">수익금</p>
              <p className="text-white text-3xl md:text-4xl font-bold">
                {portfolio.totalReturn >= 0 ? '+' : ''}{(portfolio.totalReturn / 10000).toFixed(0)}만원
              </p>
              <p className="text-white/70 text-sm mt-1">
                {portfolio.totalReturn >= 0 ? '+' : ''}{portfolio.totalReturn.toLocaleString('ko-KR', { maximumFractionDigits: 0 })}원
              </p>
            </div>

            {/* 거래 횟수 */}
            <div className="bg-white/20 backdrop-blur-sm rounded-xl p-6 border-2 border-white/30">
              <p className="text-white/90 text-sm font-medium mb-2">총 거래</p>
              <p className="text-white text-3xl md:text-4xl font-bold">
                {results.sample_info.n_signals}회
              </p>
              <p className="text-white/70 text-sm mt-1">
                백테스트 매매 횟수
              </p>
            </div>
          </div>

          {/* 자본 흐름 */}
          <div className="mt-8 bg-white/10 backdrop-blur-sm rounded-xl p-6 border-2 border-white/20">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white/80 text-xs font-medium mb-1">초기 자본</p>
                <p className="text-white text-2xl font-bold">
                  {(initialCapital / 10000).toFixed(0)}만원
                </p>
              </div>

              <div className="text-white text-4xl font-black">→</div>

              <div>
                <p className="text-white/80 text-xs font-medium mb-1">최종 자산</p>
                <p className="text-white text-2xl font-bold">
                  {(portfolio.finalValue / 10000).toFixed(0)}만원
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 📈 상세 통계 (접을 수 있게) */}
      <div className="card">
        <button
          onClick={() => setShowDetailedStats(!showDetailedStats)}
          className="w-full flex items-center justify-between p-4 bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg hover:from-purple-100 hover:to-pink-100 transition-colors"
        >
          <div className="flex items-center gap-3">
            <BarChart3 className="w-6 h-6 text-purple-600" />
            <div className="text-left">
              <h3 className="text-lg font-bold text-gray-900">상세 통계 및 분석</h3>
              <p className="text-sm text-gray-600">CAGR, 샤프 비율, 몬테카를로 시뮬레이션</p>
            </div>
          </div>
          {showDetailedStats ? (
            <ChevronUp className="w-6 h-6 text-gray-600" />
          ) : (
            <ChevronDown className="w-6 h-6 text-gray-600" />
          )}
        </button>

        {showDetailedStats && (
          <div className="mt-6 space-y-6">
            {/* 백테스트 결과 */}
            <div className="bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-300 rounded-lg p-6">
              <h3 className="text-xl font-bold mb-6 flex items-center gap-2 text-primary-900">
                <BarChart3 className="w-6 h-6 text-primary-600" />
                전략 성과 지표
              </h3>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
          <div className={`p-4 rounded-lg border-2 ${backtest.metrics.CAGR > 0 ? 'bg-green-50 border-green-300' : 'bg-red-50 border-red-300'}`}>
            <div className={`text-sm font-medium mb-1 ${backtest.metrics.CAGR > 0 ? 'text-green-600' : 'text-red-600'}`}>
              연평균 수익률 (CAGR)
            </div>
            <div className={`text-3xl font-bold ${backtest.metrics.CAGR > 0 ? 'text-green-700' : 'text-red-700'}`}>
              {backtest.metrics.CAGR > 0 ? '+' : ''}{(backtest.metrics.CAGR * 100).toFixed(2)}%
            </div>
          </div>

          <div className={`p-4 rounded-lg border-2 ${backtest.metrics.HitRatio > 0.5 ? 'bg-green-50 border-green-300' : 'bg-red-50 border-red-300'}`}>
            <div className={`text-sm font-medium mb-1 ${backtest.metrics.HitRatio > 0.5 ? 'text-green-600' : 'text-red-600'}`}>
              승률 (Hit Ratio)
            </div>
            <div className={`text-3xl font-bold ${backtest.metrics.HitRatio > 0.5 ? 'text-green-700' : 'text-red-700'}`}>
              {(backtest.metrics.HitRatio * 100).toFixed(1)}%
            </div>
          </div>

          <div className={`p-4 rounded-lg border-2 ${backtest.metrics.MaxDD > -0.2 ? 'bg-green-50 border-green-300' : 'bg-red-50 border-red-300'}`}>
            <div className={`text-sm font-medium mb-1 ${backtest.metrics.MaxDD > -0.2 ? 'text-green-600' : 'text-red-600'}`}>
              최대 낙폭 (Max DD)
            </div>
            <div className={`text-3xl font-bold ${backtest.metrics.MaxDD > -0.2 ? 'text-green-700' : 'text-red-700'}`}>
              {(backtest.metrics.MaxDD * 100).toFixed(2)}%
            </div>
          </div>

          <div className="p-4 rounded-lg border-2 bg-blue-50 border-blue-300">
            <div className="text-sm font-medium mb-1 text-blue-600">
              샤프 비율 (Sharpe)
            </div>
            <div className={`text-3xl font-bold ${backtest.metrics.Sharpe > 1 ? 'text-green-700' : 'text-blue-700'}`}>
              {backtest.metrics.Sharpe.toFixed(2)}
            </div>
          </div>

          {backtest.metrics.AvgWin && (
            <div className="p-4 rounded-lg border-2 bg-green-50 border-green-300">
              <div className="text-sm font-medium mb-1 text-green-600">
                평균 수익 (Avg Win)
              </div>
              <div className="text-3xl font-bold text-green-700">
                +{(backtest.metrics.AvgWin * 100).toFixed(2)}%
              </div>
            </div>
          )}

          {backtest.metrics.AvgLoss && (
            <div className="p-4 rounded-lg border-2 bg-red-50 border-red-300">
              <div className="text-sm font-medium mb-1 text-red-600">
                평균 손실 (Avg Loss)
              </div>
              <div className="text-3xl font-bold text-red-700">
                {(backtest.metrics.AvgLoss * 100).toFixed(2)}%
              </div>
            </div>
          )}
        </div>

        <div className="bg-white border border-blue-200 rounded-lg p-3">
          <p className="text-sm text-gray-700">
            <span className="font-semibold">거래 비용:</span> 수수료 {backtest.cost_assumptions_bps.fee}bps, 슬리피지 {backtest.cost_assumptions_bps.slippage}bps 반영
          </p>
        </div>
      </div>

      {/* 몬테카를로 시뮬레이션 - 리스크 분석 */}
      {riskSummary && (
        <div className="bg-gradient-to-r from-rose-50 to-orange-50 border-2 border-rose-300 rounded-lg p-6">
          <h3 className="text-xl font-bold text-rose-900 mb-4 flex items-center gap-2">
            <AlertCircle className="w-6 h-6 text-rose-600" />
            리스크 가드레일
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <MetricCard label="최대 낙폭" value={formatRiskValue(riskSummary.max_drawdown_pct ?? 0)} positive={false} />
            <MetricCard label="최악의 날" value={formatRiskValue(riskSummary.max_daily_loss_pct ?? 0)} positive={false} />
            <MetricCard label="연속 손실" value={`${riskSummary.max_consecutive_losses ?? 0}회`} positive={false} />
            <MetricCard label="최대 손실금액" value={formatSignedCurrency(riskSummary.largest_loss_amount ?? 0)} positive={false} />
          </div>
          {riskSummary.trading_halted && (
            <div className="mt-4 text-sm text-rose-700 bg-white border border-rose-200 rounded-lg p-3">
              ⚠️ 거래 중지: {riskSummary.halt_reason}
            </div>
          )}
        </div>
      )}

      {warnings.length > 0 && (
        <div className="bg-yellow-50 border-2 border-yellow-300 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-yellow-800 mb-3 flex items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            시뮬레이션 경고
          </h3>
          <ul className="list-disc pl-5 space-y-1 text-sm text-yellow-900">
            {warnings.map((warning, idx) => (
              <li key={idx}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 몬테카를로 시뮬레이션 */}
      <div className="bg-gradient-to-br from-purple-50 to-pink-50 border-2 border-purple-300 rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <TrendingDown className="w-5 h-5 text-purple-600" />
          몬테카를로 시뮬레이션 ({monte_carlo.runs}회 반복)
        </h3>

        <p className="text-sm text-gray-600 mb-4">
          랜덤 샘플링으로 {monte_carlo.runs}번 반복 테스트한 결과입니다. 전략의 안정성을 확인하세요.
        </p>

        <div className="space-y-4">
          <div>
            <div className="text-sm font-semibold text-gray-700 mb-2">연평균 수익률 (CAGR) 범위</div>
            <div className="flex items-center gap-4">
              <div className="flex-1">
                <div className="bg-gray-200 h-10 rounded-lg overflow-hidden flex">
                  <div className="bg-red-400 h-full" style={{ width: '33.33%' }}></div>
                  <div className="bg-yellow-400 h-full" style={{ width: '33.33%' }}></div>
                  <div className="bg-green-400 h-full" style={{ width: '33.34%' }}></div>
                </div>
                <div className="flex justify-between text-sm font-medium text-gray-700 mt-2">
                  <span>최저 5%: {(monte_carlo.p5_cagr * 100).toFixed(2)}%</span>
                  <span>중앙값: {(monte_carlo.p50_cagr * 100).toFixed(2)}%</span>
                  <span>최고 5%: {(monte_carlo.p95_cagr * 100).toFixed(2)}%</span>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white border border-purple-200 rounded-lg p-4">
            <div className="text-sm font-semibold text-gray-700 mb-3">최대 낙폭 (Max DD) 범위</div>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <div className="text-gray-500 mb-1">최저 5%</div>
                <div className="font-mono font-bold text-gray-900">{(monte_carlo.maxdd_distribution.p5 * 100).toFixed(2)}%</div>
              </div>
              <div>
                <div className="text-gray-500 mb-1">중앙값</div>
                <div className="font-mono font-bold text-gray-900">{(monte_carlo.maxdd_distribution.p50 * 100).toFixed(2)}%</div>
              </div>
              <div>
                <div className="text-gray-500 mb-1">최고 5%</div>
                <div className="font-mono font-bold text-gray-900">{(monte_carlo.maxdd_distribution.p95 * 100).toFixed(2)}%</div>
              </div>
            </div>
          </div>
        </div>
      </div>
          </div>
        )}
      </div>

      {/* 📈 자산 곡선 차트 (접을 수 있게) */}
      {backtest.equity_curve && backtest.equity_curve.length > 0 && (
        <div className="card">
          <button
            onClick={() => setShowChart(!showChart)}
            className="w-full flex items-center justify-between p-4 bg-gradient-to-r from-cyan-50 to-blue-50 rounded-lg hover:from-cyan-100 hover:to-blue-100 transition-colors"
          >
            <div className="flex items-center gap-3">
              <BarChart3 className="w-6 h-6 text-cyan-600" />
              <div className="text-left">
                <h3 className="text-lg font-bold text-gray-900">자산 곡선 차트</h3>
                <p className="text-sm text-gray-600">시간에 따른 포트폴리오 가치 변화</p>
              </div>
            </div>
            {showChart ? (
              <ChevronUp className="w-6 h-6 text-gray-600" />
            ) : (
              <ChevronDown className="w-6 h-6 text-gray-600" />
            )}
          </button>

          {showChart && (
            <div className="mt-4">
              <div className="h-[400px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={backtest.equity_curve} margin={{ top: 10, right: 30, left: 20, bottom: 10 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 12 }}
                      tickFormatter={(date) => {
                        const d = new Date(date);
                        return `${d.getMonth() + 1}/${d.getDate()}`;
                      }}
                    />
                    <YAxis
                      tick={{ fontSize: 12 }}
                      tickFormatter={(value) => `${(value / 10000).toFixed(0)}만`}
                      domain={['auto', 'auto']}
                    />
                    <Tooltip
                      formatter={(value: number) => [`${formatCurrency(value)}원`, '자산 가치']}
                      labelFormatter={(label) => `날짜: ${label}`}
                      contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.95)', border: '1px solid #e5e7eb', borderRadius: '8px' }}
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="value"
                      stroke="#0ea5e9"
                      strokeWidth={2}
                      dot={false}
                      name="포트폴리오 가치"
                      activeDot={{ r: 6 }}
                    />
                    <ReferenceLine
                      y={initialCapital}
                      stroke="#ef4444"
                      strokeDasharray="5 5"
                      label={{ value: '초기 자본', position: 'right', fill: '#ef4444', fontSize: 12 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              {/* 거래 시점 표시 */}
              {tradeHistory.length > 0 && (
                <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                  <h4 className="text-sm font-semibold text-gray-700 mb-2">거래 시점</h4>
                  <div className="flex flex-wrap gap-2">
                    {tradeHistory.slice(0, 10).map((trade, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-xs bg-white px-3 py-1 rounded-full border border-gray-200">
                        <span className="text-green-600 font-bold">매수</span>
                        <span className="text-gray-600">{trade.entry_date}</span>
                        <span className="text-gray-400">→</span>
                        <span className="text-red-600 font-bold">매도</span>
                        <span className="text-gray-600">{trade.exit_date}</span>
                      </div>
                    ))}
                    {tradeHistory.length > 10 && (
                      <span className="text-xs text-gray-500 px-3 py-1">... 외 {tradeHistory.length - 10}건</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* 📊 거래 내역 (접을 수 있게) */}
      {tradeHistory.length > 0 ? (
        <div className="card">
          <button
            onClick={() => setShowTradeHistory(!showTradeHistory)}
            className="w-full flex items-center justify-between p-4 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg hover:from-blue-100 hover:to-indigo-100 transition-colors"
          >
            <div className="flex items-center gap-3">
              <Activity className="w-6 h-6 text-blue-600" />
              <div className="text-left">
                <h3 className="text-lg font-bold text-gray-900">거래 내역 상세</h3>
                <p className="text-sm text-gray-600">총 {tradeHistory.length}건의 거래 기록</p>
              </div>
            </div>
            {showTradeHistory ? (
              <ChevronUp className="w-6 h-6 text-gray-600" />
            ) : (
              <ChevronDown className="w-6 h-6 text-gray-600" />
            )}
          </button>

          {showTradeHistory && (
            <div className="mt-4 overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="text-xs uppercase text-gray-500 bg-gray-50">
                  <tr className="border-b-2 border-gray-200">
                    <th className="px-4 py-3 text-left">매수일</th>
                    <th className="px-4 py-3 text-left">매도일</th>
                    <th className="px-4 py-3 text-right">매수가</th>
                    <th className="px-4 py-3 text-right">매도가</th>
                    <th className="px-4 py-3 text-right">주식수</th>
                    <th className="px-4 py-3 text-right">손익</th>
                    <th className="px-4 py-3 text-right">수익률</th>
                    <th className="px-4 py-3 text-center">보유일</th>
                    <th className="px-4 py-3 text-center">청산 사유</th>
                  </tr>
                </thead>
                <tbody>
                  {tradeHistory.map((trade, idx) => {
                    const pnlClass = trade.pnl >= 0 ? 'text-green-600 font-semibold' : 'text-red-600 font-semibold';
                    return (
                      <tr key={idx} className="border-b border-gray-100 hover:bg-blue-50 transition-colors">
                        <td className="px-4 py-3 text-left text-xs font-medium text-gray-700">{trade.entry_date}</td>
                        <td className="px-4 py-3 text-left text-xs text-gray-600">{trade.exit_date}</td>
                        <td className="px-4 py-3 text-right font-mono text-sm text-gray-700">{formatCurrency(trade.entry_price ?? 0, 2)}</td>
                        <td className="px-4 py-3 text-right font-mono text-sm text-gray-700">{formatCurrency(trade.exit_price ?? 0, 2)}</td>
                        <td className="px-4 py-3 text-right font-mono text-sm text-gray-700">{(trade.shares ?? 0).toFixed(2)}</td>
                        <td className={`px-4 py-3 text-right font-mono text-sm ${pnlClass}`}>{formatSignedCurrency(trade.pnl ?? 0)}</td>
                        <td className={`px-4 py-3 text-right font-mono text-sm ${pnlClass}`}>{formatSignedPercent(trade.pnl_pct ?? 0)}</td>
                        <td className="px-4 py-3 text-center text-xs text-gray-600">{trade.holding_days ?? 0}일</td>
                        <td className="px-4 py-3 text-center text-xs text-gray-600">{trade.exit_reason || '-'}{trade.partial ? ' (일부)' : ''}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        <div className="card bg-gradient-to-r from-yellow-50 to-orange-50 border-2 border-yellow-400">
          <div className="flex items-start gap-4">
            <AlertCircle className="w-12 h-12 text-yellow-600 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="text-lg font-bold text-yellow-900 mb-2">⚠️ 거래 내역 없음</h3>
              <p className="text-yellow-800 mb-3">
                백테스트 기간 동안 전략 조건을 충족하는 매매 시그널이 발생하지 않았습니다.
              </p>
              <div className="bg-white border border-yellow-300 rounded-lg p-3 text-sm">
                <p className="font-semibold text-yellow-900 mb-2">가능한 원인:</p>
                <ul className="list-disc list-inside space-y-1 text-yellow-800">
                  <li>진입 조건이 너무 까다로워 신호가 발생하지 않음</li>
                  <li>선택한 종목이 전략과 맞지 않음</li>
                  <li>백테스트 기간이 너무 짧음</li>
                  <li>기술적 지표 값이 조건을 충족하지 못함</li>
                </ul>
                <p className="mt-3 text-yellow-900 font-medium">💡 해결 방법:</p>
                <ul className="list-disc list-inside space-y-1 text-yellow-800">
                  <li>진입 조건을 완화하거나 다른 조건으로 변경</li>
                  <li>다른 종목으로 테스트</li>
                  <li>백테스트 기간을 늘림 (최소 1년 이상 권장)</li>
                </ul>
              </div>
              <div className="mt-3 text-xs text-yellow-700">
                브라우저 콘솔 (F12)에서 <code>[ResultsDisplay] Debug Info</code>를 확인하여 상세 정보를 볼 수 있습니다.
              </div>
            </div>
          </div>
        </div>
      )}

      {signal_examples.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-primary-600" />
            백테스트 매매 신호 예시
          </h3>

          <p className="text-sm text-gray-600 mb-4">
            백테스트 기간 동안 발생한 실제 매수 신호입니다. 조건이 어떻게 동작했는지 확인하세요.
          </p>

          <div className="space-y-3">
            {signal_examples.map((example, idx) => (
              <div key={idx} className="bg-gradient-to-r from-green-50 to-blue-50 border border-green-200 p-4 rounded-lg">
                <div className="flex items-center gap-4 mb-2">
                  <span className="bg-green-600 text-white px-3 py-1 rounded-full text-sm font-bold">매수</span>
                  <span className="text-sm font-semibold text-gray-800">{example.date}</span>
                  <span className="text-sm text-primary-700 font-mono font-bold">{example.symbol}</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {example.reason.map((r, i) => (
                    <span key={i} className="text-xs bg-white border border-green-300 text-green-800 px-3 py-1 rounded-full font-medium">
                      ✓ {r}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 한계 및 주의사항 */}
      <div className="card bg-yellow-50 border-yellow-200">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-yellow-900">
          <AlertCircle className="w-5 h-5" />
          한계 및 주의사항
        </h3>

        <ul className="space-y-2 text-sm text-yellow-900">
          {limitations.map((limitation, idx) => (
            <li key={idx} className="flex items-start gap-2">
              <span className="text-yellow-600 mt-1">•</span>
              <span>{limitation}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

interface MetricCardProps {
  label: string;
  value: string;
  positive: boolean;
}

function MetricCard({ label, value, positive }: MetricCardProps) {
  return (
    <div className={`p-3 rounded-lg border ${positive ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
      <div className={`text-xs font-medium mb-1 ${positive ? 'text-green-600' : 'text-red-600'}`}>
        {label}
      </div>
      <div className={`text-lg font-bold ${positive ? 'text-green-700' : 'text-red-700'}`}>
        {value}
      </div>
    </div>
  );
}






