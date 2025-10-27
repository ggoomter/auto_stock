import { useState } from 'react';
import { Calendar, TrendingUp, Settings } from 'lucide-react';
import type { AnalysisRequest } from '../services/api';

interface StrategyFormProps {
  onSubmit: (request: AnalysisRequest) => void;
  isLoading: boolean;
}

export default function StrategyForm({ onSubmit, isLoading }: StrategyFormProps) {
  const [symbols, setSymbols] = useState('AAPL, 005930.KS');
  const [startDate, setStartDate] = useState('2020-01-01');
  const [endDate, setEndDate] = useState('2025-09-30');
  const [entryCondition, setEntryCondition] = useState(
    '( MACD.cross_up == true AND RSI < 30 ) AND ( +DI > -DI )'
  );
  const [exitCondition, setExitCondition] = useState(
    '( MACD.cross_down == true ) OR ( RSI > 70 )'
  );
  const [stopPct, setStopPct] = useState(7);
  const [takePct, setTakePct] = useState(15);
  const [lookahead, setLookahead] = useState(5);
  const [mcRuns, setMcRuns] = useState(1000);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const request: AnalysisRequest = {
      symbols: symbols.split(',').map(s => s.trim()),
      date_range: {
        start: startDate,
        end: endDate,
      },
      horizon: {
        lookahead_days: lookahead,
        rebalance_days: 1,
      },
      strategy: {
        entry: entryCondition,
        exit: exitCondition,
        risk: {
          stop_pct: stopPct / 100,
          take_pct: takePct / 100,
          position_sizing: 'vol_target_10',
        },
      },
      simulate: {
        bootstrap_runs: mcRuns,
        transaction_cost_bps: 10,
        slippage_bps: 5,
      },
      features: ['MACD', 'RSI', 'DMI', 'BBANDS', 'OBV', 'RET', 'VOL'],
      events: ['ELECTION', 'FOMC', 'EARNINGS'],
      explain: true,
      output_detail: 'full',
    };

    onSubmit(request);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* 심볼 및 기간 */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <Calendar className="w-5 h-5 text-primary-600" />
          <h3 className="text-lg font-semibold">기본 설정</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="label">심볼 (쉼표로 구분)</label>
            <input
              type="text"
              className="input"
              value={symbols}
              onChange={(e) => setSymbols(e.target.value)}
              placeholder="AAPL, 005930.KS"
            />
          </div>

          <div>
            <label className="label">예측 기간 (일)</label>
            <input
              type="number"
              className="input"
              value={lookahead}
              onChange={(e) => setLookahead(Number(e.target.value))}
              min={1}
              max={252}
            />
          </div>

          <div>
            <label className="label">시작일</label>
            <input
              type="date"
              className="input"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>

          <div>
            <label className="label">종료일</label>
            <input
              type="date"
              className="input"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* 전략 조건 */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-5 h-5 text-primary-600" />
          <h3 className="text-lg font-semibold">전략 조건</h3>
        </div>

        <div className="space-y-4">
          <div>
            <label className="label">진입 조건</label>
            <textarea
              className="input font-mono text-sm"
              rows={3}
              value={entryCondition}
              onChange={(e) => setEntryCondition(e.target.value)}
              placeholder="( MACD.cross_up == true AND RSI < 30 )"
            />
            <p className="text-xs text-gray-500 mt-1">
              지원: AND, OR, (), &lt;, &gt;, ==, MACD.cross_up, RSI, +DI, -DI, WITHIN(event=&quot;ELECTION&quot;, window_days=20)
            </p>
          </div>

          <div>
            <label className="label">청산 조건</label>
            <textarea
              className="input font-mono text-sm"
              rows={3}
              value={exitCondition}
              onChange={(e) => setExitCondition(e.target.value)}
              placeholder="( MACD.cross_down == true ) OR ( RSI > 70 )"
            />
          </div>
        </div>
      </div>

      {/* 리스크 관리 */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <Settings className="w-5 h-5 text-primary-600" />
          <h3 className="text-lg font-semibold">리스크 관리</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="label">손절 비율 (%)</label>
            <input
              type="number"
              className="input"
              value={stopPct}
              onChange={(e) => setStopPct(Number(e.target.value))}
              min={1}
              max={50}
              step={0.1}
            />
          </div>

          <div>
            <label className="label">익절 비율 (%)</label>
            <input
              type="number"
              className="input"
              value={takePct}
              onChange={(e) => setTakePct(Number(e.target.value))}
              min={1}
              max={100}
              step={0.1}
            />
          </div>

          <div>
            <label className="label">몬테카를로 실행 횟수</label>
            <input
              type="number"
              className="input"
              value={mcRuns}
              onChange={(e) => setMcRuns(Number(e.target.value))}
              min={100}
              max={10000}
              step={100}
            />
          </div>
        </div>
      </div>

      {/* 제출 버튼 */}
      <button
        type="submit"
        disabled={isLoading}
        className="btn btn-primary w-full py-3 text-lg disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? '분석 중...' : '전략 분석 시작'}
      </button>
    </form>
  );
}
