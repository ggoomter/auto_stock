import { useState } from 'react';
import { TrendingUp, Award, BarChart3, CheckCircle } from 'lucide-react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface StrategyResult {
  strategy_name: string;
  strategy_description: string;
  metrics: {
    CAGR: number;
    Sharpe: number;
    MaxDD: number;
    WinRate: number;
    TotalTrades: number;
    ProfitFactor: number;
  };
  equity_curve: Array<{ date: string; equity: number }>;
  final_equity: number;
  total_return_pct: number;
  trade_count: number;
}

interface StrategyComparisonProps {
  results: StrategyResult[];
  best_strategy: string;
  initial_capital: number;
}

const STRATEGY_COLORS: Record<string, string> = {
  buffett: '#22c55e',
  lynch: '#3b82f6',
  graham: '#f59e0b',
  dalio: '#8b5cf6',
  livermore: '#ef4444',
  soros: '#ec4899',
  druckenmiller: '#14b8a6',
  oneil: '#f97316'
};

const STRATEGY_NAMES: Record<string, string> = {
  buffett: '워렌 버핏',
  lynch: '피터 린치',
  graham: '벤자민 그레이엄',
  dalio: '레이 달리오',
  livermore: '제시 리버모어',
  soros: '조지 소로스',
  druckenmiller: '스탠리 드러켄밀러',
  oneil: '윌리엄 오닐'
};

export default function StrategyComparison({
  results,
  best_strategy
}: StrategyComparisonProps) {
  const [selectedMetric, setSelectedMetric] = useState<'CAGR' | 'Sharpe' | 'MaxDD' | 'WinRate'>('CAGR');

  // 수익률 차트 데이터
  const equityChartData = {
    labels: results[0]?.equity_curve.map(d => d.date) || [],
    datasets: results.map(result => ({
      label: STRATEGY_NAMES[result.strategy_name] || result.strategy_name,
      data: result.equity_curve.map(d => d.equity),
      borderColor: STRATEGY_COLORS[result.strategy_name] || '#666',
      backgroundColor: STRATEGY_COLORS[result.strategy_name] + '20' || '#66666620',
      borderWidth: 3,
      pointRadius: 0,
      tension: 0.1,
      fill: false
    }))
  };

  const equityChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          font: { size: 12, weight: 'bold' as const },
          usePointStyle: true,
          padding: 15
        }
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
        callbacks: {
          label: (context: any) => {
            const label = context.dataset.label || '';
            const value = context.parsed.y.toLocaleString();
            return `${label}: ${value}원`;
          }
        }
      }
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: '날짜',
          font: { size: 12, weight: 'bold' }
        }
      },
      y: {
        display: true,
        title: {
          display: true,
          text: '포트폴리오 가치 (원)',
          font: { size: 12, weight: 'bold' }
        },
        ticks: {
          callback: (value: any) => value.toLocaleString()
        }
      }
    },
    interaction: {
      mode: 'nearest' as const,
      axis: 'x' as const,
      intersect: false
    }
  };

  // 지표별 정렬
  const sortedResults = [...results].sort((a, b) => {
    if (selectedMetric === 'MaxDD') {
      return a.metrics[selectedMetric] - b.metrics[selectedMetric]; // 작을수록 좋음
    }
    return b.metrics[selectedMetric] - a.metrics[selectedMetric];
  });

  const formatPercent = (value: number) => `${(value * 100).toFixed(2)}%`;

  return (
    <div className="space-y-8">
      {/* 헤더 */}
      <div className="card bg-gradient-to-r from-purple-50 to-pink-50 border-purple-200">
        <h2 className="text-2xl font-bold text-purple-900 mb-2 flex items-center gap-2">
          <BarChart3 className="w-7 h-7" />
          대가 전략 비교 분석
        </h2>
        <p className="text-purple-700">
          여러 투자 대가의 전략을 동시에 백테스트하여 성과를 비교합니다.
        </p>
        <div className="mt-4 flex items-center gap-3 bg-green-100 border-2 border-green-400 rounded-lg p-3">
          <Award className="w-6 h-6 text-green-700" />
          <div>
            <span className="text-sm font-medium text-green-700">최고 성과 전략: </span>
            <span className="text-lg font-bold text-green-900">
              {STRATEGY_NAMES[best_strategy] || best_strategy}
            </span>
          </div>
        </div>
      </div>

      {/* 수익률 비교 차트 */}
      <div className="card">
        <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
          <TrendingUp className="w-6 h-6 text-blue-600" />
          포트폴리오 가치 변화 비교
        </h3>
        <div style={{ height: '400px' }}>
          <Line data={equityChartData} options={equityChartOptions} />
        </div>
      </div>

      {/* 지표 선택 버튼 */}
      <div className="card">
        <h3 className="text-xl font-bold text-gray-900 mb-4">성과 지표별 순위</h3>
        <div className="flex gap-3 mb-6 flex-wrap">
          {['CAGR', 'Sharpe', 'MaxDD', 'WinRate'].map(metric => (
            <button
              key={metric}
              onClick={() => setSelectedMetric(metric as any)}
              className={`px-4 py-2 rounded-lg font-semibold transition-all ${
                selectedMetric === metric
                  ? 'bg-blue-600 text-white shadow-lg'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {metric === 'CAGR' && 'CAGR (연평균 수익률)'}
              {metric === 'Sharpe' && 'Sharpe Ratio (위험 대비 수익)'}
              {metric === 'MaxDD' && 'Max Drawdown (최대 낙폭)'}
              {metric === 'WinRate' && 'Win Rate (승률)'}
            </button>
          ))}
        </div>

        {/* 순위 테이블 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sortedResults.map((result, index) => {
            const isBest = result.strategy_name === best_strategy;
            return (
              <div
                key={result.strategy_name}
                className={`border-2 rounded-lg p-4 transition-all ${
                  isBest
                    ? 'bg-yellow-50 border-yellow-400 shadow-lg'
                    : 'bg-white border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-4 h-4 rounded-full"
                      style={{ backgroundColor: STRATEGY_COLORS[result.strategy_name] }}
                    />
                    <span className="font-bold text-gray-900">
                      #{index + 1} {STRATEGY_NAMES[result.strategy_name]}
                    </span>
                  </div>
                  {isBest && (
                    <CheckCircle className="w-5 h-5 text-yellow-600" />
                  )}
                </div>

                <div className="text-2xl font-bold mb-2" style={{ color: STRATEGY_COLORS[result.strategy_name] }}>
                  {selectedMetric === 'CAGR' && formatPercent(result.metrics.CAGR)}
                  {selectedMetric === 'Sharpe' && result.metrics.Sharpe.toFixed(2)}
                  {selectedMetric === 'MaxDD' && formatPercent(result.metrics.MaxDD)}
                  {selectedMetric === 'WinRate' && formatPercent(result.metrics.WinRate)}
                </div>

                <div className="text-sm text-gray-600 space-y-1">
                  <div>최종 자산: {result.final_equity.toLocaleString()}원</div>
                  <div>총 수익률: {result.total_return_pct.toFixed(2)}%</div>
                  <div>거래 횟수: {result.trade_count}회</div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 상세 지표 비교 테이블 */}
      <div className="card overflow-x-auto">
        <h3 className="text-xl font-bold text-gray-900 mb-4">전체 지표 비교표</h3>
        <table className="w-full text-sm">
          <thead className="bg-gray-100">
            <tr>
              <th className="px-4 py-3 text-left font-bold">전략</th>
              <th className="px-4 py-3 text-right font-bold">CAGR</th>
              <th className="px-4 py-3 text-right font-bold">Sharpe</th>
              <th className="px-4 py-3 text-right font-bold">MaxDD</th>
              <th className="px-4 py-3 text-right font-bold">승률</th>
              <th className="px-4 py-3 text-right font-bold">Profit Factor</th>
              <th className="px-4 py-3 text-right font-bold">거래 수</th>
              <th className="px-4 py-3 text-right font-bold">최종 자산</th>
            </tr>
          </thead>
          <tbody>
            {results.map(result => {
              const isBest = result.strategy_name === best_strategy;
              return (
                <tr
                  key={result.strategy_name}
                  className={`border-b ${isBest ? 'bg-yellow-50 font-bold' : 'hover:bg-gray-50'}`}
                >
                  <td className="px-4 py-3 flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: STRATEGY_COLORS[result.strategy_name] }}
                    />
                    {STRATEGY_NAMES[result.strategy_name]}
                    {isBest && <Award className="w-4 h-4 text-yellow-600 ml-1" />}
                  </td>
                  <td className="px-4 py-3 text-right">{formatPercent(result.metrics.CAGR)}</td>
                  <td className="px-4 py-3 text-right">{result.metrics.Sharpe.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right text-red-600">{formatPercent(result.metrics.MaxDD)}</td>
                  <td className="px-4 py-3 text-right">{formatPercent(result.metrics.WinRate)}</td>
                  <td className="px-4 py-3 text-right">{result.metrics.ProfitFactor.toFixed(2)}</td>
                  <td className="px-4 py-3 text-right">{result.trade_count}</td>
                  <td className="px-4 py-3 text-right font-semibold">
                    {result.final_equity.toLocaleString()}원
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* 요약 통계 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card bg-blue-50 border-blue-200">
          <div className="text-sm text-blue-700 mb-1">평균 CAGR</div>
          <div className="text-2xl font-bold text-blue-900">
            {formatPercent(results.reduce((sum, r) => sum + r.metrics.CAGR, 0) / results.length)}
          </div>
        </div>
        <div className="card bg-green-50 border-green-200">
          <div className="text-sm text-green-700 mb-1">평균 Sharpe</div>
          <div className="text-2xl font-bold text-green-900">
            {(results.reduce((sum, r) => sum + r.metrics.Sharpe, 0) / results.length).toFixed(2)}
          </div>
        </div>
        <div className="card bg-red-50 border-red-200">
          <div className="text-sm text-red-700 mb-1">평균 MaxDD</div>
          <div className="text-2xl font-bold text-red-900">
            {formatPercent(results.reduce((sum, r) => sum + r.metrics.MaxDD, 0) / results.length)}
          </div>
        </div>
        <div className="card bg-purple-50 border-purple-200">
          <div className="text-sm text-purple-700 mb-1">총 거래 수</div>
          <div className="text-2xl font-bold text-purple-900">
            {results.reduce((sum, r) => sum + r.trade_count, 0)}
          </div>
        </div>
      </div>
    </div>
  );
}
