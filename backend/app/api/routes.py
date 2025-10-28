"""
API 라우트: 분석 요청 처리
"""
from fastapi import APIRouter, HTTPException
from ..models.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    Prediction,
    Driver,
    Backtest,
    SampleInfo,
    SignalExample,
    MasterStrategyRequest,
    MasterStrategyResponse,
    MasterStrategyInfo
)
from typing import List, Optional
from pydantic import BaseModel
from ..services.parser import StrategyParser
from ..services.indicators import IndicatorCalculator, load_sample_data
from ..services.backtest import BacktestEngine
from ..services.monte_carlo import MonteCarloSimulator
from ..services.master_strategies import get_strategy, list_strategies
from ..services.fundamental_analysis import FundamentalAnalyzer
from ..services.exchange_rate import get_exchange_service
from ..core.logging_config import logger
import pandas as pd
import numpy as np

router = APIRouter()


def _normalize_numpy(value):
    # numpy.bool (deprecated but still used in some pandas versions)
    if hasattr(np, 'bool') and isinstance(value, np.bool):
        return bool(value)
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, np.int64, np.int32)):
        return int(value)
    if isinstance(value, (np.floating, np.float64, np.float32)):
        return float(value)
    if isinstance(value, dict):
        return {k: _normalize_numpy(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize_numpy(v) for v in value]
    return value


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_strategy(request: AnalysisRequest):
    """
    전략 분석 엔드포인트

    Args:
        request: 분석 요청 (심볼, 기간, 전략 등)

    Returns:
        분석 결과 (예측, 백테스트, 몬테카를로)
    """
    try:
        # 1. 데이터 로드 및 지표 계산
        all_data = {}
        for symbol in request.symbols:
            try:
                # 날짜를 문자열로 변환
                start_date = request.date_range.start if isinstance(request.date_range.start, str) else request.date_range.start.isoformat()
                end_date = request.date_range.end if isinstance(request.date_range.end, str) else request.date_range.end.isoformat()

                df = load_sample_data(symbol, start_date, end_date)
                df = IndicatorCalculator.calculate_all(df)
                all_data[symbol] = df
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"심볼 {symbol} 데이터 로드 실패: {str(e)}"
                )

        # 첫 번째 심볼로 분석 (간단 구현)
        symbol = request.symbols[0]
        data = all_data[symbol]

        # 2. 전략 파싱 및 시그널 생성
        try:
            parser = StrategyParser()
            entry_signals = parser.evaluate_condition(
                request.strategy.entry,
                data
            )
            exit_signals = parser.evaluate_condition(
                request.strategy.exit,
                data
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"전략 조건 파싱 실패: {str(e)}"
            )

        # 3. 백테스트 실행
        try:
            backtest_engine = BacktestEngine(
                data,
                entry_signals,
                exit_signals,
                request.strategy.risk,
                request.simulate.transaction_cost_bps,
                request.simulate.slippage_bps
            )
            metrics, equity_curve, risk_report = backtest_engine.run()
            equity_curve_payload = [
                {"date": idx.strftime("%Y-%m-%d"), "value": float(val)}
                for idx, val in equity_curve.items()
            ] if equity_curve is not None else []

            trade_history = []
            trade_df = backtest_engine.get_trade_details()
            if not trade_df.empty:
                for record in trade_df.to_dict("records"):
                    # Numpy 타입 변환
                    entry_price = float(record.get("entry_price", 0.0))
                    exit_price = float(record.get("exit_price", 0.0))
                    shares = float(record.get("shares", 0.0))
                    partial_val = record.get("partial", False)
                    # numpy.bool을 Python bool로 변환
                    partial = _normalize_numpy(partial_val)

                    trade_history.append({
                        "entry_date": pd.to_datetime(record.get("entry_date")).strftime("%Y-%m-%d"),
                        "exit_date": pd.to_datetime(record.get("exit_date")).strftime("%Y-%m-%d"),
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "shares": shares,
                        "position_value": entry_price * shares,
                        "pnl": float(record.get("pnl", 0.0)),
                        "pnl_pct": float(record.get("pnl_pct", 0.0)) * 100,
                        "exit_reason": record.get("exit_reason"),
                        "holding_days": int(record.get("holding_days", 0)),
                        "partial": partial,
                        "symbol": symbol,
                    })
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"백테스트 실행 실패: {str(e)}"
            )

        # 4. 몬테카를로 시뮬레이션
        mc_simulator = MonteCarloSimulator(
            data,
            entry_signals,
            exit_signals,
            request.strategy.risk,
            request.simulate.bootstrap_runs,
            request.simulate.transaction_cost_bps,
            request.simulate.slippage_bps
        )
        mc_result = mc_simulator.run()

        # 5. 예측 (조건부 확률)
        prediction = _calculate_prediction(
            data,
            entry_signals,
            request.horizon.lookahead_days,
            request.strategy.entry
        )

        # 6. 시그널 예시
        signal_examples = _get_signal_examples(
            data,
            entry_signals,
            symbol,
            request.strategy.entry,
            parser
        )

        # 7. 응답 구성
        response = AnalysisResponse(
            summary=f"{symbol} {request.date_range.start}~{request.date_range.end} 분석 완료",
            universe_checked={"US": 300, "KR": 300},
            sample_info=SampleInfo(
                n_signals=int(entry_signals.sum()),
                period={
                    "start": start_date,
                    "end": end_date
                }
            ),
            prediction=prediction,
            backtest=Backtest(
                metrics=metrics,
                cost_assumptions_bps={
                    "fee": request.simulate.transaction_cost_bps,
                    "slippage": request.simulate.slippage_bps
                },
                equity_curve_ref=None,
                equity_curve=equity_curve_payload,
                risk_summary=risk_report,
                warnings=risk_report.get("warnings") if isinstance(risk_report, dict) else None,
                trade_history=trade_history
            ),
            monte_carlo=mc_result,
            signal_examples=signal_examples,
            limitations=[
                "표본 편향: 과거 데이터 기반",
                "구간 최적화: 특정 기간에 과적합 가능",
                "이벤트 정의 민감도: 윈도우 크기에 따라 결과 변동"
            ]
        )

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _calculate_prediction(
    data: pd.DataFrame,
    entry_signals: pd.Series,
    lookahead_days: int,
    entry_condition: str
) -> Prediction:
    """조건부 확률 예측 계산"""

    # 컬럼명 확인 (대소문자 불일치 방지)
    close_col = None
    for col in ['close', 'Close', 'CLOSE']:
        if col in data.columns:
            close_col = col
            break

    if close_col is None:
        raise ValueError(f"'close' 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {list(data.columns)}")

    # 진입 시그널 발생 후 N일 수익률
    signal_dates = data[entry_signals].index
    future_returns = []

    for date in signal_dates:
        try:
            current_idx = data.index.get_loc(date)
            if current_idx + lookahead_days < len(data):
                current_price = data.iloc[current_idx][close_col]
                future_price = data.iloc[current_idx + lookahead_days][close_col]
                ret = (future_price / current_price - 1) * 100
                future_returns.append(ret)
        except:
            continue

    if not future_returns:
        # 기본값
        return Prediction(
            lookahead_days=lookahead_days,
            up_prob=0.5,
            down_prob=0.5,
            expected_return_pct=0.0,
            ci95_return_pct=[-5.0, 5.0],
            drivers=[
                Driver(feature="INSUFFICIENT_DATA", impact="neutral", evidence="N < 10")
            ]
        )

    returns = np.array(future_returns)
    up_prob = float((returns > 0).sum() / len(returns))
    down_prob = float(1 - up_prob)
    expected_ret = float(returns.mean())

    # 95% 신뢰구간
    ci_lower = float(np.percentile(returns, 2.5))
    ci_upper = float(np.percentile(returns, 97.5))

    # 주요 지표 기여도 (간단 구현)
    drivers = []
    if 'MACD.cross_up' in entry_condition:
        drivers.append(Driver(feature="MACD", impact="+", evidence="cross_up"))
    if 'RSI' in entry_condition:
        drivers.append(Driver(feature="RSI", impact="+", evidence="oversold"))
    if 'WITHIN' in entry_condition:
        drivers.append(Driver(feature="EVENT", impact="-", evidence="window"))

    return Prediction(
        lookahead_days=lookahead_days,
        up_prob=round(up_prob, 3),
        down_prob=round(down_prob, 3),
        expected_return_pct=round(expected_ret, 2),
        ci95_return_pct=[round(ci_lower, 2), round(ci_upper, 2)],
        drivers=drivers if drivers else [
            Driver(feature="STRATEGY", impact="neutral", evidence="default")
        ]
    )


def _get_signal_examples(
    data: pd.DataFrame,
    entry_signals: pd.Series,
    symbol: str,
    entry_condition: str,
    parser: StrategyParser
) -> list[SignalExample]:
    """시그널 발생 예시"""

    signal_dates = data[entry_signals].index[:5]  # 최대 5개
    examples = []

    features = parser.extract_features(entry_condition)

    for date in signal_dates:
        examples.append(SignalExample(
            date=date.strftime('%Y-%m-%d'),
            symbol=symbol,
            reason=features
        ))

    return examples


@router.post("/master-strategy", response_model=MasterStrategyResponse)
async def backtest_master_strategy(request: MasterStrategyRequest):
    """
    투자 대가 전략 백테스트 엔드포인트

    Args:
        request: 전략 이름, 심볼, 기간 등

    Returns:
        전략 정보 및 백테스트 결과
    """
    logger.info(f"=== Master Strategy Request ===")
    logger.info(f"Strategy: {request.strategy_name}")
    logger.info(f"Symbols: {request.symbols}")
    logger.info(f"Period: {request.date_range.start} ~ {request.date_range.end}")

    try:
        # 1. 전략 가져오기
        strategy = get_strategy(request.strategy_name)
        if strategy is None:
            logger.error(f"Unknown strategy: {request.strategy_name}")
            raise HTTPException(
                status_code=400,
                detail=f"Unknown strategy: {request.strategy_name}"
            )
        logger.info(f"Strategy loaded: {strategy.name}")

        # 2. 데이터 로드
        all_data = {}
        for symbol in request.symbols:
            try:
                start_date = request.date_range.start if isinstance(request.date_range.start, str) else request.date_range.start.isoformat()
                end_date = request.date_range.end if isinstance(request.date_range.end, str) else request.date_range.end.isoformat()

                df = load_sample_data(symbol, start_date, end_date)
                df = IndicatorCalculator.calculate_all(df)

                all_data[symbol] = df
                logger.info(f"Data loaded for {symbol}: {len(df)} rows")
            except Exception as e:
                logger.error(f"Data load failed for {symbol}: {str(e)}")
                raise HTTPException(
                    status_code=400,
                    detail=f"심볼 {symbol} 데이터 로드 실패: {str(e)}"
                )

        # 첫 번째 심볼로 백테스트 (간단 구현)
        symbol = request.symbols[0]
        data = all_data[symbol]

        # 3. 환율 조회 (백테스트 전에 미리 조회)
        try:
            exchange_service = get_exchange_service()
            usd_krw_rate = exchange_service.get_usd_krw_rate()
        except Exception as e:
            logger.warning(f"환율 조회 실패, 기본값 사용: {e}")
            usd_krw_rate = 1320.0  # 기본 환율
            exchange_service = None

        # 초기 자본 설정 (100만원)
        initial_capital_krw = 1000000
        initial_capital_usd = initial_capital_krw / usd_krw_rate  # 환율 적용

        # 한국 주식 여부 확인 (.KS, .KQ 접미사 또는 6자리 숫자)
        symbol_base = symbol.replace('.KS', '').replace('.KQ', '')
        is_korean_stock = (symbol_base.isdigit() and len(symbol_base) == 6) or symbol.endswith(('.KS', '.KQ'))

        currency_str = 'KRW' if is_korean_stock else 'USD'
        capital_amt = initial_capital_krw if is_korean_stock else initial_capital_usd

        print("\n" + "="*80)
        print("[SYMBOL DETECTION DEBUG]")
        print(f"  Original symbol: {symbol}")
        print(f"  Symbol base (removed .KS/.KQ): {symbol_base}")
        print(f"  Is digit: {symbol_base.isdigit()}")
        print(f"  Length: {len(symbol_base)}")
        print(f"  Ends with .KS/.KQ: {symbol.endswith(('.KS', '.KQ'))}")
        print(f"  FINAL RESULT - is_korean_stock: {is_korean_stock}")
        print(f"  Will use currency: {currency_str}")
        print(f"  Initial capital: {capital_amt:.2f}")
        print("="*80 + "\n")

        logger.info(f"[KOREAN_STOCK_CHECK] Symbol: {symbol}, Base: {symbol_base}, Is Korean: {is_korean_stock}")

        # 4. 전략 시그널 생성
        try:
            entry_signals, exit_signals = strategy.generate_signals(symbol, data)
            logger.info(f"Signals generated - Entry: {entry_signals.sum()}, Exit: {exit_signals.sum()}")
        except Exception as e:
            import traceback
            logger.error(f"Signal generation failed: {str(e)}")
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )

        # 5. 백테스트 실행 (한국주식은 원화, 외국주식은 달러로)
        try:
            risk_params = strategy.get_risk_params()
            backtest_initial_capital = initial_capital_krw if is_korean_stock else initial_capital_usd

            backtest_engine = BacktestEngine(
                data,
                entry_signals,
                exit_signals,
                risk_params,
                request.simulate.transaction_cost_bps,
                request.simulate.slippage_bps,
                initial_capital=backtest_initial_capital,
                is_korean_stock=is_korean_stock  # 한국 주식 여부 전달
            )

            metrics, equity_curve, risk_report = backtest_engine.run()
            equity_curve_payload = [
                {"date": idx.strftime("%Y-%m-%d"), "value": float(val)}
                for idx, val in equity_curve.items()
            ] if equity_curve is not None else []

            trade_history = []
            trade_df = backtest_engine.get_trade_details()
            if not trade_df.empty:
                for record in trade_df.to_dict("records"):
                    entry_price = float(record.get("entry_price", 0.0))
                    exit_price = float(record.get("exit_price", 0.0))
                    shares = float(record.get("shares", 0.0))
                    pnl = float(record.get("pnl", 0.0))
                    pnl_pct = float(record.get("pnl_pct", 0.0)) * 100
                    position_value = entry_price * shares
                    conversion = usd_krw_rate if currency_str == "USD" else 1.0
                    entry_price_krw = entry_price * conversion if currency_str == "USD" else entry_price
                    exit_price_krw = exit_price * conversion if currency_str == "USD" else exit_price
                    position_value_krw = position_value * conversion if currency_str == "USD" else position_value
                    pnl_krw = pnl * conversion if currency_str == "USD" else pnl
                    # numpy.bool을 Python bool로 변환
                    partial_val = record.get("partial", False)
                    partial = _normalize_numpy(partial_val)

                    # 거래 후 잔고
                    balance_after = float(record.get("balance_after", 0.0))
                    balance_after_krw = balance_after * conversion if currency_str == "USD" else balance_after

                    trade_history.append({
                        "entry_date": pd.to_datetime(record.get("entry_date")).strftime("%Y-%m-%d"),
                        "exit_date": pd.to_datetime(record.get("exit_date")).strftime("%Y-%m-%d"),
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "entry_price_krw": entry_price_krw,
                        "exit_price_krw": exit_price_krw,
                        "shares": shares,
                        "position_value": position_value,
                        "position_value_krw": position_value_krw,
                        "pnl": pnl,
                        "pnl_krw": pnl_krw,
                        "pnl_pct": pnl_pct,
                        "exit_reason": record.get("exit_reason"),
                        "holding_days": int(record.get("holding_days", 0)),
                        "partial": partial,
                        "symbol": symbol,
                        "currency": currency_str,
                        "balance_after": balance_after,
                        "balance_after_krw": balance_after_krw,
                    })
            total_trades = len(backtest_engine.trades)

            logger.info(f"Backtest complete - Trades: {total_trades}, CAGR: {metrics.CAGR:.2%}, Sharpe: {metrics.Sharpe:.2f}, MaxDD: {metrics.MaxDD:.2%}")
        except Exception as e:
            logger.error(f"Backtest execution failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"백테스트 실행 실패: {str(e)}"
            )

        # 5. 펀더멘털 스크리닝 및 조건 체크 상세 (전략에 따라)
        fundamental_screen = None
        condition_checks = None
        if request.strategy_name in ["buffett", "lynch", "graham", "oneil"]:
            try:
                from ..models.schemas import ConditionCheck
                analyzer = FundamentalAnalyzer(symbol)
                if request.strategy_name == "buffett":
                    fundamental_screen = _normalize_numpy({
                        "metrics": analyzer.get_buffett_metrics(),
                        "criteria": analyzer.check_buffett_criteria()
                    })
                    condition_details = analyzer.get_buffett_condition_details()
                    condition_checks = [
                        ConditionCheck(**{**cond, "passed": bool(cond.get("passed", False))})
                        for cond in condition_details
                    ]
                elif request.strategy_name == "lynch":
                    fundamental_screen = _normalize_numpy({
                        "metrics": analyzer.get_lynch_metrics(),
                        "criteria": analyzer.check_lynch_criteria()
                    })
                    condition_details = analyzer.get_lynch_condition_details()
                    condition_checks = [
                        ConditionCheck(**{**cond, "passed": bool(cond.get("passed", False))})
                        for cond in condition_details
                    ]
                elif request.strategy_name == "graham":
                    fundamental_screen = _normalize_numpy({
                        "metrics": analyzer.get_graham_metrics(),
                        "criteria": analyzer.check_graham_criteria()
                    })
                    condition_details = analyzer.get_graham_condition_details()
                    condition_checks = [
                        ConditionCheck(**{**cond, "passed": bool(cond.get("passed", False))})
                        for cond in condition_details
                    ]
                elif request.strategy_name == "oneil":
                    fundamental_screen = _normalize_numpy({
                        "metrics": analyzer.get_oneil_metrics(),
                        "criteria": analyzer.check_oneil_criteria()
                    })
                    condition_details = analyzer.get_oneil_condition_details()
                    condition_checks = [
                        ConditionCheck(**{**cond, "passed": bool(cond.get("passed", False))})
                        for cond in condition_details
                    ]
            except Exception as e:
                import traceback
                error_msg = f"Fundamental analysis failed: {str(e)}"
                tb = traceback.format_exc()
                logger.error(error_msg)
                logger.error(f"Traceback:\n{tb}")
                print(f"\n{'='*80}")
                print(f"ERROR in fundamental analysis:")
                print(error_msg)
                print(f"Traceback:\n{tb}")
                print(f"{'='*80}\n")
                # 에러가 발생해도 백테스트는 계속 진행 (조건 체크만 null)
                fundamental_screen = {"error": error_msg}
                condition_checks = None

        # 6. 거래 내역 (환율은 이미 조회됨)
        from ..models.schemas import TradeDetail

        logger.info(f"Trade processing - is_korean_stock: {is_korean_stock}, symbol: {symbol}")

        print(f"\n[TRADE PROCESSING] Total trades: {len(backtest_engine.trades)}")
        print(f"[TRADE PROCESSING] is_korean_stock: {is_korean_stock}")

        trade_history = []
        for idx, trade in enumerate(backtest_engine.trades):
            print(f"\n[TRADE {idx+1}] Entry: {trade['entry_date'].strftime('%Y-%m-%d')} @ {trade['entry_price']:.2f}")
            print(f"[TRADE {idx+1}] Exit: {trade['exit_date'].strftime('%Y-%m-%d')} @ {trade['exit_price']:.2f}")
            print(f"[TRADE {idx+1}] Shares: {trade['shares']:.4f}, Holding days: {trade['holding_days']}")
            print(f"[TRADE {idx+1}] PnL: {trade['pnl']:.2f} ({trade['pnl_pct']*100:.2f}%), Reason: {trade['exit_reason']}")
            if is_korean_stock:
                # 한국 주식: 이미 원화 가격
                entry_price_krw = round(trade['entry_price'], 0)
                exit_price_krw = round(trade['exit_price'], 0)
                position_value_krw = round(trade['entry_price'] * trade['shares'], 0)
                pnl_krw = round(trade['pnl'], 0)

                # USD로 환산 (표시용)
                entry_price = round(trade['entry_price'] / usd_krw_rate, 2)
                exit_price = round(trade['exit_price'] / usd_krw_rate, 2)
                position_value = round(position_value_krw / usd_krw_rate, 2)
                pnl = round(trade['pnl'] / usd_krw_rate, 2)
            else:
                # 외국 주식: 이미 달러 가격
                entry_price = round(trade['entry_price'], 2)
                exit_price = round(trade['exit_price'], 2)
                position_value = round(trade['entry_price'] * trade['shares'], 2)
                pnl = round(trade['pnl'], 2)

                # KRW로 환산
                entry_price_krw = round(entry_price * usd_krw_rate, 0)
                exit_price_krw = round(exit_price * usd_krw_rate, 0)
                position_value_krw = round(position_value * usd_krw_rate, 0)
                pnl_krw = round(pnl * usd_krw_rate, 0)

            trade_history.append(TradeDetail(
                entry_date=trade['entry_date'].strftime('%Y-%m-%d'),
                exit_date=trade['exit_date'].strftime('%Y-%m-%d'),
                symbol=symbol,
                entry_price=entry_price,
                exit_price=exit_price,
                entry_price_krw=entry_price_krw,
                exit_price_krw=exit_price_krw,
                shares=round(trade['shares'], 4),
                position_value=position_value,
                position_value_krw=position_value_krw,
                pnl=pnl,
                pnl_krw=pnl_krw,
                pnl_pct=round(trade['pnl_pct'] * 100, 2),
                holding_days=trade['holding_days'],
                exit_reason=trade['exit_reason'],
                currency="KRW" if is_korean_stock else "USD"
            ))

        # 8. 전략 정보
        strategy_info = _get_strategy_info(request.strategy_name)

        # 9. 최종 자산 계산
        backtest_final_capital = round(equity_curve.iloc[-1], 2) if len(equity_curve) > 0 else backtest_initial_capital

        if is_korean_stock:
            # 한국 주식: equity_curve가 원화
            final_capital_krw = round(backtest_final_capital, 0)
            final_capital_usd = round(backtest_final_capital / usd_krw_rate, 2)
        else:
            # 외국 주식: equity_curve가 달러
            final_capital_usd = backtest_final_capital
            final_capital_krw = round(final_capital_usd * usd_krw_rate, 0)  # 직접 계산

        # 10. 차트 데이터 준비
        equity_curve_data = [
            {"date": equity_curve.index[i].strftime("%Y-%m-%d"), "value": float(equity_curve.iloc[i])}
            for i in range(len(equity_curve))
        ]

        # 컬럼명 확인 (대소문자 불일치 방지)
        close_col = None
        for col in ['close', 'Close', 'CLOSE']:
            if col in data.columns:
                close_col = col
                break

        if close_col is None:
            raise ValueError(f"'close' 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {list(data.columns)}")

        # DataFrame의 index를 사용 (data.index는 datetime, data[close_col]는 값)
        price_data_list = [
            {"date": data.index[i].strftime("%Y-%m-%d"), "close": float(data[close_col].iloc[i])}
            for i in range(len(data))
        ]

        # 11. 실제 시그널 예시 (거래 내역에서 최대 5개)
        signal_examples = []
        for trade in (trade_history or [])[:5]:
            signal_examples.append(SignalExample(
                date=trade.entry_date,
                symbol=symbol,
                reason=[
                    f"매수가: {trade.entry_price_krw if trade.currency == 'KRW' else trade.entry_price:,.0f}{' 원' if trade.currency == 'KRW' else ' USD'}",
                    f"수량: {trade.shares:.4f}",
                    f"매수금액: {trade.position_value_krw if trade.currency == 'KRW' else trade.position_value:,.0f}{' 원' if trade.currency == 'KRW' else ' USD'}"
                ]
            ))

        # 12. 응답 구성
        logger.info(f"Response data - Exchange rate: {usd_krw_rate}, Initial KRW: {initial_capital_krw}, Final KRW: {final_capital_krw}")

        response = MasterStrategyResponse(
            strategy_info=strategy_info,
            backtest=Backtest(
                metrics=metrics,
                cost_assumptions_bps={
                    "fee": request.simulate.transaction_cost_bps,
                    "slippage": request.simulate.slippage_bps
                },
                equity_curve_ref=None,
                equity_curve=equity_curve_payload,
                risk_summary=risk_report,
                warnings=risk_report.get("warnings") if isinstance(risk_report, dict) else None,
                trade_history=None  # Backtest에는 trade_history 넣지 않음 (MasterStrategyResponse에만)
            ),
            fundamental_screen=fundamental_screen,
            condition_checks=condition_checks,  # 조건 체크 상세 추가
            signal_examples=signal_examples,
            trade_history=trade_history,
            initial_capital=initial_capital_usd,
            initial_capital_krw=initial_capital_krw,
            final_capital=final_capital_usd,
            final_capital_krw=final_capital_krw,
            exchange_rate=usd_krw_rate,
            equity_curve=equity_curve_data,
            price_data=price_data_list
        )

        logger.info(f"Response created - Fields: {list(response.model_dump().keys())}")

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _get_strategy_info(strategy_name: str) -> MasterStrategyInfo:
    """전략별 상세 정보"""
    info_map = {
        "buffett": MasterStrategyInfo(
            name="Warren Buffett - Value Investing",
            description="우량 기업을 저평가 시점에 매수하여 장기 보유",
            key_principles=[
                "ROE > 15% (자기자본이익률)",
                "부채비율 < 0.5",
                "P/E < 20, P/B < 3 (저평가)",
                "일관된 이익 성장",
                "경쟁 우위(moat) 보유"
            ],
            holding_period="장기 (수년~수십년)",
            risk_profile="낮음 (안전마진 중시)"
        ),
        "lynch": MasterStrategyInfo(
            name="Peter Lynch - Growth at Reasonable Price",
            description="저평가된 고성장 기업 발굴",
            key_principles=[
                "PEG ratio < 1.0",
                "이익 성장률 > 20%",
                "중소형주 선호",
                "이해하는 기업에 투자"
            ],
            holding_period="중장기 (1~5년)",
            risk_profile="중간 (성장주 변동성)"
        ),
        "graham": MasterStrategyInfo(
            name="Benjamin Graham - Deep Value",
            description="청산가치 이하로 거래되는 초저평가 기업 매수",
            key_principles=[
                "P/B < 0.67 (청산가치 이하)",
                "유동비율 > 2.0",
                "부채/자산 < 0.5",
                "배당 지급 이력"
            ],
            holding_period="중기 (1~3년)",
            risk_profile="중간 (가치 회복 대기)"
        ),
        "dalio": MasterStrategyInfo(
            name="Ray Dalio - All Weather Portfolio",
            description="리스크 패리티 기반 자산 배분",
            key_principles=[
                "분산 투자 (주식 30%, 채권 40%, 금/원자재 30%)",
                "리스크 패리티",
                "분기별 리밸런싱",
                "모든 경제 환경에 대비"
            ],
            holding_period="영구 보유",
            risk_profile="매우 낮음 (분산)"
        ),
        "livermore": MasterStrategyInfo(
            name="Jesse Livermore - Trend Following",
            description="신고가 돌파와 추세 추종",
            key_principles=[
                "52주 신고가 돌파 매수",
                "추세선 이탈 손절",
                "피라미딩 (분할 매수)",
                "시장이 옳다"
            ],
            holding_period="단기~중기 (추세 지속)",
            risk_profile="높음 (타이트 손절)"
        ),
        "oneil": MasterStrategyInfo(
            name="William O'Neil - CAN SLIM",
            description="고성장 모멘텀 주식 선별",
            key_principles=[
                "당기순이익 25%+ 성장",
                "연간 수익 증가",
                "신고가 돌파",
                "기관 매수 확인",
                "7-8% 손절 원칙"
            ],
            holding_period="단기~중기 (모멘텀 지속)",
            risk_profile="높음 (타이트 손절)"
        ),
        "dca": MasterStrategyInfo(
            name="DCA - Dollar Cost Averaging",
            description="정기 적립식 투자 (시간 분산)",
            key_principles=[
                "매월 정기 매수 (타이밍 리스크 분산)",
                "추세 확인 후 매수 (MA20 > MA50)",
                "하락 추세 시 매수 중지",
                "평균 매수 단가 안정화",
                "적절한 손익 실현 (무한 보유 방지)"
            ],
            holding_period="중장기 (추세 지속)",
            risk_profile="중간 (안정적)"
        ),
        "wood": MasterStrategyInfo(
            name="Cathie Wood - Disruptive Innovation",
            description="혁신 기술 집중 투자 - 고성장 + 높은 변동성 감수",
            key_principles=[
                "파괴적 혁신 기술 투자 (AI, 유전체학, 블록체인, 전기차)",
                "매출 성장률 > 25% (고성장)",
                "전통적 밸류에이션 무시 (P/E, P/B)",
                "높은 변동성 감수",
                "집중 투자 (고확신 종목)"
            ],
            holding_period="장기 (5년+)",
            risk_profile="높음 (혁신 기술 변동성)"
        )
    }
    return info_map.get(strategy_name, MasterStrategyInfo(
        name="Unknown",
        description="",
        key_principles=[],
        holding_period="",
        risk_profile=""
    ))


@router.get("/master-strategy/{strategy_name}/template")
async def get_strategy_template(strategy_name: str):
    """
    투자 대가 전략을 커스텀 전략 템플릿으로 변환

    사용자가 대가 전략을 가져와서 수정할 수 있도록 진입/청산 조건을 반환
    """
    # 전략별 조건 문자열 정의
    templates = {
        "buffett": {
            "entry": "( RSI < 40 ) AND ( close < SMA_20 )",
            "exit": "( RSI > 70 ) OR ( close > SMA_20 * 1.2 )",
            "description": "버핏 스타일: 저평가 구간 매수 + 과열 구간 청산",
            "risk": {
                "stop_pct": 0.25,
                "take_pct": 0.50
            },
            "fundamental_filters": [
                "ROE > 15%",
                "부채비율 < 0.5",
                "P/E < 25"
            ]
        },
        "lynch": {
            "entry": "( close > rolling_high_252 * 0.95 )",
            "exit": "( close < SMA_50 )",
            "description": "린치 스타일: 고점 근처 성장주 + 추세 이탈 청산",
            "risk": {
                "stop_pct": 0.15,
                "take_pct": 0.50
            },
            "fundamental_filters": [
                "PEG < 1.0",
                "이익 성장률 > 20%"
            ]
        },
        "graham": {
            "entry": "( RSI < 30 )",
            "exit": "( RSI > 60 )",
            "description": "그레이엄 스타일: 극단적 저평가 매수 + 적정가 청산",
            "risk": {
                "stop_pct": 0.20,
                "take_pct": 0.30
            },
            "fundamental_filters": [
                "P/B < 0.67",
                "유동비율 > 2.0"
            ]
        },
        "dalio": {
            "entry": "( SMA_50 > SMA_200 )",
            "exit": "( SMA_50 < SMA_200 )",
            "description": "달리오 스타일: 장기 추세 확인 매수 + 추세 전환 청산",
            "risk": {
                "stop_pct": 0.15,
                "take_pct": 0.20
            },
            "fundamental_filters": []
        },
        "livermore": {
            "entry": "( close > rolling_high_252 )",
            "exit": "( close < rolling_high_252 * 0.90 )",
            "description": "리버모어 스타일: 신고가 돌파 매수 + 10% 손절",
            "risk": {
                "stop_pct": 0.10,
                "take_pct": 0.30
            },
            "fundamental_filters": []
        },
        "oneil": {
            "entry": "( close > rolling_high_252 ) AND ( RSI > 50 )",
            "exit": "( close < close_prev * 0.92 )",
            "description": "오닐 스타일: 신고가 + 강한 모멘텀 매수 + 8% 손절",
            "risk": {
                "stop_pct": 0.08,
                "take_pct": 0.25
            },
            "fundamental_filters": [
                "이익 성장률 > 25%"
            ]
        },
        "wood": {
            "entry": "( close > rolling_high_252 * 0.80 ) AND ( RSI > 50 )",
            "exit": "( RSI > 75 ) OR ( close < SMA_50 )",
            "description": "캐시 우드 스타일: 혁신 기술 + 강한 모멘텀 + 장기 보유",
            "risk": {
                "stop_pct": 0.20,
                "take_pct": 1.00
            },
            "fundamental_filters": [
                "매출 성장률 > 25%",
                "혁신 기술 섹터 (AI, 바이오, 전기차 등)"
            ]
        }
    }

    if strategy_name not in templates:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_name} not found")

    template = templates[strategy_name]
    strategy_info = _get_strategy_info(strategy_name)

    return {
        "strategy_name": strategy_name,
        "strategy_info": strategy_info,
        "template": template
    }


@router.get("/master-strategies")
async def list_master_strategies():
    """사용 가능한 투자 대가 전략 목록"""
    strategies = list_strategies()
    return {
        "strategies": [
            {
                "name": name,
                "description": desc,
                "info": _get_strategy_info(name)
            }
            for name, desc in strategies.items()
        ]
    }


@router.get("/health")
async def health_check():
    """헬스 체크"""
    return {"status": "ok", "service": "금융 리서치 코파일럿"}


@router.post("/clear-cache")
async def clear_cache():
    """데이터 캐시 삭제 (호가 단위 조정 등 데이터 변경 후 사용)"""
    from ..services.data_cache import get_cache
    cache = get_cache()
    stats_before = cache.get_cache_stats()
    cache.clear()
    return {
        "status": "ok",
        "message": "캐시가 삭제되었습니다",
        "cleared_entries": stats_before["total_entries"],
        "cleared_symbols": stats_before["cached_symbols"]
    }


@router.get("/search-stocks")
async def search_stocks(query: str):
    """
    실시간 종목 검색 API (한글 지원)

    한국 주식 데이터베이스 + yfinance 통합 검색

    Args:
        query: 검색어 (한글명, 영문명, 심볼)

    Returns:
        검색 결과 리스트 (최대 20개)
    """
    try:
        from ..services.stock_database import get_stock_database

        if not query or len(query.strip()) < 1:
            return {"results": []}

        # 통합 검색 (한글/영문/심볼)
        db = get_stock_database()
        results = db.search(query, limit=20)

        return {
            "results": results,
            "query": query
        }

    except Exception as e:
        logger.error(f"종목 검색 오류: {str(e)}")
        return {"results": [], "error": str(e)}


# ============================================================
# 전략 비교 API
# ============================================================

class StrategyComparisonRequest(BaseModel):
    """여러 전략 비교 요청"""
    strategy_names: List[str]  # ["buffett", "lynch", "graham", ...]
    symbols: List[str]
    start_date: str
    end_date: str
    initial_capital: float = 1000000.0


class StrategyComparisonResult(BaseModel):
    """개별 전략 비교 결과"""
    strategy_name: str
    strategy_description: str
    metrics: dict  # CAGR, Sharpe, MaxDD, WinRate, etc.
    equity_curve: List[dict]  # [{date, equity}, ...]
    final_equity: float
    total_return_pct: float
    trade_count: int


class StrategyComparisonResponse(BaseModel):
    """전략 비교 응답"""
    results: List[StrategyComparisonResult]
    best_strategy: str  # CAGR 기준
    comparison_period: dict


@router.post("/compare-strategies", response_model=StrategyComparisonResponse)
async def compare_strategies(request: StrategyComparisonRequest):
    """
    여러 대가 전략을 동시에 백테스트하고 비교

    Args:
        request: 전략 이름 리스트, 종목, 기간

    Returns:
        각 전략의 성과 지표 및 수익 곡선
    """
    try:
        logger.info(f"전략 비교 시작: {request.strategy_names}")

        results = []
        best_cagr = -float('inf')
        best_strategy_name = ""

        for strategy_name in request.strategy_names:
            try:
                # 각 전략 실행
                strategy_class = get_strategy(strategy_name)
                if not strategy_class:
                    logger.warning(f"전략을 찾을 수 없음: {strategy_name}")
                    continue

                strategy = strategy_class()

                # 전략별 백테스트 실행
                strategy_results = []
                all_equity_curves = []

                for symbol in request.symbols:
                    # 데이터 로드
                    data = load_sample_data(symbol, request.start_date, request.end_date)
                    if data is None or len(data) < 50:
                        logger.warning(f"데이터 부족: {symbol}")
                        continue

                    # 지표 계산
                    calculator = IndicatorCalculator(data)
                    data_with_indicators = calculator.calculate_all()

                    # 펀더멘털 분석 (필요한 경우)
                    fundamental_screen = {}
                    if hasattr(strategy, 'requires_fundamental') and strategy.requires_fundamental:
                        try:
                            analyzer = FundamentalAnalyzer(symbol)
                            if strategy_name == "buffett":
                                fundamental_screen = analyzer.get_buffett_metrics()
                            elif strategy_name == "lynch":
                                fundamental_screen = analyzer.get_lynch_metrics()
                            elif strategy_name == "graham":
                                fundamental_screen = analyzer.get_graham_metrics()
                        except Exception as e:
                            logger.warning(f"펀더멘털 분석 실패 ({symbol}): {e}")

                    # 전략 실행
                    entry_signals, exit_signals = strategy.generate_signals(
                        data_with_indicators,
                        fundamental_screen
                    )

                    # 백테스트
                    engine = BacktestEngine(
                        data=data_with_indicators,
                        entry_signals=entry_signals,
                        exit_signals=exit_signals,
                        initial_capital=request.initial_capital / len(request.symbols),  # 균등 배분
                        stop_loss_pct=getattr(strategy, 'stop_loss_pct', None),
                        take_profit_pct=getattr(strategy, 'take_profit_pct', None)
                    )
                    backtest_result = engine.run()
                    strategy_results.append(backtest_result)

                    # Equity curve 저장
                    if backtest_result.get("equity_curve"):
                        all_equity_curves.append(backtest_result["equity_curve"])

                if not strategy_results:
                    logger.warning(f"전략 {strategy_name}: 유효한 결과 없음")
                    continue

                # 평균 지표 계산
                avg_cagr = np.mean([r["metrics"]["CAGR"] for r in strategy_results])
                avg_sharpe = np.mean([r["metrics"]["Sharpe"] for r in strategy_results])
                avg_max_dd = np.mean([r["metrics"]["MaxDD"] for r in strategy_results])
                avg_win_rate = np.mean([r["metrics"]["WinRate"] for r in strategy_results])
                total_trades = sum([r["metrics"]["TotalTrades"] for r in strategy_results])

                # Equity curve 합산 (간단히 첫 번째만 사용)
                equity_curve_data = []
                if all_equity_curves:
                    first_curve = all_equity_curves[0]
                    equity_curve_data = [
                        {"date": item["date"], "equity": item["equity"]}
                        for item in first_curve
                    ]

                # 최종 수익률 계산
                final_equity = strategy_results[-1]["risk_summary"]["ending_equity"] if strategy_results else request.initial_capital
                total_return_pct = ((final_equity / request.initial_capital) - 1) * 100

                # 최고 전략 갱신
                if avg_cagr > best_cagr:
                    best_cagr = avg_cagr
                    best_strategy_name = strategy_name

                # 결과 추가
                results.append(StrategyComparisonResult(
                    strategy_name=strategy_name,
                    strategy_description=strategy.description,
                    metrics={
                        "CAGR": float(avg_cagr),
                        "Sharpe": float(avg_sharpe),
                        "MaxDD": float(avg_max_dd),
                        "WinRate": float(avg_win_rate),
                        "TotalTrades": int(total_trades),
                        "ProfitFactor": float(np.mean([r["metrics"].get("ProfitFactor", 0) for r in strategy_results]))
                    },
                    equity_curve=equity_curve_data,
                    final_equity=float(final_equity),
                    total_return_pct=float(total_return_pct),
                    trade_count=int(total_trades)
                ))

            except Exception as e:
                logger.error(f"전략 {strategy_name} 실행 오류: {e}")
                continue

        if not results:
            raise HTTPException(status_code=400, detail="모든 전략 실행 실패")

        return StrategyComparisonResponse(
            results=results,
            best_strategy=best_strategy_name,
            comparison_period={
                "start": request.start_date,
                "end": request.end_date
            }
        )

    except Exception as e:
        logger.error(f"전략 비교 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# LLM 트레이딩 전략 API
# ============================================================

from ..services.llm_strategy import LLMTradingStrategy, get_available_llm_models


class LLMStrategyRequest(BaseModel):
    """LLM 전략 요청"""
    model_provider: str  # openai, anthropic, google
    model_name: str
    symbols: List[str]
    start_date: str
    end_date: str
    initial_capital: float = 1000000.0
    temperature: float = 0.3
    custom_prompt: Optional[str] = None


class LLMStrategyResponse(BaseModel):
    """LLM 전략 응답"""
    model_info: dict
    backtest: dict
    decisions_log: List[dict]  # LLM의 결정 이력
    equity_curve: List[dict]
    trade_history: List[dict]


@router.post("/llm-strategy", response_model=LLMStrategyResponse)
async def run_llm_strategy(request: LLMStrategyRequest):
    """
    LLM 기반 트레이딩 전략 실행

    Args:
        request: LLM 모델 설정, 종목, 기간

    Returns:
        백테스트 결과 및 LLM 결정 로그
    """
    try:
        logger.info(f"LLM 전략 시작: {request.model_provider} - {request.model_name}")

        # LLM 전략 인스턴스 생성
        llm_strategy = LLMTradingStrategy(
            model_provider=request.model_provider,
            model_name=request.model_name,
            temperature=request.temperature,
            custom_prompt=request.custom_prompt
        )

        # 종목별 백테스트
        all_results = []
        all_decisions = []

        for symbol in request.symbols:
            # 데이터 로드
            data = load_sample_data(symbol, request.start_date, request.end_date)
            if data is None or len(data) < 100:
                logger.warning(f"데이터 부족: {symbol}")
                continue

            # 지표 계산
            calculator = IndicatorCalculator(data)
            data_with_indicators = calculator.calculate_all()

            # LLM 신호 생성
            entry_signals, exit_signals = llm_strategy.generate_signals(
                data_with_indicators,
                symbol=symbol
            )

            # 백테스트
            engine = BacktestEngine(
                data=data_with_indicators,
                entry_signals=entry_signals,
                exit_signals=exit_signals,
                initial_capital=request.initial_capital / len(request.symbols),
                stop_loss_pct=0.10,  # 10% 손절
                take_profit_pct=0.20  # 20% 익절
            )
            backtest_result = engine.run()
            all_results.append(backtest_result)

            # LLM 결정 로그 추가
            for decision in llm_strategy.decisions_log:
                all_decisions.append({
                    **decision,
                    "symbol": symbol,
                    "date": decision["date"].strftime("%Y-%m-%d") if hasattr(decision["date"], "strftime") else str(decision["date"])
                })

        if not all_results:
            raise HTTPException(status_code=400, detail="유효한 백테스트 결과 없음")

        # 평균 지표 계산
        avg_cagr = np.mean([r["metrics"]["CAGR"] for r in all_results])
        avg_sharpe = np.mean([r["metrics"]["Sharpe"] for r in all_results])
        avg_max_dd = np.mean([r["metrics"]["MaxDD"] for r in all_results])
        avg_win_rate = np.mean([r["metrics"]["WinRate"] for r in all_results])
        total_trades = sum([r["metrics"]["TotalTrades"] for r in all_results])

        # Equity curve (첫 번째 결과만)
        equity_curve_data = []
        if all_results[0].get("equity_curve"):
            equity_curve_data = [
                {"date": item["date"], "equity": item["equity"]}
                for item in all_results[0]["equity_curve"]
            ]

        # 거래 내역
        trade_history = []
        for result in all_results:
            if result.get("trade_history"):
                trade_history.extend(result["trade_history"])

        return LLMStrategyResponse(
            model_info={
                "provider": request.model_provider,
                "model_name": request.model_name,
                "temperature": request.temperature,
                "symbols": request.symbols
            },
            backtest={
                "CAGR": float(avg_cagr),
                "Sharpe": float(avg_sharpe),
                "MaxDD": float(avg_max_dd),
                "WinRate": float(avg_win_rate),
                "TotalTrades": int(total_trades),
                "final_equity": float(all_results[-1]["risk_summary"]["ending_equity"]) if all_results else request.initial_capital
            },
            decisions_log=all_decisions,
            equity_curve=equity_curve_data,
            trade_history=trade_history
        )

    except Exception as e:
        logger.error(f"LLM 전략 오류: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/llm-models")
async def list_llm_models():
    """사용 가능한 LLM 모델 목록"""
    return get_available_llm_models()







