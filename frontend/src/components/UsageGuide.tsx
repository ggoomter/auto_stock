import { TrendingUp, Search, BarChart3, CheckCircle } from 'lucide-react';

export default function UsageGuide() {
  return (
    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-6 mb-6">
      <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
        <CheckCircle className="w-5 h-5 text-blue-600" />
        사용 방법 (3단계)
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* 1단계 */}
        <div className="bg-white rounded-lg p-4 border border-blue-100">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">
              1
            </div>
            <Search className="w-5 h-5 text-blue-600" />
            <h4 className="font-semibold text-gray-900">종목 선택</h4>
          </div>
          <p className="text-sm text-gray-600 ml-10">
            분석하고 싶은 주식 종목을 선택하세요. 예: AAPL (애플), TSLA (테슬라)
          </p>
        </div>

        {/* 2단계 */}
        <div className="bg-white rounded-lg p-4 border border-blue-100">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">
              2
            </div>
            <TrendingUp className="w-5 h-5 text-blue-600" />
            <h4 className="font-semibold text-gray-900">조건 설정</h4>
          </div>
          <p className="text-sm text-gray-600 ml-10">
            언제 사고, 언제 팔지 조건을 설정하세요. 여러 조건을 조합할 수 있습니다.
          </p>
        </div>

        {/* 3단계 */}
        <div className="bg-white rounded-lg p-4 border border-blue-100">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-bold">
              3
            </div>
            <BarChart3 className="w-5 h-5 text-blue-600" />
            <h4 className="font-semibold text-gray-900">결과 확인</h4>
          </div>
          <p className="text-sm text-gray-600 ml-10">
            설정한 조건으로 과거 데이터를 시뮬레이션하여 수익률, 승률 등을 확인하세요.
          </p>
        </div>
      </div>

      <div className="mt-4 bg-white rounded-lg p-3 border border-yellow-200 bg-yellow-50">
        <p className="text-sm text-gray-700">
          <span className="font-semibold">💡 핵심:</span> 이 프로그램은 여러분이 설정한 "매수/매도 조건"으로
          과거 데이터를 시뮬레이션하여, 만약 그때 그 전략을 사용했다면 얼마나 벌었을지(또는 잃었을지)를 보여줍니다.
          이를 통해 실제 투자 전에 전략의 유효성을 검증할 수 있습니다.
        </p>
      </div>
    </div>
  );
}
