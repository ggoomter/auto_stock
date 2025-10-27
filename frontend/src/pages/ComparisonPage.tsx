import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Users, Calendar } from 'lucide-react';
import StrategyComparison from '../components/StrategyComparison';
import StockAutocomplete from '../components/StockAutocomplete';
import {
  compareStrategies,
  type StrategyComparisonRequest,
  type StrategyComparisonResponse
} from '../services/api';

const AVAILABLE_STRATEGIES = [
  { id: 'buffett', name: '워렌 버핏', description: '가치투자의 대가' },
  { id: 'lynch', name: '피터 린치', description: '성장주 투자' },
  { id: 'graham', name: '벤자민 그레이엄', description: '심층 가치투자' },
  { id: 'dalio', name: '레이 달리오', description: 'All Weather 포트폴리오' },
  { id: 'livermore', name: '제시 리버모어', description: '추세 추종' },
  { id: 'soros', name: '조지 소로스', description: '매크로 투자' },
  { id: 'druckenmiller', name: '스탠리 드러켄밀러', description: '성장 + 매크로' },
  { id: 'oneil', name: '윌리엄 오닐', description: 'CAN SLIM' }
];

export default function ComparisonPage() {
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>(['buffett', 'lynch', 'graham']);
  const [symbols, setSymbols] = useState<string[]>(['AAPL']);
  const [startDate, setStartDate] = useState('2020-01-01');
  const [endDate, setEndDate] = useState('2024-12-31');
  const [initialCapital, setInitialCapital] = useState(1000000);
  const [results, setResults] = useState<StrategyComparisonResponse | null>(null);

  const mutation = useMutation({
    mutationFn: compareStrategies,
    onSuccess: (data) => {
      setResults(data);
    },
    onError: (error: any) => {
      console.error('비교 오류:', error);
      alert(`비교 중 오류가 발생했습니다.\n\n${error?.response?.data?.detail || error.message}`);
    }
  });

  const handleStrategyToggle = (strategyId: string) => {
    if (selectedStrategies.includes(strategyId)) {
      setSelectedStrategies(selectedStrategies.filter(id => id !== strategyId));
    } else {
      setSelectedStrategies([...selectedStrategies, strategyId]);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedStrategies.length < 2) {
      alert('최소 2개 이상의 전략을 선택해주세요.');
      return;
    }
    if (symbols.length === 0) {
      alert('최소 1개 이상의 종목을 선택해주세요.');
      return;
    }

    const request: StrategyComparisonRequest = {
      strategy_names: selectedStrategies,
      symbols,
      start_date: startDate,
      end_date: endDate,
      initial_capital: initialCapital
    };

    mutation.mutate(request);
  };

  return (
    <div className="space-y-8">
      {/* 헤더 */}
      <div className="card bg-gradient-to-r from-indigo-50 to-blue-50 border-indigo-200">
        <h1 className="text-3xl font-bold text-indigo-900 mb-2 flex items-center gap-3">
          <Users className="w-8 h-8" />
          투자 대가 전략 비교
        </h1>
        <p className="text-indigo-700 text-lg">
          여러 투자 대가의 전략을 동시에 백테스트하여 성과를 비교하고, 최적의 전략을 찾아보세요.
        </p>
      </div>

      {/* 설정 폼 */}
      <div className="card">
        <h2 className="text-xl font-bold text-gray-900 mb-4">비교 설정</h2>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* 전략 선택 */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-3">
              비교할 전략 선택 (최소 2개)
            </label>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
              {AVAILABLE_STRATEGIES.map(strategy => (
                <button
                  key={strategy.id}
                  type="button"
                  onClick={() => handleStrategyToggle(strategy.id)}
                  className={`p-4 border-2 rounded-lg text-left transition-all ${
                    selectedStrategies.includes(strategy.id)
                      ? 'bg-blue-50 border-blue-500 shadow-md'
                      : 'bg-white border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="font-bold text-gray-900">{strategy.name}</div>
                  <div className="text-xs text-gray-600 mt-1">{strategy.description}</div>
                  {selectedStrategies.includes(strategy.id) && (
                    <div className="mt-2 text-blue-600 font-semibold text-sm">✓ 선택됨</div>
                  )}
                </button>
              ))}
            </div>
            <div className="mt-2 text-sm text-gray-600">
              선택된 전략: {selectedStrategies.length}개
            </div>
          </div>

          {/* 종목 선택 */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              분석할 종목
            </label>
            <div className="flex gap-2 flex-wrap mb-2">
              {symbols.map(sym => (
                <div key={sym} className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm flex items-center gap-2">
                  {sym}
                  <button onClick={() => setSymbols(symbols.filter(s => s !== sym))} className="text-blue-600 hover:text-blue-800">✕</button>
                </div>
              ))}
            </div>
            <StockAutocomplete
              value=""
              onChange={(symbol) => {
                if (symbol && !symbols.includes(symbol)) {
                  setSymbols([...symbols, symbol]);
                }
              }}
            />
          </div>

          {/* 기간 선택 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                <Calendar className="inline w-4 h-4 mr-1" />
                시작일
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                <Calendar className="inline w-4 h-4 mr-1" />
                종료일
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                required
              />
            </div>
          </div>

          {/* 초기 자본 */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              초기 자본 (원)
            </label>
            <input
              type="number"
              value={initialCapital}
              onChange={(e) => setInitialCapital(Number(e.target.value))}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              min="100000"
              step="100000"
              required
            />
            <div className="mt-1 text-sm text-gray-600">
              {(initialCapital / 10000).toLocaleString()}만원
            </div>
          </div>

          {/* 실행 버튼 */}
          <button
            type="submit"
            disabled={mutation.isPending || selectedStrategies.length < 2}
            className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-4 rounded-lg font-bold text-lg hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-lg"
          >
            {mutation.isPending ? '비교 중...' : `${selectedStrategies.length}개 전략 비교 시작`}
          </button>
        </form>
      </div>

      {/* 로딩 */}
      {mutation.isPending && (
        <div className="card text-center py-12">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
          <p className="text-gray-600 font-semibold">전략 비교 중...</p>
          <p className="text-sm text-gray-500 mt-2">
            {selectedStrategies.length}개 전략을 {symbols.length}개 종목으로 백테스트하고 있습니다.
          </p>
        </div>
      )}

      {/* 결과 */}
      {results && !mutation.isPending && (
        <StrategyComparison
          results={results.results}
          best_strategy={results.best_strategy}
          initial_capital={initialCapital}
        />
      )}
    </div>
  );
}
