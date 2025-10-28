import { useState, useEffect } from 'react';
import { TrendingUp, AlertTriangle, HelpCircle } from 'lucide-react';
import type { AnalysisRequest } from '../services/api';
import AdvancedStrategyBuilder from './AdvancedStrategyBuilder';
import UsageGuide from './UsageGuide';
import StockChart from './StockChart';
import StockAutocomplete from './StockAutocomplete';

interface SimpleStrategyFormProps {
  onSubmit: (request: AnalysisRequest) => void;
  isLoading: boolean;
  initialSymbols?: string[];
  loadedTemplate?: any;  // 로드된 템플릿
}

export default function SimpleStrategyForm({ onSubmit, isLoading, initialSymbols = [], loadedTemplate }: SimpleStrategyFormProps) {
  // 기본 설정
  const [symbol, setSymbol] = useState('AAPL');

  // initialSymbols가 변경되면 symbol 업데이트
  useEffect(() => {
    if (initialSymbols.length > 0) {
      setSymbol(initialSymbols[0]);
    }
  }, [initialSymbols]);

  // 템플릿 로드시 폼 채우기
  useEffect(() => {
    if (loadedTemplate) {
      setEntryCondition(loadedTemplate.entry);
      setExitCondition(loadedTemplate.exit);
      setStopLoss(loadedTemplate.risk.stop_pct * 100);
      setTakeProfit(loadedTemplate.risk.take_pct * 100);
    }
  }, [loadedTemplate]);

  const [testPeriod, setTestPeriod] = useState('6months'); // 테스트 기간

  // 전략 조건
  const [entryCondition, setEntryCondition] = useState('');
  const [exitCondition, setExitCondition] = useState('');

  // 리스크 관리
  const [stopLoss, setStopLoss] = useState(7); // 손절
  const [takeProfit, setTakeProfit] = useState(15); // 익절
  const [holdingDays, setHoldingDays] = useState(5); // 보유 기간

  // 자금 관리
  const [initialCapital, setInitialCapital] = useState(1000000); // 초기 자본 (원)
  const [positionSize, setPositionSize] = useState(100); // 1회 매수 비율 (%)

  // 날짜 계산
  const getDateRange = () => {
    const endDate = new Date();
    const startDate = new Date();

    switch (testPeriod) {
      case '3months':
        startDate.setMonth(startDate.getMonth() - 3);
        break;
      case '6months':
        startDate.setMonth(startDate.getMonth() - 6);
        break;
      case '1year':
        startDate.setFullYear(startDate.getFullYear() - 1);
        break;
      case '2years':
        startDate.setFullYear(startDate.getFullYear() - 2);
        break;
      case '3years':
        startDate.setFullYear(startDate.getFullYear() - 3);
        break;
    }

    return {
      start: startDate.toISOString().split('T')[0],
      end: endDate.toISOString().split('T')[0],
    };
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const dateRange = getDateRange();

    const request: AnalysisRequest = {
      symbols: [symbol.trim()],
      date_range: dateRange,
      horizon: {
        lookahead_days: holdingDays,
        rebalance_days: 1,
      },
      strategy: {
        entry: entryCondition,
        exit: exitCondition,
        risk: {
          stop_pct: stopLoss / 100,
          take_pct: takeProfit / 100,
          position_sizing: 'vol_target_10',
        },
      },
      simulate: {
        bootstrap_runs: 1000,
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
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
      {/* 왼쪽: 컴팩트 설정 패널 */}
      <div className="lg:col-span-4 space-y-3">
        {/* 템플릿 로드 안내 */}
        {loadedTemplate && (
          <div className="bg-purple-50 border-2 border-purple-300 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <div className="text-lg">📋</div>
              <div>
                <div className="font-semibold text-purple-900 text-sm">
                  {loadedTemplate.strategyInfo.name} 템플릿 로드됨
                </div>
                <div className="text-xs text-purple-700 mt-1">
                  {loadedTemplate.description}
                </div>
                {loadedTemplate.fundamental_filters && loadedTemplate.fundamental_filters.length > 0 && (
                  <div className="mt-2 text-xs text-purple-600">
                    <div className="font-medium">펀더멘털 필터:</div>
                    <ul className="list-disc list-inside">
                      {loadedTemplate.fundamental_filters.map((filter: string, idx: number) => (
                        <li key={idx}>{filter}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3 lg:sticky lg:top-4">

          {/* 종목 선택 (최상단) */}
          <div className="card bg-gradient-to-br from-blue-50 to-blue-100 border-2 border-blue-300 p-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold text-sm">1</div>
              <h3 className="text-base font-bold text-gray-900">종목 선택</h3>
            </div>

            <div className="space-y-2">
              <div>
                <label className="text-sm font-semibold text-gray-700 block mb-1">티커 심볼</label>
                <StockAutocomplete value={symbol} onChange={setSymbol} />
              </div>

              <div>
                <label className="text-sm font-semibold text-gray-700 block mb-1">테스트 기간</label>
                <select className="input w-full" value={testPeriod} onChange={(e) => setTestPeriod(e.target.value)}>
                  <option value="3months">최근 3개월</option>
                  <option value="6months">최근 6개월 ⭐</option>
                  <option value="1year">최근 1년</option>
                  <option value="2years">최근 2년</option>
                  <option value="3years">최근 3년</option>
                </select>
              </div>
            </div>
          </div>

          {/* 매수 조건 */}
          <div className="card bg-gradient-to-br from-green-50 to-green-100 border-2 border-green-300 p-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 bg-green-600 text-white rounded-full flex items-center justify-center font-bold text-sm">2</div>
              <h3 className="text-base font-bold text-gray-900">매수 조건</h3>
            </div>

            <AdvancedStrategyBuilder type="entry" onChange={setEntryCondition} />

            <div className="mt-2 bg-white rounded p-2 border border-green-200">
              <p className="text-xs text-gray-700">
                <span className="font-semibold">현재:</span> <code className="text-xs">{entryCondition}</code>
              </p>
            </div>
          </div>

          {/* 매도 조건 */}
          <div className="card bg-gradient-to-br from-red-50 to-red-100 border-2 border-red-300 p-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 bg-red-600 text-white rounded-full flex items-center justify-center font-bold text-sm">3</div>
              <h3 className="text-base font-bold text-gray-900">매도 조건</h3>
            </div>

            <AdvancedStrategyBuilder type="exit" onChange={setExitCondition} />

            <div className="mt-2 bg-white rounded p-2 border border-red-200">
              <p className="text-xs text-gray-700">
                <span className="font-semibold">현재:</span> <code className="text-xs">{exitCondition}</code>
              </p>
            </div>
          </div>

          {/* 리스크 관리 */}
          <div className="card bg-gradient-to-br from-purple-50 to-purple-100 border-2 border-purple-300 p-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 bg-purple-600 text-white rounded-full flex items-center justify-center font-bold text-sm">4</div>
              <h3 className="text-base font-bold text-gray-900">리스크 관리</h3>
            </div>

            <div className="space-y-3">
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-sm font-semibold text-gray-700">손절매</label>
                  <span className="text-sm font-bold text-red-600">-{stopLoss}%</span>
                </div>
                <input
                  type="range"
                  className="w-full"
                  value={stopLoss}
                  onChange={(e) => setStopLoss(Number(e.target.value))}
                  min={3}
                  max={20}
                  step={1}
                />
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-sm font-semibold text-gray-700">익절매</label>
                  <span className="text-sm font-bold text-green-600">+{takeProfit}%</span>
                </div>
                <input
                  type="range"
                  className="w-full"
                  value={takeProfit}
                  onChange={(e) => setTakeProfit(Number(e.target.value))}
                  min={5}
                  max={50}
                  step={1}
                />
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-sm font-semibold text-gray-700">최대 보유일</label>
                  <span className="text-sm font-bold text-blue-600">{holdingDays}일</span>
                </div>
                <input
                  type="range"
                  className="w-full"
                  value={holdingDays}
                  onChange={(e) => setHoldingDays(Number(e.target.value))}
                  min={1}
                  max={30}
                  step={1}
                />
              </div>
            </div>
          </div>

          {/* 안내 메시지 */}
          <div className="card bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-300 p-4">
            <div className="text-sm text-blue-900">
              <strong>💡 Tip:</strong> 조건을 설정하면 오른쪽에서 실시간으로 미리보기가 업데이트됩니다.
              <br />
              <strong>🚀 실행:</strong> 오른쪽 상단의 "백테스트 실행" 버튼을 클릭하세요!
            </div>
          </div>

          {/* 사용 가이드 (접을 수 있도록) */}
          <details className="card bg-gray-50 border border-gray-200 p-3">
            <summary className="cursor-pointer text-sm font-semibold text-gray-700 flex items-center gap-2">
              <HelpCircle className="w-4 h-4" />
              사용 가이드 보기
            </summary>
            <div className="mt-3 text-xs text-gray-600 space-y-2">
              <p><strong>1. 종목 선택:</strong> 분석할 주식의 티커 심볼을 입력하세요.</p>
              <p><strong>2. 매수/매도 조건:</strong> RSI, MACD 등 지표로 진입/청산 조건을 설정하세요.</p>
              <p><strong>3. 리스크 관리:</strong> 손절/익절 비율로 위험을 통제하세요.</p>
              <p><strong>4. 분석:</strong> 과거 데이터로 전략을 테스트하고 확률적 예측을 확인하세요.</p>
            </div>
          </details>
        </form>
      </div>

      {/* 오른쪽: 전략 미리보기 + 차트 */}
      <div className="lg:col-span-8 space-y-4">

        {/* 실시간 전략 요약 (Sticky) */}
        <div className="lg:sticky lg:top-4 z-10">
          <div className="card bg-gradient-to-br from-indigo-50 to-purple-50 border-2 border-indigo-300 p-5">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <span className="text-2xl">📋</span>
                전략 미리보기
              </h3>
              <button
                onClick={handleSubmit}
                disabled={isLoading}
                className="btn btn-primary px-6 py-3 text-base font-bold shadow-lg hover:shadow-xl transition-all disabled:opacity-50"
              >
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    실행 중...
                  </span>
                ) : (
                  '🚀 백테스트 실행'
                )}
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3">
              {/* 종목 & 기간 */}
              <div className="bg-white bg-opacity-70 rounded-lg p-3 border border-indigo-200">
                <div className="text-xs text-gray-600 font-medium mb-1">종목</div>
                <div className="text-lg font-bold text-indigo-900">{symbol || '-'}</div>
              </div>
              <div className="bg-white bg-opacity-70 rounded-lg p-3 border border-indigo-200">
                <div className="text-xs text-gray-600 font-medium mb-1">테스트 기간</div>
                <div className="text-sm font-bold text-indigo-900">
                  {testPeriod === '3months' && '최근 3개월'}
                  {testPeriod === '6months' && '최근 6개월'}
                  {testPeriod === '1year' && '최근 1년'}
                  {testPeriod === '2years' && '최근 2년'}
                  {testPeriod === '3years' && '최근 3년'}
                </div>
              </div>

              {/* 매수 조건 */}
              <div className="col-span-2 bg-green-50 bg-opacity-80 rounded-lg p-3 border-2 border-green-300">
                <div className="text-xs text-green-700 font-bold mb-1 flex items-center gap-1">
                  <span>🟢</span> 매수 조건 (Entry)
                </div>
                <div className="text-sm font-mono text-green-900 bg-white rounded px-2 py-1 break-all">
                  {entryCondition || '조건 없음'}
                </div>
              </div>

              {/* 매도 조건 */}
              <div className="col-span-2 bg-red-50 bg-opacity-80 rounded-lg p-3 border-2 border-red-300">
                <div className="text-xs text-red-700 font-bold mb-1 flex items-center gap-1">
                  <span>🔴</span> 매도 조건 (Exit)
                </div>
                <div className="text-sm font-mono text-red-900 bg-white rounded px-2 py-1 break-all">
                  {exitCondition || '조건 없음'}
                </div>
              </div>

              {/* 리스크 관리 */}
              <div className="bg-white bg-opacity-70 rounded-lg p-3 border border-red-300">
                <div className="text-xs text-gray-600 font-medium mb-1">손절매</div>
                <div className="text-lg font-bold text-red-600">-{stopLoss}%</div>
              </div>
              <div className="bg-white bg-opacity-70 rounded-lg p-3 border border-green-300">
                <div className="text-xs text-gray-600 font-medium mb-1">익절매</div>
                <div className="text-lg font-bold text-green-600">+{takeProfit}%</div>
              </div>
              <div className="bg-white bg-opacity-70 rounded-lg p-3 border border-blue-300">
                <div className="text-xs text-gray-600 font-medium mb-1">최대 보유일</div>
                <div className="text-lg font-bold text-blue-600">{holdingDays}일</div>
              </div>
              <div className="bg-white bg-opacity-70 rounded-lg p-3 border border-purple-300">
                <div className="text-xs text-gray-600 font-medium mb-1">상태</div>
                <div className="text-sm font-bold text-purple-600">
                  {entryCondition && exitCondition ? '✅ 준비 완료' : '⚠️ 조건 설정 필요'}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 차트 영역 */}
        <div className="card bg-white border border-gray-200 p-4">
          <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-blue-600" />
            {symbol} 주가 차트
          </h3>

          {symbol && (
            <StockChart
              symbol={symbol}
              startDate={getDateRange().start}
              endDate={getDateRange().end}
            />
          )}
        </div>
      </div>
    </div>
  );
}
