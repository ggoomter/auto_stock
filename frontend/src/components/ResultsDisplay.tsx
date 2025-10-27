import { TrendingUp, TrendingDown, BarChart3, AlertCircle, Info, Activity } from 'lucide-react';
import type { AnalysisResponse } from '../services/api';

interface ResultsDisplayProps {
  results: AnalysisResponse;
  initialCapital?: number;
}

export default function ResultsDisplay({ results, initialCapital = 1000000 }: ResultsDisplayProps) {
  const { prediction, backtest, monte_carlo, signal_examples, limitations } = results;

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
    const cagr = backtest.metrics.CAGR;
    const startDate = new Date(results.sample_info.period.start);
    const endDate = new Date(results.sample_info.period.end);
    const years = (endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24 * 365.25);

    const projectedFinal = initialCapital * Math.pow(1 + cagr, Math.max(years, 1 / 12));
    const finalEquity = riskSummary?.ending_equity ?? projectedFinal;
    const totalReturn = finalEquity - initialCapital;
    const totalReturnPct = (totalReturn / initialCapital) * 100;

    return { finalValue: finalEquity, totalReturn, totalReturnPct, years };
  };

  const portfolio = calculatePortfolioValue();

  return (
    <div className="space-y-6">
      {/* 요약 */}
      <div className="card bg-gradient-to-r from-primary-50 to-blue-50 border-primary-200">
        <h2 className="text-xl font-bold text-primary-900 mb-2">백테스트 요약</h2>
        <p className="text-primary-800">{results.summary}</p>
        <div className="mt-4 flex gap-6 text-sm">
          <div>
            <span className="text-primary-600 font-medium">매매 횟수: </span>
            <span className="text-primary-900">{results.sample_info.n_signals}회</span>
          </div>
          <div>
            <span className="text-primary-600 font-medium">테스트 기간: </span>
            <span className="text-primary-900">
              {results.sample_info.period.start} ~ {results.sample_info.period.end}
            </span>
          </div>
        </div>
      </div>

      {/* 포트폴리오 시뮬레이션 */}
      <div className="card bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-400">
        <h2 className="text-xl font-bold text-green-900 mb-4 flex items-center gap-2">
          💰 포트폴리오 시뮬레이션
        </h2>
        <p className="text-sm text-green-700 mb-4">
          초기 자본 {(initialCapital / 10000).toFixed(0)}만원으로 시작했을 때 백테스트 기간 동안의 성과입니다.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white border-2 border-green-300 rounded-lg p-4">
            <div className="text-sm font-medium text-green-600 mb-2">초기 자본</div>
            <div className="text-3xl font-bold text-gray-900">
              {initialCapital.toLocaleString()}원
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {(initialCapital / 10000).toFixed(0)}만원
            </div>
          </div>

          <div className={`border-2 rounded-lg p-4 ${portfolio.totalReturn >= 0 ? 'bg-green-100 border-green-400' : 'bg-red-100 border-red-400'}`}>
            <div className={`text-sm font-medium mb-2 ${portfolio.totalReturn >= 0 ? 'text-green-700' : 'text-red-700'}`}>
              최종 자산
            </div>
            <div className={`text-3xl font-bold ${portfolio.totalReturn >= 0 ? 'text-green-800' : 'text-red-800'}`}>
              {portfolio.finalValue.toLocaleString('ko-KR', { maximumFractionDigits: 0 })}원
            </div>
            <div className="text-xs text-gray-600 mt-1">
              {(portfolio.finalValue / 10000).toLocaleString('ko-KR', { maximumFractionDigits: 1 })}만원
            </div>
          </div>

          <div className={`border-2 rounded-lg p-4 ${portfolio.totalReturn >= 0 ? 'bg-blue-100 border-blue-400' : 'bg-orange-100 border-orange-400'}`}>
            <div className={`text-sm font-medium mb-2 ${portfolio.totalReturn >= 0 ? 'text-blue-700' : 'text-orange-700'}`}>
              총 수익금
            </div>
            <div className={`text-3xl font-bold ${portfolio.totalReturn >= 0 ? 'text-blue-800' : 'text-orange-800'}`}>
              {portfolio.totalReturn >= 0 ? '+' : ''}{portfolio.totalReturn.toLocaleString('ko-KR', { maximumFractionDigits: 0 })}원
            </div>
            <div className={`text-xs mt-1 ${portfolio.totalReturn >= 0 ? 'text-blue-600' : 'text-orange-600'}`}>
              {portfolio.totalReturn >= 0 ? '+' : ''}{(portfolio.totalReturn / 10000).toLocaleString('ko-KR', { maximumFractionDigits: 1 })}만원
            </div>
          </div>

          <div className={`border-2 rounded-lg p-4 ${portfolio.totalReturnPct >= 0 ? 'bg-purple-100 border-purple-400' : 'bg-pink-100 border-pink-400'}`}>
            <div className={`text-sm font-medium mb-2 ${portfolio.totalReturnPct >= 0 ? 'text-purple-700' : 'text-pink-700'}`}>
              수익률
            </div>
            <div className={`text-3xl font-bold ${portfolio.totalReturnPct >= 0 ? 'text-purple-800' : 'text-pink-800'}`}>
              {portfolio.totalReturnPct >= 0 ? '+' : ''}{portfolio.totalReturnPct.toFixed(2)}%
            </div>
            <div className="text-xs text-gray-600 mt-1">
              {portfolio.years.toFixed(1)}년 기간
            </div>
          </div>
        </div>

        <div className="mt-4 bg-white border border-green-300 rounded-lg p-3">
          <p className="text-xs text-gray-700">
            <span className="font-semibold">시뮬레이션 가정:</span> 연평균 수익률(CAGR) {(backtest.metrics.CAGR * 100).toFixed(2)}%를 기준으로 복리 계산
          </p>
        </div>
      </div>

      {/* 백테스트 결과 - 최상단으로 이동 */}
      <div className="card bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-300">
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
        <div className="card bg-gradient-to-r from-rose-50 to-orange-50 border border-rose-200">
          <h2 className="text-xl font-bold text-rose-900 mb-4 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-rose-600" />
            Risk Guardrails
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <MetricCard label="Max Drawdown" value={formatRiskValue(riskSummary.max_drawdown_pct ?? 0)} positive={false} />
            <MetricCard label="Worst Day" value={formatRiskValue(riskSummary.max_daily_loss_pct ?? 0)} positive={false} />
            <MetricCard label="Losing Streak" value={`${riskSummary.max_consecutive_losses ?? 0} trades`} positive={false} />
            <MetricCard label="Largest Loss" value={formatSignedCurrency(riskSummary.largest_loss_amount ?? 0)} positive={false} />
          </div>
          {riskSummary.trading_halted && (
            <div className="mt-4 text-sm text-rose-700 bg-white border border-rose-200 rounded-lg p-3">
              ⚠️ Trading halted: {riskSummary.halt_reason}
            </div>
          )}
        </div>
      )}

      {warnings.length > 0 && (
        <div className="card bg-yellow-50 border border-yellow-200">
          <h3 className="text-lg font-semibold text-yellow-800 mb-3 flex items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            Simulation Alerts
          </h3>
          <ul className="list-disc pl-5 space-y-1 text-sm text-yellow-900">
            {warnings.map((warning, idx) => (
              <li key={idx}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="card">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <TrendingDown className="w-5 h-5 text-primary-600" />
          리스크 시뮬레이션 ({monte_carlo.runs}회 반복)
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

          <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
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

      {/* 매매 신호 예시 */}
      {tradeHistory.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-emerald-600" />
            Trade History (filled orders)
          </h3>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="text-xs uppercase text-gray-500">
                <tr className="border-b border-gray-200">
                  <th className="px-3 py-2 text-left">Entry</th>
                  <th className="px-3 py-2 text-left">Exit</th>
                  <th className="px-3 py-2 text-right">Entry Price</th>
                  <th className="px-3 py-2 text-right">Exit Price</th>
                  <th className="px-3 py-2 text-right">Shares</th>
                  <th className="px-3 py-2 text-right">PnL</th>
                  <th className="px-3 py-2 text-right">Return</th>
                  <th className="px-3 py-2 text-center">Days</th>
                  <th className="px-3 py-2 text-center">Reason</th>
                </tr>
              </thead>
              <tbody>
                {tradeHistory.map((trade, idx) => {
                  const pnlClass = trade.pnl >= 0 ? 'text-green-600' : 'text-red-600';
                  return (
                    <tr key={idx} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="px-3 py-2 text-left text-xs font-medium text-gray-700">{trade.entry_date}</td>
                      <td className="px-3 py-2 text-left text-xs text-gray-600">{trade.exit_date}</td>
                      <td className="px-3 py-2 text-right font-mono text-sm text-gray-700">{formatCurrency(trade.entry_price ?? 0, 2)}</td>
                      <td className="px-3 py-2 text-right font-mono text-sm text-gray-700">{formatCurrency(trade.exit_price ?? 0, 2)}</td>
                      <td className="px-3 py-2 text-right font-mono text-sm text-gray-700">{(trade.shares ?? 0).toFixed(2)}</td>
                      <td className={`px-3 py-2 text-right font-mono text-sm ${pnlClass}`}>{formatSignedCurrency(trade.pnl ?? 0)}</td>
                      <td className={`px-3 py-2 text-right font-mono text-sm ${pnlClass}`}>{formatSignedPercent(trade.pnl_pct ?? 0)}</td>
                      <td className="px-3 py-2 text-center text-xs text-gray-600">{trade.holding_days ?? 0}</td>
                      <td className="px-3 py-2 text-center text-xs text-gray-600">{trade.exit_reason || '-'}{trade.partial ? ' (partial)' : ''}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
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






