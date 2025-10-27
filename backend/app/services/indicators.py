"""
기술지표 계산: MACD, RSI, DMI, Bollinger Bands, OBV 등
"""
import pandas as pd
import numpy as np
import pandas_ta as ta


class IndicatorCalculator:
    """기술지표 계산 클래스"""

    @staticmethod
    def _get_close_col(df: pd.DataFrame) -> str:
        """컬럼명 확인 (대소문자 불일치 방지)"""
        for col in ['close', 'Close', 'CLOSE']:
            if col in df.columns:
                return col
        raise ValueError(f"'close' 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {list(df.columns)}")

    @staticmethod
    def _get_ohlcv_cols(df: pd.DataFrame) -> dict:
        """OHLCV 컬럼명 확인 (대소문자 불일치 방지)"""
        cols = {}
        for name in ['open', 'high', 'low', 'close', 'volume']:
            found = False
            for col in [name, name.capitalize(), name.upper()]:
                if col in df.columns:
                    cols[name] = col
                    found = True
                    break
            if not found:
                raise ValueError(f"'{name}' 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {list(df.columns)}")
        return cols

    @staticmethod
    def calculate_macd(
        df: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> pd.DataFrame:
        """MACD 계산"""
        close_col = IndicatorCalculator._get_close_col(df)
        macd = ta.macd(df[close_col], fast=fast, slow=slow, signal=signal)
        df['MACD'] = macd[f'MACD_{fast}_{slow}_{signal}']
        df['MACD_signal'] = macd[f'MACDs_{fast}_{slow}_{signal}']
        df['MACD_hist'] = macd[f'MACDh_{fast}_{slow}_{signal}']
        return df

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """RSI 계산"""
        close_col = IndicatorCalculator._get_close_col(df)
        df['RSI'] = ta.rsi(df[close_col], length=period)
        return df

    @staticmethod
    def calculate_dmi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """DMI (+DI, -DI, ADX) 계산"""
        cols = IndicatorCalculator._get_ohlcv_cols(df)
        dmi = ta.adx(df[cols['high']], df[cols['low']], df[cols['close']], length=period)
        df['DI_plus'] = dmi[f'DMP_{period}']
        df['DI_minus'] = dmi[f'DMN_{period}']
        df['ADX'] = dmi[f'ADX_{period}']
        return df

    @staticmethod
    def calculate_bbands(
        df: pd.DataFrame,
        period: int = 20,
        std: float = 2.0
    ) -> pd.DataFrame:
        """Bollinger Bands 계산"""
        close_col = IndicatorCalculator._get_close_col(df)
        bbands = ta.bbands(df[close_col], length=period, std=std)
        # pandas-ta의 실제 컬럼명 형식: BBU_20_2.0_2.0 (std가 두번 들어감)
        df['BB_upper'] = bbands[f'BBU_{period}_{std}_{std}']
        df['BB_middle'] = bbands[f'BBM_{period}_{std}_{std}']
        df['BB_lower'] = bbands[f'BBL_{period}_{std}_{std}']
        df['BB_width'] = bbands[f'BBB_{period}_{std}_{std}']
        return df

    @staticmethod
    def calculate_obv(df: pd.DataFrame) -> pd.DataFrame:
        """OBV (On-Balance Volume) 계산"""
        cols = IndicatorCalculator._get_ohlcv_cols(df)
        df['OBV'] = ta.obv(df[cols['close']], df[cols['volume']])
        return df

    @staticmethod
    def calculate_stochastic(
        df: pd.DataFrame,
        k_period: int = 14,
        d_period: int = 3
    ) -> pd.DataFrame:
        """Stochastic Oscillator 계산"""
        cols = IndicatorCalculator._get_ohlcv_cols(df)
        stoch = ta.stoch(df[cols['high']], df[cols['low']], df[cols['close']], k=k_period, d=d_period)
        df['Stoch_K'] = stoch[f'STOCHk_{k_period}_{d_period}_3']
        df['Stoch_D'] = stoch[f'STOCHd_{k_period}_{d_period}_3']
        return df

    @staticmethod
    def calculate_returns(df: pd.DataFrame) -> pd.DataFrame:
        """수익률 계산"""
        # 컬럼명 확인 (대소문자 불일치 방지)
        close_col = None
        for col in ['close', 'Close', 'CLOSE']:
            if col in df.columns:
                close_col = col
                break

        if close_col is None:
            raise ValueError(f"'close' 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {list(df.columns)}")

        df['RET'] = df[close_col].pct_change()
        df['RET_log'] = np.log(df[close_col] / df[close_col].shift(1))
        return df

    @staticmethod
    def calculate_volatility(
        df: pd.DataFrame,
        window: int = 20
    ) -> pd.DataFrame:
        """변동성 계산"""
        df['VOL'] = df['RET'].rolling(window=window).std()
        df['VOL_annualized'] = df['VOL'] * np.sqrt(252)
        return df

    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        """모든 지표 한번에 계산"""
        # 필수 컬럼 확인 (대소문자 무관)
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        actual_cols = {}
        for req_col in required_cols:
            found = False
            for col in df.columns:
                if col.lower() == req_col:
                    actual_cols[req_col] = col
                    found = True
                    break
            if not found:
                raise ValueError(f"DataFrame에 '{req_col}' 컬럼이 없습니다. 사용 가능: {list(df.columns)}")

        # 각 지표 계산
        df = IndicatorCalculator.calculate_returns(df)
        df = IndicatorCalculator.calculate_volatility(df)
        df = IndicatorCalculator.calculate_macd(df)
        df = IndicatorCalculator.calculate_rsi(df)
        df = IndicatorCalculator.calculate_dmi(df)
        df = IndicatorCalculator.calculate_bbands(df)
        df = IndicatorCalculator.calculate_obv(df)
        df = IndicatorCalculator.calculate_stochastic(df)

        # NaN 제거
        df = df.dropna()

        return df


def round_to_korean_tick(price: float) -> int:
    """
    한국 주식 호가 단위에 맞게 가격 반올림

    한국 거래소 호가 단위:
    - 1,000원 미만: 1원
    - 1,000원 이상 5,000원 미만: 5원
    - 5,000원 이상 10,000원 미만: 10원
    - 10,000원 이상 50,000원 미만: 50원
    - 50,000원 이상 100,000원 미만: 100원
    - 100,000원 이상 500,000원 미만: 500원
    - 500,000원 이상: 1,000원
    """
    if price < 1000:
        tick = 1
    elif price < 5000:
        tick = 5
    elif price < 10000:
        tick = 10
    elif price < 50000:
        tick = 50
    elif price < 100000:
        tick = 100
    elif price < 500000:
        tick = 500
    else:
        tick = 1000

    return int(round(price / tick) * tick)


def load_sample_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    실제 주가 데이터 로드 (yfinance 사용, 캐싱 포함)

    Args:
        symbol: 주식 심볼 (예: AAPL, 005930.KS, 035720.KQ)
        start_date: 시작 날짜 (YYYY-MM-DD)
        end_date: 종료 날짜 (YYYY-MM-DD)

    Returns:
        OHLCV 데이터프레임 (open, high, low, close, volume)
    """
    import yfinance as yf
    from datetime import datetime
    from .data_cache import get_cache

    # 캐시 확인
    cache = get_cache()
    cached_data = cache.get(symbol, start_date, end_date)
    if cached_data is not None:
        print(f"[CACHE] {symbol} 데이터 로드")
        return cached_data

    # 한국 주식 심볼 자동 변환
    # 숫자로만 이루어진 6자리 = 한국 주식 코드
    yf_symbol = symbol
    if symbol.isdigit() and len(symbol) == 6:
        # KOSPI는 .KS, KOSDAQ는 .KQ
        # 기본적으로 .KS 시도 후 실패하면 .KQ 시도
        symbol_ks = f"{symbol}.KS"
        symbol_kq = f"{symbol}.KQ"

        print(f"한국 주식 감지: {symbol} → {symbol_ks} 시도 중...")
        # KOSPI 먼저 시도
        ticker = yf.Ticker(symbol_ks)
        df = ticker.history(start=start_date, end=end_date)

        # 데이터 없으면 KOSDAQ 시도
        if df.empty:
            print(f"KOSPI 데이터 없음 → {symbol_kq} 시도 중...")
            ticker = yf.Ticker(symbol_kq)
            df = ticker.history(start=start_date, end=end_date)
            yf_symbol = symbol_kq if not df.empty else symbol_ks
        else:
            yf_symbol = symbol_ks

        if df.empty:
            raise ValueError(f"한국 주식 {symbol}에 대한 데이터를 찾을 수 없습니다 (KOSPI/KOSDAQ 모두 시도)")
    else:
        # 미국 주식 또는 이미 .KS/.KQ가 붙은 경우
        print(f"해외 주식: {symbol} 데이터 로드 중...")
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date)

    if df.empty:
        raise ValueError(f"심볼 {symbol}에 대한 데이터를 찾을 수 없습니다. 심볼을 확인해주세요.")

    # yfinance 컬럼명을 소문자로 변환 (Open -> open)
    df.columns = [col.lower() for col in df.columns]

    # 필요한 컬럼만 선택
    required_cols = ['open', 'high', 'low', 'close', 'volume']

    # 실제로 존재하는 컬럼만 선택
    available_cols = [col for col in required_cols if col in df.columns]

    if len(available_cols) != len(required_cols):
        missing = set(required_cols) - set(available_cols)
        raise ValueError(f"필수 컬럼 누락: {missing}")

    df = df[required_cols]

    # 한국 주식의 경우 호가 단위에 맞게 가격 조정
    symbol_base = symbol.replace('.KS', '').replace('.KQ', '')
    is_korean = (symbol_base.isdigit() and len(symbol_base) == 6) or symbol.endswith(('.KS', '.KQ'))

    if is_korean:
        print(f"[한국 주식] 호가 단위 조정 적용: {symbol}")
        # OHLC 가격들을 한국 호가 단위에 맞게 조정
        df['open'] = df['open'].apply(round_to_korean_tick)
        df['high'] = df['high'].apply(round_to_korean_tick)
        df['low'] = df['low'].apply(round_to_korean_tick)
        df['close'] = df['close'].apply(round_to_korean_tick)

    # timezone 제거 (timezone-aware timestamp는 fundamental_analysis와 충돌)
    if hasattr(df.index, 'tz') and df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    # 인덱스 이름을 'date'로 설정
    df.index.name = 'date'

    # 캐시에 저장
    cache.set(symbol, start_date, end_date, df)
    print(f"[OK] {symbol} ({yf_symbol}) 데이터 {len(df)}개 로드 완료 (최신: {df.index[-1].date()})")

    return df
