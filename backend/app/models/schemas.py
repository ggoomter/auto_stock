from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Literal
from datetime import date


class Universe(BaseModel):
    country: List[str] = Field(default=["US", "KR"])
    top_n: int = Field(default=300, ge=1, le=1000)


class Horizon(BaseModel):
    lookahead_days: int = Field(default=5, ge=1, le=252)
    rebalance_days: int = Field(default=1, ge=1, le=63)


class DateRange(BaseModel):
    start: date
    end: date

    @field_validator('end')
    @classmethod
    def end_after_start(cls, v, info):
        if 'start' in info.data and v <= info.data['start']:
            raise ValueError('end date must be after start date')
        return v


class RiskParams(BaseModel):
    stop_pct: float = Field(default=0.07, ge=0.01, le=0.5)
    take_pct: float = Field(default=0.15, ge=0.01, le=10.0)  # 최대 10.0 (익절 수치 보수적 제한)
    position_sizing: Literal["equal_weight", "vol_target_10", "kelly"] = "vol_target_10"
    trailing_pct: float = Field(default=0.10, ge=0.01, le=0.5)
    max_risk_per_trade_pct: float = Field(default=0.02, ge=0.0005, le=1.0)
    max_portfolio_drawdown_pct: float = Field(default=0.30, ge=0.05, le=0.9)
    daily_loss_limit_pct: float = Field(default=0.05, ge=0.0, le=0.5)
    cooldown_days_after_loss: int = Field(default=2, ge=0, le=30)
    max_consecutive_losses: int = Field(default=3, ge=0, le=20)
    scale_down_after_drawdown_pct: float = Field(default=0.10, ge=0.0, le=0.5)
    scale_down_factor: float = Field(default=0.50, ge=0.1, le=1.0)
    allow_partial_profits: bool = True
    risk_free_rate: float = Field(default=0.015, ge=0.0, le=0.15)


class Strategy(BaseModel):
    entry: str = Field(..., description="Entry signal logic with AND/OR/parentheses")
    exit: str = Field(..., description="Exit signal logic")
    risk: RiskParams = Field(default_factory=RiskParams)


class SimulateParams(BaseModel):
    bootstrap_runs: int = Field(default=1000, ge=100, le=10000)
    transaction_cost_bps: int = Field(default=10, ge=0, le=100)
    slippage_bps: int = Field(default=5, ge=0, le=50)


class TargetMetrics(BaseModel):
    metric: List[Literal["CAGR", "Sharpe", "MaxDD", "HitRatio", "AvgWin", "AvgLoss"]] = [
        "CAGR", "Sharpe", "MaxDD", "HitRatio"
    ]


class AnalysisRequest(BaseModel):
    universe: Universe = Field(default_factory=Universe)
    horizon: Horizon = Field(default_factory=Horizon)
    symbols: List[str] = Field(..., min_length=1)
    date_range: DateRange
    features: List[str] = Field(
        default=["MACD", "RSI", "DMI", "BBANDS", "OBV", "RET", "VOL"]
    )
    events: List[str] = Field(
        default=["ELECTION", "FOMC", "EARNINGS"]
    )
    strategy: Strategy
    simulate: SimulateParams = Field(default_factory=SimulateParams)
    target: TargetMetrics = Field(default_factory=TargetMetrics)
    explain: bool = True
    output_detail: Literal["brief", "full"] = "brief"


class MasterStrategyRequest(BaseModel):
    """투자 대가 전략 백테스트 요청"""
    strategy_name: Literal["buffett", "lynch", "graham", "dalio", "livermore", "modern_livermore", "oneil", "chanos"] = Field(
        ..., description="Master investor strategy name"
    )
    symbols: List[str] = Field(..., min_length=1, description="Stock symbols to backtest")
    date_range: DateRange = Field(..., description="Backtest date range")
    simulate: SimulateParams = Field(default_factory=SimulateParams)
    output_detail: Literal["brief", "full"] = "brief"


class MasterStrategyInfo(BaseModel):
    """전략 정보"""
    name: str
    description: str
    key_principles: List[str]
    holding_period: str
    risk_profile: str


class Driver(BaseModel):
    feature: str
    impact: str  # "+", "-", "neutral"
    evidence: str


class Prediction(BaseModel):
    lookahead_days: int
    up_prob: float
    down_prob: float
    expected_return_pct: float
    ci95_return_pct: List[float]
    drivers: List[Driver]


class BacktestMetrics(BaseModel):
    CAGR: float
    Sharpe: float
    MaxDD: float
    HitRatio: float
    AvgWin: Optional[float] = None
    AvgLoss: Optional[float] = None
    TotalTrades: Optional[int] = None
    WinTrades: Optional[int] = None
    LossTrades: Optional[int] = None


class Backtest(BaseModel):
    metrics: BacktestMetrics
    cost_assumptions_bps: Dict[str, int]
    equity_curve_ref: Optional[str] = None
    equity_curve: Optional[List[Dict[str, Any]]] = None
    risk_summary: Optional[Dict[str, Any]] = None
    warnings: Optional[List[str]] = None
    trade_history: Optional[List[Dict[str, Any]]] = None


class MonteCarloResult(BaseModel):
    runs: int
    p5_cagr: float
    p50_cagr: float
    p95_cagr: float
    maxdd_distribution: Dict[str, float]


class SignalExample(BaseModel):
    date: str
    symbol: str
    reason: List[str]


class TradeDetail(BaseModel):
    """거래 상세 내역"""
    entry_date: str
    exit_date: str
    symbol: str
    entry_price: float  # USD (yfinance 기준)
    exit_price: float  # USD (yfinance 기준)
    entry_price_krw: Optional[float] = None  # 원화 환산
    exit_price_krw: Optional[float] = None  # 원화 환산
    shares: float
    position_value: float  # USD
    position_value_krw: Optional[float] = None  # 원화
    pnl: float  # 손익 (USD)
    pnl_krw: Optional[float] = None  # 손익 (원화)
    pnl_pct: float  # 손익률 (%)
    holding_days: int
    exit_reason: str
    currency: str = "USD"  # 기준 통화


class ConditionCheck(BaseModel):
    """조건 체크 상세"""
    condition_name: str  # 조건명 (한글)
    condition_name_en: str  # 조건명 (영어)
    required_value: str  # 필요한 값
    actual_value: Optional[str]  # 실제 값
    passed: bool  # 통과 여부


class MasterStrategyResponse(BaseModel):
    """투자 대가 전략 백테스트 결과"""
    strategy_info: MasterStrategyInfo
    backtest: Backtest
    fundamental_screen: Optional[Dict[str, Any]] = None
    condition_checks: Optional[List[ConditionCheck]] = None  # 조건 체크 상세
    signal_examples: List[SignalExample]
    trade_history: Optional[List[TradeDetail]] = None
    initial_capital: float = 1000000  # 기본 100만원
    initial_capital_krw: Optional[float] = None  # 원화
    final_capital: Optional[float] = None  # USD 기준
    final_capital_krw: Optional[float] = None  # 원화
    exchange_rate: Optional[float] = None  # 적용된 환율 (USD/KRW)
    equity_curve: Optional[List[Dict[str, Any]]] = None  # 자산 곡선 (날짜, 자산)
    price_data: Optional[List[Dict[str, Any]]] = None  # 가격 데이터 (날짜, 종가)


class SampleInfo(BaseModel):
    n_signals: int
    period: Dict[str, str]


class AnalysisResponse(BaseModel):
    summary: str
    universe_checked: Dict[str, int]
    sample_info: SampleInfo
    prediction: Prediction
    backtest: Backtest
    monte_carlo: MonteCarloResult
    signal_examples: List[SignalExample]
    limitations: List[str]



