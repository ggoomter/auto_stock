import axios from 'axios';

export interface AnalysisRequest {
  universe?: {
    country: string[];
    top_n: number;
  };
  horizon?: {
    lookahead_days: number;
    rebalance_days: number;
  };
  symbols: string[];
  date_range: {
    start: string;
    end: string;
  };
  features?: string[];
  events?: string[];
  strategy: {
    entry: string;
    exit: string;
    risk?: {
      stop_pct: number;
      take_pct: number;
      position_sizing: string;
    };
  };
  simulate?: {
    bootstrap_runs: number;
    transaction_cost_bps: number;
    slippage_bps: number;
  };
  target?: {
    metric: string[];
  };
  explain?: boolean;
  output_detail?: 'brief' | 'full';
}

export interface AnalysisResponse {
  summary: string;
  universe_checked: Record<string, number>;
  sample_info: {
    n_signals: number;
    period: Record<string, string>;
  };
  prediction: {
    lookahead_days: number;
    up_prob: number;
    down_prob: number;
    expected_return_pct: number;
    ci95_return_pct: number[];
    drivers: Array<{
      feature: string;
      impact: string;
      evidence: string;
    }>;
  };
  backtest: {
    metrics: {
      CAGR: number;
      Sharpe: number;
      MaxDD: number;
      HitRatio: number;
      AvgWin?: number;
      AvgLoss?: number;
      TotalTrades?: number;
      WinTrades?: number;
      LossTrades?: number;
    };
    cost_assumptions_bps: Record<string, number>;
    equity_curve_ref?: string;
    equity_curve?: Array<{ date: string; value: number }>;
    risk_summary?: Record<string, any>;
    warnings?: string[] | null;
    trade_history?: TradeHistoryEntry[];
  };
  monte_carlo: {
    runs: number;
    p5_cagr: number;
    p50_cagr: number;
    p95_cagr: number;
    maxdd_distribution: Record<string, number>;
  };
  signal_examples: Array<{
    date: string;
    symbol: string;
    reason: string[];
  }>;
  limitations: string[];
}

export interface TradeHistoryEntry {
  entry_date: string;
  exit_date: string;
  entry_price: number;
  exit_price: number;
  shares: number;
  position_value?: number;
  position_value_krw?: number;
  pnl: number;
  pnl_krw?: number;
  pnl_pct: number;
  exit_reason?: string;
  holding_days?: number;
  partial?: boolean;
  symbol?: string;
  currency?: string;
  entry_price_krw?: number;
  exit_price_krw?: number;
}

const api = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

export const analyzeStrategy = async (
  request: AnalysisRequest
): Promise<AnalysisResponse> => {
  const response = await api.post<AnalysisResponse>('/analyze', request);
  return response.data;
};

export const healthCheck = async () => {
  const response = await api.get('/health');
  return response.data;
};

// ========== 투자 대가 전략 API ==========
export interface MasterStrategyRequest {
  strategy_name: 'buffett' | 'lynch' | 'graham' | 'dalio' | 'livermore' | 'oneil';
  symbols: string[];
  date_range: {
    start: string;
    end: string;
  };
  simulate?: {
    bootstrap_runs: number;
    transaction_cost_bps: number;
    slippage_bps: number;
  };
  output_detail?: 'brief' | 'full';
}

export interface MasterStrategyInfo {
  name: string;
  description: string;
  key_principles: string[];
  holding_period: string;
  risk_profile: string;
}


export interface ConditionCheck {
  condition_name: string;  // 조건명 (한글)
  condition_name_en: string;  // 조건명 (영어)
  required_value: string;  // 필요한 값
  actual_value: string | null;  // 실제 값
  passed: boolean;  // 통과 여부
}

export interface MasterStrategyResponse {
  strategy_info: MasterStrategyInfo;
  backtest: {
    metrics: {
      CAGR: number;
      Sharpe: number;
      MaxDD: number;
      HitRatio: number;
      AvgWin?: number;
      AvgLoss?: number;
      TotalTrades?: number;
      WinTrades?: number;
      LossTrades?: number;
    };
    cost_assumptions_bps: Record<string, number>;
    equity_curve_ref?: string;
    equity_curve?: Array<{ date: string; value: number }>;
    risk_summary?: Record<string, any>;
    warnings?: string[] | null;
    trade_history?: TradeHistoryEntry[];
  };
  fundamental_screen?: {
    metrics?: Record<string, any>;
    criteria?: {
      passed_count: number;
      total_count: number;
      pass_rate: number;
      [key: string]: any;
    };
    error?: string;
  };
  condition_checks?: ConditionCheck[];  // 조건 체크 상세 추가
  signal_examples: Array<{
    date: string;
    symbol: string;
    reason: string[];
  }>;
  trade_history?: TradeHistoryEntry[];
  initial_capital: number;
  final_capital?: number;
  initial_capital_krw?: number;
  final_capital_krw?: number;
  exchange_rate?: number;
  equity_curve?: Array<{ date: string; value: number }>;
  price_data?: Array<{ date: string; close: number }>;
}

export interface MasterStrategyListItem {
  name: string;
  description: string;
  info: MasterStrategyInfo;
}

export const getMasterStrategies = async (): Promise<{ strategies: MasterStrategyListItem[] }> => {
  const response = await api.get('/master-strategies');
  return response.data;
};

export const analyzeMasterStrategy = async (
  request: MasterStrategyRequest
): Promise<MasterStrategyResponse> => {
  const response = await api.post<MasterStrategyResponse>('/master-strategy', request);
  return response.data;
};

export interface StrategyTemplate {
  entry: string;
  exit: string;
  description: string;
  risk: {
    stop_pct: number;
    take_pct: number;
  };
  fundamental_filters: string[];
}

export interface StrategyTemplateResponse {
  strategy_name: string;
  strategy_info: MasterStrategyInfo;
  template: StrategyTemplate;
}

export const getStrategyTemplate = async (
  strategyName: string
): Promise<StrategyTemplateResponse> => {
  const response = await api.get<StrategyTemplateResponse>(`/master-strategy/${strategyName}/template`);
  return response.data;
};

export interface StockSearchResult {
  symbol: string;
  nameKo: string;
  nameEn: string;
  market: 'US' | 'KR';
  sector: string;
  industry?: string;
  marketCap?: number;
}

export interface StockSearchResponse {
  results: StockSearchResult[];
  query: string;
  error?: string;
}

export const searchStocks = async (query: string): Promise<StockSearchResponse> => {
  try {
    const response = await api.get<StockSearchResponse>('/search-stocks', {
      params: { query }
    });
    return response.data;
  } catch (error) {
    console.error('종목 검색 오류:', error);
    return { results: [], query };
  }
};

// ============================================================
// 전략 비교 API
// ============================================================

export interface StrategyComparisonRequest {
  strategy_names: string[];  // ["buffett", "lynch", "graham", ...]
  symbols: string[];
  start_date: string;
  end_date: string;
  initial_capital?: number;
}

export interface StrategyComparisonResult {
  strategy_name: string;
  strategy_description: string;
  metrics: {
    CAGR: number;
    Sharpe: number;
    MaxDD: number;
    WinRate: number;
    TotalTrades: number;
    ProfitFactor: number;
  };
  equity_curve: Array<{ date: string; equity: number }>;
  final_equity: number;
  total_return_pct: number;
  trade_count: number;
}

export interface StrategyComparisonResponse {
  results: StrategyComparisonResult[];
  best_strategy: string;
  comparison_period: {
    start: string;
    end: string;
  };
}

export const compareStrategies = async (
  request: StrategyComparisonRequest
): Promise<StrategyComparisonResponse> => {
  const response = await api.post<StrategyComparisonResponse>('/compare-strategies', request);
  return response.data;
};

// ============================================================
// 자동매매 API
// ============================================================

export interface TradingStartRequest {
  mode: 'paper' | 'live';  // 모의 거래 or 실전 거래
  total_capital: number;  // 초기 자본 (KRW)
  max_positions: number;  // 최대 포지션 수
  max_position_size: number;  // 종목당 최대 비중 (0.2 = 20%)
  max_risk_per_trade: number;  // 거래당 최대 리스크 (0.02 = 2%)
  max_daily_loss: number;  // 일일 최대 손실 (0.05 = 5%)
  enabled_strategies: string[];  // 활성화 전략 ["buffett", "lynch"]
  trading_symbols: string[];  // 거래 종목
  use_trailing_stop: boolean;
  trailing_stop_percent: number;
  order_type: 'market' | 'limit';
  slippage_tolerance?: number;
}

export interface TradingStopRequest {
  close_all_positions: boolean;  // 모든 포지션 청산 여부
  reason: string;  // 중지 사유
}

export interface EmergencyStopRequest {
  reason: string;
}

export interface TradingStatusResponse {
  is_running: boolean;
  mode: string;
  uptime_seconds: number;
  active_positions: number;
  total_trades_today: number;
  daily_pnl: number;
  daily_pnl_pct: number;
  enabled_strategies: string[];
  risk_level: 'low' | 'medium' | 'high' | 'extreme';
  last_update: string;
}

export interface PositionInfo {
  symbol: string;
  quantity: number;
  entry_price: number;
  entry_date: string;
  current_price: number;
  pnl: number;
  pnl_pct: number;
  stop_loss: number | null;
  take_profit: number | null;
  strategy: string;
}

export interface PortfolioStatusResponse {
  total_value: number;
  cash: number;
  positions_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  positions: PositionInfo[];
  risk_metrics: {
    concentration_risk: number;
    daily_var: number;
    max_position_size: number;
  };
  last_update: string;
}

export interface TradingPerformanceResponse {
  total_trades: number;
  win_rate: number;
  profit_factor: number;
  sharpe_ratio: number;
  max_drawdown: number;
  average_win: number;
  average_loss: number;
  largest_win: number;
  largest_loss: number;
}

export interface TradingHealthResponse {
  timestamp: string;
  system: {
    cpu_percent: number;
    memory_percent: number;
    disk_percent: number;
  };
  trading: {
    is_running: boolean;
    engine_status: string;
  };
  checks: Array<{
    status: string;
    message: string;
  }>;
  overall_status: 'healthy' | 'warning' | 'error';
}

/**
 * 자동매매 시작
 */
export const startTrading = async (
  request: TradingStartRequest
): Promise<any> => {
  const response = await api.post('/trading/start', request);
  return response.data;
};

/**
 * 자동매매 중지
 */
export const stopTrading = async (
  request: TradingStopRequest
): Promise<any> => {
  const response = await api.post('/trading/stop', request);
  return response.data;
};

/**
 * 자동매매 상태 조회
 */
export const getTradingStatus = async (): Promise<TradingStatusResponse> => {
  const response = await api.get<TradingStatusResponse>('/trading/status');
  return response.data;
};

/**
 * 포트폴리오 상태 조회
 */
export const getPortfolioStatus = async (): Promise<PortfolioStatusResponse> => {
  const response = await api.get<PortfolioStatusResponse>('/portfolio/status');
  return response.data;
};

/**
 * 긴급 정지 (킬 스위치)
 */
export const emergencyStop = async (
  request: EmergencyStopRequest
): Promise<any> => {
  const response = await api.post('/trading/emergency-stop', request);
  return response.data;
};

/**
 * 거래 성과 조회
 */
export const getTradingPerformance = async (): Promise<TradingPerformanceResponse> => {
  const response = await api.get<TradingPerformanceResponse>('/trading/performance');
  return response.data;
};

/**
 * 시스템 헬스 체크
 */
export const getTradingHealth = async (): Promise<TradingHealthResponse> => {
  const response = await api.get<TradingHealthResponse>('/trading/health');
  return response.data;
};

export default api;
