import { useState } from 'react';
import { TrendingUp, TrendingDown, BarChart3, AlertCircle, Activity, ChevronDown, ChevronUp } from 'lucide-react';
import type { AnalysisResponse } from '../services/api';
import TradingViewChart from './TradingViewChart';

interface ResultsDisplayProps {
  results: AnalysisResponse;
  initialCapital?: number;
}

export default function ResultsDisplay({ results, initialCapital = 1000000 }: ResultsDisplayProps) {
  const { backtest, monte_carlo, signal_examples, limitations } = results;

  // 접기/펼치기 상태
  const [showTradeHistory, setShowTradeHistory] = useState(true);
  const [showChart, setShowChart] = useState(true);
  const [showDetailedStats, setShowDetailedStats] = useState(false);

  const riskSummary = backtest.risk_summary;
  const warnings = backtest.warnings ?? (riskSummary?.warnings ?? []);
  const tradeHistory = backtest.trade_history ?? [];

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

    if (tradeHistory.length === 0) {
      return { finalValue: initialCapital, totalReturn: 0, totalReturnPct: 0, years };
    }

    let finalEquity = riskSummary?.ending_equity;
    if (finalEquity === undefined || finalEquity === null) {
      const totalPnL = tradeHistory.reduce((sum, trade) => sum + (trade.pnl ?? 0), 0);
      finalEquity = initialCapital + totalPnL;
    }

    const totalReturn = finalEquity - initialCapital;
    const totalReturnPct = (totalReturn / initialCapital) * 100;

    return { finalValue: finalEquity, totalReturn, totalReturnPct, years };
  };

  const portfolio = calculatePortfolioValue();
  const isProfit = portfolio.totalReturn >= 0;

  // 차트 데이터 변환
  const equityChartData = backtest.equity_curve?.map(item => ({
    time: item.date,
    value: item.value
  })) || [];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* 🎯 히어로 섹션 */}
      <div className={`relative overflow-hidden rounded-2xl shadow-2xl transition-all duration-500 ${
        isProfit
          ? 'bg-gradient-to-br from-green-500 via-emerald-600 to-teal-700'
          : 'bg-gradient-to-br from-red-500 via-rose-600 to-pink-700'
      }`}>
        <div className="absolute inset-0 opacity-10">
          <div className="text-white text-[300px] font-black absolute -right-20 -top-20 rotate-12 select-none">
            {isProfit ? '💰' : '📉'}
          </div>
        </div>

        <div className="relative z-10 p-8 md:p-10">
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="text-white/90 text-lg font-medium mb-1">
                {results.sample_info.period.start} ~ {results.sample_info.period.end} ({portfolio.years.toFixed(1)}년)
              </p>
              <h2 className="text-white text-4xl md:text-5xl font-black tracking-tight">
                {isProfit ? '수익 발생' : '손실 발생'}
              </h2>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white/20 backdrop-blur-md rounded-xl p-6 border border-white/30 shadow-lg">
              <p className="text-white/90 text-sm font-medium mb-2">수익률</p>
              <p className="text-white text-5xl md:text-6xl font-black tracking-tighter">
                {portfolio.totalReturnPct >= 0 ? '+' : ''}{portfolio.totalReturnPct.toFixed(1)}%
              </p>
            </div>

            <div className="bg-white/20 backdrop-blur-md rounded-xl p-6 border border-white/30 shadow-lg">
              <p className="text-white/90 text-sm font-medium mb-2">수익금</p>
              <p className="text-white text-3xl md:text-4xl font-bold">
                {portfolio.totalReturn >= 0 ? '+' : ''}{(portfolio.totalReturn / 10000).toFixed(0)}만원
              </p>
              <p className="text-white/80 text-sm mt-1">
                {portfolio.totalReturn >= 0 ? '+' : ''}{portfolio.totalReturn.toLocaleString('ko-KR', { maximumFractionDigits: 0 })}원
              </p>
            </div>

            <div className="bg-white/20 backdrop-blur-md rounded-xl p-6 border border-white/30 shadow-lg">
              <p className="text-white/90 text-sm font-medium mb-2">총 거래</p>
              <p className="text-white text-3xl md:text-4xl font-bold">
                {results.sample_info.n_signals}회
              </p>
              <p className="text-white/80 text-sm mt-1">
                시뮬레이션 매매 횟수
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* 📈 자산 곡선 차트 */}
      {equityChartData.length > 0 && (
        <div className="card dark:bg-gray-800 dark:border-gray-700">
          <button
            onClick={() => setShowChart(!showChart)}
            className="w-full flex items-center justify-between p-4 bg-gradient-to-r from-gray-50 to-gray-100 dark:from-gray-700 dark:to-gray-800 rounded-lg hover:from-gray-100 hover:to-gray-200 dark:hover:from-gray-600 dark:hover:to-gray-700 transition-colors"
          >
            <div className="flex items-center gap-3">
              <BarChart3 className="w-6 h-6 text-primary-600 dark:text-primary-400" />
              <div className="text-left">
                <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">자산 곡선 차트</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">시간에 따른 포트폴리오 가치 변화</p>
              </div>
            </div>
            {showChart ? <ChevronUp className="w-6 h-6 text-gray-500" /> : <ChevronDown className="w-6 h-6 text-gray-500" />}
          </button>

          {showChart && (
            <div className="mt-4 p-2 bg-white dark:bg-gray-900 rounded-lg border border-gray-100 dark:border-gray-800">
              <TradingViewChart 
                data={equityChartData} 
                type="area"
                colors={{
                  lineColor: isProfit ? '#10b981' : '#ef4444',
                  areaTopColor: isProfit ? 'rgba(16, 185, 129, 0.56)' : 'rgba(239, 68, 68, 0.56)',
                  areaBottomColor: isProfit ? 'rgba(16, 185, 129, 0.04)' : 'rgba(239, 68, 68, 0.04)',
                  textColor: '#9ca3af', // gray-400
                  backgroundColor: 'transparent',
                }}
                height={400}
              />
            </div>
          )}
        </div>
      )}

      {/* 📊 상세 통계 */}
      <div className="card dark:bg-gray-800 dark:border-gray-700">
        <button
          onClick={() => setShowDetailedStats(!showDetailedStats)}
          className="w-full flex items-center justify-between p-4 bg-gradient-to-r from-purple-50 to-indigo-50 dark:from-purple-900/20 dark:to-indigo-900/20 rounded-lg hover:from-purple-100 hover:to-indigo-100 dark:hover:from-purple-900/30 dark:hover:to-indigo-900/30 transition-colors"
        >
          <div className="flex items-center gap-3">
            <Activity className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            <div className="text-left">
              <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">상세 통계 및 분석</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">CAGR, MDD, 샤프/소르티노 비율</p>
            </div>
          </div>
          {showDetailedStats ? <ChevronUp className="w-6 h-6 text-gray-500" /> : <ChevronDown className="w-6 h-6 text-gray-500" />}
        </button>

        {showDetailedStats && (
          <div className="mt-6 space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetricCard 
                label="연평균 수익률" 
                value={`${(backtest.metrics.CAGR * 100).toFixed(2)}%`} 
                positive={backtest.metrics.CAGR > 0} 
              />
              <MetricCard 
                label="최대 낙폭" 
                value={`${(backtest.metrics.MaxDD * 100).toFixed(2)}%`} 
                positive={backtest.metrics.MaxDD > -0.2} 
                invert 
              />
              <MetricCard 
                label="승률" 
                value={`${(backtest.metrics.HitRatio * 100).toFixed(1)}%`} 
                positive={backtest.metrics.HitRatio > 0.5} 
              />
              <MetricCard 
                label="샤프 비율" 
                value={backtest.metrics.Sharpe.toFixed(2)} 
                positive={backtest.metrics.Sharpe > 1} 
              />
              
              {/* 고급 지표 */}
              <MetricCard 
                label="소르티노 비율" 
                value={backtest.metrics.Sortino?.toFixed(2) ?? 'N/A'} 
                positive={(backtest.metrics.Sortino ?? 0) > 1} 
              />
              <MetricCard 
                label="칼마 비율" 
                value={backtest.metrics.Calmar?.toFixed(2) ?? 'N/A'} 
                positive={(backtest.metrics.Calmar ?? 0) > 1} 
              />
              <MetricCard 
                label="테일 비율" 
                value={backtest.metrics.TailRatio?.toFixed(2) ?? 'N/A'} 
                positive={(backtest.metrics.TailRatio ?? 0) > 1} 
              />
              <MetricCard 
                label="총 거래수" 
                value={`${backtest.metrics.TotalTrades}회`} 
                positive={true} 
                neutral 
              />
            </div>

            {/* 리스크 가드레일 */}
            {riskSummary && (
              <div className="bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-lg p-6">
                <h3 className="text-lg font-bold text-rose-900 dark:text-rose-300 mb-4 flex items-center gap-2">
                  <AlertCircle className="w-5 h-5" />
                  리스크 분석
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-sm">
                    <span className="text-gray-500 dark:text-gray-400">최대 연속 손실</span>
                    <p className="font-bold text-rose-700 dark:text-rose-400">{riskSummary.max_consecutive_losses}회</p>
                  </div>
                  <div className="text-sm">
                    <span className="text-gray-500 dark:text-gray-400">최대 손실금액</span>
                    <p className="font-bold text-rose-700 dark:text-rose-400">{formatSignedCurrency(riskSummary.largest_loss_amount ?? 0)}</p>
                  </div>
                  <div className="text-sm">
                    <span className="text-gray-500 dark:text-gray-400">최악의 날</span>
                    <p className="font-bold text-rose-700 dark:text-rose-400">{formatRiskValue(riskSummary.max_daily_loss_pct ?? 0)}</p>
                  </div>
                  <div className="text-sm">
                    <span className="text-gray-500 dark:text-gray-400">거래 중지 여부</span>
                    <p className={`font-bold ${riskSummary.trading_halted ? 'text-red-600' : 'text-green-600'}`}>
                      {riskSummary.trading_halted ? '중지됨' : '정상'}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 📜 거래 내역 */}
      {tradeHistory.length > 0 && (
        <div className="card dark:bg-gray-800 dark:border-gray-700">
          <button
            onClick={() => setShowTradeHistory(!showTradeHistory)}
            className="w-full flex items-center justify-between p-4 bg-gradient-to-r from-blue-50 to-cyan-50 dark:from-blue-900/20 dark:to-cyan-900/20 rounded-lg hover:from-blue-100 hover:to-cyan-100 dark:hover:from-blue-900/30 dark:hover:to-cyan-900/30 transition-colors"
          >
            <div className="flex items-center gap-3">
              <TrendingUp className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              <div className="text-left">
                <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">거래 내역 상세</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">총 {tradeHistory.length}건의 거래 기록</p>
              </div>
            </div>
            {showTradeHistory ? <ChevronUp className="w-6 h-6 text-gray-500" /> : <ChevronDown className="w-6 h-6 text-gray-500" />}
          </button>

          {showTradeHistory && (
            <div className="mt-4 overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
              <table className="min-w-full text-sm text-left">
                <thead className="bg-gray-50 dark:bg-gray-700/50 text-gray-500 dark:text-gray-400 uppercase text-xs font-medium">
                  <tr>
                    <th className="px-4 py-3">종목</th>
                    <th className="px-4 py-3">매수일</th>
                    <th className="px-4 py-3">매도일</th>
                    <th className="px-4 py-3 text-right">매수가</th>
                    <th className="px-4 py-3 text-right">매도가</th>
                    <th className="px-4 py-3 text-right">수익률</th>
                    <th className="px-4 py-3 text-right">손익</th>
                    <th className="px-4 py-3 text-center">사유</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
                  {tradeHistory.map((trade, idx) => {
                    const isWin = trade.pnl >= 0;
                    return (
                      <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
                        <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">{trade.symbol || 'DEFAULT'}</td>
                        <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{trade.entry_date}</td>
                        <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{trade.exit_date}</td>
                        <td className="px-4 py-3 text-right font-mono text-gray-700 dark:text-gray-300">{formatCurrency(trade.entry_price ?? 0)}</td>
                        <td className="px-4 py-3 text-right font-mono text-gray-700 dark:text-gray-300">{formatCurrency(trade.exit_price ?? 0)}</td>
                        <td className={`px-4 py-3 text-right font-mono font-bold ${isWin ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                          {formatSignedPercent(trade.pnl_pct ?? 0)}
                        </td>
                        <td className={`px-4 py-3 text-right font-mono font-bold ${isWin ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}`}>
                          {formatSignedCurrency(trade.pnl ?? 0)}
                        </td>
                        <td className="px-4 py-3 text-center text-xs text-gray-500 dark:text-gray-400">
                          <span className={`px-2 py-1 rounded-full ${trade.partial ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300' : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'}`}>
                            {trade.exit_reason}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface MetricCardProps {
  label: string;
  value: string;
  positive: boolean;
  invert?: boolean;
  neutral?: boolean;
}

function MetricCard({ label, value, positive, invert = false, neutral = false }: MetricCardProps) {
  const isGood = invert ? !positive : positive;
  
  let bgClass = 'bg-gray-50 border-gray-200 dark:bg-gray-700/50 dark:border-gray-600';
  let textClass = 'text-gray-700 dark:text-gray-300';
  let valueClass = 'text-gray-900 dark:text-gray-100';

  if (!neutral) {
    if (isGood) {
      bgClass = 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-800';
      textClass = 'text-green-700 dark:text-green-400';
      valueClass = 'text-green-800 dark:text-green-300';
    } else {
      bgClass = 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800';
      textClass = 'text-red-700 dark:text-red-400';
      valueClass = 'text-red-800 dark:text-red-300';
    }
  }

  return (
    <div className={`p-4 rounded-lg border ${bgClass}`}>
      <div className={`text-xs font-medium mb-1 ${textClass}`}>
        {label}
      </div>
      <div className={`text-2xl font-bold ${valueClass}`}>
        {value}
      </div>
    </div>
  );
}
