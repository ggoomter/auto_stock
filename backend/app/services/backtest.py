"""
Backtesting engine for rule-based strategies with realistic execution and risk controls.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

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
    """Backtest execution engine with risk guardrails."""

    def __init__(
        self,
        data: pd.DataFrame,
        entry_signals: pd.Series,
        exit_signals: pd.Series,
        risk_params: RiskParams,
        transaction_cost_bps: int = 10,
        slippage_bps: int = 5,
        initial_capital: float = 100000.0,
        is_korean_stock: bool = False,
    ) -> None:
        if data.empty:
            raise ValueError("Price data is empty.")

        self.data = data.sort_index().copy()
        self.entry_signals = entry_signals.reindex(self.data.index, fill_value=False).astype(bool)
        self.exit_signals = exit_signals.reindex(self.data.index, fill_value=False).astype(bool)
        self.risk_params = risk_params
        self.transaction_cost = transaction_cost_bps / 10000.0
        self.slippage = slippage_bps / 10000.0
        self.initial_capital = float(initial_capital)
        self.is_korean_stock = is_korean_stock

        (
            self.close_col,
            self.open_col,
            self.high_col,
            self.low_col,
        ) = self._resolve_price_columns(self.data)

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
            "Backtest started for period %s → %s",
            self.data.index[0].date(),
            self.data.index[-1].date(),
        )

        cash = float(self.initial_capital)
        equity = float(self.initial_capital)
        previous_equity = equity

        position: Optional[Dict[str, Any]] = None
        pending_entry_idx: Optional[int] = None
        pending_entry_fraction: float = 0.0
        pending_exit_idx: Optional[int] = None
        cooldown = 0
        consecutive_losses = 0
        max_consecutive_losses_observed = 0
        trading_halted = False
        halt_reason: Optional[str] = None
        scale_down_active = False
        size_multiplier = 1.0

        equity_history: List[float] = []
        self.daily_returns = []

        drawdown_halt_level = self.initial_capital * (1 - self.risk_params.max_portfolio_drawdown_pct)
        scale_down_level = self.initial_capital * (1 - self.risk_params.scale_down_after_drawdown_pct)

        dates = self.data.index

        for i, date in enumerate(dates):
            row = self.data.iloc[i]
            open_price = float(row[self.open_col])
            high_price = float(row[self.high_col])
            low_price = float(row[self.low_col])
            close_price = float(row[self.close_col])

            if any(pd.isna(v) for v in (open_price, high_price, low_price, close_price)):
                warning = f"{date.date()} skipped due to missing OHLC data."
                self.warnings.append(warning)
                equity_history.append(equity)
                self.daily_returns.append(0.0)
                continue

            if not trading_halted and equity <= drawdown_halt_level:
                trading_halted = True
                halt_reason = (
                    f"Trading halted on {date.date()} after reaching max drawdown "
                    f"{1 - equity / self.initial_capital:.2%}."
                )
                self.warnings.append(halt_reason)

            if position and pending_exit_idx == i:
                exit_price = self._execute_exit_price(open_price)
                cash, equity, pnl, pnl_pct = self._close_position(position, exit_price, date, "exit_signal_open", cash)
                position = None
                pending_exit_idx = None
                if pnl <= 0 and self.risk_params.cooldown_days_after_loss > 0:
                    cooldown = max(cooldown, self.risk_params.cooldown_days_after_loss)
                consecutive_losses = 0 if pnl > 0 else consecutive_losses + 1
                max_consecutive_losses_observed = max(max_consecutive_losses_observed, consecutive_losses)

            if position is None and pending_entry_idx == i and not trading_halted and cooldown == 0:
                entry_price = self._execute_entry_price(open_price)
                shares, capital_used, _ = self._determine_shares(
                    cash,
                    equity,
                    entry_price,
                    pending_entry_fraction,
                    size_multiplier,
                )
                if shares > 0:
                    position = {
                        "shares": shares,
                        "entry_price": entry_price,
                        "entry_date": date,
                        "stop_loss": entry_price * (1 - self.risk_params.stop_pct),
                        "take_profit": entry_price * (1 + self.risk_params.take_pct),
                        "highest_price": entry_price,
                        "invested_capital": capital_used,
                        "pending_exit": False,
                        "partial_flags": {rule["flag"]: False for rule in self.partial_rules},
                    }
                    cash -= capital_used
                    logger.info(
                        "Entered position on %s @ %.2f (%s shares)",
                        date.strftime("%Y-%m-%d"),
                        entry_price,
                        shares,
                    )
                else:
                    self.warnings.append(
                        f"{date.date()} entry skipped (capital or risk budget insufficient)."
                    )
                pending_entry_idx = None

            if position:
                if high_price > position["highest_price"]:
                    position["highest_price"] = high_price

                trailing_stop = position["highest_price"] * (1 - self.risk_params.trailing_pct)
                if trailing_stop > position["stop_loss"]:
                    position["stop_loss"] = trailing_stop

                closed_by_partial, cash, equity = self._evaluate_partial_exits(
                    position,
                    high_price,
                    close_price,
                    date,
                    cash,
                )
                if closed_by_partial:
                    position = None
                    pending_exit_idx = None
                else:
                    exit_triggered = False
                    exit_reason = ""
                    exit_price_level = 0.0

                    if low_price <= position["stop_loss"]:
                        exit_triggered = True
                        exit_reason = "stop_loss"
                        exit_price_level = position["stop_loss"]
                    elif high_price >= position["take_profit"]:
                        exit_triggered = True
                        exit_reason = "take_profit"
                        exit_price_level = position["take_profit"]

                    if exit_triggered:
                        execution_price = self._execute_exit_price(exit_price_level)
                        cash, equity, pnl, pnl_pct = self._close_position(
                            position,
                            execution_price,
                            date,
                            exit_reason,
                            cash,
                        )
                        position = None
                        pending_exit_idx = None
                        if pnl <= 0 and self.risk_params.cooldown_days_after_loss > 0:
                            cooldown = max(cooldown, self.risk_params.cooldown_days_after_loss)
                        consecutive_losses = 0 if pnl > 0 else consecutive_losses + 1
                        max_consecutive_losses_observed = max(max_consecutive_losses_observed, consecutive_losses)
                    else:
                        equity = cash + position["shares"] * close_price
            else:
                equity = cash

            if position and not pending_exit_idx and self.exit_signals.iloc[i] and i + 1 < len(dates):
                pending_exit_idx = i + 1
                position["pending_exit"] = True

            if (
                position is None
                and pending_entry_idx is None
                and not trading_halted
                and cooldown == 0
                and i + 1 < len(dates)
                and self.entry_signals.iloc[i]
            ):
                position_fraction = self._calculate_position_size(equity, close_price, self.data.iloc[: i + 1])
                pending_entry_idx = i + 1
                pending_entry_fraction = max(0.0, min(1.0, position_fraction))

            daily_return = (equity - previous_equity) / previous_equity if previous_equity else 0.0
            self.daily_returns.append(float(daily_return))
            equity_history.append(equity)
            previous_equity = equity

            if (
                daily_return <= -self.risk_params.daily_loss_limit_pct
                and self.risk_params.cooldown_days_after_loss > 0
            ):
                cooldown = max(cooldown, self.risk_params.cooldown_days_after_loss)
                self.warnings.append(
                    f"{date.date()} daily loss {daily_return:.2%} breached limit "
                    f"{self.risk_params.daily_loss_limit_pct:.2%}; applying cooldown."
                )

            if (
                not scale_down_active
                and self.risk_params.scale_down_after_drawdown_pct > 0
                and equity <= scale_down_level
            ):
                scale_down_active = True
                size_multiplier = self.risk_params.scale_down_factor
                self.warnings.append(
                    f"Position sizing scaled to {size_multiplier:.0%} after reaching drawdown buffer on {date.date()}."
                )

            if (
                consecutive_losses >= self.risk_params.max_consecutive_losses
                and self.risk_params.max_consecutive_losses > 0
            ):
                if self.risk_params.cooldown_days_after_loss > 0:
                    cooldown = max(cooldown, self.risk_params.cooldown_days_after_loss)
                self.warnings.append(
                    f"{date.date()} consecutive loss limit reached; triggering cooldown."
                )
                consecutive_losses = 0

            if cooldown > 0:
                cooldown -= 1

        if position:
            final_close = float(self.data.iloc[-1][self.close_col])
            execution_price = self._execute_exit_price(final_close)
            cash, equity, pnl, pnl_pct = self._close_position(
                position,
                execution_price,
                dates[-1],
                "final_exit",
                cash,
            )
            consecutive_losses = 0 if pnl > 0 else consecutive_losses + 1
            max_consecutive_losses_observed = max(max_consecutive_losses_observed, consecutive_losses)
            position = None
            equity_history[-1] = equity

        self.equity_curve = pd.Series(equity_history, index=dates)
        metrics = self._calculate_metrics(self.initial_capital, self.daily_returns)
        self.risk_summary = self._build_risk_summary(
            metrics,
            max_consecutive_losses_observed,
            trading_halted,
            halt_reason,
        )
        return metrics, self.equity_curve, self.risk_summary

    def _evaluate_partial_exits(
        self,
        position: Dict[str, Any],
        intraday_high: float,
        close_price: float,
        date: pd.Timestamp,
        cash: float,
    ) -> Tuple[bool, float, float]:
        closed = False
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
                cash += proceeds
                pnl = (exit_price - position["entry_price"]) * shares_to_exit
                pnl_pct = (exit_price / position["entry_price"]) - 1 if position["entry_price"] else 0.0
                trade = {
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
                }
                self.trades.append(trade)
                position["shares"] -= shares_to_exit
                position["invested_capital"] = max(
                    0.0,
                    position["invested_capital"] - shares_to_exit * position["entry_price"],
                )
                position["partial_flags"][rule["flag"]] = True
                logger.info(
                    "Partial exit %s on %s: sold %s shares @ %.2f",
                    rule["flag"],
                    date.strftime("%Y-%m-%d"),
                    shares_to_exit,
                    exit_price,
                )
                if position["shares"] <= 0:
                    closed = True
                    break
        equity = cash if closed else cash + position["shares"] * close_price
        return closed, cash, equity

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
            logger.debug("Position sizing equal_weight -> 100%%")
            return 1.0
        if self.risk_params.position_sizing == "vol_target_10":
            if "VOL_annualized" in historical_data.columns:
                current_vol = historical_data["VOL_annualized"].iloc[-1]
                if current_vol > 0:
                    target_vol = 0.10
                    size = min(target_vol / current_vol, 1.0)
                    logger.debug("Position sizing vol_target_10 (vol %.2f) -> %.2f", current_vol, size)
                    return float(size)
            logger.debug("Position sizing vol_target_10 fallback -> 100%%")
            return 1.0
        if self.risk_params.position_sizing == "kelly":
            if len(self.trades) >= 10:
                wins = [t for t in self.trades if t.get("pnl", 0) > 0]
                win_rate = len(wins) / len(self.trades) if self.trades else 0.0
                avg_win = np.mean([t["pnl_pct"] for t in wins]) if wins else 0.0
                avg_loss = np.mean([abs(t["pnl_pct"]) for t in self.trades if t.get("pnl", 0) <= 0]) or 0.0
                if avg_loss > 0 and avg_win > 0:
                    kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
                    size = max(0.0, min(kelly * 0.5, 1.0))
                    logger.debug("Position sizing kelly -> %.2f", size)
                    return float(size)
            logger.debug("Position sizing kelly fallback -> 100%%")
            return 1.0
        logger.debug("Unknown position sizing -> default 100%%")
        return 1.0

    def _close_position(
        self,
        position: Dict[str, Any],
        exit_price: float,
        exit_date: pd.Timestamp,
        exit_reason: str,
        cash: float,
    ) -> Tuple[float, float, float, float]:
        shares = position.get("shares", 0)
        if shares <= 0:
            return cash, cash, 0.0, 0.0
        proceeds = exit_price * shares
        cash += proceeds
        pnl = (exit_price - position["entry_price"]) * shares
        pnl_pct = (exit_price / position["entry_price"]) - 1 if position["entry_price"] else 0.0
        trade = {
            "entry_date": position["entry_date"],
            "exit_date": exit_date,
            "entry_price": position["entry_price"],
            "exit_price": exit_price,
            "shares": shares,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "exit_reason": exit_reason,
            "holding_days": _holding_days(position["entry_date"], exit_date),
            "partial": False,
        }
        self.trades.append(trade)
        equity = cash
        logger.info(
            "Exit %s on %s @ %.2f (%s shares, PnL %s)",
            exit_reason,
            exit_date.strftime("%Y-%m-%d"),
            exit_price,
            shares,
            f"{pnl:+.0f}",
        )
        return cash, equity, pnl, pnl_pct

    def _calculate_metrics(self, initial_capital: float, daily_returns: List[float]) -> BacktestMetrics:
        if not self.trades or self.equity_curve is None or self.equity_curve.empty:
            return BacktestMetrics(
                CAGR=0.0,
                Sharpe=0.0,
                MaxDD=0.0,
                HitRatio=0.0,
                AvgWin=0.0,
                AvgLoss=0.0,
                TotalTrades=len(self.trades),
                WinTrades=0,
                LossTrades=0,
            )

        total_return = (self.equity_curve.iloc[-1] / initial_capital) - 1
        period_days = (self.data.index[-1] - self.data.index[0]).days
        years = period_days / 365.25 if period_days > 0 else 0.0
        cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 else total_return

        returns_series = pd.Series(daily_returns).replace([np.inf, -np.inf], np.nan).dropna()
        if returns_series.empty:
            sharpe = 0.0
        else:
            excess = returns_series - (self.risk_params.risk_free_rate / 252.0)
            sharpe = float(excess.mean() / excess.std() * np.sqrt(252)) if excess.std() > 0 else 0.0

        drawdown = (self.equity_curve / self.equity_curve.cummax()) - 1
        max_dd = float(drawdown.min()) if not drawdown.empty else 0.0

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
                raise ValueError(f"'{base}' column not found. Available columns: {list(df.columns)}")
        return mapping["close"], mapping["open"], mapping["high"], mapping["low"]

    def get_trade_details(self) -> pd.DataFrame:
        if not self.trades:
            return pd.DataFrame()
        df = pd.DataFrame(self.trades)
        if not df.empty:
            df["entry_date"] = pd.to_datetime(df["entry_date"])
            df["exit_date"] = pd.to_datetime(df["exit_date"])
        return df


