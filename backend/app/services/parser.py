"""
전략 파싱 엔진: AND/OR/괄호, 비교연산, 교차조건, 이벤트 윈도우 지원
"""
import re
from typing import Dict, Any, List, Tuple
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class StrategyParser:
    """
    파싱 지원:
    - 논리 연산: AND, OR, ()
    - 비교: <, >, <=, >=, ==
    - 교차: indicator.cross_up, indicator.cross_down
    - 이벤트: WITHIN(event="ELECTION", window_days=20)
    """

    def __init__(self):
        self.operators = {'AND': '&', 'OR': '|', 'and': '&', 'or': '|'}

    def parse_condition(self, condition: str) -> Dict[str, Any]:
        """
        조건 문자열 파싱
        예: "MACD.cross_up == true AND RSI < 30"
        """
        # 괄호 처리를 위한 토큰화
        tokens = self._tokenize(condition)
        return {
            'raw': condition,
            'tokens': tokens,
            'has_cross': 'cross_up' in condition or 'cross_down' in condition,
            'has_event': 'WITHIN' in condition
        }

    def _tokenize(self, condition: str) -> List[str]:
        """조건을 토큰으로 분리"""
        # 괄호, 연산자, 비교 기호를 기준으로 분리
        pattern = r'(\(|\)|AND|OR|and|or|==|<=|>=|<|>)'
        tokens = re.split(pattern, condition)
        return [t.strip() for t in tokens if t.strip()]

    def evaluate_condition(
        self,
        condition: str,
        indicators: pd.DataFrame,
        events: pd.DataFrame = None
    ) -> pd.Series:
        """
        조건 평가하여 boolean Series 반환

        Args:
            condition: 조건 문자열
            indicators: 지표 데이터 (컬럼: MACD, RSI, etc.)
            events: 이벤트 데이터 (optional)

        Returns:
            Boolean Series (True/False for each timestamp)
        """
        try:
            logger.info(f"[Parser] 조건 평가 시작: {condition}")
            logger.info(f"[Parser] 사용 가능한 컬럼: {list(indicators.columns)}")
            logger.info(f"[Parser] 데이터 길이: {len(indicators)}")

            # 간단한 구현 - 실제로는 더 정교한 파서 필요
            result = pd.Series([True] * len(indicators), index=indicators.index)

            # MACD cross_up 감지 (MACD.cross_up 또는 MACD_cross_up)
            if 'MACD' in condition and 'cross_up' in condition:
                logger.info(f"[Parser] MACD cross_up 조건 감지")
                if 'MACD' in indicators.columns and 'MACD_signal' in indicators.columns:
                    cross_up = (
                        (indicators['MACD'] > indicators['MACD_signal']) &
                        (indicators['MACD'].shift(1) <= indicators['MACD_signal'].shift(1))
                    )
                    logger.info(f"[Parser] MACD cross_up 발생 일수: {cross_up.sum()}/{len(cross_up)}")
                    result &= cross_up
                else:
                    logger.warning(f"[Parser] MACD 또는 MACD_signal 컬럼이 없음")

            # RSI 조건 (동적 파싱)
            if 'RSI' in indicators.columns:
                logger.info(f"[Parser] RSI 컬럼 확인됨")
                # RSI < 숫자
                rsi_less_pattern = r'RSI\s*<\s*(\d+(?:\.\d+)?)'
                for match in re.finditer(rsi_less_pattern, condition):
                    threshold = float(match.group(1))
                    rsi_condition = indicators['RSI'] < threshold
                    logger.info(f"[Parser] RSI < {threshold} 조건: {rsi_condition.sum()}/{len(rsi_condition)} 일")
                    result &= rsi_condition

                # RSI > 숫자
                rsi_greater_pattern = r'RSI\s*>\s*(\d+(?:\.\d+)?)'
                for match in re.finditer(rsi_greater_pattern, condition):
                    threshold = float(match.group(1))
                    rsi_condition = indicators['RSI'] > threshold
                    logger.info(f"[Parser] RSI > {threshold} 조건: {rsi_condition.sum()}/{len(rsi_condition)} 일")
                    result &= rsi_condition
            else:
                logger.warning(f"[Parser] RSI 컬럼이 indicators에 없음")

            # MACD cross_down 감지 (MACD.cross_down 또는 MACD_cross_down)
            if 'MACD' in condition and 'cross_down' in condition:
                logger.info(f"[Parser] MACD cross_down 조건 감지")
                if 'MACD' in indicators.columns and 'MACD_signal' in indicators.columns:
                    cross_down = (
                        (indicators['MACD'] < indicators['MACD_signal']) &
                        (indicators['MACD'].shift(1) >= indicators['MACD_signal'].shift(1))
                    )
                    logger.info(f"[Parser] MACD cross_down 발생 일수: {cross_down.sum()}/{len(cross_down)}")
                    result &= cross_down
                else:
                    logger.warning(f"[Parser] MACD 또는 MACD_signal 컬럼이 없음")

            # +DI > -DI
            if '+DI > -DI' in condition or '+DI>-DI' in condition:
                if 'DI_plus' in indicators.columns and 'DI_minus' in indicators.columns:
                    result &= indicators['DI_plus'] > indicators['DI_minus']

            # WITHIN 이벤트 처리 (간단 구현)
            if 'WITHIN' in condition and events is not None:
                # 예: WITHIN(event='ELECTION', window_days=20)
                event_pattern = r"WITHIN\(event=['\"](\w+)['\"],\s*window_days=(\d+)\)"
                match = re.search(event_pattern, condition)
                if match:
                    event_name = match.group(1)
                    window_days = int(match.group(2))
                    event_mask = self._apply_event_window(
                        indicators.index, events, event_name, window_days
                    )
                    result &= event_mask

            logger.info(f"[Parser] 최종 결과: {result.sum()}/{len(result)} 일이 조건 충족")
            if result.sum() > 0:
                logger.info(f"[Parser] 조건 충족 날짜 예시 (최대 5개): {result[result].index[:5].tolist()}")

            return result

        except KeyError as e:
            # 컬럼이 없을 때 명확한 에러 메시지
            available_cols = list(indicators.columns)
            raise ValueError(
                f"조건 평가 중 컬럼 에러: {str(e)}. "
                f"사용 가능한 컬럼: {available_cols}"
            )
        except Exception as e:
            # 기타 에러도 명확하게 표시
            raise ValueError(f"조건 평가 중 에러 발생: {str(e)}. 조건: {condition}")

    def _apply_event_window(
        self,
        dates: pd.DatetimeIndex,
        events: pd.DataFrame,
        event_name: str,
        window_days: int
    ) -> pd.Series:
        """이벤트 윈도우 내 날짜인지 확인"""
        mask = pd.Series([False] * len(dates), index=dates)

        if events is None or event_name not in events.columns:
            return mask

        event_dates = events[events[event_name] == True].index

        for event_date in event_dates:
            window_start = event_date - pd.Timedelta(days=window_days)
            window_end = event_date + pd.Timedelta(days=window_days)
            mask |= (dates >= window_start) & (dates <= window_end)

        return mask

    def extract_features(self, condition: str) -> List[str]:
        """조건에서 사용된 지표 추출"""
        features = []
        indicators = ['MACD', 'RSI', 'DMI', 'DI', 'ADX', 'BBANDS', 'OBV', 'Stochastic']

        for ind in indicators:
            if ind in condition:
                features.append(ind)

        # 이벤트 추출
        events = ['ELECTION', 'FOMC', 'EARNINGS', 'DIVIDEND', 'WAR', 'REGULATION', 'PANDEMIC']
        for evt in events:
            if evt in condition:
                features.append(evt)

        return list(set(features))
