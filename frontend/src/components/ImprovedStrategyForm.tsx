import { useState } from 'react';
import { Calendar, TrendingUp, Settings, AlertTriangle } from 'lucide-react';
import type { AnalysisRequest } from '../services/api';
import StrategyBuilder from './StrategyBuilder';

interface ImprovedStrategyFormProps {
  onSubmit: (request: AnalysisRequest) => void;
  isLoading: boolean;
}

export default function ImprovedStrategyForm({ onSubmit, isLoading }: ImprovedStrategyFormProps) {
  // 기본 설정
  const [symbols, setSymbols] = useState('AAPL');
  const [lookahead, setLookahead] = useState(5);

  // 날짜 설정 - 기본값을 예측 기간에 맞게 자동 조정
  const today = new Date();
  const defaultEndDate = today.toISOString().split('T')[0];
  const defaultStartDate = new Date(today);
  defaultStartDate.setMonth(defaultStartDate.getMonth() - 6); // 6개월 전

  const [startDate, setStartDate] = useState(defaultStartDate.toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState(defaultEndDate);

  // 전략 조건
  const [entryCondition, setEntryCondition] = useState('RSI < 30');
  const [exitCondition, setExitCondition] = useState('RSI > 70');

  // 리스크 관리
  const [stopPct, setStopPct] = useState(7);
  const [takePct, setTakePct] = useState(15);
  const [mcRuns, setMcRuns] = useState(1000);
  const [investmentAmount, setInvestmentAmount] = useState(10000000); // 1천만원

  // 학습 기간 자동 조정
  const handleLookaheadChange = (days: number) => {
    setLookahead(days);

    // 예측 기간의 최소 60배 데이터 확보 (통계적 유의성)
    const minMonths = Math.max(6, Math.ceil(days / 5)); // 최소 6개월
    const newStartDate = new Date(today);
    newStartDate.setMonth(newStartDate.getMonth() - minMonths);
    setStartDate(newStartDate.toISOString().split('T')[0]);
  };

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

  // 날짜 범위 검증
  const getDataMonths = () => {
    const start = new Date(startDate);
    const end = new Date(endDate);
    const months = (end.getFullYear() - start.getFullYear()) * 12 +
                   (end.getMonth() - start.getMonth());
    return months;
  };

  const isDataSufficient = getDataMonths() >= 6;
  const recommendedMonths = Math.max(6, Math.ceil(lookahead / 5));

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* 기본 설정 */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <Calendar className="w-5 h-5 text-primary-600" />
          <h3 className="text-lg font-semibold">기본 설정</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="label">
              종목 코드 (티커)
              <span className="text-xs text-gray-500 ml-2">예: AAPL, 005930.KS</span>
            </label>
            <input
              type="text"
              className="input"
              value={symbols}
              onChange={(e) => setSymbols(e.target.value)}
              placeholder="AAPL"
              required
            />
          </div>

          <div>
            <label className="label">
              예측 기간 (일)
              <span className="text-xs text-gray-500 ml-2">매수 후 보유 일수</span>
            </label>
            <div className="flex gap-2">
              <input
                type="range"
                className="flex-1"
                value={lookahead}
                onChange={(e) => handleLookaheadChange(Number(e.target.value))}
                min={1}
                max={60}
              />
              <input
                type="number"
                className="input w-20"
                value={lookahead}
                onChange={(e) => handleLookaheadChange(Number(e.target.value))}
                min={1}
                max={252}
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              현재: {lookahead}일 (약 {Math.round(lookahead / 5)}주)
            </p>
          </div>

          <div>
            <label className="label">
              데이터 시작일
              <span className="text-xs text-gray-500 ml-2">학습 데이터 시작</span>
            </label>
            <input
              type="date"
              className="input"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              max={endDate}
              required
            />
          </div>

          <div>
            <label className="label">
              데이터 종료일
              <span className="text-xs text-gray-500 ml-2">학습 데이터 종료</span>
            </label>
            <input
              type="date"
              className="input"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              min={startDate}
              max={new Date().toISOString().split('T')[0]}
              required
            />
          </div>
        </div>

        {/* 데이터 기간 경고 */}
        {!isDataSufficient && (
          <div className="mt-4 bg-yellow-50 border border-yellow-200 rounded-lg p-3 flex items-start gap-2">
            <AlertTriangle className="w-5 h-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-yellow-800">
              <p className="font-medium">데이터 기간이 부족합니다</p>
              <p className="text-xs mt-1">
                현재: {getDataMonths()}개월 | 권장: 최소 {recommendedMonths}개월 이상
                (예측 기간의 60배 데이터 필요)
              </p>
            </div>
          </div>
        )}
      </div>

      {/* 진입 전략 */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-5 h-5 text-green-600" />
          <h3 className="text-lg font-semibold">진입 조건 (언제 매수할까?)</h3>
        </div>
        <StrategyBuilder type="entry" onChange={setEntryCondition} />
      </div>

      {/* 청산 전략 */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-5 h-5 text-red-600" />
          <h3 className="text-lg font-semibold">청산 조건 (언제 매도할까?)</h3>
        </div>
        <StrategyBuilder type="exit" onChange={setExitCondition} />
      </div>

      {/* 리스크 관리 */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <Settings className="w-5 h-5 text-primary-600" />
          <h3 className="text-lg font-semibold">리스크 관리 및 시뮬레이션</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="label">
              손절 비율 (%)
              <span className="text-xs text-gray-500 ml-2">이 만큼 손실시 자동 청산</span>
            </label>
            <div className="flex gap-2 items-center">
              <input
                type="range"
                className="flex-1"
                value={stopPct}
                onChange={(e) => setStopPct(Number(e.target.value))}
                min={1}
                max={30}
                step={0.5}
              />
              <input
                type="number"
                className="input w-20"
                value={stopPct}
                onChange={(e) => setStopPct(Number(e.target.value))}
                min={1}
                max={50}
                step={0.1}
              />
              <span className="text-sm text-gray-600">%</span>
            </div>
          </div>

          <div>
            <label className="label">
              익절 비율 (%)
              <span className="text-xs text-gray-500 ml-2">이 만큼 수익시 자동 청산</span>
            </label>
            <div className="flex gap-2 items-center">
              <input
                type="range"
                className="flex-1"
                value={takePct}
                onChange={(e) => setTakePct(Number(e.target.value))}
                min={1}
                max={50}
                step={0.5}
              />
              <input
                type="number"
                className="input w-20"
                value={takePct}
                onChange={(e) => setTakePct(Number(e.target.value))}
                min={1}
                max={100}
                step={0.1}
              />
              <span className="text-sm text-gray-600">%</span>
            </div>
          </div>

          <div>
            <label className="label">
              몬테카를로 실행 횟수
              <span className="text-xs text-gray-500 ml-2">가상 시나리오 생성 횟수</span>
            </label>
            <select
              className="input"
              value={mcRuns}
              onChange={(e) => setMcRuns(Number(e.target.value))}
            >
              <option value={100}>100회 (빠름, 부정확)</option>
              <option value={500}>500회 (보통)</option>
              <option value={1000}>1,000회 (권장) ⭐</option>
              <option value={2000}>2,000회 (정확)</option>
              <option value={5000}>5,000회 (매우 정확)</option>
              <option value={10000}>10,000회 (최고 정확도)</option>
            </select>
          </div>

          <div>
            <label className="label">
              투자 예정 금액 (원)
              <span className="text-xs text-gray-500 ml-2">시뮬레이션용</span>
            </label>
            <input
              type="number"
              className="input"
              value={investmentAmount}
              onChange={(e) => setInvestmentAmount(Number(e.target.value))}
              min={1000000}
              step={1000000}
            />
            <p className="text-xs text-gray-500 mt-1">
              {(investmentAmount / 10000).toLocaleString()}만원
            </p>
          </div>
        </div>

        {/* 실전 투자 경고 */}
        <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-red-800">
              <p className="font-bold mb-2">⚠️ 실전 투자 전 필수 체크리스트</p>
              <ul className="space-y-1 text-xs">
                <li>✓ 몬테카를로 P5 (최악 시나리오)의 손실을 견딜 수 있는가?</li>
                <li>✓ 백테스트 기간이 최소 6개월 이상인가?</li>
                <li>✓ 몬테카를로 실행 횟수가 1,000회 이상인가?</li>
                <li>✓ 과거 성과는 미래 수익을 보장하지 않습니다</li>
                <li>✓ 손실 가능한 금액만 투자하십시오</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* 제출 버튼 */}
      <button
        type="submit"
        disabled={isLoading || !isDataSufficient}
        className="btn btn-primary w-full py-4 text-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? '전략 분석 중...' : '📊 전략 분석 시작'}
      </button>

      {!isDataSufficient && (
        <p className="text-sm text-red-600 text-center">
          데이터 기간을 {recommendedMonths}개월 이상으로 설정해주세요
        </p>
      )}
    </form>
  );
}
