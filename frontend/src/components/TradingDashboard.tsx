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
  StopCircle
} from 'lucide-react';

interface Position {
  symbol: string;
  shares: number;
  entryPrice: number;
  currentPrice: number;
  stopLoss: number;
  takeProfit: number;
  pnl: number;
  pnlPercent: number;
  status: 'active' | 'pending' | 'closed';
  strategy: string;
}

interface RiskMetrics {
  포트폴리오위험도: number;
  위험가치95: number;
  위험조정수익률: number;
  최대낙폭: number;
  위험수준: 'low' | 'medium' | 'high' | 'extreme';
}

interface Alert {
  id: string;
  type: 'info' | 'warning' | 'success' | 'danger';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
}

interface TradingDashboardProps {
  isAutoTrading: boolean;
  onToggleAutoTrading: (enabled: boolean) => void;
}

const TradingDashboard: React.FC<TradingDashboardProps> = ({
  isAutoTrading,
  onToggleAutoTrading
}) => {
  const [positions, setPositions] = useState<Position[]>([]);
  const [riskMetrics, setRiskMetrics] = useState<RiskMetrics | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [totalPnL, setTotalPnL] = useState(0);
  const [totalPnLPercent, setTotalPnLPercent] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const [showAlerts, setShowAlerts] = useState(false);
  const [selectedTimeframe, setSelectedTimeframe] = useState('1D');
  const [refreshInterval, setRefreshInterval] = useState(10); // seconds

  // WebSocket 연결 (실시간 데이터)
  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/realtime');

    ws.onopen = () => {
      setIsConnected(true);
      console.log('실시간 데이터 연결됨');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'position_update') {
        setPositions(data.positions);
        calculateTotalPnL(data.positions);
      } else if (data.type === 'risk_update') {
        setRiskMetrics(data.riskMetrics);
      } else if (data.type === 'alert') {
        addAlert(data.alert);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      console.log('실시간 데이터 연결 끊김');
    };

    return () => {
      ws.close();
    };
  }, []);

  // 자동 새로고침
  useEffect(() => {
    const interval = setInterval(() => {
      refreshData();
    }, refreshInterval * 1000);

    return () => clearInterval(interval);
  }, [refreshInterval]);

  const calculateTotalPnL = (positions: Position[]) => {
    const total = positions.reduce((sum, pos) => sum + pos.pnl, 0);
    const totalPercent = positions.reduce((sum, pos) => sum + pos.pnlPercent, 0) / positions.length;
    setTotalPnL(total);
    setTotalPnLPercent(totalPercent);
  };

  const refreshData = async () => {
    // API 호출로 최신 데이터 가져오기
    try {
      const response = await fetch('http://localhost:8000/api/v1/portfolio/status');
      const data = await response.json();
      setPositions(data.positions);
      setRiskMetrics(data.riskMetrics);
    } catch (error) {
      console.error('데이터 새로고침 실패:', error);
    }
  };

  const addAlert = (alert: Alert) => {
    setAlerts(prev => [alert, ...prev].slice(0, 50)); // 최대 50개
  };

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'low': return 'text-green-500';
      case 'medium': return 'text-yellow-500';
      case 'high': return 'text-orange-500';
      case 'extreme': return 'text-red-500';
      default: return 'text-gray-500';
    }
  };

  const formatKRW = (value: number) => {
    return new Intl.NumberFormat('ko-KR', {
      style: 'currency',
      currency: 'KRW',
      minimumFractionDigits: 0
    }).format(value);
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white p-4">
      {/* 헤더 */}
      <div className="flex justify-between items-center mb-6">
        <div className="flex items-center gap-4">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            실시간 트레이딩 대시보드
          </h1>
          <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${
            isConnected ? 'bg-green-900/30 text-green-400' : 'bg-red-900/30 text-red-400'
          }`}>
            <div className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-400 animate-pulse' : 'bg-red-400'
            }`} />
            {isConnected ? '실시간 연결됨' : '연결 끊김'}
          </div>
        </div>

        {/* 자동매매 토글 */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => setShowAlerts(!showAlerts)}
            className="relative p-2 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors"
          >
            <Bell className="w-5 h-5" />
            {alerts.filter(a => !a.read).length > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full text-xs flex items-center justify-center">
                {alerts.filter(a => !a.read).length}
              </span>
            )}
          </button>

          <button
            onClick={() => onToggleAutoTrading(!isAutoTrading)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold transition-all transform hover:scale-95 ${
              isAutoTrading
                ? 'bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700'
                : 'bg-gradient-to-r from-gray-600 to-gray-700 hover:from-gray-700 hover:to-gray-800'
            }`}
          >
            {isAutoTrading ? (
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

          <button
            onClick={refreshData}
            className="p-2 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* 주요 지표 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div
          className="bg-gray-900 rounded-xl p-6 border border-gray-800 animate-fade-in"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400">총 손익</span>
            <DollarSign className="w-5 h-5 text-gray-600" />
          </div>
          <div className={`text-2xl font-bold ${totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {formatKRW(totalPnL)}
          </div>
          <div className={`text-sm mt-1 ${totalPnLPercent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {totalPnLPercent >= 0 ? '+' : ''}{totalPnLPercent.toFixed(2)}%
          </div>
        </div>

        <div
          className="bg-gray-900 rounded-xl p-6 border border-gray-800 animate-fade-in"
          transition={{ delay: 0.1 }}
          className="bg-gray-900 rounded-xl p-6 border border-gray-800"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400">포트폴리오 위험도</span>
            <Shield className="w-5 h-5 text-gray-600" />
          </div>
          <div className="text-2xl font-bold">
            {riskMetrics ? `${(riskMetrics.포트폴리오위험도 * 100).toFixed(1)}%` : '-'}
          </div>
          <div className={`text-sm mt-1 ${riskMetrics ? getRiskColor(riskMetrics.위험수준) : ''}`}>
            {riskMetrics ? (
              riskMetrics.위험수준 === 'low' ? '낮음' :
              riskMetrics.위험수준 === 'medium' ? '보통' :
              riskMetrics.위험수준 === 'high' ? '높음' : '매우높음'
            ) : '-'}
          </div>
        </div>

        <div
          className="bg-gray-900 rounded-xl p-6 border border-gray-800 animate-fade-in"
          transition={{ delay: 0.2 }}
          className="bg-gray-900 rounded-xl p-6 border border-gray-800"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400">위험조정수익률</span>
            <Activity className="w-5 h-5 text-gray-600" />
          </div>
          <div className="text-2xl font-bold">
            {riskMetrics?.위험조정수익률.toFixed(2) || '-'}
          </div>
          <div className="text-sm mt-1 text-gray-500">
            위험 대비 수익 효율성
          </div>
        </div>

        <div
          className="bg-gray-900 rounded-xl p-6 border border-gray-800 animate-fade-in"
          transition={{ delay: 0.3 }}
          className="bg-gray-900 rounded-xl p-6 border border-gray-800"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-gray-400">활성 포지션</span>
            <PieChart className="w-5 h-5 text-gray-600" />
          </div>
          <div className="text-2xl font-bold">
            {positions.filter(p => p.status === 'active').length}
          </div>
          <div className="text-sm mt-1 text-gray-500">
            / {positions.length} 전체
          </div>
        </div>
      </div>

      {/* 포지션 테이블 */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 mb-6">
        <div className="px-6 py-4 border-b border-gray-800">
          <h2 className="text-xl font-semibold">실시간 포지션</h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">종목</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">전략</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">수량</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">진입가</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">현재가</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">손익</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">손익률</th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-400 uppercase tracking-wider">상태</th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-400 uppercase tracking-wider">액션</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {positions.map((position, index) => (
                <tr
                  key={position.symbol}
                  className="hover:bg-gray-800/50 transition-colors animate-slide-in"
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="font-medium">{position.symbol}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 py-1 text-xs bg-blue-900/30 text-blue-400 rounded">
                      {position.strategy}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    {position.shares.toLocaleString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    {formatKRW(position.entryPrice)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className="flex items-center justify-end gap-1">
                      {formatKRW(position.currentPrice)}
                      {position.currentPrice > position.entryPrice ? (
                        <TrendingUp className="w-4 h-4 text-green-400" />
                      ) : (
                        <TrendingDown className="w-4 h-4 text-red-400" />
                      )}
                    </div>
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-right font-medium ${
                    position.pnl >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {formatKRW(position.pnl)}
                  </td>
                  <td className={`px-6 py-4 whitespace-nowrap text-right font-medium ${
                    position.pnlPercent >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {position.pnlPercent >= 0 ? '+' : ''}{position.pnlPercent.toFixed(2)}%
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <span className={`px-2 py-1 text-xs rounded ${
                      position.status === 'active'
                        ? 'bg-green-900/30 text-green-400'
                        : position.status === 'pending'
                        ? 'bg-yellow-900/30 text-yellow-400'
                        : 'bg-gray-900/30 text-gray-400'
                    }`}>
                      {position.status === 'active' ? '활성' :
                       position.status === 'pending' ? '대기' : '종료'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-center">
                    <div className="flex items-center justify-center gap-2">
                      <button
                        className="p-1 hover:bg-gray-700 rounded transition-colors"
                        title="상세보기"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        className="p-1 hover:bg-gray-700 rounded transition-colors"
                        title="설정"
                      >
                        <Settings className="w-4 h-4" />
                      </button>
                      {position.status === 'active' && (
                        <button
                          className="p-1 hover:bg-red-900/30 text-red-400 rounded transition-colors"
                          title="청산"
                        >
                          <StopCircle className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 알림 패널 */}
      {showAlerts && (
        <div
          className="fixed right-4 top-20 w-80 max-h-96 bg-gray-900 rounded-xl border border-gray-800 shadow-2xl overflow-hidden transition-all duration-300"
        >
            <div className="px-4 py-3 border-b border-gray-800 flex justify-between items-center">
              <h3 className="font-semibold">알림</h3>
              <button
                onClick={() => setShowAlerts(false)}
                className="text-gray-400 hover:text-white"
              >
                ✕
              </button>
            </div>
            <div className="max-h-80 overflow-y-auto">
              {alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`px-4 py-3 border-b border-gray-800 ${
                    !alert.read ? 'bg-gray-800/50' : ''
                  }`}
                >
                  <div className="flex items-start gap-2">
                    {alert.type === 'danger' && <AlertTriangle className="w-4 h-4 text-red-400 mt-0.5" />}
                    {alert.type === 'success' && <Zap className="w-4 h-4 text-green-400 mt-0.5" />}
                    {alert.type === 'warning' && <AlertTriangle className="w-4 h-4 text-yellow-400 mt-0.5" />}
                    <div className="flex-1">
                      <div className="font-medium text-sm">{alert.title}</div>
                      <div className="text-xs text-gray-400 mt-1">{alert.message}</div>
                      <div className="text-xs text-gray-500 mt-1">
                        {new Date(alert.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
        </div>
      )}
    </div>
  );
};

export default TradingDashboard;