import { useState } from 'react';
import { Plus, Trash2, HelpCircle } from 'lucide-react';

interface Condition {
  id: string;
  indicator: string;
  operator: string;
  value: number;
  type: 'cross' | 'compare';
}

interface StrategyBuilderProps {
  type: 'entry' | 'exit';
  onChange: (condition: string) => void;
}

export default function StrategyBuilder({ type, onChange }: StrategyBuilderProps) {
  const [conditions, setConditions] = useState<Condition[]>([
    {
      id: '1',
      indicator: 'RSI',
      operator: '<',
      value: 30,
      type: 'compare',
    },
  ]);
  const [logic, setLogic] = useState<'AND' | 'OR'>('AND');

  const indicators = [
    { value: 'RSI', label: 'RSI (상대강도지수)', min: 0, max: 100, default: 30 },
    { value: 'MACD', label: 'MACD', min: -100, max: 100, default: 0 },
    { value: '+DI', label: '+DI (상승방향성)', min: 0, max: 100, default: 25 },
    { value: '-DI', label: '-DI (하락방향성)', min: 0, max: 100, default: 25 },
    { value: 'ADX', label: 'ADX (추세강도)', min: 0, max: 100, default: 25 },
  ];

  const crossIndicators = [
    { value: 'MACD.cross_up', label: 'MACD 골든크로스 (상승 전환)' },
    { value: 'MACD.cross_down', label: 'MACD 데드크로스 (하락 전환)' },
  ];

  const operators = [
    { value: '<', label: '미만 (<)' },
    { value: '>', label: '초과 (>)' },
    { value: '<=', label: '이하 (≤)' },
    { value: '>=', label: '이상 (≥)' },
    { value: '==', label: '같음 (=)' },
  ];

  const addCondition = () => {
    const newCondition: Condition = {
      id: Date.now().toString(),
      indicator: 'RSI',
      operator: '<',
      value: 30,
      type: 'compare',
    };
    setConditions([...conditions, newCondition]);
    updateStrategy([...conditions, newCondition], logic);
  };

  const removeCondition = (id: string) => {
    const updated = conditions.filter((c) => c.id !== id);
    setConditions(updated);
    updateStrategy(updated, logic);
  };

  const updateCondition = (id: string, field: keyof Condition, value: any) => {
    const updated = conditions.map((c) => {
      if (c.id === id) {
        return { ...c, [field]: value };
      }
      return c;
    });
    setConditions(updated);
    updateStrategy(updated, logic);
  };

  const updateStrategy = (conds: Condition[], logicOp: 'AND' | 'OR') => {
    if (conds.length === 0) {
      onChange('');
      return;
    }

    const parts = conds.map((c) => {
      if (c.indicator.includes('cross')) {
        return `${c.indicator} == true`;
      }
      return `${c.indicator} ${c.operator} ${c.value}`;
    });

    const result = parts.join(` ${logicOp} `);
    onChange(result);
  };

  const handleLogicChange = (newLogic: 'AND' | 'OR') => {
    setLogic(newLogic);
    updateStrategy(conditions, newLogic);
  };

  const getRecommendedValue = (indicator: string, operator: string, type: 'entry' | 'exit'): number => {
    if (indicator === 'RSI') {
      if (type === 'entry') return operator === '<' ? 30 : 70;
      return operator === '<' ? 30 : 70;
    }
    if (indicator === '+DI' || indicator === '-DI') return 25;
    if (indicator === 'ADX') return 25;
    return 0;
  };

  return (
    <div className="space-y-4">
      {/* 조건 목록 */}
      {conditions.map((condition, index) => (
        <div key={condition.id} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
          <div className="flex items-start gap-3">
            <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-3">
              {/* 지표 선택 */}
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  {index === 0 ? '지표' : ''}
                </label>
                <select
                  className="input text-sm"
                  value={condition.indicator}
                  onChange={(e) => {
                    const isCross = e.target.value.includes('cross');
                    updateCondition(condition.id, 'indicator', e.target.value);
                    updateCondition(condition.id, 'type', isCross ? 'cross' : 'compare');
                  }}
                >
                  <optgroup label="비교 지표">
                    {indicators.map((ind) => (
                      <option key={ind.value} value={ind.value}>
                        {ind.label}
                      </option>
                    ))}
                  </optgroup>
                  <optgroup label="교차 신호">
                    {crossIndicators.map((ind) => (
                      <option key={ind.value} value={ind.value}>
                        {ind.label}
                      </option>
                    ))}
                  </optgroup>
                </select>
              </div>

              {/* 조건 타입에 따른 입력 */}
              {!condition.indicator.includes('cross') ? (
                <>
                  {/* 연산자 */}
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      {index === 0 ? '조건' : ''}
                    </label>
                    <select
                      className="input text-sm"
                      value={condition.operator}
                      onChange={(e) => {
                        updateCondition(condition.id, 'operator', e.target.value);
                        const recommended = getRecommendedValue(condition.indicator, e.target.value, type);
                        updateCondition(condition.id, 'value', recommended);
                      }}
                    >
                      {operators.map((op) => (
                        <option key={op.value} value={op.value}>
                          {op.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* 값 */}
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      {index === 0 ? '기준값' : ''}
                    </label>
                    <input
                      type="number"
                      className="input text-sm"
                      value={condition.value}
                      onChange={(e) => updateCondition(condition.id, 'value', Number(e.target.value))}
                      min={0}
                      max={100}
                      step={0.1}
                    />
                  </div>
                </>
              ) : (
                <div className="md:col-span-2">
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    {index === 0 ? '신호 발생 시' : ''}
                  </label>
                  <div className="input text-sm bg-gray-100 text-gray-600">
                    {condition.indicator === 'MACD.cross_up' ? '매수 신호' : '매도 신호'}
                  </div>
                </div>
              )}
            </div>

            {/* 삭제 버튼 */}
            {conditions.length > 1 && (
              <button
                type="button"
                onClick={() => removeCondition(condition.id)}
                className="p-2 text-red-500 hover:bg-red-50 rounded transition-colors mt-5"
                title="조건 삭제"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>

          {/* 논리 연산자 (마지막 항목 제외) */}
          {index < conditions.length - 1 && (
            <div className="mt-3 flex items-center justify-center gap-2">
              <div className="flex-1 border-t border-gray-300"></div>
              <div className="flex gap-1">
                <button
                  type="button"
                  onClick={() => handleLogicChange('AND')}
                  className={`px-3 py-1 text-xs font-medium rounded ${
                    logic === 'AND'
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
                  }`}
                >
                  그리고 (AND)
                </button>
                <button
                  type="button"
                  onClick={() => handleLogicChange('OR')}
                  className={`px-3 py-1 text-xs font-medium rounded ${
                    logic === 'OR'
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
                  }`}
                >
                  또는 (OR)
                </button>
              </div>
              <div className="flex-1 border-t border-gray-300"></div>
            </div>
          )}
        </div>
      ))}

      {/* 조건 추가 버튼 */}
      <button
        type="button"
        onClick={addCondition}
        className="w-full py-2 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-primary-400 hover:text-primary-600 transition-colors flex items-center justify-center gap-2"
      >
        <Plus className="w-4 h-4" />
        조건 추가
      </button>

      {/* 도움말 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm">
        <div className="flex items-start gap-2">
          <HelpCircle className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
          <div className="text-blue-800">
            <p className="font-medium mb-1">
              {type === 'entry' ? '진입 조건 설정 팁' : '청산 조건 설정 팁'}
            </p>
            <ul className="text-xs space-y-1 text-blue-700">
              {type === 'entry' ? (
                <>
                  <li>• RSI {'<'} 30: 과매도 구간에서 매수 (저가 매수)</li>
                  <li>• MACD 골든크로스: 상승 추세 전환 시점 포착</li>
                  <li>• 여러 조건을 AND로 결합하면 더 보수적 (신호 감소, 정확도 증가)</li>
                  <li>• OR로 결합하면 더 공격적 (신호 증가, 정확도 감소)</li>
                </>
              ) : (
                <>
                  <li>• RSI {'>'} 70: 과매수 구간에서 매도 (고가 매도)</li>
                  <li>• MACD 데드크로스: 하락 추세 전환 시점 포착</li>
                  <li>• 손절/익절과 별도로 기술적 신호로 청산 가능</li>
                  <li>• 너무 빠른 청산보다는 추세 추종 권장</li>
                </>
              )}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
