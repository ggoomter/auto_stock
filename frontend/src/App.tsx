import { useState } from 'react';
import { QueryClient, QueryClientProvider, useMutation } from '@tanstack/react-query';
import { Activity, Github, BookOpen, Users, Settings, BarChart3, Radio } from 'lucide-react';
import SimpleStrategyForm from './components/SimpleStrategyForm';
import MasterStrategySelector from './components/MasterStrategySelector';
import ResultsDisplay from './components/ResultsDisplay';
import MasterStrategyResults from './components/MasterStrategyResults';
import LearnMenu from './components/LearnMenu';
import NewsFetchButton from './components/NewsFetchButton';
import ComparisonPage from './pages/ComparisonPage';
import RealtimeMonitor from './pages/RealtimeMonitor';
import {
  analyzeStrategy,
  analyzeMasterStrategy,
  type AnalysisRequest,
  type AnalysisResponse,
  type MasterStrategyRequest,
  type MasterStrategyResponse
} from './services/api';

const queryClient = new QueryClient();

type StrategyType = 'custom' | 'master';
type ActiveTab = 'strategy' | 'compare' | 'realtime' | 'learn';

function AppContent() {
  const [strategyType, setStrategyType] = useState<StrategyType>('master');
  const [results, setResults] = useState<AnalysisResponse | null>(null);
  const [masterResults, setMasterResults] = useState<MasterStrategyResponse | null>(null);
  const [activeTab, setActiveTab] = useState<ActiveTab>('strategy');
  const [pendingRequest, setPendingRequest] = useState<AnalysisRequest | null>(null);
  const [pendingMasterRequest, setPendingMasterRequest] = useState<MasterStrategyRequest | null>(null);
  const [sharedSymbols, setSharedSymbols] = useState<string[]>([]);
  const [loadedTemplate, setLoadedTemplate] = useState<any>(null);  // 로드된 템플릿 저장

  const mutation = useMutation({
    mutationFn: analyzeStrategy,
    onSuccess: (data) => {
      setResults(data);
      setMasterResults(null);
    },
    onError: (error: any) => {
      console.error('분석 오류:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || '알 수 없는 오류';
      console.error('상세 에러:', errorMessage);
      alert(`분석 중 오류가 발생했습니다.\n\n에러: ${errorMessage}\n\n백엔드 서버(http://localhost:8000)가 실행 중인지 확인해주세요.`);
    },
  });

  const masterMutation = useMutation({
    mutationFn: analyzeMasterStrategy,
    onSuccess: (data) => {
      setMasterResults(data);
      setResults(null);
    },
    onError: (error: any) => {
      console.error('분석 오류:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || '알 수 없는 오류';
      console.error('상세 에러:', errorMessage);
      alert(`분석 중 오류가 발생했습니다.\n\n에러: ${errorMessage}\n\n백엔드 서버(http://localhost:8000)가 실행 중인지 확인해주세요.`);
    },
  });

  const handleSubmit = (request: AnalysisRequest) => {
    setResults(null);
    setMasterResults(null);
    setSharedSymbols(request.symbols);
    setPendingRequest(null);
    setPendingMasterRequest(null);
    // 즉시 분석 실행
    mutation.mutate(request);
  };

  const handleMasterSubmit = (request: MasterStrategyRequest) => {
    setResults(null);
    setMasterResults(null);
    setSharedSymbols(request.symbols);
    setPendingRequest(null);
    setPendingMasterRequest(null);
    // 즉시 분석 실행
    masterMutation.mutate(request);
  };

  // 템플릿 로드 핸들러 - 커스텀 전략 탭으로 전환하고 조건 채우기
  const handleLoadTemplate = (template: any) => {
    setStrategyType('custom');
    setLoadedTemplate(template);
    setResults(null);
    setMasterResults(null);
    alert(`${template.strategyInfo.name} 전략이 로드되었습니다!\n\n커스텀 전략 탭에서 조건을 수정할 수 있습니다.`);
  };

  const isLoading = mutation.isPending || masterMutation.isPending;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-primary-600 p-2 rounded-lg">
                <Activity className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">금융 리서치 코파일럿</h1>
                <p className="text-sm text-gray-600">설명 가능한 확률 예측과 전략 시뮬레이션</p>
              </div>
            </div>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-600 hover:text-gray-900 transition-colors"
            >
              <Github className="w-6 h-6" />
            </a>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        {/* 탭 네비게이션 */}
        <div className="flex gap-4 mb-8 border-b border-gray-200">
          <button
            onClick={() => setActiveTab('strategy')}
            className={`px-6 py-3 font-semibold transition-colors ${
              activeTab === 'strategy'
                ? 'text-primary-600 border-b-2 border-primary-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5" />
              전략 분석
            </div>
          </button>
          <button
            onClick={() => setActiveTab('compare')}
            className={`px-6 py-3 font-semibold transition-colors ${
              activeTab === 'compare'
                ? 'text-primary-600 border-b-2 border-primary-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <div className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              전략 비교
            </div>
          </button>
          <button
            onClick={() => setActiveTab('realtime')}
            className={`px-6 py-3 font-semibold transition-colors ${
              activeTab === 'realtime'
                ? 'text-primary-600 border-b-2 border-primary-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <div className="flex items-center gap-2">
              <Radio className="w-5 h-5" />
              실시간 모니터링
            </div>
          </button>
          <button
            onClick={() => setActiveTab('learn')}
            className={`px-6 py-3 font-semibold transition-colors ${
              activeTab === 'learn'
                ? 'text-primary-600 border-b-2 border-primary-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <div className="flex items-center gap-2">
              <BookOpen className="w-5 h-5" />
              학습 자료
            </div>
          </button>
        </div>

        {/* 전략 분석 탭 */}
        {activeTab === 'strategy' && (
          <div className="space-y-8">
            {/* 뉴스 가져오기 버튼 */}
            <NewsFetchButton />

            {/* 전략 타입 선택 */}
            <div className="flex gap-4 justify-center">
              <button
                onClick={() => {
                  setStrategyType('master');
                  setResults(null);
                  setMasterResults(null);
                }}
                className={`px-6 py-3 rounded-lg font-semibold transition-all ${
                  strategyType === 'master'
                    ? 'bg-primary-600 text-white shadow-lg'
                    : 'bg-white text-gray-700 border-2 border-gray-300 hover:border-primary-400'
                }`}
              >
                <Users className="inline w-5 h-5 mr-2" />
                투자 대가 전략
              </button>
              <button
                onClick={() => {
                  setStrategyType('custom');
                  setResults(null);
                  setMasterResults(null);
                }}
                className={`px-6 py-3 rounded-lg font-semibold transition-all ${
                  strategyType === 'custom'
                    ? 'bg-primary-600 text-white shadow-lg'
                    : 'bg-white text-gray-700 border-2 border-gray-300 hover:border-primary-400'
                }`}
              >
                <Settings className="inline w-5 h-5 mr-2" />
                커스텀 전략
              </button>
            </div>

            {/* Form */}
            <div>
              <div className="mb-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-2">전략 설정</h2>
                <p className="text-sm text-gray-600">
                  {strategyType === 'master'
                    ? '투자 대가를 선택하고 해당 전략으로 백테스트를 수행하세요.'
                    : '매매 전략을 직접 설정하고 백테스트를 수행하세요.'}
                </p>
              </div>
              {strategyType === 'custom' ? (
                <SimpleStrategyForm
                  onSubmit={handleSubmit}
                  isLoading={isLoading}
                  initialSymbols={sharedSymbols}
                  loadedTemplate={loadedTemplate}
                />
              ) : (
                <MasterStrategySelector
                  onSubmit={handleMasterSubmit}
                  onLoadTemplate={handleLoadTemplate}
                  isLoading={isLoading}
                  initialSymbols={sharedSymbols}
                />
              )}
            </div>

            {/* Results */}
            {(isLoading || mutation.isError || masterMutation.isError || results || masterResults) && (
              <div>
                <div className="mb-6">
                  <h2 className="text-xl font-semibold text-gray-900 mb-2">백테스트 결과</h2>
                  <p className="text-sm text-gray-600">
                    설정한 기간 동안 전략을 반복 실행했을 때의 매매 성과와 통계를 확인하세요.
                  </p>
                </div>

                {isLoading && (
                  <div className="card text-center py-12">
                    <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
                    <p className="text-gray-600">백테스트 실행 중...</p>
                    <p className="text-sm text-gray-500 mt-2">과거 데이터로 전략을 시뮬레이션하고 있습니다.</p>
                  </div>
                )}

                {(mutation.isError || masterMutation.isError) && (
                  <div className="card bg-red-50 border-red-200 text-center py-8">
                    <p className="text-red-700 font-medium">백테스트 중 오류가 발생했습니다.</p>
                    <p className="text-sm text-red-600 mt-2">백엔드 서버가 실행 중인지 확인해주세요.</p>
                  </div>
                )}

                {results && !isLoading && (
                  <ResultsDisplay results={results} />
                )}

                {masterResults && !isLoading && (
                  <MasterStrategyResults results={masterResults} />
                )}
              </div>
            )}
          </div>
        )}

        {/* 전략 비교 탭 */}
        {activeTab === 'compare' && (
          <div className="max-w-7xl mx-auto">
            <ComparisonPage />
          </div>
        )}

        {/* 실시간 모니터링 탭 */}
        {activeTab === 'realtime' && (
          <div className="max-w-7xl mx-auto">
            <RealtimeMonitor />
          </div>
        )}

        {/* 학습 자료 탭 */}
        {activeTab === 'learn' && (
          <div className="max-w-4xl mx-auto">
            <LearnMenu />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-16">
        <div className="container mx-auto px-4 py-6">
          <p className="text-center text-sm text-gray-600">
            본 서비스는 교육 및 리서치 목적으로만 제공되며, 투자 조언이 아닙니다.
          </p>
        </div>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}
