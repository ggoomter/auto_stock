import { useState, useEffect } from 'react';
import { Plus, Trash2, HelpCircle, Lightbulb } from 'lucide-react';

interface Condition {
  id: string;
  timeframe: 'daily' | 'weekly' | 'monthly';
  indicator: string;
  operator: string;
  value: number;
  type: 'cross' | 'compare';
}

interface AdvancedStrategyBuilderProps {
  type: 'entry' | 'exit';
  onChange: (condition: string) => void;
}

// 투자 대가들의 전략 프리셋
// 주의: 기술적 지표만으로는 실제 투자 철학을 완벽히 재현할 수 없습니다
const PRESETS = {
  entry: {
    warren_buffett: {
      name: '워렌 버핏 스타일 (가치투자 근사)',
      description: '하락 후 반등 시점 포착 (실제 버핏은 펀더멘털 중심)',
      conditions: [
        { timeframe: 'monthly' as const, indicator: 'RSI', operator: '<', value: 35, type: 'compare' as const },
        { timeframe: 'weekly' as const, indicator: 'RSI', operator: '>', value: 40, type: 'compare' as const },
      ],
    },
    william_oneil: {
      name: '윌리엄 오닐 (CAN SLIM)',
      description: '강한 상승 모멘텀 포착',
      conditions: [
        { timeframe: 'daily' as const, indicator: 'RSI', operator: '>', value: 55, type: 'compare' as const },
        { timeframe: 'daily' as const, indicator: '+DI', operator: '>', value: 25, type: 'compare' as const },
        { timeframe: 'weekly' as const, indicator: 'MACD_cross_up', operator: '==', value: 1, type: 'cross' as const },
      ],
    },
    john_murphy: {
      name: '존 머피 (기술적 분석)',
      description: '다중 시간프레임 추세 일치',
      conditions: [
        { timeframe: 'monthly' as const, indicator: 'MACD', operator: '>', value: 0, type: 'compare' as const },
        { timeframe: 'weekly' as const, indicator: 'MACD', operator: '>', value: 0, type: 'compare' as const },
        { timeframe: 'daily' as const, indicator: 'RSI', operator: '>', value: 50, type: 'compare' as const },
      ],
    },
  },
  exit: {
    conservative: {
      name: '보수적 청산',
      description: '과열 시 수익 실현',
      conditions: [
        { timeframe: 'daily' as const, indicator: 'RSI', operator: '>', value: 75, type: 'compare' as const },
      ],
    },
    trend_following: {
      name: '추세 추종',
      description: '추세 전환 감지 시 청산',
      conditions: [
        { timeframe: 'daily' as const, indicator: 'MACD_cross_down', operator: '==', value: 1, type: 'cross' as const },
        { timeframe: 'daily' as const, indicator: '-DI', operator: '>', value: 25, type: 'compare' as const },
      ],
    },
  },
};

export default function AdvancedStrategyBuilder({ type, onChange }: AdvancedStrategyBuilderProps) {
  // 초기 조건을 매수/매도에 따라 다르게 설정
  const getInitialCondition = (): Condition => {
    const defaults = type === 'entry'
      ? { operator: '<', value: 30 }  // 매수: RSI < 30 (과매도)
      : { operator: '>', value: 70 }; // 매도: RSI > 70 (과매수)

    return {
      id: '1',
      timeframe: 'daily',
      indicator: 'RSI',
      operator: defaults.operator,
      value: defaults.value,
      type: 'compare',
    };
  };

  const [conditions, setConditions] = useState<Condition[]>([getInitialCondition()]);
  const [logic, setLogic] = useState<'AND' | 'OR'>('AND');
  const [showTooltip, setShowTooltip] = useState<string | null>(null);

  // 지표별 디폴트 설정 (매수/매도별로 다른 기본값)
  const getIndicatorDefaults = (indicator: string, strategyType: 'entry' | 'exit') => {
    const defaults: Record<string, { entry: { operator: string; value: number }; exit: { operator: string; value: number } }> = {
      'RSI': {
        entry: { operator: '<', value: 30 },    // 매수: 과매도
        exit: { operator: '>', value: 70 }      // 매도: 과매수
      },
      'MACD': {
        entry: { operator: '>', value: 0 },     // 매수: 양수 (상승 추세)
        exit: { operator: '<', value: 0 }       // 매도: 음수 (하락 추세)
      },
      '+DI': {
        entry: { operator: '>', value: 25 },    // 매수: 강한 상승
        exit: { operator: '<', value: 20 }      // 매도: 약한 상승
      },
      '-DI': {
        entry: { operator: '<', value: 20 },    // 매수: 약한 하락
        exit: { operator: '>', value: 25 }      // 매도: 강한 하락
      },
      'ADX': {
        entry: { operator: '>', value: 25 },    // 매수: 추세 강도 충분
        exit: { operator: '<', value: 20 }      // 매도: 추세 약화
      }
    };

    return defaults[indicator]?.[strategyType] || { operator: '>', value: 50 };
  };

  const indicators = [
    { value: 'RSI', label: 'RSI', min: 0, max: 100 },
    { value: 'MACD', label: 'MACD', min: -100, max: 100 },
    { value: '+DI', label: '+DI', min: 0, max: 100 },
    { value: '-DI', label: '-DI', min: 0, max: 100 },
    { value: 'ADX', label: 'ADX', min: 0, max: 100 },
  ];

  const crossIndicators = [
    { value: 'MACD_cross_up', label: 'MACD 골든크로스' },
    { value: 'MACD_cross_down', label: 'MACD 데드크로스' },
  ];

  const operators = [
    { value: '<', label: '미만 (<)' },
    { value: '>', label: '초과 (>)' },
    { value: '<=', label: '이하 (≤)' },
    { value: '>=', label: '이상 (≥)' },
    { value: '==', label: '같음 (=)' },
  ];

  const timeframes = [
    { value: 'daily', label: '일봉', color: 'blue' },
    { value: 'weekly', label: '주봉', color: 'green' },
    { value: 'monthly', label: '월봉', color: 'purple' },
  ];

  useEffect(() => {
    updateStrategy(conditions, logic);
  }, [conditions, logic]);

  const addCondition = () => {
    const defaults = getIndicatorDefaults('RSI', type);
    const newCondition: Condition = {
      id: Date.now().toString(),
      timeframe: 'daily',
      indicator: 'RSI',
      operator: defaults.operator,
      value: defaults.value,
      type: 'compare',
    };
    setConditions([...conditions, newCondition]);
  };

  const removeCondition = (id: string) => {
    const updated = conditions.filter((c) => c.id !== id);
    setConditions(updated);
  };

  const updateCondition = (id: string, updates: Partial<Condition>) => {
    const updated = conditions.map((c) => {
      if (c.id !== id) return c;

      const newCondition = { ...c, ...updates };

      // 지표가 변경되면 해당 지표의 디폴트 값으로 변경
      if (updates.indicator && updates.indicator !== c.indicator) {
        const isCross = updates.indicator.includes('cross');
        if (!isCross) {
          const defaults = getIndicatorDefaults(updates.indicator, type);
          newCondition.operator = defaults.operator;
          newCondition.value = defaults.value;
          newCondition.type = 'compare';
        } else {
          newCondition.type = 'cross';
          newCondition.operator = '==';
          newCondition.value = 1;
        }
      }

      return newCondition;
    });
    setConditions(updated);
  };

  const updateStrategy = (conds: Condition[], logicOp: 'AND' | 'OR') => {
    if (conds.length === 0) {
      onChange('');
      return;
    }

    const parts = conds.map((c) => {
      const prefix = c.timeframe === 'weekly' ? 'W_' : c.timeframe === 'monthly' ? 'M_' : '';

      // MACD 크로스 신호 처리
      if (c.indicator === 'MACD_cross_up') {
        return `${prefix}MACD_cross_up == 1`;
      }
      if (c.indicator === 'MACD_cross_down') {
        return `${prefix}MACD_cross_down == 1`;
      }

      // 일반 지표 비교
      return `${prefix}${c.indicator} ${c.operator} ${c.value}`;
    });

    const result = parts.join(` ${logicOp} `);
    onChange(result);
  };

  const loadPreset = (presetKey: string) => {
    const presets = type === 'entry' ? PRESETS.entry : PRESETS.exit;
    const preset = presets[presetKey as keyof typeof presets];
    if (!preset) return;

    const newConditions: Condition[] = preset.conditions.map((c, idx) => ({
      id: Date.now().toString() + idx,
      timeframe: c.timeframe,
      indicator: c.indicator,
      operator: c.operator,
      value: c.value,
      type: c.type,
    }));

    setConditions(newConditions);
    setLogic('AND');
  };

  const getTimeframeColor = (tf: string) => {
    const colors = {
      daily: 'blue',
      weekly: 'green',
      monthly: 'purple',
    };
    return colors[tf as keyof typeof colors] || 'gray';
  };

  return (
    <div className="space-y-4">
      {/* 프리셋 선택 */}
      <div className="bg-gradient-to-r from-yellow-50 to-orange-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <Lightbulb className="w-5 h-5 text-yellow-600" />
          <h4 className="font-semibold text-gray-900">투자 대가 전략 적용</h4>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          {type === 'entry' ? (
            <>
              <button
                type="button"
                onClick={() => loadPreset('warren_buffett')}
                className="p-3 bg-white border border-yellow-300 rounded-lg hover:bg-yellow-50 transition-colors text-left"
              >
                <p className="font-medium text-sm">워렌 버핏</p>
                <p className="text-xs text-gray-600">가치투자, 저평가 매수</p>
              </button>
              <button
                type="button"
                onClick={() => loadPreset('william_oneil')}
                className="p-3 bg-white border border-yellow-300 rounded-lg hover:bg-yellow-50 transition-colors text-left"
              >
                <p className="font-medium text-sm">윌리엄 오닐</p>
                <p className="text-xs text-gray-600">CAN SLIM, 모멘텀</p>
              </button>
              <button
                type="button"
                onClick={() => loadPreset('john_murphy')}
                className="p-3 bg-white border border-yellow-300 rounded-lg hover:bg-yellow-50 transition-colors text-left"
              >
                <p className="font-medium text-sm">존 머피</p>
                <p className="text-xs text-gray-600">다중 시간프레임 분석</p>
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                onClick={() => loadPreset('conservative')}
                className="p-3 bg-white border border-yellow-300 rounded-lg hover:bg-yellow-50 transition-colors text-left"
              >
                <p className="font-medium text-sm">보수적 청산</p>
                <p className="text-xs text-gray-600">수익 확보 우선</p>
              </button>
              <button
                type="button"
                onClick={() => loadPreset('trend_following')}
                className="p-3 bg-white border border-yellow-300 rounded-lg hover:bg-yellow-50 transition-colors text-left"
              >
                <p className="font-medium text-sm">추세 추종</p>
                <p className="text-xs text-gray-600">추세 전환 시 청산</p>
              </button>
            </>
          )}
        </div>
      </div>

      {/* 조건 목록 */}
      {conditions.map((condition, index) => {
        const tfColor = getTimeframeColor(condition.timeframe);
        return (
          <div key={condition.id} className={`border-2 border-${tfColor}-200 rounded-lg p-4 bg-${tfColor}-50`}>
            <div className="flex items-start gap-3">
              <div className="flex-1 space-y-3">
                {/* 시간프레임 선택 */}
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    시간 프레임
                  </label>
                  <div className="flex gap-2">
                    {timeframes.map((tf) => (
                      <button
                        key={tf.value}
                        type="button"
                        onClick={() => updateCondition(condition.id, { timeframe: tf.value as any })}
                        className={`flex-1 px-3 py-2 text-sm font-medium rounded transition-colors ${
                          condition.timeframe === tf.value
                            ? `bg-${tf.color}-600 text-white`
                            : `bg-white text-gray-600 border border-${tf.color}-200 hover:bg-${tf.color}-100`
                        }`}
                      >
                        {tf.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* 지표 및 조건 */}
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">지표</label>
                    <select
                      className="input text-sm"
                      value={condition.indicator}
                      onChange={(e) => {
                        const isCross = e.target.value.includes('cross');
                        updateCondition(condition.id, {
                          indicator: e.target.value,
                          type: isCross ? 'cross' : 'compare',
                        });
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

                  {condition.type === 'compare' && (
                    <>
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">조건</label>
                        <select
                          className="input text-sm"
                          value={condition.operator}
                          onChange={(e) => updateCondition(condition.id, { operator: e.target.value })}
                        >
                          {operators.map((op) => (
                            <option key={op.value} value={op.value}>
                              {op.label}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">값</label>
                        <input
                          type="number"
                          className="input text-sm"
                          value={condition.value}
                          onChange={(e) => updateCondition(condition.id, { value: Number(e.target.value) })}
                          min={0}
                          max={100}
                          step={1}
                        />
                      </div>
                    </>
                  )}
                  {condition.type === 'cross' && (
                    <div className="col-span-2">
                      <div className="bg-green-100 border border-green-300 rounded px-3 py-2 text-sm text-green-800">
                        ✓ 크로스 신호 발생 시 조건 만족
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {conditions.length > 1 && (
                <button
                  type="button"
                  onClick={() => removeCondition(condition.id)}
                  className="p-2 text-red-500 hover:bg-red-50 rounded transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              )}
            </div>

            {index < conditions.length - 1 && (
              <div className="mt-3 flex items-center justify-center gap-2">
                <div className="flex-1 border-t border-gray-300"></div>
                <div className="flex gap-1">
                  <button
                    type="button"
                    onClick={() => setLogic('AND')}
                    className={`px-3 py-1 text-xs font-medium rounded ${
                      logic === 'AND'
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-200 text-gray-600'
                    }`}
                  >
                    AND
                  </button>
                  <button
                    type="button"
                    onClick={() => setLogic('OR')}
                    className={`px-3 py-1 text-xs font-medium rounded ${
                      logic === 'OR'
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-200 text-gray-600'
                    }`}
                  >
                    OR
                  </button>
                </div>
                <div className="flex-1 border-t border-gray-300"></div>
              </div>
            )}
          </div>
        );
      })}

      <button
        type="button"
        onClick={addCondition}
        className="w-full py-2 border-2 border-dashed border-gray-300 rounded-lg text-gray-600 hover:border-primary-400 hover:text-primary-600 transition-colors flex items-center justify-center gap-2"
      >
        <Plus className="w-4 h-4" />
        조건 추가
      </button>
    </div>
  );
}
