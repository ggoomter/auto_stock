import { BookOpen, TrendingUp, BarChart3, Dice3 } from 'lucide-react';
import { useState } from 'react';

export default function LearnMenu() {
  const [activeTab, setActiveTab] = useState<'indicators' | 'montecarlo'>('indicators');

  const indicators = [
    {
      name: 'MACD (Moving Average Convergence Divergence)',
      icon: <TrendingUp className="w-6 h-6" />,
      description: '이동평균 수렴확산 지표',
      details: {
        what: '단기 이동평균과 장기 이동평균의 차이를 이용한 추세 추종 지표입니다.',
        how: '12일 EMA - 26일 EMA = MACD 선, 그리고 MACD의 9일 EMA = 시그널 선',
        signal: 'MACD 선이 시그널 선을 상향 돌파하면 매수 신호 (cross_up), 하향 돌파하면 매도 신호 (cross_down)',
        range: '값 범위: 제한 없음 (주가에 따라 다름)',
        usage: '중장기 추세 전환 포착에 유용. 골든크로스/데드크로스 확인',
        strategies: [
          {
            name: '골든크로스 전략',
            entry: 'MACD선 > 시그널선 교차 (골든크로스)',
            exit: 'MACD선 < 시그널선 교차 (데드크로스)',
            logic: '골든크로스 = 상승 추세 전환. 데드크로스 = 하락 전환. 승률: 60~65%',
            risk: '후행 지표 → 추세 전환 확인 시 이미 상당히 진행됨',
          },
          {
            name: 'MACD 히스토그램 전략',
            entry: 'MACD 히스토그램 음→양 전환',
            exit: 'MACD 히스토그램 양→음 전환',
            logic: '히스토그램 = MACD와 시그널 차이. 더 빠른 신호. 승률: 55~60%',
            risk: '골든크로스보다 빠르지만 거짓 신호 증가',
          },
          {
            name: 'MACD 다이버전스',
            entry: '주가 신저가 + MACD 고저가',
            exit: 'MACD 데드크로스',
            logic: '주가와 MACD 괴리 = 반전 신호. 강력한 매수 타이밍. 승률: 75~80%',
            risk: '다이버전스 확인 시간 필요 → 즉각 진입 어려움',
          },
        ],
      },
    },
    {
      name: 'RSI (Relative Strength Index)',
      icon: <BarChart3 className="w-6 h-6" />,
      description: '상대 강도 지수',
      details: {
        what: '일정 기간 동안의 가격 상승폭과 하락폭의 비율로 과매수/과매도를 판단하는 모멘텀 지표입니다.',
        how: '14일간의 상승분 평균 / (상승분 평균 + 하락분 평균) × 100',
        signal: 'RSI < 30: 과매도 구간 (매수 고려), RSI > 70: 과매수 구간 (매도 고려)',
        range: '0 ~ 100 사이의 값',
        usage: '단기 과열/침체 판단. 다른 지표와 함께 사용 권장',
        strategies: [
          {
            name: '전통적 역추세 전략',
            entry: 'RSI < 30 (과매도)',
            exit: 'RSI > 70 (과매수)',
            logic: '지나치게 팔린 구간에서 매수, 과열 구간에서 매도. 승률: 60~65%',
            risk: '강한 하락 추세에서는 30 이하로 계속 하락 가능 → 손절 필수 (-7%)',
          },
          {
            name: '모멘텀 추종 전략',
            entry: 'RSI > 50 돌파 (상승 모멘텀)',
            exit: 'RSI < 50 하락 (모멘텀 약화)',
            logic: '강한 종목은 RSI 50 이상 유지. 상승 추세 추종. 승률: 55~60%',
            risk: '횡보 구간에서 잦은 매매 발생 → 거래비용 주의',
          },
          {
            name: '다이버전스 전략 (고급)',
            entry: '주가 신저가 + RSI 고저가 (강세 다이버전스)',
            exit: 'RSI > 70 또는 다이버전스 소멸',
            logic: '주가는 하락하지만 RSI는 상승 → 반등 신호. 승률: 70~75%',
            risk: '다이버전스 확인에 시간 필요 → 진입 타이밍 늦을 수 있음',
          },
        ],
      },
    },
    {
      name: 'DMI (Directional Movement Index)',
      icon: <TrendingUp className="w-6 h-6" />,
      description: '방향성 지표',
      details: {
        what: '상승 추세력(+DI)과 하락 추세력(-DI)을 측정하여 추세의 방향과 강도를 파악하는 지표입니다.',
        how: '+DI (상승 방향성)와 -DI (하락 방향성), ADX (추세 강도)로 구성',
        signal: '+DI > -DI: 상승 추세, +DI < -DI: 하락 추세. ADX > 25면 강한 추세',
        range: '0 ~ 100 사이의 값',
        usage: '추세의 방향과 강도를 동시에 파악. 횡보장/추세장 구분',
        strategies: [
          {
            name: '추세 추종 전략',
            entry: '+DI > -DI AND ADX > 25 (강한 상승 추세)',
            exit: '+DI < -DI OR ADX < 20 (추세 약화)',
            logic: 'ADX 25 이상 = 강한 추세. DI 교차로 방향 확인. 승률: 65~70%',
            risk: 'ADX는 후행 지표 → 추세 후반 진입 가능성',
          },
          {
            name: '횡보 구간 회피 전략',
            entry: 'ADX > 25 AND +DI > -DI (추세장 확인)',
            exit: 'ADX < 20 (횡보 전환)',
            logic: 'ADX < 20은 횡보 → 거래 중단. 추세장만 거래. 승률: 70~75%',
            risk: '거래 기회 감소 → 수익률은 높지만 거래 빈도 낮음',
          },
        ],
      },
    },
    {
      name: 'Bollinger Bands',
      icon: <BarChart3 className="w-6 h-6" />,
      description: '볼린저 밴드',
      details: {
        what: '이동평균선을 중심으로 표준편차를 이용해 상단/하단 밴드를 그려 변동성을 시각화하는 지표입니다.',
        how: '중심선 (20일 이동평균) ± (2 × 20일 표준편차) = 상단/하단 밴드',
        signal: '가격이 하단 밴드 접근시 저평가 가능성, 상단 밴드 접근시 고평가 가능성. 밴드 폭 확대는 변동성 증가',
        range: '주가 움직임에 따라 동적으로 변화',
        usage: '변동성 측정, 과매수/과매도 판단. 밴드 돌파시 강한 추세 전환 가능',
        strategies: [
          {
            name: '밴드 반등 전략 (횡보장)',
            entry: '주가 하단 밴드 접촉 (저평가)',
            exit: '주가 상단 밴드 접촉 (고평가)',
            logic: '횡보 구간에서 하단=매수, 상단=매도. 승률: 70~75%',
            risk: '강한 추세에서는 밴드 돌파 후 계속 이탈 → 큰 손실. 횡보장만 유효',
          },
          {
            name: '밴드 돌파 전략 (추세장)',
            entry: '주가 상단 밴드 돌파 + 거래량 급증',
            exit: '주가 중심선(20일 MA) 하락',
            logic: '상단 돌파 = 강한 상승 추세 시작. 달리는 열차에 탑승. 승률: 60~65%',
            risk: '거짓 돌파 가능 → 거래량 확인 필수. 추세 후반 진입 시 조정',
          },
          {
            name: '스퀴즈 전략 (변동성 확대)',
            entry: '밴드 폭 최소 → 밴드 폭 확대 + 방향 확인',
            exit: '밴드 폭 다시 축소',
            logic: '밴드 수축 = 변동성 감소 → 곧 큰 움직임. 방향 확인 후 진입. 승률: 65~70%',
            risk: '방향 예측 어려움 → 돌파 방향 확인 후 진입 (늦을 수 있음)',
          },
        ],
      },
    },
    {
      name: 'OBV (On-Balance Volume)',
      icon: <BarChart3 className="w-6 h-6" />,
      description: '거래량 균형 지표',
      details: {
        what: '가격과 거래량을 함께 고려하여 자금의 흐름을 파악하는 누적 거래량 지표입니다.',
        how: '가격 상승일: OBV += 거래량, 가격 하락일: OBV -= 거래량',
        signal: 'OBV 상승 + 가격 상승: 강한 상승 추세, OBV 하락 + 가격 상승: 상승세 약화 경고',
        range: '누적 값이므로 절대값보다 추세가 중요',
        usage: '가격과 OBV의 다이버전스(괴리) 확인으로 추세 전환 포착',
      },
    },
    {
      name: 'Stochastic',
      icon: <TrendingUp className="w-6 h-6" />,
      description: '스토캐스틱',
      details: {
        what: '일정 기간의 최고가와 최저가 범위 내에서 현재 가격의 위치를 백분율로 나타낸 모멘텀 지표입니다.',
        how: '%K = (현재가 - N일 최저가) / (N일 최고가 - N일 최저가) × 100, %D = %K의 3일 이동평균',
        signal: '%K < 20: 과매도, %K > 80: 과매수. %K가 %D를 상향 돌파시 매수 신호',
        range: '0 ~ 100 사이의 값',
        usage: '단기 과매수/과매도 판단. RSI보다 민감하게 반응',
      },
    },
  ];

  return (
    <div className="space-y-6">
      {/* 탭 메뉴 */}
      <div className="flex gap-2 border-b border-gray-200">
        <button
          onClick={() => setActiveTab('indicators')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'indicators'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4" />
            기술지표 설명
          </div>
        </button>
        <button
          onClick={() => setActiveTab('montecarlo')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'montecarlo'
              ? 'text-primary-600 border-b-2 border-primary-600'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <div className="flex items-center gap-2">
            <Dice3 className="w-4 h-4" />
            몬테카를로 시뮬레이션
          </div>
        </button>
      </div>

      {/* 기술지표 설명 */}
      {activeTab === 'indicators' && (
        <div className="space-y-4">
          {indicators.map((indicator) => (
            <div key={indicator.name} className="card">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-primary-50 rounded-lg text-primary-600">
                  {indicator.icon}
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-bold text-gray-900">{indicator.name}</h3>
                  <p className="text-sm text-gray-600 mb-3">{indicator.description}</p>

                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="font-semibold text-gray-700">📌 무엇인가?</span>
                      <p className="text-gray-600 mt-1">{indicator.details.what}</p>
                    </div>
                    <div>
                      <span className="font-semibold text-gray-700">🔢 어떻게 계산?</span>
                      <p className="text-gray-600 mt-1 font-mono text-xs bg-gray-50 p-2 rounded">
                        {indicator.details.how}
                      </p>
                    </div>
                    <div>
                      <span className="font-semibold text-gray-700">📊 신호 해석</span>
                      <p className="text-gray-600 mt-1">{indicator.details.signal}</p>
                    </div>
                    <div>
                      <span className="font-semibold text-gray-700">📈 값의 범위</span>
                      <p className="text-gray-600 mt-1">{indicator.details.range}</p>
                    </div>
                    <div>
                      <span className="font-semibold text-gray-700">💡 실전 활용</span>
                      <p className="text-gray-600 mt-1">{indicator.details.usage}</p>
                    </div>

                    {/* 실전 전략 */}
                    {indicator.details.strategies && indicator.details.strategies.length > 0 && (
                      <div>
                        <span className="font-semibold text-gray-700">🎯 구체적인 실전 전략</span>
                        <div className="mt-2 space-y-3">
                          {indicator.details.strategies.map((strategy: any, idx: number) => (
                            <div key={idx} className="bg-white border border-gray-200 rounded-lg p-3">
                              <h5 className="font-semibold text-sm text-primary-700 mb-2">
                                {idx + 1}. {strategy.name}
                              </h5>
                              <div className="text-xs space-y-1">
                                <p>
                                  <span className="font-medium text-green-700">📥 진입:</span>{' '}
                                  <code className="bg-green-50 px-1 py-0.5 rounded">{strategy.entry}</code>
                                </p>
                                <p>
                                  <span className="font-medium text-red-700">📤 청산:</span>{' '}
                                  <code className="bg-red-50 px-1 py-0.5 rounded">{strategy.exit}</code>
                                </p>
                                <p>
                                  <span className="font-medium text-blue-700">💭 논리:</span>{' '}
                                  <span className="text-gray-700">{strategy.logic}</span>
                                </p>
                                <p>
                                  <span className="font-medium text-yellow-700">⚠️ 리스크:</span>{' '}
                                  <span className="text-gray-700">{strategy.risk}</span>
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 몬테카를로 시뮬레이션 설명 */}
      {activeTab === 'montecarlo' && (
        <div className="space-y-4">
          <div className="card">
            <h3 className="text-xl font-bold text-gray-900 mb-4">몬테카를로 시뮬레이션이란?</h3>

            <div className="space-y-4 text-sm">
              <div>
                <h4 className="font-semibold text-gray-700 mb-2">📌 개념</h4>
                <p className="text-gray-600">
                  과거 데이터를 무작위로 재샘플링하여 수천 번의 가상 시나리오를 만들어내는 통계적 기법입니다.
                  하나의 백테스트 결과가 아닌 "가능한 미래의 범위"를 시뮬레이션합니다.
                </p>
              </div>

              <div>
                <h4 className="font-semibold text-gray-700 mb-2">🔢 작동 원리</h4>
                <ol className="list-decimal list-inside space-y-2 text-gray-600">
                  <li>과거 수익률 데이터를 블록 단위로 무작위 샘플링</li>
                  <li>샘플링한 데이터로 새로운 가상 시나리오 생성</li>
                  <li>각 시나리오에서 전략 성과 계산 (CAGR, MaxDD 등)</li>
                  <li>1~3번을 1,000회 반복</li>
                  <li>1,000개의 결과 분포에서 P5 (하위 5%), P50 (중간값), P95 (상위 5%) 추출</li>
                </ol>
              </div>

              <div>
                <h4 className="font-semibold text-gray-700 mb-2">📊 결과 해석</h4>
                <div className="bg-gray-50 p-4 rounded space-y-2">
                  <p className="text-gray-600">
                    <span className="font-semibold">P5 (하위 5%):</span> 최악의 시나리오.
                    100번 중 5번은 이 정도로 나쁠 수 있음
                  </p>
                  <p className="text-gray-600">
                    <span className="font-semibold">P50 (중간값):</span> 평균적인 시나리오.
                    가장 가능성 높은 결과
                  </p>
                  <p className="text-gray-600">
                    <span className="font-semibold">P95 (상위 5%):</span> 최고의 시나리오.
                    100번 중 5번은 이 정도로 좋을 수 있음
                  </p>
                </div>
              </div>

              <div>
                <h4 className="font-semibold text-gray-700 mb-2">⚠️ 실행 횟수의 의미</h4>
                <ul className="space-y-2 text-gray-600">
                  <li>
                    <span className="font-semibold">100회:</span> 빠르지만 부정확. 테스트용
                  </li>
                  <li>
                    <span className="font-semibold">1,000회 (권장):</span> 신뢰할 만한 결과.
                    대부분의 경우 충분
                  </li>
                  <li>
                    <span className="font-semibold">5,000회:</span> 매우 정확. 실전 투자 전 최종 검증
                  </li>
                  <li>
                    <span className="font-semibold">10,000회:</span> 최고 정확도.
                    대규모 자금 투자시
                  </li>
                </ul>
              </div>

              <div>
                <h4 className="font-semibold text-gray-700 mb-2">💡 왜 중요한가?</h4>
                <p className="text-gray-600">
                  단 한 번의 백테스트는 "과거에 운이 좋았던 한 가지 경우"일 수 있습니다.
                  몬테카를로는 "다양한 시장 상황"을 시뮬레이션하여 전략의 강건성(robustness)을 확인합니다.
                  실제 투자 전 최악의 경우(P5)를 견딜 수 있는지 반드시 확인해야 합니다.
                </p>
              </div>

              <div className="bg-yellow-50 border border-yellow-200 rounded p-4">
                <h4 className="font-semibold text-yellow-800 mb-2">⚠️ 투자 전 체크리스트</h4>
                <ul className="space-y-1 text-yellow-700 text-sm">
                  <li>✓ P5 (최악 시나리오)의 MaxDD를 견딜 수 있는가?</li>
                  <li>✓ P50 (평균)의 CAGR이 목표 수익률을 만족하는가?</li>
                  <li>✓ 몬테카를로 실행 횟수가 1,000회 이상인가?</li>
                  <li>✓ 백테스트 기간이 최소 3년 이상인가?</li>
                  <li>✓ 과최적화(overfitting) 가능성은 없는가?</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
