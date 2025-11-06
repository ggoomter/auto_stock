import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Activity,
  DollarSign,
  PieChart,
  Bell,
  Shield,
  Zap,
  Eye,
  Settings,
  RefreshCw,
  Play,
  Pause,
  StopCircle,
  AlertCircle
} from 'lucide-react';
import {
  startTrading,
  stopTrading,
  getTradingStatus,
  getPortfolioStatus,
  emergencyStop,
  type TradingStartRequest,
  type TradingStopRequest,
  type TradingStatusResponse,
  type PortfolioStatusResponse,
  type PositionInfo
} from '../services/api';

interface TradingDashboardProps {
  isAutoTrading: boolean;
  onToggleAutoTrading: (enabled: boolean) => void;
}

const TradingDashboard: React.FC<TradingDashboardProps> = ({
  isAutoTrading: initialIsAutoTrading,
  onToggleAutoTrading
}) => {
  // 상태 관리
  const [isAutoTrading, setIsAutoTrading] = useState(initialIsAutoTrading);
  const [tradingMode, setTradingMode] = useState<'paper' | 'live'>('paper');
  const [tradingStatus, setTradingStatus] = useState<TradingStatusResponse | null>(null);
  const [portfolio, setPortfolio] = useState<PortfolioStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 설정
  const [totalCapital, setTotalCapital] = useState(10000000);
  const [maxPositions, setMaxPositions] = useState(5);
  const [enabledStrategies, setEnabledStrategies] = useState<string[]>(['buffett', 'lynch']);
  const [tradingSymbols, setTradingSymbols] = useState<string[]>(['AAPL', 'TSLA', '005930.KS']);

  // UI 상태
  const [showSettings, setShowSettings] = useState(false);
  const [showEmergencyConfirm, setShowEmergencyConfirm] = useState(false);

  // 자동 새로고침 (5초마다)
  useEffect(() => {
    const interval = setInterval(() => {
      if (isAutoTrading) {
        refreshData();
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [isAutoTrading]);

  // 초기 데이터 로드
  useEffect(() => {
    refreshData();
  }, []);

  /**
   * 데이터 새로고침
   */
  const refreshData = async () => {
    try {
      // 자동매매 상태 조회
      const status = await getTradingStatus();
      setTradingStatus(status);
      setIsAutoTrading(status.is_running);

      // 포트폴리오 조회 (자동매매 실행 중일 때만)
      if (status.is_running) {
        const portfolioData = await getPortfolioStatus();
        setPortfolio(portfolioData);
      }
    } catch (err: any) {
      // 자동매매가 실행 중이 아니면 에러 무시
      if (err.response?.status !== 400) {
        console.error('데이터 새로고침 실패:', err);
      }
    }
  };

  /**
   * 자동매매 시작
   */
  const handleStartTrading = async () => {
    // 실전 모드 경고
    if (tradingMode === 'live') {
      const confirmed = window.confirm(
        '⚠️ 실전 거래 모드로 시작하시겠습니까?\n\n' +
        '실제 자금이 사용되며 손실 위험이 있습니다.\n' +
        '충분히 테스트한 후 사용하시기 바랍니다.'
      );
      if (!confirmed) return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const request: TradingStartRequest = {
        mode: tradingMode,
        total_capital: totalCapital,
        max_positions: maxPositions,
        max_position_size: 0.2,
        max_risk_per_trade: 0.02,
        max_daily_loss: 0.05,
        enabled_strategies: enabledStrategies,
        trading_symbols: tradingSymbols,
        use_trailing_stop: true,
        trailing_stop_percent: 0.05,
        order_type: 'market'
      };

      const response = await startTrading(request);
      console.log('자동매매 시작 성공:', response);

      setIsAutoTrading(true);
      onToggleAutoTrading(true);

      // 상태 즉시 새로고침
      await refreshData();

      alert('✅ 자동매매가 시작되었습니다!');
    } catch (err: any) {
      console.error('자동매매 시작 실패:', err);
      setError(err.response?.data?.detail || err.message || '자동매매 시작 실패');
      alert(`❌ 자동매매 시작 실패\n\n${err.response?.data?.detail || err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * 자동매매 중지
   */
  const handleStopTrading = async () => {
    const confirmed = window.confirm(
      '자동매매를 중지하시겠습니까?\n\n' +
      '기존 포지션은 유지됩니다.'
    );
    if (!confirmed) return;

    setIsLoading(true);
    setError(null);

    try {
      const request: TradingStopRequest = {
        close_all_positions: false,
        reason: '사용자 요청'
      };

      const response = await stopTrading(request);
      console.log('자동매매 중지 성공:', response);

      setIsAutoTrading(false);
      onToggleAutoTrading(false);

      await refreshData();

      alert('✅ 자동매매가 중지되었습니다.');
    } catch (err: any) {
      console.error('자동매매 중지 실패:', err);
      setError(err.response?.data?.detail || err.message || '자동매매 중지 실패');
      alert(`❌ 자동매매 중지 실패\n\n${err.response?.data?.detail || err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * 긴급 정지 (킬 스위치)
   */
  const handleEmergencyStop = async () => {
    setShowEmergencyConfirm(false);
    setIsLoading(true);

    try {
      const response = await emergencyStop({ reason: '긴급 정지 - 사용자 요청' });
      console.log('긴급 정지 성공:', response);

      setIsAutoTrading(false);
      onToggleAutoTrading(false);

      await refreshData();

      alert(`🛑 긴급 정지 완료\n\n청산된 포지션: ${response.closed_positions}개`);
    } catch (err: any) {
      console.error('긴급 정지 실패:', err);
      alert(`❌ 긴급 정지 실패\n\n${err.response?.data?.detail || err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * 자동매매 토글
   */
  const handleToggle = () => {
    if (isAutoTrading) {
      handleStopTrading();
    } else {
      handleStartTrading();
    }
  };

  /**
   * 리스크 레벨 색상
   */
  const getRiskColor = (level: string) => {
    switch (level) {
      case 'low': return 'text-green-400';
      case 'medium': return 'text-yellow-400';
      case 'high': return 'text-orange-400';
      case 'extreme': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  /**
   * 한국 원화 포맷
   */
  const formatKRW = (value: number) => {
    return new Intl.NumberFormat('ko-KR', {
      style: 'currency',
      currency: 'KRW',
      minimumFractionDigits: 0
    }).format(value);
  };

  /**
   * 업타임 포맷 (초 → 시:분:초)
   */
  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      {/* 헤더 */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-4">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            자동매매 대시보드
          </h1>

          {/* 실행 상태 배지 */}
          <div className={`flex items-center gap-2 px-4 py-2 rounded-lg border-2 ${
            isAutoTrading
              ? 'border-green-500 bg-green-900/20 text-green-400'
              : 'border-gray-600 bg-gray-800/50 text-gray-400'
          }`}>
            <div className={`w-3 h-3 rounded-full ${
              isAutoTrading ? 'bg-green-400 animate-pulse' : 'bg-gray-500'
            }`} />
            <span className="font-semibold">
              {isAutoTrading ? '실행 중' : '정지'}
            </span>
          </div>

          {/* 모드 배지 */}
          {tradingStatus && (
            <div className={`px-3 py-1 rounded-lg text-sm font-semibold ${
              tradingStatus.mode === 'live'
                ? 'bg-red-900/30 text-red-400 border border-red-500'
                : 'bg-blue-900/30 text-blue-400 border border-blue-500'
            }`}>
              {tradingStatus.mode === 'live' ? '🔴 실전' : '🟢 모의'}
            </div>
          )}
        </div>

        <div className="flex items-center gap-3">
          {/* 새로고침 */}
          <button
            onClick={refreshData}
            disabled={isLoading}
            className="p-2 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors disabled:opacity-50"
            title="새로고침"
          >
            <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>

          {/* 설정 */}
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="p-2 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors"
            title="설정"
          >
            <Settings className="w-5 h-5" />
          </button>

          {/* 긴급 정지 버튼 (킬 스위치) */}
          {isAutoTrading && (
            <button
              onClick={() => setShowEmergencyConfirm(true)}
              className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg font-semibold transition-all transform hover:scale-95"
              title="모든 포지션을 즉시 청산하고 자동매매를 중지합니다"
            >
              <StopCircle className="w-5 h-5" />
              긴급 정지
            </button>
          )}

          {/* 자동매매 시작/중지 버튼 */}
          <button
            onClick={handleToggle}
            disabled={isLoading}
            className={`flex items-center gap-2 px-6 py-3 rounded-lg font-bold transition-all transform hover:scale-95 disabled:opacity-50 disabled:cursor-not-allowed ${
              isAutoTrading
                ? 'bg-gradient-to-r from-orange-500 to-red-600 hover:from-orange-600 hover:to-red-700'
                : 'bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700'
            }`}
          >
            {isLoading ? (
              <>
                <RefreshCw className="w-5 h-5 animate-spin" />
                처리 중...
              </>
            ) : isAutoTrading ? (
              <>
                <Pause className="w-5 h-5" />
                자동매매 중지
              </>
            ) : (
              <>
                <Play className="w-5 h-5" />
                자동매매 시작
              </>
            )}
          </button>
        </div>
      </div>

      {/* 긴급 정지 확인 모달 */}
      {showEmergencyConfirm && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-gray-900 border-2 border-red-500 rounded-xl p-6 max-w-md w-full mx-4">
            <div className="flex items-center gap-3 mb-4">
              <AlertCircle className="w-8 h-8 text-red-500" />
              <h3 className="text-xl font-bold text-red-500">긴급 정지 확인</h3>
            </div>

            <p className="text-gray-300 mb-2">
              🚨 <strong>모든 포지션을 시장가로 즉시 청산</strong>하고 자동매매를 중지합니다.
            </p>

            <p className="text-sm text-gray-400 mb-6">
              이 작업은 되돌릴 수 없습니다. 정말로 긴급 정지하시겠습니까?
            </p>

            <div className="flex gap-3">
              <button
                onClick={() => setShowEmergencyConfirm(false)}
                className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg font-semibold transition-colors"
              >
                취소
              </button>
              <button
                onClick={handleEmergencyStop}
                className="flex-1 px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg font-bold transition-colors"
              >
                긴급 정지 실행
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 에러 메시지 */}
      {error && (
        <div className="mb-4 p-4 bg-red-900/30 border border-red-500 rounded-lg flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold text-red-400">오류 발생</p>
            <p className="text-sm text-red-300">{error}</p>
          </div>
          <button
            onClick={() => setError(null)}
            className="text-red-400 hover:text-red-300"
          >
            ✕
          </button>
        </div>
      )}

      {/* 설정 패널 */}
      {showSettings && (
        <div className="mb-6 p-6 bg-gray-900 rounded-xl border border-gray-700">
          <h2 className="text-xl font-bold mb-4">자동매매 설정</h2>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-gray-400 mb-2">거래 모드</label>
              <select
                value={tradingMode}
                onChange={(e) => setTradingMode(e.target.value as 'paper' | 'live')}
                disabled={isAutoTrading}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none disabled:opacity-50"
              >
                <option value="paper">모의 거래 (Paper Trading)</option>
                <option value="live">실전 거래 (Live Trading)</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-400 mb-2">초기 자본 (KRW)</label>
              <input
                type="number"
                value={totalCapital}
                onChange={(e) => setTotalCapital(Number(e.target.value))}
                disabled={isAutoTrading}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none disabled:opacity-50"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-400 mb-2">최대 포지션 수</label>
              <input
                type="number"
                value={maxPositions}
                onChange={(e) => setMaxPositions(Number(e.target.value))}
                disabled={isAutoTrading}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none disabled:opacity-50"
              />
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-400 mb-2">활성화 전략</label>
              <input
                type="text"
                value={enabledStrategies.join(', ')}
                onChange={(e) => setEnabledStrategies(e.target.value.split(',').map(s => s.trim()))}
                disabled={isAutoTrading}
                placeholder="buffett, lynch, graham"
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg focus:border-blue-500 focus:outline-none disabled:opacity-50"
              />
            </div>
          </div>
        </div>
      )}

      {/* 통계 카드 */}
      {tradingStatus && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          {/* 일일 손익 */}
          <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-400 text-sm font-semibold">일일 손익</span>
              <DollarSign className="w-5 h-5 text-gray-500" />
            </div>
            <div className="text-2xl font-bold mb-1">
              {formatKRW(tradingStatus.daily_pnl)}
            </div>
            <div className={`text-sm font-semibold ${
              tradingStatus.daily_pnl_pct >= 0 ? 'text-green-400' : 'text-red-400'
            }`}>
              {tradingStatus.daily_pnl_pct >= 0 ? '▲' : '▼'} {Math.abs(tradingStatus.daily_pnl_pct).toFixed(2)}%
            </div>
          </div>

          {/* 활성 포지션 */}
          <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-400 text-sm font-semibold">활성 포지션</span>
              <PieChart className="w-5 h-5 text-gray-500" />
            </div>
            <div className="text-2xl font-bold mb-1">
              {tradingStatus.active_positions}개
            </div>
            <div className="text-sm text-gray-500">
              최대 {maxPositions}개
            </div>
          </div>

          {/* 오늘 거래 */}
          <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-400 text-sm font-semibold">오늘 거래</span>
              <Activity className="w-5 h-5 text-gray-500" />
            </div>
            <div className="text-2xl font-bold mb-1">
              {tradingStatus.total_trades_today}회
            </div>
            <div className="text-sm text-gray-500">
              실행 시간: {formatUptime(tradingStatus.uptime_seconds)}
            </div>
          </div>

          {/* 리스크 레벨 */}
          <div className="bg-gray-900 rounded-xl p-6 border border-gray-800">
            <div className="flex items-center justify-between mb-2">
              <span className="text-gray-400 text-sm font-semibold">리스크 레벨</span>
              <Shield className="w-5 h-5 text-gray-500" />
            </div>
            <div className={`text-2xl font-bold mb-1 uppercase ${getRiskColor(tradingStatus.risk_level)}`}>
              {tradingStatus.risk_level}
            </div>
            <div className="text-sm text-gray-500">
              전략: {tradingStatus.enabled_strategies.join(', ')}
            </div>
          </div>
        </div>
      )}

      {/* 포트폴리오 정보 */}
      {portfolio && (
        <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 mb-6">
          <h2 className="text-xl font-bold mb-4">포트폴리오</h2>

          <div className="grid grid-cols-3 gap-4 mb-6">
            <div>
              <p className="text-sm text-gray-400 mb-1">총 자산</p>
              <p className="text-2xl font-bold">{formatKRW(portfolio.total_value)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-400 mb-1">현금</p>
              <p className="text-2xl font-bold">{formatKRW(portfolio.cash)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-400 mb-1">포지션 가치</p>
              <p className="text-2xl font-bold">{formatKRW(portfolio.positions_value)}</p>
            </div>
          </div>

          {/* 포지션 테이블 */}
          {portfolio.positions.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-sm text-gray-400 border-b border-gray-800">
                    <th className="pb-2">종목</th>
                    <th className="pb-2 text-right">수량</th>
                    <th className="pb-2 text-right">진입가</th>
                    <th className="pb-2 text-right">현재가</th>
                    <th className="pb-2 text-right">손익</th>
                    <th className="pb-2">전략</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolio.positions.map((pos, idx) => (
                    <tr key={idx} className="border-b border-gray-800/50">
                      <td className="py-3 font-semibold">{pos.symbol}</td>
                      <td className="py-3 text-right">{pos.quantity}</td>
                      <td className="py-3 text-right">{formatKRW(pos.entry_price)}</td>
                      <td className="py-3 text-right">{formatKRW(pos.current_price)}</td>
                      <td className={`py-3 text-right font-semibold ${
                        pos.pnl >= 0 ? 'text-green-400' : 'text-red-400'
                      }`}>
                        {formatKRW(pos.pnl)} ({pos.pnl_pct >= 0 ? '+' : ''}{pos.pnl_pct.toFixed(2)}%)
                      </td>
                      <td className="py-3">
                        <span className="px-2 py-1 bg-blue-900/30 text-blue-400 rounded text-xs">
                          {pos.strategy}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-center text-gray-500 py-8">활성 포지션이 없습니다</p>
          )}
        </div>
      )}

      {/* 자동매매가 실행 중이 아닐 때 안내 메시지 */}
      {!isAutoTrading && (
        <div className="bg-gray-900 rounded-xl p-12 border border-gray-800 text-center">
          <Zap className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-2xl font-bold mb-2 text-gray-400">자동매매가 실행되지 않았습니다</h3>
          <p className="text-gray-500 mb-6">
            "자동매매 시작" 버튼을 눌러 자동 거래를 시작하세요.
          </p>
          <button
            onClick={handleStartTrading}
            disabled={isLoading}
            className="px-6 py-3 bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 rounded-lg font-bold transition-all transform hover:scale-95 disabled:opacity-50"
          >
            <Play className="w-5 h-5 inline mr-2" />
            자동매매 시작
          </button>
        </div>
      )}
    </div>
  );
};

export default TradingDashboard;
