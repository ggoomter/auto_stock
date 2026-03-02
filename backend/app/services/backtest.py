"""
규칙 기반 전략을 위한 현실적인 실행 및 리스크 제어 기능을 갖춘 백테스팅 엔진.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from ..core.logging_config import logger
from ..models.schemas import BacktestMetrics, RiskParams
from ..utils.tick_size import round_to_tick_down, round_to_tick_up


def _holding_days(entry_date: pd.Timestamp, exit_date: pd.Timestamp) -> int:
    try:
        return int((exit_date - entry_date).days)
    except Exception:
        return 0


class BacktestEngine:
    """리스크 가드레일이 포함된 백테스트 실행 엔진."""

    def __init__(
        self,
        data: Union[pd.DataFrame, Dict[str, pd.DataFrame]],
        entry_signals: Union[pd.Series, Dict[str, pd.Series]],
        exit_signals: Union[pd.Series, Dict[str, pd.Series]],
        risk_params: RiskParams,
        transaction_cost_bps: int = 10,
        slippage_bps: int = 5,
        initial_capital: float = 100000.0,
        is_korean_stock: bool = False,
    ) -> None:
        # 단일 종목일 경우 딕셔너리로 변환하여 통일된 처리
        if isinstance(data, pd.DataFrame):
            self.data = {"DEFAULT": data.sort_index().copy()}
            self.entry_signals = {"DEFAULT": entry_signals.reindex(data.index, fill_value=False).astype(bool)}
            self.exit_signals = {"DEFAULT": exit_signals.reindex(data.index, fill_value=False).astype(bool)}
        else:
            self.data = {k: v.sort_index().copy() for k, v in data.items()}
            self.entry_signals = {k: v.reindex(self.data[k].index, fill_value=False).astype(bool) for k, v in entry_signals.items()}
            self.exit_signals = {k: v.reindex(self.data[k].index, fill_value=False).astype(bool) for k, v in exit_signals.items()}

        if not self.data:
            raise ValueError("가격 데이터가 비어있습니다.")

        self.risk_params = risk_params
        self.transaction_cost = transaction_cost_bps / 10000.0
        self.slippage = slippage_bps / 10000.0
        self.initial_capital = float(initial_capital)
        self.is_korean_stock = is_korean_stock

        # 모든 종목의 날짜 합집합 생성 (전체 타임라인)
        all_dates = sorted(list(set().union(*[df.index for df in self.data.values()])))
        self.dates = pd.DatetimeIndex(all_dates)

        self.trades: List[Dict[str, Any]] = []
        self.equity_curve: Optional[pd.Series] = None
        self.daily_returns: List[float] = []
        self.risk_summary: Dict[str, Any] = {}
        self.warnings: List[str] = []

        self.partial_rules = [
            {"threshold": 0.20, "sell_pct": 0.50, "flag": "partial_20"},
            {"threshold": 0.40, "sell_pct": 0.25, "flag": "partial_40"},
        ]

    def run(self) -> Tuple[BacktestMetrics, pd.Series, Dict[str, Any]]:
        logger.info(
            "백테스트 시작: %s → %s",
            self.dates[0].date(),
            self.dates[-1].date(),
        )

        cash = float(self.initial_capital)
        equity = float(self.initial_capital)
        previous_equity = equity

        # 포트폴리오 상태 관리: {symbol: position_dict}
        positions: Dict[str, Dict[str, Any]] = {}
        
        # 각 종목별 상태
        pending_entries: Dict[str, Dict[str, Any]] = {} # {symbol: {idx, fraction}}
        pending_exits: Dict[str, int] = {} # {symbol: idx}
        cooldowns: Dict[str, int] = {sym: 0 for sym in self.data.keys()}
        consecutive_losses: Dict[str, int] = {sym: 0 for sym in self.data.keys()}
        
        max_consecutive_losses_observed = 0
        trading_halted = False
        halt_reason: Optional[str] = None
        scale_down_active = False
        size_multiplier = 1.0

        equity_history: List[float] = []
        self.daily_returns = []

        drawdown_halt_level = self.initial_capital * (1 - self.risk_params.max_portfolio_drawdown_pct)
        scale_down_level = self.initial_capital * (1 - self.risk_params.scale_down_after_drawdown_pct)

        # 컬럼 매핑 캐싱
        col_maps = {sym: self._resolve_price_columns(df) for sym, df in self.data.items()}

        for current_date in self.dates:
            # 1. 현재 자산 평가 (Mark to Market)
            portfolio_value = 0.0
            for sym, pos in positions.items():
                # 해당 날짜의 종가가 있으면 업데이트, 없으면 이전 가치 유지 (또는 0)
                # 여기서는 간단히 해당 날짜 데이터가 없으면 이전 종가(pos에 저장된)를 사용한다고 가정하거나
                # 데이터가 있는 경우에만 업데이트.
                if current_date in self.data[sym].index:
                    row = self.data[sym].loc[current_date]
                    close_col = col_maps[sym][0]
                    current_price = float(row[close_col])
                    portfolio_value += pos["shares"] * current_price
                else:
                    # 데이터가 없는 날(휴장일 등)은 직전 평가액 유지
                    # 정확한 처리를 위해선 forward fill된 데이터가 필요하지만,
                    # 여기서는 entry_price 등으로 추정하기보다 직전 루프의 가격을 저장해두는 것이 좋음.
                    # 편의상 현재는 보수적으로 진입가 또는 직전 평가가 사용
                    # (실제로는 데이터 전처리가 되어있어야 함)
                    pass 
            
            # 정확한 일별 Equity 계산을 위해, 데이터가 있는 종목만 업데이트하고 나머지는 유지해야 함.
            # 하지만 구조상 loop 안에서 처리하므로, 아래 로직에서 개별 종목 처리 후 합산.
            
            daily_equity = cash
            for sym, pos in positions.items():
                if current_date in self.data[sym].index:
                    row = self.data[sym].loc[current_date]
                    close_col = col_maps[sym][0]
                    price = float(row[close_col])
                    daily_equity += pos["shares"] * price
                else:
                    # 데이터 없는 날은 이전 가격 기준 가치 (대략적)
                    # pos에 'last_price'를 저장해두면 좋음
                    daily_equity += pos["shares"] * pos.get("last_close", pos["entry_price"])

            equity = daily_equity
            
            # 2. 리스크 체크 (Drawdown)
            if not trading_halted and equity <= drawdown_halt_level:
                trading_halted = True
                halt_reason = (
                    f"{current_date.date()} 최대 낙폭 도달로 거래 중지 "
                    f"{1 - equity / self.initial_capital:.2%}."
                )
                self.warnings.append(halt_reason)

            if (
                not scale_down_active
                and self.risk_params.scale_down_after_drawdown_pct > 0
                and equity <= scale_down_level
            ):
                scale_down_active = True
                size_multiplier = self.risk_params.scale_down_factor
                self.warnings.append(
                    f"{current_date.date()} 낙폭 버퍼 도달로 포지션 크기 축소 ({size_multiplier:.0%})."
                )

            # 3. 종목별 로직 수행
            for sym in self.data.keys():
                if current_date not in self.data[sym].index:
                    continue

                row = self.data[sym].loc[current_date]
                close_col, open_col, high_col, low_col = col_maps[sym]
                
                open_price = float(row[open_col])
                high_price = float(row[high_col])
                low_price = float(row[low_col])
                close_price = float(row[close_col])

                if any(pd.isna(v) for v in (open_price, high_price, low_price, close_price)):
                    continue

                # 쿨다운 감소
                if cooldowns[sym] > 0:
                    cooldowns[sym] -= 1

                # --- 포지션 청산 (Exit) ---
                if sym in positions:
                    pos = positions[sym]
                    pos["last_close"] = close_price # 평가용 업데이트

                    # 고가 갱신 (트레일링 스탑용)
                    if high_price > pos["highest_price"]:
                        pos["highest_price"] = high_price

                    # 트레일링 스탑 업데이트
                    trailing_stop = pos["highest_price"] * (1 - self.risk_params.trailing_pct)
                    if trailing_stop > pos["stop_loss"]:
                        pos["stop_loss"] = trailing_stop

                    # 1) 시그널에 의한 청산 (Pending Exit)
                    if sym in pending_exits:
                        exit_price = self._execute_exit_price(open_price)
                        cash, pnl, pnl_pct = self._close_position_logic(pos, exit_price, current_date, "exit_signal_open")
                        
                        self._record_trade(sym, pos, exit_price, current_date, "exit_signal_open", pnl, pnl_pct, cash + self._get_positions_value(positions, sym)) # 잔고는 근사치
                        
                        del positions[sym]
                        del pending_exits[sym]
                        
                        if pnl <= 0 and self.risk_params.cooldown_days_after_loss > 0:
                            cooldowns[sym] = max(cooldowns[sym], self.risk_params.cooldown_days_after_loss)
                        consecutive_losses[sym] = 0 if pnl > 0 else consecutive_losses[sym] + 1
                        max_consecutive_losses_observed = max(max_consecutive_losses_observed, consecutive_losses[sym])
                        continue # 포지션 청산했으므로 다음 종목으로

                    # 2) 부분 청산 (Partial Exit)
                    closed_by_partial, cash_proceeds = self._evaluate_partial_exits(
                        sym, pos, high_price, current_date
                    )
                    cash += cash_proceeds
                    if closed_by_partial:
                        del positions[sym]
                        if sym in pending_exits: del pending_exits[sym]
                        continue

                    # 3) 손절/익절 (Stop Loss / Take Profit)
                    exit_triggered = False
                    exit_reason = ""
                    exit_price_level = 0.0

                    if low_price <= pos["stop_loss"]:
                        exit_triggered = True
                        exit_reason = "stop_loss"
                        exit_price_level = pos["stop_loss"]
                    elif high_price >= pos["take_profit"]:
                        exit_triggered = True
                        exit_reason = "take_profit"
                        exit_price_level = pos["take_profit"]

                    if exit_triggered:
                        execution_price = self._execute_exit_price(exit_price_level)
                        cash, pnl, pnl_pct = self._close_position_logic(pos, execution_price, current_date, exit_reason)
                        
                        self._record_trade(sym, pos, execution_price, current_date, exit_reason, pnl, pnl_pct, cash + self._get_positions_value(positions, sym))
                        
                        del positions[sym]
                        if sym in pending_exits: del pending_exits[sym]

                        if pnl <= 0 and self.risk_params.cooldown_days_after_loss > 0:
                            cooldowns[sym] = max(cooldowns[sym], self.risk_params.cooldown_days_after_loss)
                        consecutive_losses[sym] = 0 if pnl > 0 else consecutive_losses[sym] + 1
                        max_consecutive_losses_observed = max(max_consecutive_losses_observed, consecutive_losses[sym])
                        continue

                # --- 포지션 진입 (Entry) ---
                # 포지션이 없고, 진입 대기 중이며, 거래 중지가 아니고, 쿨다운이 없을 때
                if (sym not in positions) and (sym in pending_entries) and (not trading_halted) and (cooldowns[sym] == 0):
                    entry_info = pending_entries[sym]
                    entry_price = self._execute_entry_price(open_price)
                    
                    shares, capital_used, _ = self._determine_shares(
                        cash,
                        equity,
                        entry_price,
                        entry_info["fraction"],
                        size_multiplier,
                    )

                    if shares > 0:
                        positions[sym] = {
                            "shares": shares,
                            "entry_price": entry_price,
                            "entry_date": current_date,
                            "stop_loss": entry_price * (1 - self.risk_params.stop_pct),
                            "take_profit": entry_price * (1 + self.risk_params.take_pct),
                            "highest_price": entry_price,
                            "invested_capital": capital_used,
                            "last_close": close_price,
                            "partial_flags": {rule["flag"]: False for rule in self.partial_rules},
                        }
                        cash -= capital_used
                        logger.info(
                            "[%s] 포지션 진입 %s @ %.2f (%s주)",
                            sym,
                            current_date.strftime("%Y-%m-%d"),
                            entry_price,
                            shares,
                        )
                    else:
                        # 자금 부족 등으로 진입 실패 시 경고
                        # self.warnings.append(f"{current_date.date()} {sym} 진입 실패 (자금 부족).")
                        pass
                    
                    del pending_entries[sym]

                # --- 시그널 확인 (다음 날을 위한) ---
                # 현재 포지션이 있고, 아직 청산 대기가 없으며, 오늘 청산 신호가 떴다면 -> 내일 시가 청산 예약
                if sym in positions and sym not in pending_exits:
                    if self.exit_signals[sym].get(current_date, False):
                        pending_exits[sym] = True # 값은 중요하지 않음

                # 현재 포지션이 없고, 진입 대기도 없으며, 쿨다운/중지 아님, 오늘 진입 신호 -> 내일 시가 진입 예약
                if (sym not in positions) and (sym not in pending_entries) and (not trading_halted) and (cooldowns[sym] == 0):
                    if self.entry_signals[sym].get(current_date, False):
                        # 포지션 사이징 계산
                        position_fraction = self._calculate_position_size(equity, close_price, self.data[sym].loc[:current_date])
                        pending_entries[sym] = {
                            "fraction": max(0.0, min(1.0, position_fraction))
                        }

            # 일별 수익률 기록
            daily_return = (equity - previous_equity) / previous_equity if previous_equity else 0.0
            self.daily_returns.append(float(daily_return))
            equity_history.append(equity)
            previous_equity = equity

            # 일일 손실 한도 체크 (전체 포트폴리오 기준)
            if (
                daily_return <= -self.risk_params.daily_loss_limit_pct
                and self.risk_params.cooldown_days_after_loss > 0
            ):
                # 전체 쿨다운을 걸거나, 경고만? 여기서는 경고만 추가
                self.warnings.append(
                    f"{current_date.date()} 일일 손실 {daily_return:.2%} 한도 초과."
                )

        # 마지막 날 강제 청산 (평가용)
        final_date = self.dates[-1]
        for sym, pos in list(positions.items()):
            if final_date in self.data[sym].index:
                final_close = float(self.data[sym].loc[final_date][col_maps[sym][0]])
            else:
                final_close = pos["last_close"]
                
            execution_price = self._execute_exit_price(final_close)
            cash, pnl, pnl_pct = self._close_position_logic(pos, execution_price, final_date, "final_exit")
            self._record_trade(sym, pos, execution_price, final_date, "final_exit", pnl, pnl_pct, cash)
            del positions[sym]

        self.equity_curve = pd.Series(equity_history, index=self.dates)
        metrics = self._calculate_metrics(self.initial_capital, self.daily_returns)
        self.risk_summary = self._build_risk_summary(
            metrics,
            max_consecutive_losses_observed,
            trading_halted,
            halt_reason,
        )
        return metrics, self.equity_curve, self.risk_summary

    def _get_positions_value(self, positions: Dict[str, Any], exclude_sym: str = None) -> float:
        val = 0.0
        for sym, pos in positions.items():
            if sym == exclude_sym: continue
            val += pos["shares"] * pos["last_close"]
        return val

    def _close_position_logic(self, position: Dict[str, Any], exit_price: float, date: pd.Timestamp, reason: str) -> Tuple[float, float, float]:
        shares = position["shares"]
        proceeds = exit_price * shares
        pnl = (exit_price - position["entry_price"]) * shares
        pnl_pct = (exit_price / position["entry_price"]) - 1 if position["entry_price"] else 0.0
        return proceeds, pnl, pnl_pct # cash는 외부에서 더함

    def _record_trade(self, symbol: str, position: Dict[str, Any], exit_price: float, exit_date: pd.Timestamp, reason: str, pnl: float, pnl_pct: float, balance_after: float):
        trade = {
            "symbol": symbol,
            "entry_date": position["entry_date"],
            "exit_date": exit_date,
            "entry_price": position["entry_price"],
            "exit_price": exit_price,
            "shares": position["shares"],
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "exit_reason": reason,
            "holding_days": _holding_days(position["entry_date"], exit_date),
            "partial": False,
            "balance_after": balance_after,
        }
        self.trades.append(trade)
        logger.info(
            "[%s] 청산 %s @ %.2f (PnL %s)",
            symbol,
            reason,
            exit_price,
            f"{pnl:+.0f}",
        )

    def _evaluate_partial_exits(
        self,
        symbol: str,
        position: Dict[str, Any],
        intraday_high: float,
        date: pd.Timestamp,
    ) -> Tuple[bool, float]:
        closed = False
        total_proceeds = 0.0
        
        for rule in self.partial_rules:
            if position["partial_flags"].get(rule["flag"], False):
                continue
            target_price = position["entry_price"] * (1 + rule["threshold"])
            if intraday_high >= target_price:
                shares_to_exit = position["shares"] * rule["sell_pct"]
                shares_to_exit = int(shares_to_exit) if self.is_korean_stock else math.floor(shares_to_exit)
                if shares_to_exit <= 0:
                    position["partial_flags"][rule["flag"]] = True
                    continue
                
                exit_price = self._execute_exit_price(target_price)
                proceeds = exit_price * shares_to_exit
                total_proceeds += proceeds
                
                pnl = (exit_price - position["entry_price"]) * shares_to_exit
                pnl_pct = (exit_price / position["entry_price"]) - 1 if position["entry_price"] else 0.0
                
                trade = {
                    "symbol": symbol,
                    "entry_date": position["entry_date"],
                    "exit_date": date,
                    "entry_price": position["entry_price"],
                    "exit_price": exit_price,
                    "shares": shares_to_exit,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "exit_reason": rule["flag"],
                    "holding_days": _holding_days(position["entry_date"], date),
                    "partial": True,
                    "balance_after": 0.0, # 부분 청산 시 잔고 계산 복잡하므로 생략 혹은 추후 개선
                }
                self.trades.append(trade)
                
                position["shares"] -= shares_to_exit
                position["invested_capital"] = max(
                    0.0,
                    position["invested_capital"] - shares_to_exit * position["entry_price"],
                )
                position["partial_flags"][rule["flag"]] = True
                
                logger.info(
                    "[%s] 부분 청산 %s @ %.2f (%s주)",
                    symbol,
                    rule["flag"],
                    exit_price,
                    shares_to_exit,
                )
                
                if position["shares"] <= 0:
                    closed = True
                    break
                    
        return closed, total_proceeds

    def _determine_shares(
        self,
        cash: float,
        equity: float,
        entry_price: float,
        position_fraction: float,
        size_multiplier: float,
    ) -> Tuple[int, float, float]:
        if entry_price <= 0:
            return 0, 0.0, 0.0
        capital_budget = equity * position_fraction * size_multiplier
        capital_budget = min(capital_budget, cash)
        risk_per_share = entry_price * self.risk_params.stop_pct
        risk_budget = equity * self.risk_params.max_risk_per_trade_pct * size_multiplier
        shares_by_capital = capital_budget / entry_price if entry_price else 0.0
        shares_by_risk = risk_budget / risk_per_share if risk_per_share > 0 else shares_by_capital
        shares_by_cash = cash / entry_price
        shares = min(shares_by_capital, shares_by_risk, shares_by_cash)
        shares = int(math.floor(shares))
        if shares <= 0:
            return 0, 0.0, risk_per_share
        capital_used = shares * entry_price
        return shares, capital_used, risk_per_share

    def _execute_entry_price(self, price: float) -> float:
        adjusted = price * (1 + self.slippage)
        adjusted *= (1 + self.transaction_cost)
        return round_to_tick_up(adjusted, self.is_korean_stock)

    def _execute_exit_price(self, price: float) -> float:
        adjusted = price * (1 - self.slippage)
        adjusted *= (1 - self.transaction_cost)
        return round_to_tick_down(adjusted, self.is_korean_stock)

    def _calculate_position_size(
        self,
        equity: float,
        price: float,
        historical_data: pd.DataFrame,
    ) -> float:
        if self.risk_params.position_sizing == "equal_weight":
            return 1.0 # 기본적으로 100%가 아니라, 호출하는 쪽에서 1/N 등을 고려해야 함. 여기서는 단일 종목 비중.
            # 포트폴리오 레벨에서는 N개 종목이면 1/N이 되어야 함.
            # 현재 구조상 외부에서 fraction을 제어하거나 여기서 하드코딩해야 함.
            # 일단 1.0으로 두고 determine_shares에서 cash 제한을 받도록 함.
        
        if self.risk_params.position_sizing == "vol_target_10":
            if "VOL_annualized" in historical_data.columns:
                current_vol = historical_data["VOL_annualized"].iloc[-1]
                if current_vol > 0:
                    target_vol = 0.10
                    size = min(target_vol / current_vol, 1.0)
                    return float(size)
            return 1.0
            
        if self.risk_params.position_sizing == "kelly":
            # 켈리 공식은 승률과 손익비가 필요함. 초기에는 데이터가 없으므로 1.0
            if len(self.trades) >= 10:
                wins = [t for t in self.trades if t.get("pnl", 0) > 0]
                win_rate = len(wins) / len(self.trades) if self.trades else 0.0
                avg_win = np.mean([t["pnl_pct"] for t in wins]) if wins else 0.0
                avg_loss = np.mean([abs(t["pnl_pct"]) for t in self.trades if t.get("pnl", 0) <= 0]) or 0.0
                if avg_loss > 0 and avg_win > 0:
                    kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
                    size = max(0.0, min(kelly * 0.5, 1.0)) # 하프 켈리
                    return float(size)
            return 1.0
            
        return 1.0

    def _calculate_metrics(self, initial_capital: float, daily_returns: List[float]) -> BacktestMetrics:
        if not self.trades or self.equity_curve is None or self.equity_curve.empty:
            return BacktestMetrics(
                CAGR=0.0, Sharpe=0.0, MaxDD=0.0, HitRatio=0.0,
                AvgWin=0.0, AvgLoss=0.0, TotalTrades=len(self.trades),
                WinTrades=0, LossTrades=0,
                Sortino=0.0, Calmar=0.0, TailRatio=0.0 # New Metrics
            )

        total_return = (self.equity_curve.iloc[-1] / initial_capital) - 1
        period_days = (self.dates[-1] - self.dates[0]).days
        years = period_days / 365.25 if period_days > 0 else 0.0
        
        # CAGR 계산: 기간이 1년 미만이면 총 수익률을 연환산하지 않고 그대로 사용
        # (짧은 기간의 연환산은 부정확할 수 있음)
        if years < 1.0:
            # 1년 미만 기간은 총 수익률을 그대로 사용 (연환산하지 않음)
            cagr = total_return
        else:
            cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 else total_return

        returns_series = pd.Series(daily_returns).replace([np.inf, -np.inf], np.nan).dropna()
        
        # Sharpe Ratio
        if returns_series.empty:
            sharpe = 0.0
            sortino = 0.0
        else:
            excess = returns_series - (self.risk_params.risk_free_rate / 252.0)
            std_dev = excess.std()
            sharpe = float(excess.mean() / std_dev * np.sqrt(252)) if std_dev > 0 else 0.0
            
            # Sortino Ratio (Downside Deviation)
            downside_returns = returns_series[returns_series < 0]
            downside_std = downside_returns.std()
            sortino = float(excess.mean() / downside_std * np.sqrt(252)) if downside_std > 0 else 0.0

        # Max Drawdown
        drawdown = (self.equity_curve / self.equity_curve.cummax()) - 1
        max_dd = float(drawdown.min()) if not drawdown.empty else 0.0
        
        # Calmar Ratio (CAGR / MaxDD)
        calmar = abs(cagr / max_dd) if max_dd != 0 else 0.0

        # Tail Ratio (95th percentile / 5th percentile absolute)
        if not returns_series.empty:
            p95 = returns_series.quantile(0.95)
            p5 = abs(returns_series.quantile(0.05))
            tail_ratio = float(p95 / p5) if p5 != 0 else 0.0
        else:
            tail_ratio = 0.0

        wins = [t for t in self.trades if t["pnl"] > 0]
        losses = [t for t in self.trades if t["pnl"] <= 0]
        hit_ratio = len(wins) / len(self.trades) if self.trades else 0.0
        avg_win = float(np.mean([t["pnl_pct"] for t in wins])) if wins else 0.0
        avg_loss = float(np.mean([t["pnl_pct"] for t in losses])) if losses else 0.0

        return BacktestMetrics(
            CAGR=round(float(cagr), 4),
            Sharpe=round(float(sharpe), 2),
            MaxDD=round(float(max_dd), 4),
            HitRatio=round(float(hit_ratio), 2),
            AvgWin=round(float(avg_win), 4),
            AvgLoss=round(float(avg_loss), 4),
            TotalTrades=len(self.trades),
            WinTrades=len(wins),
            LossTrades=len(losses),
            Sortino=round(float(sortino), 2),
            Calmar=round(float(calmar), 2),
            TailRatio=round(float(tail_ratio), 2),
        )

    def _build_risk_summary(
        self,
        metrics: BacktestMetrics,
        max_consecutive_losses: int,
        trading_halted: bool,
        halt_reason: Optional[str],
    ) -> Dict[str, Any]:
        if self.equity_curve is None or self.equity_curve.empty:
            equity_series = pd.Series(dtype=float)
        else:
            equity_series = self.equity_curve
        drawdown = (equity_series / equity_series.cummax()) - 1 if not equity_series.empty else pd.Series(dtype=float)
        largest_loss_trade = min(self.trades, key=lambda t: t["pnl"], default=None)
        largest_loss_pct = min((t["pnl_pct"] for t in self.trades), default=0.0)
        summary = {
            "max_drawdown_pct": float(drawdown.min()) if not drawdown.empty else 0.0,
            "max_daily_loss_pct": float(min(self.daily_returns)) if self.daily_returns else 0.0,
            "max_consecutive_losses": int(max_consecutive_losses),
            "largest_loss_amount": float(largest_loss_trade["pnl"]) if largest_loss_trade else 0.0,
            "largest_loss_pct": float(largest_loss_pct),
            "total_trades": len(self.trades),
            "trading_halted": bool(trading_halted),
            "halt_reason": halt_reason,
            "warnings": self.warnings,
            "ending_equity": float(equity_series.iloc[-1]) if not equity_series.empty else float(self.initial_capital),
        }
        return summary

    def _resolve_price_columns(self, df: pd.DataFrame) -> Tuple[str, str, str, str]:
        mapping: Dict[str, Optional[str]] = {key: None for key in ("close", "open", "high", "low")}
        for base in mapping:
            for candidate in (base, base.capitalize(), base.upper()):
                if candidate in df.columns:
                    mapping[base] = candidate
                    break
            if mapping[base] is None:
                # Fallback: if OHLC not found, try to use Close for all or error
                # For robustness, if only Close exists, use it for all
                if base != "close" and mapping["close"]:
                     mapping[base] = mapping["close"]
                else:
                     raise ValueError(f"'{base}' 컬럼을 찾을 수 없습니다. 사용 가능 컬럼: {list(df.columns)}")
        return mapping["close"], mapping["open"], mapping["high"], mapping["low"]

    def get_trade_details(self) -> pd.DataFrame:
        if not self.trades:
            return pd.DataFrame()
        df = pd.DataFrame(self.trades)
        if not df.empty:
            df["entry_date"] = pd.to_datetime(df["entry_date"])
            df["exit_date"] = pd.to_datetime(df["exit_date"])
        return df
