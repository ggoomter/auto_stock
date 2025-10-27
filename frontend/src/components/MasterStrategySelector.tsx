import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { TrendingUp, Calendar, Edit3 } from 'lucide-react';
import StockAutocomplete from './StockAutocomplete';
import { getMasterStrategies, getStrategyTemplate, type MasterStrategyRequest, type MasterStrategyListItem } from '../services/api';

interface MasterStrategySelectorProps {
  onSubmit: (request: MasterStrategyRequest) => void;
  onLoadTemplate?: (template: any) => void;  // 템플릿 로드 콜백
  isLoading: boolean;
  initialSymbols?: string[];
}

export default function MasterStrategySelector({ onSubmit, onLoadTemplate, isLoading, initialSymbols = [] }: MasterStrategySelectorProps) {
  const [selectedStrategy, setSelectedStrategy] = useState<string>('');
  const [symbol, setSymbol] = useState('');
  const [symbolName, setSymbolName] = useState('');
  const [dateRange, setDateRange] = useState({
    start: '2024-01-01',
    end: '2024-12-31',
  });

  // 템플릿 로드 핸들러
  const handleLoadTemplate = async () => {
    if (!selectedStrategy) {
      alert('먼저 전략을 선택해주세요.');
      return;
    }

    try {
      const templateData = await getStrategyTemplate(selectedStrategy);

      if (onLoadTemplate) {
        onLoadTemplate({
          ...templateData.template,
          strategyName: selectedStrategy,
          strategyInfo: templateData.strategy_info
        });
      }
    } catch (error) {
      console.error('템플릿 로드 실패:', error);
      alert('템플릿을 불러오는데 실패했습니다.');
    }
  };

  // initialSymbols가 변경되면 symbol 업데이트
  useEffect(() => {
    if (initialSymbols.length > 0 && !symbol) {
      setSymbol(initialSymbols[0]);
    }
  }, [initialSymbols]);

  const { data: strategiesData, isLoading: strategiesLoading } = useQuery({
    queryKey: ['masterStrategies'],
    queryFn: getMasterStrategies,
  });

  const selectedStrategyInfo = strategiesData?.strategies.find(
    s => s.name === selectedStrategy
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!selectedStrategy || !symbol) {
      alert('전략과 종목을 선택해주세요.');
      return;
    }

    const request: MasterStrategyRequest = {
      strategy_name: selectedStrategy as any,
      symbols: [symbol],
      date_range: dateRange,
      simulate: {
        bootstrap_runs: 1000,
        transaction_cost_bps: 10,
        slippage_bps: 5,
      },
      output_detail: 'full',
    };

    onSubmit(request);
  };

  return (
    <div className="card">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* 전략 선택 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            투자 대가 선택
          </label>
          {strategiesLoading ? (
            <div className="text-center py-4">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {strategiesData?.strategies.map((strategy) => (
                <button
                  key={strategy.name}
                  type="button"
                  onClick={() => setSelectedStrategy(strategy.name)}
                  className={`p-4 border-2 rounded-lg text-left transition-all ${
                    selectedStrategy === strategy.name
                      ? 'border-primary-600 bg-primary-50'
                      : 'border-gray-200 hover:border-gray-300 bg-white'
                  }`}
                >
                  <div className="font-semibold text-gray-900 mb-1">
                    {strategy.info.name.split(' - ')[0]}
                  </div>
                  <div className="text-sm text-gray-600 mb-2">
                    {strategy.description}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <span className="bg-gray-100 px-2 py-1 rounded">
                      {strategy.info.holding_period}
                    </span>
                    <span className="bg-gray-100 px-2 py-1 rounded">
                      {strategy.info.risk_profile}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 선택된 전략 상세 정보 */}
        {selectedStrategyInfo && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="font-semibold text-blue-900 mb-2">
              {selectedStrategyInfo.info.name}
            </h3>
            <div className="text-sm text-blue-800 mb-3">
              {selectedStrategyInfo.description}
            </div>
            <div className="text-sm text-blue-700">
              <div className="font-medium mb-1">핵심 원칙:</div>
              <ul className="list-disc list-inside space-y-1">
                {selectedStrategyInfo.info.key_principles.map((principle, idx) => (
                  <li key={idx}>{principle}</li>
                ))}
              </ul>
            </div>
            <div className="mt-3 pt-3 border-t border-blue-200 flex gap-4 text-sm">
              <div>
                <span className="font-medium text-blue-900">보유 기간:</span>{' '}
                <span className="text-blue-700">{selectedStrategyInfo.info.holding_period}</span>
              </div>
              <div>
                <span className="font-medium text-blue-900">리스크:</span>{' '}
                <span className="text-blue-700">{selectedStrategyInfo.info.risk_profile}</span>
              </div>
            </div>
          </div>
        )}

        {/* 종목 선택 - 강조 박스 */}
        <div className="bg-gradient-to-r from-indigo-50 to-purple-50 border-4 border-indigo-300 rounded-xl p-6 shadow-lg">
          <label className="block text-lg font-bold text-indigo-900 mb-3 flex items-center gap-2">
            <div className="bg-indigo-600 text-white rounded-full p-2">
              <TrendingUp className="w-6 h-6" />
            </div>
            📊 종목 선택 (필수)
          </label>
          <StockAutocomplete
            value={symbol}
            onChange={(sym, name) => {
              setSymbol(sym);
              setSymbolName(name || sym);
            }}
            placeholder="예: AAPL, MSFT, 005930.KS"
          />
          <p className="text-sm text-indigo-700 mt-2 font-medium">
            💡 미국 주식은 티커만 입력 (예: AAPL), 한국 주식은 .KS 추가 (예: 005930.KS)
          </p>
        </div>

        {/* 기간 선택 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            <Calendar className="inline w-4 h-4 mr-1" />
            백테스트 기간
          </label>
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-3">
            <p className="text-sm text-yellow-800">
              ⚠️ <strong>펀더멘털 데이터는 최근 1년만 정확합니다.</strong>
              <br />
              yfinance는 최근 4분기 재무제표만 제공하므로, 그 이전 기간은 기술적 분석만 수행됩니다.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-600 mb-1">시작일</label>
              <input
                type="date"
                value={dateRange.start}
                onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
                max={dateRange.end}
                className="input"
                required
              />
            </div>
            <div>
              <label className="block text-xs text-gray-600 mb-1">종료일</label>
              <input
                type="date"
                value={dateRange.end}
                onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
                min={dateRange.start}
                max={new Date().toISOString().split('T')[0]}
                className="input"
                required
              />
            </div>
          </div>
        </div>

        {/* 제출 버튼 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <button
            type="submit"
            disabled={isLoading || !selectedStrategy || !symbol}
            className="btn btn-primary"
          >
            {isLoading ? '백테스트 실행 중...' : '🚀 백테스트 실행'}
          </button>

          <button
            type="button"
            onClick={handleLoadTemplate}
            disabled={!selectedStrategy || !onLoadTemplate}
            className="btn bg-purple-600 text-white hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <Edit3 className="w-4 h-4" />
            커스터마이징하기
          </button>
        </div>

        {onLoadTemplate && (
          <p className="text-xs text-center text-gray-500">
            💡 "커스터마이징하기"를 클릭하면 대가의 전략을 가져와서 직접 수정할 수 있습니다
          </p>
        )}
      </form>
    </div>
  );
}
