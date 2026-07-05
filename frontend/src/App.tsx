import { useState } from 'react';
import { QueryClient, QueryClientProvider, useMutation } from '@tanstack/react-query';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Users, Settings } from 'lucide-react';

import Layout from './components/Layout';
import SimpleStrategyForm from './components/SimpleStrategyForm';
import MasterStrategySelector from './components/MasterStrategySelector';
import ResultsDisplay from './components/ResultsDisplay';
import MasterStrategyResults from './components/MasterStrategyResults';
import LearnMenu from './components/LearnMenu';
import NewsFetchButton from './components/NewsFetchButton';
import ComparisonPage from './pages/ComparisonPage';
import RealtimeMonitor from './pages/RealtimeMonitor';
import TradingDashboard from './components/TradingDashboard';
import { ToastProvider } from './components/Toast';
import ErrorBoundary from './components/ErrorBoundary';
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

function StrategyPage() {
  const [strategyType, setStrategyType] = useState<StrategyType>('master');
  const [results, setResults] = useState<AnalysisResponse | null>(null);
  const [masterResults, setMasterResults] = useState<MasterStrategyResponse | null>(null);
  const [sharedSymbols, setSharedSymbols] = useState<string[]>([]);
  const [loadedTemplate, setLoadedTemplate] = useState<any>(null);

  const mutation = useMutation({
    mutationFn: analyzeStrategy,
    onSuccess: (data) => {
      setResults(data);
      setMasterResults(null);
    },
    onError: (error: any) => {
      console.error('분석 오류:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || '알 수 없는 오류';
      alert(`분석 중 오류가 발생했습니다.\n\n에러: ${errorMessage}`);
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
      alert(`분석 중 오류가 발생했습니다.\n\n에러: ${errorMessage}`);
    },
  });

  const handleSubmit = (request: AnalysisRequest) => {
    setResults(null);
    setMasterResults(null);
    setSharedSymbols(request.symbols);
    mutation.mutate(request);
  };

  const handleMasterSubmit = (request: MasterStrategyRequest) => {
    setResults(null);
    setMasterResults(null);
    setSharedSymbols(request.symbols);
    masterMutation.mutate(request);
  };

  const handleLoadTemplate = (template: any) => {
    setStrategyType('custom');
    setLoadedTemplate(template);
    setResults(null);
    setMasterResults(null);
    alert(`${template.strategyInfo.name} 전략이 로드되었습니다!`);
  };

  const isLoading = mutation.isPending || masterMutation.isPending;

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
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
              ? 'bg-primary-600 text-white shadow-lg dark:bg-primary-500'
              : 'bg-white text-gray-700 border-2 border-gray-300 hover:border-primary-400 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-600'
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
              ? 'bg-primary-600 text-white shadow-lg dark:bg-primary-500'
              : 'bg-white text-gray-700 border-2 border-gray-300 hover:border-primary-400 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-600'
          }`}
        >
          <Settings className="inline w-5 h-5 mr-2" />
          커스텀 전략
        </button>
      </div>

      {/* Form */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-200 dark:border-gray-700">
        <div className="mb-6">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">전략 설정</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400">
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
        <div className="animate-fade-in">
          <div className="mb-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">백테스트 결과</h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              시뮬레이션 성과와 통계를 확인하세요.
            </p>
          </div>

          {isLoading && (
            <div className="card text-center py-12 dark:bg-gray-800 dark:border-gray-700">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mb-4"></div>
              <p className="text-gray-600 dark:text-gray-300">백테스트 실행 중...</p>
            </div>
          )}

          {(mutation.isError || masterMutation.isError) && (
            <div className="card bg-red-50 border-red-200 text-center py-8 dark:bg-red-900/20 dark:border-red-800">
              <p className="text-red-700 dark:text-red-400 font-medium">오류가 발생했습니다.</p>
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
  );
}

function DashboardPage() {
  const [isAutoTrading, setIsAutoTrading] = useState(false);
  return (
    <TradingDashboard
      isAutoTrading={isAutoTrading}
      onToggleAutoTrading={setIsAutoTrading}
    />
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <ErrorBoundary>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<StrategyPage />} />
              <Route path="compare" element={<ComparisonPage />} />
              <Route path="realtime" element={<RealtimeMonitor />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="learn" element={<LearnMenu />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </ErrorBoundary>
      </ToastProvider>
    </QueryClientProvider>
  );
}
