"""
투자 대가들의 실제 전략 구현
- 워렌 버핏: 가치 투자 (롱)
- 피터 린치: 성장주 투자 (롱)
- 벤저민 그레이엄: 딥 밸류 (롱)
- 레이 달리오: 올웨더 포트폴리오 (롱)
- 제시 리버모어: 추세 추종 (롱/숏)
- 윌리엄 오닐: CAN SLIM (롱)
- 짐 채노스: 공매도 (숏 전문)
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from .fundamental_analysis import FundamentalAnalyzer
from ..models.schemas import RiskParams


def _get_close_series(df: pd.DataFrame) -> pd.Series:
    """컬럼명 대소문자 무관하게 close 시리즈 반환"""
    for col in ['close', 'Close', 'CLOSE']:
        if col in df.columns:
            return df[col]
    raise KeyError(f"'close' 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {list(df.columns)}")


def _to_bool_series(series: pd.Series) -> pd.Series:
    """
    pandas Series를 Python bool Series로 변환
    numpy.bool_ → bool 변환으로 JSON 직렬화 오류 방지
    """
    return series.fillna(False).astype(bool)


class MasterStrategy:
    """투자 대가 전략 베이스 클래스"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def generate_signals(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        **kwargs
    ) -> Tuple[pd.Series, pd.Series]:
        """
        매매 시그널 생성

        Returns:
            (entry_signals, exit_signals) - Boolean Series
        """
        raise NotImplementedError

    def get_risk_params(self) -> RiskParams:
        """전략별 리스크 파라미터"""
        raise NotImplementedError


class BuffettStrategy(MasterStrategy):
    """
    워렌 버핏 - 가치 투자 전략

    핵심 원칙:
    1. 우량 기업 선별: ROE > 15%, 낮은 부채비율
    2. 저평가 매수: P/E < 20, P/B < 3
    3. 장기 보유: 최소 1년 이상
    4. 안전마진: 내재가치 대비 할인된 가격
    """

    def __init__(self):
        super().__init__(
            name="Warren Buffett - Value Investing",
            description="우량 기업을 저평가 시점에 매수하여 장기 보유"
        )

    def generate_signals(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        **kwargs
    ) -> Tuple[pd.Series, pd.Series]:
        """
        진입: 펀더멘털 충족 + 안전마진 (52주 최저가 근처)
        청산: 펀더멘털 악화 OR 과대평가 (목표가 도달)

        버핏 원칙: "훌륭한 기업을 적정가에" - 저평가 시점 매수 필수
        개선: 무조건 매수 → 저평가 구간(52주 저점 근처)에서만 매수
        """
        # TIMEZONE 제거
        if hasattr(price_data.index, 'tz') and price_data.index.tz is not None:
            price_data = price_data.copy()
            price_data.index = price_data.index.tz_localize(None)

        analyzer = FundamentalAnalyzer(symbol)
        close = _get_close_series(price_data)

        entry_signals = pd.Series([False] * len(price_data), index=price_data.index)
        exit_signals = pd.Series([False] * len(price_data), index=price_data.index)

        # 안전마진: 52주 최저가 대비 +20% 이내 (저평가 구간)
        rolling_low_252 = close.rolling(252, min_periods=100).min()
        safety_margin = close < (rolling_low_252 * 1.20)

        # 각 날짜별로 펀더멘털 체크
        for date in price_data.index:
            passes_fundamental = analyzer.check_buffett_criteria_at_date(date)

            if passes_fundamental and safety_margin.loc[date]:
                # 진입: 펀더멘털 OK + 안전마진 (저평가)
                entry_signals.loc[date] = True
            elif not passes_fundamental:
                # 청산: 펀더멘털 악화
                exit_signals.loc[date] = True

        return entry_signals, exit_signals

    def get_risk_params(self) -> RiskParams:
        """
        버핏식 리스크 관리:
        - 손절폭 넓음 (단기 변동성 무시)
        - 익절 목표 명확 (+50%)
        """
        return RiskParams(
            stop_pct=0.30,  # -30% (매우 넓은 손절, 장기 투자)
            take_pct=0.50,  # +50% (적정 익절)
            position_sizing="equal_weight"
        )


class LynchStrategy(MasterStrategy):
    """
    피터 린치 - 성장주 투자 전략

    핵심 원칙:
    1. PEG < 1.0 (저평가된 성장주)
    2. 이익 성장률 > 20%
    3. 중소형주 선호
    """

    def __init__(self):
        super().__init__(
            name="Peter Lynch - Growth at Reasonable Price",
            description="저평가된 고성장 기업 발굴"
        )

    def generate_signals(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        **kwargs
    ) -> Tuple[pd.Series, pd.Series]:
        """
        진입: PEG < 1.0 + 골든크로스 (상승 추세 시작)
        청산: PEG > 2.0 OR 데드크로스 (성장 둔화 OR 추세 이탈)

        린치 원칙: "저평가된 성장주" + 추세 확인
        개선: 골든크로스 확인으로 매수 타이밍 개선
        """
        # TIMEZONE 제거
        if hasattr(price_data.index, 'tz') and price_data.index.tz is not None:
            price_data = price_data.copy()
            price_data.index = price_data.index.tz_localize(None)

        analyzer = FundamentalAnalyzer(symbol)
        close = _get_close_series(price_data)

        entry_signals = pd.Series([False] * len(price_data), index=price_data.index)
        exit_signals = pd.Series([False] * len(price_data), index=price_data.index)

        # 기술적 조건: 골든크로스 (MA20 > MA50 상향 돌파)
        ma20 = close.rolling(20).mean()
        ma50 = close.rolling(50).mean()
        ma20_prev = ma20.shift(1)
        ma50_prev = ma50.shift(1)

        golden_cross = (ma20 > ma50) & (ma20_prev <= ma50_prev)
        death_cross = (ma20 < ma50) & (ma20_prev >= ma50_prev)

        # 각 날짜별로 펀더멘털 체크
        for date in price_data.index:
            passes_fundamental = analyzer.check_lynch_criteria_at_date(date)

            if passes_fundamental and golden_cross.loc[date]:
                # 진입: PEG < 1.0 + 골든크로스 (추세 시작)
                entry_signals.loc[date] = True
            elif not passes_fundamental or death_cross.loc[date]:
                # 청산: PEG > 2.0 OR 데드크로스
                exit_signals.loc[date] = True

        return entry_signals, exit_signals

    def get_risk_params(self) -> RiskParams:
        """성장주는 변동성 크지만 빠른 손절 필요"""
        return RiskParams(
            stop_pct=0.12,  # -12% (적정 손절)
            take_pct=0.50,  # +50% (성장주 목표)
            position_sizing="vol_target_10"
        )


class GrahamStrategy(MasterStrategy):
    """
    벤저민 그레이엄 - 딥 밸류 전략

    핵심 원칙:
    1. P/B < 0.67 (청산가치 이하)
    2. 유동비율 > 2.0
    3. 낮은 부채비율
    4. 배당 지급
    """

    def __init__(self):
        super().__init__(
            name="Benjamin Graham - Deep Value",
            description="청산가치 이하로 거래되는 초저평가 기업 매수"
        )

    def generate_signals(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        **kwargs
    ) -> Tuple[pd.Series, pd.Series]:
        """
        진입: P/B < 0.67 + 52주 최저가 근처 + 골든크로스
        청산: P/B > 1.0 (더 이상 저평가 아님) OR 데드크로스

        그레이엄 원칙: "안전마진" - 극단적 저평가 + 반등 확인
        개선: 골든크로스로 반등 확인 강화
        """
        # TIMEZONE 제거
        if hasattr(price_data.index, 'tz') and price_data.index.tz is not None:
            price_data = price_data.copy()
            price_data.index = price_data.index.tz_localize(None)

        analyzer = FundamentalAnalyzer(symbol)
        close = _get_close_series(price_data)

        entry_signals = pd.Series([False] * len(price_data), index=price_data.index)
        exit_signals = pd.Series([False] * len(price_data), index=price_data.index)

        # 기술적 조건: 52주 최저가 + 골든크로스 (반등 시작)
        rolling_low = close.rolling(252, min_periods=100).min()
        near_low = close < rolling_low * 1.15  # 저점 대비 +15% 이내

        ma20 = close.rolling(20).mean()
        ma50 = close.rolling(50).mean()
        ma20_prev = ma20.shift(1)
        ma50_prev = ma50.shift(1)

        golden_cross = (ma20 > ma50) & (ma20_prev <= ma50_prev)
        death_cross = (ma20 < ma50) & (ma20_prev >= ma50_prev)

        # 각 날짜별로 펀더멘털 체크
        for date in price_data.index:
            passes_fundamental = analyzer.check_graham_criteria_at_date(date)

            if passes_fundamental and near_low.loc[date] and golden_cross.loc[date]:
                # 진입: P/B < 0.67 + 저점 + 골든크로스
                entry_signals.loc[date] = True
            elif not passes_fundamental or death_cross.loc[date]:
                # 청산: P/B > 1.0 OR 데드크로스
                exit_signals.loc[date] = True

        return entry_signals, exit_signals

    def get_risk_params(self) -> RiskParams:
        """안전마진 중시, 보수적 익절"""
        return RiskParams(
            stop_pct=0.20,  # -20% (넓은 손절)
            take_pct=0.35,  # +35% (보수적 익절)
            position_sizing="equal_weight"
        )


class DalioStrategy(MasterStrategy):
    """
    ⚠️ 비활성화됨 - 단일 종목에 적합하지 않음

    레이 달리오 - 올웨더 포트폴리오 (원래 전략)

    원래 핵심 원칙:
    1. 자산 배분: 주식 30%, 채권 40%, 금 15%, 원자재 15%
    2. 리스크 패리티 (각 자산의 리스크 균등 배분)
    3. 분산 투자 (4가지 경제 사이클 대비)
    4. 분기별 리밸런싱

    ❌ 단일 종목 적용 시 문제점:
    - 매월 무조건 매수 → 하락장에서 계속 물타기
    - 청산 조건이 너무 느슨 (52주 최고가 + 20%)
    - 올웨더의 핵심인 "자산 분산"을 단일 종목에 적용 불가
    - Trailing Stop -10%에 걸려 모든 거래가 손실로 청산됨

    ✅ 대안: DCAStrategy (Dollar Cost Averaging) 사용 권장
    """

    def __init__(self):
        super().__init__(
            name="Ray Dalio - All Weather (DEPRECATED)",
            description="⚠️ 비활성화됨 - 단일 종목에 부적합 (DCA 전략 사용 권장)"
        )

    def generate_signals(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        **kwargs
    ) -> Tuple[pd.Series, pd.Series]:
        """
        ⚠️ 이 전략은 비활성화되었습니다.

        사용하려고 하면 에러를 발생시킵니다.
        """
        raise ValueError(
            "❌ Dalio 올웨더 전략은 단일 종목에 적합하지 않아 비활성화되었습니다.\n\n"
            "올웨더 포트폴리오는 '자산 분산'이 핵심입니다:\n"
            "  - 주식 30% + 채권 40% + 금 15% + 원자재 15%\n"
            "  - 4가지 경제 사이클(성장/침체/인플레/디플레) 대비\n\n"
            "단일 종목 적용 시 문제점:\n"
            "  1. 매월 무조건 매수 → 하락장에서 계속 물타기\n"
            "  2. 청산 조건 너무 느슨 (52주 최고가 + 20%)\n"
            "  3. Trailing Stop -10%에 걸려 계속 손실\n\n"
            "✅ 대안: 'dca' 전략 사용을 권장합니다.\n"
            "   - 정기 적립식 투자 (Dollar Cost Averaging)\n"
            "   - 추세 확인 후 매수 (MA 상승 구간만)\n"
            "   - 적절한 손익 관리"
        )

    def get_risk_params(self) -> RiskParams:
        """사용 불가"""
        raise ValueError("Dalio 전략은 비활성화되었습니다. DCA 전략을 사용하세요.")


class LivermoreStrategy(MasterStrategy):
    """
    제시 리버모어 - 순수 추세 추종 전략 (역사적 방법론)

    핵심 원칙 (Reminiscences of a Stock Operator):
    1. 피봇 포인트 돌파 매수 (52주 신고가)
    2. 추세가 끝날 때까지 전량 보유
    3. "It never was my thinking that made the big money. It was my sitting."
    4. 이익을 손실로 바꾸지 마라
    5. 감정 배제, 시장이 말할 때까지 기다림

    주의사항:
    - MA20/MA50 같은 기술적 지표 사용 안 함 (당시 컴퓨터 없었음)
    - 부분 익절 없음 (추세 끝까지 보유가 원칙)
    - 가격 패턴과 거래량만으로 판단
    """

    def __init__(self):
        super().__init__(
            name="Jesse Livermore - Pure Trend Following",
            description="순수 리버모어 전략: 신고가 돌파 + 추세 끝까지 보유 (MA 사용 안 함)"
        )

    def generate_signals(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        **kwargs
    ) -> Tuple[pd.Series, pd.Series]:
        """
        진입: 52주 신고가 돌파 + 거래량 급증
        청산: 5일 연속 하락 + 거래량 증가 (추세 반전 신호)

        역사적 방법론:
        - MA 같은 기술적 지표 사용 안 함
        - 가격 패턴과 거래량만으로 판단
        - 추세가 끝날 때까지 보유 (부분 익절 없음)
        """
        # TIMEZONE 제거
        if hasattr(price_data.index, 'tz') and price_data.index.tz is not None:
            price_data = price_data.copy()
            price_data.index = price_data.index.tz_localize(None)

        close = _get_close_series(price_data)

        # 진입 조건 1: 52주(252일) 신고가 돌파
        rolling_high_252d = close.rolling(252, min_periods=100).max()
        breakout_52week = close > rolling_high_252d.shift(1)

        # 진입 조건 2: 거래량 급증 (평균 대비 1.5배 이상)
        if 'volume' in price_data.columns:
            vol_ma20 = price_data['volume'].rolling(20).mean()
            volume_surge = price_data['volume'] > vol_ma20 * 1.5
            entry_signals = breakout_52week & volume_surge
        else:
            entry_signals = breakout_52week

        # 청산 조건: 5일 연속 하락 + 거래량 증가 (명확한 추세 반전)
        # Livermore는 "시장이 명확히 말할 때까지 기다림"
        decline_5days = (
            (close < close.shift(1)) &
            (close.shift(1) < close.shift(2)) &
            (close.shift(2) < close.shift(3)) &
            (close.shift(3) < close.shift(4)) &
            (close.shift(4) < close.shift(5))
        )

        if 'volume' in price_data.columns:
            # 거래량 증가 (추세 반전 확인)
            vol_increasing = (
                (price_data['volume'] > price_data['volume'].shift(1)) &
                (price_data['volume'].shift(1) > price_data['volume'].shift(2))
            )
            reversal_signal = decline_5days & vol_increasing
        else:
            reversal_signal = decline_5days

        exit_signals = reversal_signal

        return entry_signals, exit_signals

    def get_risk_params(self) -> RiskParams:
        """
        순수 Livermore 리스크 관리:
        - 손절 8% (Never let a profit turn into a loss)
        - 익절 목표 없음 (추세 끝까지 보유)
        - 100% 투자 (equal_weight)
        """
        return RiskParams(
            stop_pct=0.08,  # -8% (타이트한 손절)
            take_pct=10.0,  # 익절 목표 없음 (사실상 무제한, 청산 신호로만 매도)
            position_sizing="equal_weight"  # 100% 투자
        )


class ModernLivermoreStrategy(MasterStrategy):
    """
    제시 리버모어 현대 해석 전략

    핵심 철학: "가격 행동 중심의 추세 추종 + 심리 기반 포지션 관리"
    Livermore는 기술지표보다 시장 참여자의 행동 패턴을 본 사람입니다.

    전략 5단계:
    1. 시장 위상 판단 (Campaign Phase): Bull/Distribution/Bear 구분
    2. 리더 식별 (Strong Horse): 상대 강도 상위 종목만 선택
    3. Pivot Point 트리거: 돌파 확인 후 진입
    4. Pyramiding: 수익 중에만 추가 매수
    5. Failure Signal 청산: 추세 붕괴 즉시 탈출

    Livermore 4대 원칙:
    - "큰 추세만 노린다" - 잡음(trivial movement)은 무시
    - "확인된 방향에만 베팅한다" - 예측이 아니라 확인 후 진입
    - "손실은 즉시, 수익은 천천히" - 엄격한 손절, 느긋한 익절
    - "가격은 사람들의 반응이 포화될 때 멈춘다" - 거래량 급증 + 하락 = 청산

    현대적 구조:
    - Pivot Point = 20주 신고가 돌파 + 거래량 확인
    - Campaign Phase = MACD + MA20/MA50 크로스
    - Normal Reaction = 20일 저점 이탈 시 청산
    - Failure Signal = 거래량 급증 하락 또는 MA20 하향 돌파
    """

    def __init__(self):
        super().__init__(
            name="Modern Livermore - Price Action Trend Following",
            description="리버모어 현대 해석: 시장 심리 패턴 추적 + Pivot Point 진입"
        )

    def generate_signals(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        **kwargs
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Modern Livermore 시그널 생성

        진입 (Pivot Point 확인):
        1. 20주(100일) 신고가 돌파 - "Point of Least Resistance"
        2. 시장 위상 Bull Campaign - MACD > 0 AND MA20 > MA50
        3. 거래량 확인 - 진짜 돌파인지 검증 (50일 평균 대비 1.2배)
        4. 변동성 확장 - ATR 증가 또는 BB 확장

        청산 (Failure Signal 탐지):
        1. 추세선 붕괴 - 이전 20일 저점 이탈
        2. 거래량 급증 하락 - "대중이 공포에 빠질 때"
        3. 리더십 상실 - MA20 하향 돌파
        """
        # TIMEZONE 제거
        if hasattr(price_data.index, 'tz') and price_data.index.tz is not None:
            price_data = price_data.copy()
            price_data.index = price_data.index.tz_localize(None)

        close = _get_close_series(price_data)

        # === 1. 시장 위상 판단 (Campaign Phase) ===
        ma20 = close.rolling(20).mean()
        ma50 = close.rolling(50).mean()

        # Bull Campaign: MA20 > MA50 (상승 추세)
        bull_campaign = ma20 > ma50

        # MACD로 모멘텀 확인
        try:
            macd_line = close.ewm(span=12).mean() - close.ewm(span=26).mean()
            macd_positive = macd_line > 0
        except:
            macd_positive = pd.Series(True, index=close.index)

        # === 2. Pivot Point 트리거 (돌파 확인) ===
        # 20주(100일) 신고가 돌파 - "Point of Least Resistance"
        rolling_high_100d = close.rolling(100, min_periods=50).max()
        pivot_breakout = close > rolling_high_100d.shift(1)

        # === 3. 거래량 확인 (진짜 돌파) ===
        if 'volume' in price_data.columns:
            vol_ma50 = price_data['volume'].rolling(50).mean()
            # 거래량 1.2배 이상 = 시장 참여자 증가
            volume_surge = price_data['volume'] > vol_ma50 * 1.2
        else:
            volume_surge = pd.Series(True, index=close.index)

        # === 4. 변동성 확장 (BB 밴드 확장 또는 ATR 증가) ===
        # ATR (Average True Range) 증가 = 변동성 확장
        high = price_data['high'] if 'high' in price_data.columns else close
        low = price_data['low'] if 'low' in price_data.columns else close
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        atr_expanding = atr > atr.shift(5)  # ATR이 5일 전보다 커짐

        # === 진입 신호 조합 ===
        # Pivot 돌파 + Bull Campaign + 거래량 확인 + 변동성 확장
        entry_signals = pivot_breakout & bull_campaign & macd_positive & volume_surge & atr_expanding

        # === 5. 청산 신호 (Failure Signal) ===

        # 청산 1: 추세선 붕괴 - 20일 저점 이탈 (Livermore의 "Normal Reaction" 실패)
        rolling_low_20d = close.rolling(20, min_periods=10).min()
        support_break = close < rolling_low_20d.shift(1)

        # 청산 2: 거래량 급증 하락 - "대중의 공포" 신호
        price_decline = close < close.shift(1)
        if 'volume' in price_data.columns:
            volume_panic = price_data['volume'] > vol_ma50 * 1.5  # 1.5배 급증
            panic_sell = price_decline & volume_panic
        else:
            panic_sell = price_decline

        # 청산 3: MA20 하향 돌파 - 리더십 상실
        ma20_cross_down = (close.shift(1) >= ma20.shift(1)) & (close < ma20)

        # === 청산 신호 조합 ===
        # 추세선 붕괴 OR 거래량 급증 하락 OR MA20 하향 돌파
        exit_signals = support_break | panic_sell | ma20_cross_down

        return entry_signals, exit_signals

    def get_risk_params(self) -> RiskParams:
        """
        Livermore 리스크 관리 원칙

        핵심: "손실은 즉시, 수익은 천천히"

        - 손절 10% (엄격) - 실수를 빠르게 인정
        - 익절 40% (여유) - 큰 추세를 끝까지 탐
        - Pyramiding 지향 - 수익 중 추가 매수 철학 (부분 익절 허용)
        - Trailing Stop 15% - 고점 대비 -15% 이탈 시 청산
        - 포지션 사이즈 - 전체 자본의 100% 투입 (단순 배분)

        Livermore: "Big money is made in big swings, not in small movements."
        """
        return RiskParams(
            stop_pct=0.10,  # -10% 손절 (엄격하게)
            take_pct=0.40,  # +40% 익절 (큰 추세 노림)
            position_sizing="equal_weight",  # 단순 배분
            allow_partial_profits=True,  # 부분 익절 허용
            trailing_pct=0.15,  # 고점 대비 -15% Trailing Stop
        )


class ONeilStrategy(MasterStrategy):
    """
    윌리엄 오닐 - CAN SLIM 전략

    핵심 원칙:
    C: Current earnings (당기순이익 25%+ 성장)
    A: Annual earnings (연간 수익 증가)
    N: New products/New high (신제품, 신고가)
    S: Supply and demand (소형주, 적은 유통주식)
    L: Leader (시장 선도주)
    I: Institutional sponsorship (기관 매수)
    M: Market direction (시장 방향성)
    """

    def __init__(self):
        super().__init__(
            name="William O'Neil - CAN SLIM",
            description="고성장 모멘텀 주식 선별"
        )

    def generate_signals(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        **kwargs
    ) -> Tuple[pd.Series, pd.Series]:
        """
        진입: CAN SLIM + 52주 신고가 돌파 + 컵앤핸들 패턴
        청산: MA21 하향 돌파 OR 7% 손절 (빠른 손절)

        오닐 원칙: "Leading stocks in leading industries"
        개선: 컵앤핸들 패턴 확인 + 엄격한 7% 손절
        """
        # TIMEZONE 제거
        if hasattr(price_data.index, 'tz') and price_data.index.tz is not None:
            price_data = price_data.copy()
            price_data.index = price_data.index.tz_localize(None)

        analyzer = FundamentalAnalyzer(symbol)
        close = _get_close_series(price_data)

        entry_signals = pd.Series([False] * len(price_data), index=price_data.index)
        exit_signals = pd.Series([False] * len(price_data), index=price_data.index)

        # 기술적 조건: 52주 신고가 돌파 (정확한 신고가)
        rolling_high_252 = close.rolling(252, min_periods=100).max()
        breakout_high = close > rolling_high_252.shift(1)

        # 상승 추세 확인
        ma21 = close.rolling(21).mean()
        ma50 = close.rolling(50).mean()
        in_uptrend = (close > ma21) & (ma21 > ma50)

        # 거래량 급증 (1.5배 이상)
        if 'volume' in price_data.columns:
            vol_ma50 = price_data['volume'].rolling(50).mean()
            volume_surge = price_data['volume'] > vol_ma50 * 1.5
        else:
            volume_surge = pd.Series([True] * len(price_data), index=price_data.index)

        # 청산: MA21 하향 돌파
        price_prev = close.shift(1)
        ma21_prev = ma21.shift(1)
        ma21_cross_down = (price_prev >= ma21_prev) & (close < ma21)

        # 각 날짜별로 펀더멘털 체크
        for date in price_data.index:
            passes_fundamental = analyzer.check_oneil_criteria_at_date(date)

            if passes_fundamental and breakout_high.loc[date] and in_uptrend.loc[date] and volume_surge.loc[date]:
                # 진입: CAN SLIM + 신고가 돌파 + 추세 + 거래량
                entry_signals.loc[date] = True

            if ma21_cross_down.loc[date]:
                # 청산: MA21 하향 돌파
                exit_signals.loc[date] = True

        return entry_signals, exit_signals

    def get_risk_params(self) -> RiskParams:
        """오닐의 엄격한 7% 손절 원칙"""
        return RiskParams(
            stop_pct=0.07,  # -7% (타이트한 손절)
            take_pct=0.25,  # +25% (현실적 익절)
            position_sizing="vol_target_10"
        )


class DCAStrategy(MasterStrategy):
    """
    정기 적립식 투자 (Dollar Cost Averaging)

    핵심 원칙:
    1. 정기적 매수로 타이밍 리스크 분산
    2. 시장 변동성에 둔감하게 장기 투자
    3. 평균 매수 단가 안정화

    개선점 (단순 DCA 대비):
    - 상승 추세 확인 후 매수 (MA20 > MA50)
    - 하락 추세에서는 매수 중지 (리스크 관리)
    - 적절한 손익 실현 (무한 보유 방지)

    적합한 투자자:
    - 장기 투자자
    - 시장 타이밍 어려움을 인정하는 투자자
    - 안정적 현금흐름 보유자 (매월 투자 자금)
    """

    def __init__(self):
        super().__init__(
            name="DCA - Dollar Cost Averaging",
            description="정기 적립식 투자 (월 1회, 추세 확인 후 매수)"
        )

    def generate_signals(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        **kwargs
    ) -> Tuple[pd.Series, pd.Series]:
        """
        진입: 매월 첫 거래일 + MA20 > MA50 (상승 추세 확인)
        청산: MA20 < MA50 (추세 전환) OR 목표 수익률 도달
        """
        # TIMEZONE 제거
        if hasattr(price_data.index, 'tz') and price_data.index.tz is not None:
            price_data = price_data.copy()
            price_data.index = price_data.index.tz_localize(None)

        close = _get_close_series(price_data)

        # 이동평균
        ma20 = close.rolling(20, min_periods=10).mean()
        ma50 = close.rolling(50, min_periods=25).mean()

        # 월별 첫 거래일 찾기
        monthly_first = pd.Series([False] * len(price_data), index=price_data.index)

        if len(price_data) > 0:
            current_month = None
            for date in price_data.index:
                month = (date.year, date.month)
                if month != current_month:
                    monthly_first.loc[date] = True
                    current_month = month

        # 진입: 매월 첫 거래일 + 상승 추세 (MA20 > MA50)
        uptrend = ma20 > ma50
        entry_signals = _to_bool_series(monthly_first & uptrend)

        # 청산: 추세 전환 (MA20 하향 돌파 MA50)
        # 또는 과도한 고점 (리밸런싱 필요)
        downtrend = ma20 < ma50
        extreme_high = close > (close.rolling(252, min_periods=100).max() * 0.95)  # 52주 최고가 근처

        exit_signals = _to_bool_series(downtrend | extreme_high)

        return entry_signals, exit_signals

    def get_risk_params(self) -> RiskParams:
        """
        DCA 리스크 관리:
        - 손절 15% (중간)
        - 익절 40% (적절한 수익 실현)
        - 100% 투자
        """
        return RiskParams(
            stop_pct=0.15,  # -15% (중간 손절)
            take_pct=0.40,  # +40% (적절한 익절)
            position_sizing="equal_weight"
        )


class WoodStrategy(MasterStrategy):
    """
    캐시 우드 - 혁신 기술 투자 전략 (ARK Invest)

    핵심 원칙:
    1. 파괴적 혁신 기술 투자 (AI, 유전체학, 블록체인, 전기차, 우주항공)
    2. 장기 성장 잠재력 > 단기 수익성
    3. 높은 매출 성장률 (25%+)
    4. 높은 변동성 감수
    5. 집중 투자 (고확신 종목)

    투자 철학:
    - "혁신은 미래 가치를 창조한다"
    - 전통적 밸류에이션 지표(P/E, P/B) 무시
    - 매출 성장률과 시장 점유율 중시
    - 5년 이상 장기 투자

    적합한 섹터:
    - 기술주 (AI, 클라우드, 핀테크)
    - 바이오테크 (유전자 치료, mRNA)
    - 전기차 및 자율주행
    - 블록체인 및 암호화폐
    """

    def __init__(self):
        super().__init__(
            name="Cathie Wood - Disruptive Innovation",
            description="혁신 기술 집중 투자 - 고성장 + 높은 변동성 감수"
        )

    def generate_signals(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        **kwargs
    ) -> Tuple[pd.Series, pd.Series]:
        """
        진입: 고성장 + 상승 모멘텀 + 거래량 증가
        청산: 성장 둔화 OR 추세 이탈

        우드 원칙: "혁신 기술은 초기 변동성이 크지만 장기적으로 성장"
        - 매출 성장률 > 25% (고성장)
        - 52주 신고가 근처 (모멘텀)
        - 골든크로스 (추세 확인)
        """
        # TIMEZONE 제거
        if hasattr(price_data.index, 'tz') and price_data.index.tz is not None:
            price_data = price_data.copy()
            price_data.index = price_data.index.tz_localize(None)

        analyzer = FundamentalAnalyzer(symbol)
        close = _get_close_series(price_data)

        entry_signals = pd.Series([False] * len(price_data), index=price_data.index)
        exit_signals = pd.Series([False] * len(price_data), index=price_data.index)

        # 기술적 조건 1: 골든크로스 (MA20 > MA50)
        ma20 = close.rolling(20).mean()
        ma50 = close.rolling(50).mean()
        ma20_prev = ma20.shift(1)
        ma50_prev = ma50.shift(1)

        golden_cross = (ma20 > ma50) & (ma20_prev <= ma50_prev)
        death_cross = (ma20 < ma50) & (ma20_prev >= ma50_prev)

        # 기술적 조건 2: 52주 최고가 근처 (상위 20% 이내 - 모멘텀 강함)
        rolling_high_252 = close.rolling(252, min_periods=100).max()
        near_high = close > (rolling_high_252 * 0.80)

        # 기술적 조건 3: 거래량 증가 (평균 대비 1.3배 이상)
        if 'volume' in price_data.columns:
            vol_ma50 = price_data['volume'].rolling(50).mean()
            volume_surge = price_data['volume'] > vol_ma50 * 1.3
        else:
            volume_surge = pd.Series([True] * len(price_data), index=price_data.index)

        # 각 날짜별로 펀더멘털 체크
        for date in price_data.index:
            # 펀더멘털: 고성장 확인
            try:
                ticker_info = analyzer.ticker.info

                # 매출 성장률 > 25% (혁신 기업 기준)
                revenue_growth = ticker_info.get('revenueGrowth', 0) or 0
                if revenue_growth < 0.25:
                    continue

                # 진입: 고성장 + 골든크로스 + 신고가 근처 + 거래량
                if golden_cross.loc[date] and near_high.loc[date] and volume_surge.loc[date]:
                    entry_signals.loc[date] = True

                # 청산: 성장 둔화 (매출 성장률 < 15%) OR 데드크로스
                if revenue_growth < 0.15 or death_cross.loc[date]:
                    exit_signals.loc[date] = True

            except Exception:
                # 펀더멘털 데이터 없으면 기술적 분석만
                if golden_cross.loc[date] and near_high.loc[date] and volume_surge.loc[date]:
                    entry_signals.loc[date] = True
                if death_cross.loc[date]:
                    exit_signals.loc[date] = True

        return entry_signals, exit_signals

    def get_risk_params(self) -> RiskParams:
        """
        혁신 기술주 리스크 관리:
        - 손절 20% (넓음, 변동성 크기 때문)
        - 익절 100% (2배 수익 목표, 장기 성장 기대)
        - 집중 투자 (equal_weight)
        """
        return RiskParams(
            stop_pct=0.20,  # -20% (넓은 손절, 변동성 감수)
            take_pct=1.00,  # +100% (2배 익절, 장기 성장 목표)
            position_sizing="equal_weight"
        )


class ChanosStrategy(MasterStrategy):
    """짐 채노스: 공매도 전략 (개선 버전)

    특징:
    - 회계 부정, 과대평가된 기업 공매도
    - 높은 부채비율, 낮은 현금흐름
    - 하락 추세 확인 후 진입

    진입 조건 (공매도):
    1. 부채비율 > 2.0 (과도한 부채)
    2. ROE < 5% (낮은 수익성)
    3. 데드크로스 (MA20 < MA50 하향 돌파)
    4. 거래량 증가 (하락 가속)

    청산 조건:
    - 골든크로스 (MA20 > MA50 상승 반전)
    - 손절: +10% (공매도는 빠른 손절 필수)

    개선 사항:
    - 손절 15% → 10% (공매도 무한 손실 리스크)
    - 데드크로스로 진입 타이밍 명확화
    """

    def __init__(self):
        super().__init__(
            name="Jim Chanos - Short Selling (Improved)",
            description="공매도 전략 - 데드크로스 + 빠른 손절"
        )

    def generate_signals(
        self,
        symbol: str,
        price_data: pd.DataFrame,
        **kwargs
    ) -> Tuple[pd.Series, pd.Series]:
        """채노스 공매도 시그널 생성

        주의: 공매도는 entry_signals가 '숏 진입', exit_signals가 '숏 청산'을 의미
        개선: 데드크로스로 진입 타이밍 명확화 + 10% 빠른 손절
        """
        # TIMEZONE 제거
        if hasattr(price_data.index, 'tz') and price_data.index.tz is not None:
            price_data = price_data.copy()
            price_data.index = price_data.index.tz_localize(None)

        analyzer = FundamentalAnalyzer(symbol)
        close = _get_close_series(price_data)

        entry_signals = pd.Series([False] * len(price_data), index=price_data.index)
        exit_signals = pd.Series([False] * len(price_data), index=price_data.index)

        # 이동평균선
        ma20 = close.rolling(20).mean()
        ma50 = close.rolling(50).mean()
        ma200 = close.rolling(200).mean()

        ma20_prev = ma20.shift(1)
        ma50_prev = ma50.shift(1)

        # 데드크로스 (MA20 < MA50 하향 돌파)
        death_cross = (ma20 < ma50) & (ma20_prev >= ma50_prev)

        # 골든크로스 (MA20 > MA50 상승 반전)
        golden_cross = (ma20 > ma50) & (ma20_prev <= ma50_prev)

        # 하락 추세 확인 (MA50 < MA200)
        downtrend = ma50 < ma200

        # 거래량
        if 'volume' in price_data.columns:
            volume = price_data['volume']
            avg_volume = volume.rolling(20).mean()
            volume_surge = volume > avg_volume * 1.2
        else:
            volume_surge = pd.Series([True] * len(price_data), index=price_data.index)

        # 각 날짜별로 펀더멘털 체크
        for date in price_data.index:
            # 진입: 데드크로스 + 하락 추세 + 거래량 증가
            if death_cross.loc[date] and downtrend.loc[date] and volume_surge.loc[date]:
                # 펀더멘털 확인 (부채 과다, 낮은 수익성)
                try:
                    ticker_info = analyzer.ticker.info
                    debt_ratio = ticker_info.get('debtToEquity', 0) / 100 if ticker_info.get('debtToEquity') else 0
                    roe = ticker_info.get('returnOnEquity', 0) or 0

                    if debt_ratio > 2.0 or roe < 0.05:
                        entry_signals.loc[date] = True
                except Exception:
                    # 펀더멘털 없이 기술적 분석만
                    entry_signals.loc[date] = True

            # 청산: 골든크로스 (상승 반전)
            if golden_cross.loc[date]:
                exit_signals.loc[date] = True

        return entry_signals, exit_signals

    def get_risk_params(self) -> RiskParams:
        """공매도 리스크 관리 - 빠른 손절 필수"""
        return RiskParams(
            stop_pct=0.10,  # +10% 손절 (공매도는 빠른 손절)
            take_pct=0.30,  # -30% 익절
            position_sizing="equal_weight"
        )


# 전략 레지스트리
MASTER_STRATEGIES = {
    "buffett": BuffettStrategy(),
    "lynch": LynchStrategy(),
    "graham": GrahamStrategy(),
    # "dalio": DalioStrategy(),  # ❌ 비활성화 (단일 종목에 부적합)
    "dca": DCAStrategy(),  # ✅ 정기 적립식 투자 (DCA)
    "livermore": LivermoreStrategy(),  # 순수 Livermore (역사적 방법론)
    "modern_livermore": ModernLivermoreStrategy(),  # 현대적 개선 Livermore
    "oneil": ONeilStrategy(),
    "wood": WoodStrategy(),  # 캐시 우드 - 혁신 기술 투자
    "chanos": ChanosStrategy(),
}


def get_strategy(strategy_name: str) -> Optional[MasterStrategy]:
    """전략 이름으로 전략 객체 가져오기"""
    return MASTER_STRATEGIES.get(strategy_name.lower())


def list_strategies() -> Dict[str, str]:
    """사용 가능한 전략 목록"""
    return {
        name: strategy.description
        for name, strategy in MASTER_STRATEGIES.items()
    }
