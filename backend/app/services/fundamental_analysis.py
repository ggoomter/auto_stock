"""
재무제표 분석 서비스: yfinance를 활용한 펀더멘털 데이터 수집 및 분석

주의: yfinance는 최근 4분기 재무제표만 제공
→ 백테스트는 최근 1년 데이터만 정확
→ 그 이전 기간은 기술적 분석만 사용
"""
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta


class FundamentalAnalyzer:
    """재무제표 기반 펀더멘털 분석 (시점별 데이터)"""

    # 실적 발표 지연 (분기말 기준 45일 후 공개)
    EARNINGS_DELAY_DAYS = 45

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.ticker = yf.Ticker(symbol)
        self._info: Optional[Dict] = None

        # 분기별 재무제표 (최근 4분기)
        self._quarterly_financials: Optional[pd.DataFrame] = None
        self._quarterly_balance_sheet: Optional[pd.DataFrame] = None

        # 한국 주식 여부 확인
        symbol_base = symbol.replace('.KS', '').replace('.KQ', '')
        self.is_korean = (symbol_base.isdigit() and len(symbol_base) == 6) or symbol.endswith(('.KS', '.KQ'))
        self.stock_code = symbol_base if self.is_korean else None

        # DART 클라이언트 (한국 주식만)
        self._dart_client = None
        if self.is_korean:
            try:
                from .dart_api import get_dart_client
                self._dart_client = get_dart_client()
            except Exception as e:
                print(f"DART API 초기화 실패: {e}")
                self._dart_client = None

    def get_info(self) -> Dict:
        """기본 정보 가져오기 (현재 시점 - 참고용만)"""
        if self._info is None:
            try:
                self._info = self.ticker.info
            except Exception as e:
                print(f"Failed to fetch info for {self.symbol}: {e}")
                self._info = {}
        return self._info

    def get_quarterly_financials(self) -> pd.DataFrame:
        """분기별 손익계산서 (최근 4분기)"""
        if self._quarterly_financials is None:
            try:
                self._quarterly_financials = self.ticker.quarterly_financials
                # 컬럼(분기 날짜)의 timezone 제거
                if not self._quarterly_financials.empty and hasattr(self._quarterly_financials.columns, 'tz'):
                    if self._quarterly_financials.columns.tz is not None:
                        self._quarterly_financials.columns = self._quarterly_financials.columns.tz_localize(None)
            except Exception as e:
                print(f"Failed to fetch quarterly financials for {self.symbol}: {e}")
                self._quarterly_financials = pd.DataFrame()
        return self._quarterly_financials

    def get_quarterly_balance_sheet(self) -> pd.DataFrame:
        """분기별 대차대조표 (최근 4분기)"""
        if self._quarterly_balance_sheet is None:
            try:
                self._quarterly_balance_sheet = self.ticker.quarterly_balance_sheet
                # 컬럼(분기 날짜)의 timezone 제거
                if not self._quarterly_balance_sheet.empty and hasattr(self._quarterly_balance_sheet.columns, 'tz'):
                    if self._quarterly_balance_sheet.columns.tz is not None:
                        self._quarterly_balance_sheet.columns = self._quarterly_balance_sheet.columns.tz_localize(None)
            except Exception as e:
                print(f"Failed to fetch quarterly balance sheet for {self.symbol}: {e}")
                self._quarterly_balance_sheet = pd.DataFrame()
        return self._quarterly_balance_sheet

    def _calculate_growth_from_financials(self, metric_name: str) -> Optional[float]:
        """
        분기별 재무제표에서 YoY 성장률 계산

        Args:
            metric_name: 'Net Income', 'Total Revenue' 등

        Returns:
            성장률 (소수, 예: 0.25 = 25%) 또는 None
        """
        try:
            financials = self.get_quarterly_financials()

            if financials.empty or len(financials.columns) < 4:
                return None

            # 지표 찾기 (대소문자 무관, 부분 일치)
            matching_rows = [
                row for row in financials.index
                if metric_name.lower() in str(row).lower()
            ]

            if not matching_rows:
                return None

            # 첫 번째 매칭 행 사용
            row_name = matching_rows[0]
            values = financials.loc[row_name]

            # 최신 분기 vs 4분기 전 (YoY)
            latest = values.iloc[0]
            year_ago = values.iloc[3] if len(values) >= 4 else None

            if pd.isna(latest) or pd.isna(year_ago) or year_ago == 0:
                return None

            growth_rate = (latest - year_ago) / abs(year_ago)
            return float(growth_rate)

        except Exception as e:
            print(f"재무제표 성장률 계산 실패 ({metric_name}): {e}")
            return None

    def get_available_date_range(self) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        펀더멘털 데이터가 사용 가능한 날짜 범위

        Returns:
            (start_date, end_date) - 백테스트 가능한 기간
        """
        financials = self.get_quarterly_financials()

        if financials.empty or len(financials.columns) == 0:
            return None, None

        # 가장 오래된 분기 + 45일 (실적 발표 지연)
        oldest_quarter = financials.columns[-1]
        start_date = oldest_quarter + timedelta(days=self.EARNINGS_DELAY_DAYS)

        # 현재 날짜까지
        end_date = datetime.now()

        return start_date, end_date

    def _get_applicable_quarter(self, as_of_date: datetime) -> Optional[pd.Timestamp]:
        """
        특정 날짜에 사용 가능한 가장 최근 분기 찾기

        Args:
            as_of_date: 기준 날짜

        Returns:
            해당 날짜에 공개된 가장 최근 분기 (45일 지연 고려)
        """
        financials = self.get_quarterly_financials()

        if financials.empty:
            return None

        # as_of_date의 타임존 확인 및 정규화
        if isinstance(as_of_date, pd.Timestamp):
            # pandas Timestamp인 경우
            if as_of_date.tz is not None:
                as_of_date = as_of_date.tz_localize(None)
        elif hasattr(as_of_date, 'tzinfo') and as_of_date.tzinfo is not None:
            # timezone-aware datetime 객체인 경우
            as_of_date = as_of_date.replace(tzinfo=None)
        # timezone-naive는 그대로 사용

        # 실적 발표 지연 고려하여 가장 최근 사용 가능한 분기 찾기
        for quarter_date in financials.columns:
            # quarter_date도 timezone 제거
            if isinstance(quarter_date, pd.Timestamp):
                if quarter_date.tz is not None:
                    quarter_date_naive = quarter_date.tz_localize(None)
                else:
                    quarter_date_naive = quarter_date
            elif hasattr(quarter_date, 'tzinfo') and quarter_date.tzinfo is not None:
                quarter_date_naive = quarter_date.replace(tzinfo=None)
            else:
                quarter_date_naive = quarter_date

            announcement_date = quarter_date_naive + timedelta(days=self.EARNINGS_DELAY_DAYS)

            if announcement_date <= as_of_date:
                return quarter_date

        return None

    # ========== 현재 시점 지표 (참고용) ==========
    def get_buffett_metrics(self) -> Dict:
        """현재 시점 워렌 버핏 지표 (참고용)"""
        info = self.get_info()

        metrics = {}
        metrics['ROE'] = info.get('returnOnEquity', None)
        if metrics['ROE']:
            metrics['ROE'] = round(metrics['ROE'] * 100, 2)

        metrics['debt_to_equity'] = info.get('debtToEquity', None)
        if metrics['debt_to_equity']:
            metrics['debt_to_equity'] = round(metrics['debt_to_equity'] / 100, 2)

        metrics['PE'] = info.get('trailingPE', None)

        # P/B: yfinance 제공 또는 계산
        pb = info.get('priceToBook', None)
        if pb is None:
            # 재무제표에서 계산 시도
            try:
                bs = self.ticker.quarterly_balance_sheet
                if not bs.empty:
                    latest = bs.columns[0]
                    tbv = bs.loc['Tangible Book Value', latest] if 'Tangible Book Value' in bs.index else None
                    shares = bs.loc['Ordinary Shares Number', latest] if 'Ordinary Shares Number' in bs.index else None
                    current_price = info.get('currentPrice')

                    if tbv and shares and shares > 0 and current_price:
                        bps = tbv / shares
                        pb = current_price / bps
                        metrics['PB'] = round(pb, 2)
                        metrics['PB_calculated'] = True
                        metrics['PB_source'] = 'calculated'
                    else:
                        metrics['PB'] = None
                else:
                    metrics['PB'] = None
            except:
                metrics['PB'] = None
        else:
            metrics['PB'] = pb
            metrics['PB_source'] = 'yfinance'

        metrics['free_cashflow'] = info.get('freeCashflow', None)

        return metrics

    def check_buffett_criteria(self) -> Dict:
        """현재 시점 워렌 버핏 기준 체크 (참고용)"""
        metrics = self.get_buffett_metrics()

        criteria = {
            'ROE_above_15': metrics.get('ROE', 0) > 15 if metrics.get('ROE') else False,
            'low_debt': metrics.get('debt_to_equity', 999) < 0.5 if metrics.get('debt_to_equity') else False,
            'positive_fcf': metrics.get('free_cashflow', 0) > 0 if metrics.get('free_cashflow') else False,
            'reasonable_PE': 0 < metrics.get('PE', 999) < 25 if metrics.get('PE') else False,
            'low_PB': metrics.get('PB', 999) < 3 if metrics.get('PB') else False,
        }

        criteria['passed_count'] = sum(criteria.values())
        criteria['total_count'] = 5
        criteria['pass_rate'] = criteria['passed_count'] / criteria['total_count']

        return criteria

    def get_buffett_condition_details(self) -> List[Dict]:
        """워렌 버핏 조건 상세 체크 (한글 포함)"""
        metrics = self.get_buffett_metrics()

        conditions = []

        # ROE 체크
        roe_value = metrics.get('ROE')
        conditions.append({
            'condition_name': '자기자본이익률',
            'condition_name_en': 'ROE (Return on Equity)',
            'required_value': '> 15%',
            'actual_value': f"{roe_value:.2f}%" if roe_value else '데이터 없음',
            'passed': (roe_value > 15) if roe_value else False
        })

        # 부채비율 체크
        debt_value = metrics.get('debt_to_equity')
        conditions.append({
            'condition_name': '부채비율',
            'condition_name_en': 'Debt to Equity',
            'required_value': '< 0.5',
            'actual_value': f"{debt_value:.2f}" if debt_value else '데이터 없음',
            'passed': (debt_value < 0.5) if debt_value else False
        })

        # 잉여현금흐름 체크
        fcf_value = metrics.get('free_cashflow')
        conditions.append({
            'condition_name': '잉여현금흐름',
            'condition_name_en': 'Free Cash Flow',
            'required_value': '> 0',
            'actual_value': f"${fcf_value:,.0f}" if fcf_value else '데이터 없음',
            'passed': (fcf_value > 0) if fcf_value else False
        })

        # P/E 체크
        pe_value = metrics.get('PE')
        conditions.append({
            'condition_name': '주가수익비율',
            'condition_name_en': 'P/E (Price to Earnings)',
            'required_value': '< 25',
            'actual_value': f"{pe_value:.2f}" if pe_value else '데이터 없음',
            'passed': (0 < pe_value < 25) if pe_value else False
        })

        # P/B 체크
        pb_value = metrics.get('PB')
        conditions.append({
            'condition_name': '주가순자산비율',
            'condition_name_en': 'P/B (Price to Book)',
            'required_value': '< 3',
            'actual_value': f"{pb_value:.2f}" if pb_value else '데이터 없음',
            'passed': (pb_value < 3) if pb_value else False
        })

        return conditions

    def get_lynch_metrics(self) -> Dict:
        """현재 시점 피터 린치 지표 (참고용)"""
        info = self.get_info()

        metrics = {}

        # 성장률 계산 우선순위: DART (한국) > yfinance > 직접 계산
        dart_earnings_growth = None
        dart_revenue_growth = None

        # 1. DART API 시도 (한국 주식만)
        if self.is_korean and self._dart_client and self.stock_code:
            try:
                dart_earnings_growth = self._dart_client.calculate_growth_rate(self.stock_code, 'net_income')
                dart_revenue_growth = self._dart_client.calculate_growth_rate(self.stock_code, 'revenue')
            except Exception as e:
                print(f"DART 성장률 계산 실패: {e}")

        # 2. yfinance 데이터
        yf_earnings_growth = info.get('earningsGrowth', None)
        yf_revenue_growth = info.get('revenueGrowth', None)

        # 3. 직접 계산 (분기별 재무제표)
        calculated_earnings_growth = self._calculate_growth_from_financials('Net Income')
        calculated_revenue_growth = self._calculate_growth_from_financials('Total Revenue')

        # 이익 성장률 결정
        if dart_earnings_growth is not None:
            metrics['earnings_growth'] = round(dart_earnings_growth * 100, 2)
            metrics['earnings_growth_source'] = 'DART'
        elif yf_earnings_growth is not None:
            metrics['earnings_growth'] = round(yf_earnings_growth * 100, 2)
            metrics['earnings_growth_source'] = 'yfinance'
        elif calculated_earnings_growth is not None:
            metrics['earnings_growth'] = round(calculated_earnings_growth * 100, 2)
            metrics['earnings_growth_source'] = 'calculated'
        else:
            metrics['earnings_growth'] = None
            metrics['earnings_growth_source'] = 'unavailable'

        # 매출 성장률 결정
        if dart_revenue_growth is not None:
            metrics['revenue_growth'] = round(dart_revenue_growth * 100, 2)
            metrics['revenue_growth_source'] = 'DART'
        elif yf_revenue_growth is not None:
            metrics['revenue_growth'] = round(yf_revenue_growth * 100, 2)
            metrics['revenue_growth_source'] = 'yfinance'
        elif calculated_revenue_growth is not None:
            metrics['revenue_growth'] = round(calculated_revenue_growth * 100, 2)
            metrics['revenue_growth_source'] = 'calculated'
        else:
            metrics['revenue_growth'] = None
            metrics['revenue_growth_source'] = 'unavailable'

        # PEG Ratio: yfinance에서 제공하지 않으면 직접 계산
        peg = info.get('pegRatio', None)

        # P/E 가져오기
        pe = info.get('trailingPE') or info.get('forwardPE')

        # 성장률 가져오기 (위에서 계산된 값)
        earnings_growth_pct = metrics.get('earnings_growth')

        if peg is not None:
            # yfinance에서 제공하는 PEG 사용
            metrics['PEG'] = round(peg, 2)
            metrics['PEG_calculated'] = False
            metrics['PEG_source'] = 'yfinance'
        elif pe and earnings_growth_pct and earnings_growth_pct > 0:
            # PEG 계산: P/E ÷ 성장률(%)
            peg = pe / earnings_growth_pct
            metrics['PEG'] = round(peg, 2)
            metrics['PEG_calculated'] = True
            metrics['PEG_source'] = 'calculated'
        else:
            # 계산 불가
            metrics['PEG'] = None
            metrics['PEG_calculated'] = False
            metrics['PEG_source'] = 'unavailable'

            # 디버깅 정보
            if not pe:
                metrics['PEG_missing_reason'] = 'P/E 없음'
            elif not earnings_growth_pct:
                metrics['PEG_missing_reason'] = '이익성장률 없음'
            elif earnings_growth_pct <= 0:
                metrics['PEG_missing_reason'] = f'성장률 음수 ({earnings_growth_pct}%)'

        return metrics

    def check_lynch_criteria(self) -> Dict:
        """현재 시점 피터 린치 기준 체크 (참고용)"""
        metrics = self.get_lynch_metrics()

        criteria = {
            'PEG_below_1': 0 < metrics.get('PEG', 999) < 1.0 if metrics.get('PEG') else False,
            'high_earnings_growth': metrics.get('earnings_growth', 0) > 20 if metrics.get('earnings_growth') else False,
            'positive_revenue_growth': metrics.get('revenue_growth', 0) > 0 if metrics.get('revenue_growth') else False,
        }

        criteria['passed_count'] = sum(criteria.values())
        criteria['total_count'] = 3
        criteria['pass_rate'] = criteria['passed_count'] / criteria['total_count']

        return criteria

    def get_lynch_condition_details(self) -> List[Dict]:
        """피터 린치 조건 상세 체크 (한글 포함)"""
        metrics = self.get_lynch_metrics()

        conditions = []

        # PEG 체크
        peg_value = metrics.get('PEG')
        peg_calculated = metrics.get('PEG_calculated', False)

        if peg_value:
            peg_display = f"{peg_value:.2f}"
            if peg_calculated:
                peg_display += " (계산됨: P/E ÷ 성장률)"
        else:
            peg_display = '데이터 없음 (P/E 또는 성장률 부재)'

        conditions.append({
            'condition_name': '주가이익성장비율',
            'condition_name_en': 'PEG (Price/Earnings to Growth)',
            'required_value': '< 1.0',
            'actual_value': peg_display,
            'passed': (0 < peg_value < 1.0) if peg_value else False
        })

        # 이익 성장률 체크
        earnings_growth_value = metrics.get('earnings_growth')
        earnings_growth_source = metrics.get('earnings_growth_source', '')

        # 데이터 출처 표시
        source_label = ""
        if 'DART' in earnings_growth_source:
            source_label = " [DART 공식 데이터]"
        elif 'yfinance' in earnings_growth_source:
            source_label = " [yfinance]"

        conditions.append({
            'condition_name': '이익 성장률',
            'condition_name_en': 'Earnings Growth',
            'required_value': '> 20%',
            'actual_value': f"{earnings_growth_value:.2f}%{source_label}" if earnings_growth_value else '데이터 없음',
            'passed': (earnings_growth_value > 20) if earnings_growth_value else False
        })

        # 매출 성장률 체크
        revenue_growth_value = metrics.get('revenue_growth')
        conditions.append({
            'condition_name': '매출 성장률',
            'condition_name_en': 'Revenue Growth',
            'required_value': '> 0%',
            'actual_value': f"{revenue_growth_value:.2f}%" if revenue_growth_value else '데이터 없음',
            'passed': (revenue_growth_value > 0) if revenue_growth_value else False
        })

        return conditions

    def get_graham_metrics(self) -> Dict:
        """현재 시점 벤저민 그레이엄 지표 (참고용)"""
        info = self.get_info()

        metrics = {}

        # P/B: yfinance 제공 또는 계산
        pb = info.get('priceToBook', None)
        if pb is None:
            # 재무제표에서 계산 시도
            try:
                bs = self.ticker.quarterly_balance_sheet
                if not bs.empty:
                    latest = bs.columns[0]
                    tbv = bs.loc['Tangible Book Value', latest] if 'Tangible Book Value' in bs.index else None
                    shares = bs.loc['Ordinary Shares Number', latest] if 'Ordinary Shares Number' in bs.index else None
                    current_price = info.get('currentPrice')

                    if tbv and shares and shares > 0 and current_price:
                        bps = tbv / shares
                        pb = current_price / bps
                        metrics['PB'] = round(pb, 2)
                        metrics['PB_calculated'] = True
                        metrics['PB_source'] = 'calculated'
                    else:
                        metrics['PB'] = None
                else:
                    metrics['PB'] = None
            except:
                metrics['PB'] = None
        else:
            metrics['PB'] = pb
            metrics['PB_source'] = 'yfinance'

        metrics['current_ratio'] = info.get('currentRatio', None)

        metrics['debt_to_equity'] = info.get('debtToEquity', None)
        if metrics['debt_to_equity']:
            metrics['debt_to_equity'] = round(metrics['debt_to_equity'] / 100, 2)

        metrics['dividend_yield'] = info.get('dividendYield', None)
        if metrics['dividend_yield']:
            metrics['dividend_yield'] = round(metrics['dividend_yield'] * 100, 2)

        return metrics

    def check_graham_criteria(self) -> Dict:
        """현재 시점 벤저민 그레이엄 기준 체크 (참고용)"""
        metrics = self.get_graham_metrics()

        criteria = {
            'deep_value_PB': 0 < metrics.get('PB', 999) < 0.67 if metrics.get('PB') else False,
            'high_current_ratio': metrics.get('current_ratio', 0) > 2.0 if metrics.get('current_ratio') else False,
            'low_debt': metrics.get('debt_to_equity', 999) < 0.5 if metrics.get('debt_to_equity') else False,
            'has_dividend': metrics.get('dividend_yield', 0) > 0 if metrics.get('dividend_yield') else False,
        }

        criteria['passed_count'] = sum(criteria.values())
        criteria['total_count'] = 4
        criteria['pass_rate'] = criteria['passed_count'] / criteria['total_count']

        return criteria

    def get_graham_condition_details(self) -> List[Dict]:
        """벤저민 그레이엄 조건 상세 체크 (한글 포함)"""
        metrics = self.get_graham_metrics()

        conditions = []

        # P/B 체크
        pb_value = metrics.get('PB')
        conditions.append({
            'condition_name': '주가순자산비율 (청산가치)',
            'condition_name_en': 'P/B (Price to Book)',
            'required_value': '< 0.67',
            'actual_value': f"{pb_value:.2f}" if pb_value else '데이터 없음',
            'passed': (0 < pb_value < 0.67) if pb_value else False
        })

        # 유동비율 체크
        current_ratio_value = metrics.get('current_ratio')
        conditions.append({
            'condition_name': '유동비율',
            'condition_name_en': 'Current Ratio',
            'required_value': '> 2.0',
            'actual_value': f"{current_ratio_value:.2f}" if current_ratio_value else '데이터 없음',
            'passed': (current_ratio_value > 2.0) if current_ratio_value else False
        })

        # 부채비율 체크
        debt_value = metrics.get('debt_to_equity')
        conditions.append({
            'condition_name': '부채비율',
            'condition_name_en': 'Debt to Equity',
            'required_value': '< 0.5',
            'actual_value': f"{debt_value:.2f}" if debt_value else '데이터 없음',
            'passed': (debt_value < 0.5) if debt_value else False
        })

        # 배당수익률 체크
        dividend_yield_value = metrics.get('dividend_yield')
        conditions.append({
            'condition_name': '배당수익률',
            'condition_name_en': 'Dividend Yield',
            'required_value': '> 0%',
            'actual_value': f"{dividend_yield_value:.2f}%" if dividend_yield_value else '데이터 없음',
            'passed': (dividend_yield_value > 0) if dividend_yield_value else False
        })

        return conditions

    def get_oneil_metrics(self) -> Dict:
        """현재 시점 윌리엄 오닐 지표 (참고용)"""
        info = self.get_info()

        metrics = {}
        metrics['earnings_growth'] = info.get('earningsGrowth', None)
        if metrics['earnings_growth']:
            metrics['earnings_growth'] = round(metrics['earnings_growth'] * 100, 2)

        metrics['revenue_growth'] = info.get('revenueGrowth', None)
        if metrics['revenue_growth']:
            metrics['revenue_growth'] = round(metrics['revenue_growth'] * 100, 2)

        metrics['ROE'] = info.get('returnOnEquity', None)
        if metrics['ROE']:
            metrics['ROE'] = round(metrics['ROE'] * 100, 2)

        return metrics

    def check_oneil_criteria(self) -> Dict:
        """현재 시점 윌리엄 오닐 기준 체크 (참고용)"""
        metrics = self.get_oneil_metrics()

        criteria = {
            'strong_earnings_growth': metrics.get('earnings_growth', 0) > 25 if metrics.get('earnings_growth') else False,
            'positive_revenue_growth': metrics.get('revenue_growth', 0) > 0 if metrics.get('revenue_growth') else False,
            'high_ROE': metrics.get('ROE', 0) > 17 if metrics.get('ROE') else False,
        }

        criteria['passed_count'] = sum(criteria.values())
        criteria['total_count'] = 3
        criteria['pass_rate'] = criteria['passed_count'] / criteria['total_count']

        return criteria

    def get_oneil_condition_details(self) -> List[Dict]:
        """윌리엄 오닐 조건 상세 체크 (한글 포함)"""
        metrics = self.get_oneil_metrics()

        conditions = []

        # 이익 성장률 체크
        earnings_growth_value = metrics.get('earnings_growth')
        conditions.append({
            'condition_name': '이익 성장률',
            'condition_name_en': 'Earnings Growth',
            'required_value': '> 25%',
            'actual_value': f"{earnings_growth_value:.2f}%" if earnings_growth_value else '데이터 없음',
            'passed': (earnings_growth_value > 25) if earnings_growth_value else False
        })

        # 매출 성장률 체크
        revenue_growth_value = metrics.get('revenue_growth')
        conditions.append({
            'condition_name': '매출 성장률',
            'condition_name_en': 'Revenue Growth',
            'required_value': '> 0%',
            'actual_value': f"{revenue_growth_value:.2f}%" if revenue_growth_value else '데이터 없음',
            'passed': (revenue_growth_value > 0) if revenue_growth_value else False
        })

        # ROE 체크
        roe_value = metrics.get('ROE')
        conditions.append({
            'condition_name': '자기자본이익률',
            'condition_name_en': 'ROE (Return on Equity)',
            'required_value': '> 17%',
            'actual_value': f"{roe_value:.2f}%" if roe_value else '데이터 없음',
            'passed': (roe_value > 17) if roe_value else False
        })

        return conditions

    # ========== 시점별 펀더멘털 체크 (백테스트용) ==========
    def check_buffett_criteria_at_date(self, as_of_date: datetime) -> bool:
        """
        특정 날짜에 버핏 기준 통과 여부

        현대 버핏 스타일: "합리적 가격의 훌륭한 기업"
        - 높은 ROE (자본 효율성)
        - 긍정적 현금흐름
        - P/E는 완화된 기준 (성장주도 인정)
        """
        applicable_quarter = self._get_applicable_quarter(as_of_date)

        # 펀더멘털 데이터 없으면 기술적 분석만 사용
        if applicable_quarter is None:
            return True  # 데이터 제약으로 통과 처리

        info = self.get_info()

        # 핵심 지표
        roe = info.get('returnOnEquity', 0)
        fcf = info.get('freeCashflow', 0)
        pe = info.get('trailingPE', 0)

        # 현대 버핏 기준: 질적 우수성 중심
        return (
            roe and roe > 0.15 and  # ROE > 15% (자본 효율성)
            fcf and fcf > 0 and  # 긍정적 현금흐름
            pe and 0 < pe < 50  # P/E < 50 (성장주 허용)
        )

    def check_lynch_criteria_at_date(self, as_of_date: datetime) -> bool:
        """
        특정 날짜에 린치 기준 통과 여부

        PEG 계산: yfinance 제공 → P/E ÷ 성장률 계산 → 성장률만 → 기술적 분석
        """
        applicable_quarter = self._get_applicable_quarter(as_of_date)

        if applicable_quarter is None:
            # 펀더멘털 데이터가 없으면 기술적 분석만 진행 (골든크로스)
            return True  # 기술적 조건만으로 매매

        # get_lynch_metrics()를 사용하여 계산된 PEG 포함 모든 지표 가져오기
        metrics = self.get_lynch_metrics()

        peg = metrics.get('PEG')  # yfinance 또는 계산된 PEG
        earnings_growth_pct = metrics.get('earnings_growth')  # 성장률 (%)

        # PEG 있으면 (yfinance 제공 또는 계산됨) PEG와 성장률 모두 체크
        if peg and peg > 0:
            # PEG < 1.0이고 성장률 > 20%
            return (
                0 < peg < 1.0 and  # PEG < 1
                earnings_growth_pct and earnings_growth_pct > 20  # 20% 이상 성장
            )
        # PEG 없지만 성장률 있으면 성장률만으로 판단
        elif earnings_growth_pct and earnings_growth_pct > 0:
            return earnings_growth_pct > 15  # 15% 이상 성장으로 완화
        # 둘 다 없으면 기술적 분석만 (골든크로스)
        else:
            return True  # 기술적 조건만으로 매매

    def check_graham_criteria_at_date(self, as_of_date: datetime) -> bool:
        """특정 날짜에 그레이엄 기준 통과 여부"""
        applicable_quarter = self._get_applicable_quarter(as_of_date)

        if applicable_quarter is None:
            return False

        info = self.get_info()
        pb = info.get('priceToBook', None)
        current_ratio = info.get('currentRatio', None)

        # P/B 있으면: 둘 다 체크, 없으면: current_ratio만 체크
        if pb is not None:
            return (
                0 < pb < 0.67 and  # 청산가치 이하
                current_ratio is not None and current_ratio > 2.0  # 높은 유동비율
            )
        else:
            # P/B 데이터 없는 경우 (한국 주식): current_ratio만 체크
            return current_ratio is not None and current_ratio > 2.0

    def check_oneil_criteria_at_date(self, as_of_date: datetime) -> bool:
        """특정 날짜에 오닐 기준 통과 여부"""
        applicable_quarter = self._get_applicable_quarter(as_of_date)

        if applicable_quarter is None:
            return False

        info = self.get_info()
        earnings_growth = info.get('earningsGrowth', 0)

        return (
            earnings_growth and earnings_growth > 0.25  # 25% 이상 성장
        )
