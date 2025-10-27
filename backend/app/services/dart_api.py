"""
DART (전자공시) API 클라이언트
한국 상장 기업의 재무제표 데이터 수집

API 키 발급: https://opendart.fss.or.kr/
"""
from typing import Dict, List, Optional
import requests
from datetime import datetime, timedelta
import pandas as pd
from ..core.logging_config import logger
import xml.etree.ElementTree as ET
import zipfile
import io
import os
import json
from pathlib import Path


class DartAPI:
    """DART API 클라이언트"""

    BASE_URL = "https://opendart.fss.or.kr/api"
    CACHE_DIR = Path("backend/cache/dart")
    CORP_CODE_CACHE = CACHE_DIR / "corp_code_mapping.json"

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: DART API 키 (없으면 settings에서 읽음)
        """
        if api_key is None:
            try:
                from ..core.config import settings
                api_key = settings.DART_API_KEY
            except:
                pass

        self.api_key = api_key
        self.enabled = bool(self.api_key)

        # 기업코드 매핑 테이블 (메모리 캐싱)
        self._corp_code_map: Optional[Dict[str, str]] = None

        if not self.api_key:
            logger.warning("DART API 키가 설정되지 않았습니다. yfinance로 대체됩니다. backend/.env 파일에 DART_API_KEY를 설정하세요.")
        else:
            # 캐시 디렉토리 생성
            self.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _get(self, endpoint: str, params: Dict) -> Dict:
        """API 호출"""
        if not self.api_key:
            raise ValueError("DART API 키가 필요합니다")

        params['crtfc_key'] = self.api_key
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # 에러 체크
            if data.get('status') != '000':
                error_msg = data.get('message', 'Unknown error')
                raise Exception(f"DART API 오류: {error_msg}")

            return data
        except Exception as e:
            logger.error(f"DART API 호출 실패 ({endpoint}): {str(e)}")
            raise

    def _download_corp_code_xml(self) -> bool:
        """
        DART에서 기업코드 XML 다운로드 및 파싱

        Returns:
            성공 여부
        """
        if not self.api_key:
            return False

        try:
            # corpCode.xml 다운로드 (ZIP 압축)
            url = f"{self.BASE_URL}/corpCode.xml"
            params = {'crtfc_key': self.api_key}

            logger.info("DART 기업코드 목록 다운로드 중...")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            # ZIP 파일 압축 해제
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                # CORPCODE.xml 파일 추출
                xml_content = z.read('CORPCODE.xml')

            # XML 파싱
            root = ET.fromstring(xml_content)

            # stock_code → corp_code 매핑 생성
            mapping = {}
            for corp in root.findall('list'):
                stock_code = corp.findtext('stock_code', '').strip()
                corp_code = corp.findtext('corp_code', '').strip()
                corp_name = corp.findtext('corp_name', '').strip()

                # 상장 기업만 (stock_code가 있는 경우)
                if stock_code and corp_code:
                    mapping[stock_code] = {
                        'corp_code': corp_code,
                        'corp_name': corp_name
                    }

            # JSON으로 캐싱
            with open(self.CORP_CODE_CACHE, 'w', encoding='utf-8') as f:
                json.dump(mapping, f, ensure_ascii=False, indent=2)

            logger.info(f"DART 기업코드 {len(mapping)}개 다운로드 완료")
            return True

        except Exception as e:
            logger.error(f"DART 기업코드 다운로드 실패: {str(e)}")
            return False

    def _load_corp_code_map(self) -> Dict[str, str]:
        """
        기업코드 매핑 테이블 로드 (캐시 우선)

        Returns:
            {stock_code: corp_code} 딕셔너리
        """
        # 메모리 캐시 확인
        if self._corp_code_map is not None:
            return self._corp_code_map

        # 파일 캐시 확인 (7일 이내)
        if self.CORP_CODE_CACHE.exists():
            cache_age = datetime.now() - datetime.fromtimestamp(self.CORP_CODE_CACHE.stat().st_mtime)
            if cache_age.days < 7:
                try:
                    with open(self.CORP_CODE_CACHE, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # corp_code만 추출 (corp_name 제거)
                        self._corp_code_map = {k: v['corp_code'] for k, v in data.items()}
                        logger.info(f"DART 기업코드 캐시 로드 ({len(self._corp_code_map)}개)")
                        return self._corp_code_map
                except Exception as e:
                    logger.warning(f"캐시 로드 실패: {str(e)}")

        # 캐시 없으면 다운로드
        if self._download_corp_code_xml():
            return self._load_corp_code_map()  # 재귀 호출 (다운로드 후 재로드)
        else:
            self._corp_code_map = {}
            return {}

    def get_corp_code(self, stock_code: str) -> Optional[str]:
        """
        주식 코드로 기업 고유번호 조회

        Args:
            stock_code: 6자리 주식 코드 (예: 005930)

        Returns:
            8자리 기업 고유번호 또는 None
        """
        if not self.api_key:
            return None

        # 매핑 테이블 로드
        mapping = self._load_corp_code_map()

        # 주식 코드 정규화 (앞 0 제거하지 않음)
        stock_code_clean = stock_code.replace('.KS', '').replace('.KQ', '')

        # 조회
        corp_code = mapping.get(stock_code_clean)

        if not corp_code:
            logger.warning(f"DART: {stock_code_clean} 기업코드 매핑 없음")

        return corp_code

    def get_financial_statement(
        self,
        corp_code: str,
        year: int,
        report_type: str = "11011",  # 사업보고서
        fs_div: str = "CFS"  # 연결재무제표
    ) -> pd.DataFrame:
        """
        재무제표 조회

        Args:
            corp_code: 기업 고유번호
            year: 사업연도
            report_type: 보고서 코드 (11011=사업보고서, 11012=반기보고서, 11013=1분기보고서, 11014=3분기보고서)
            fs_div: CFS(연결), OFS(별도)

        Returns:
            재무제표 DataFrame
        """
        endpoint = "fnlttSinglAcntAll.json"
        params = {
            'corp_code': corp_code,
            'bsns_year': str(year),
            'reprt_code': report_type,
            'fs_div': fs_div
        }

        data = self._get(endpoint, params)

        if 'list' not in data:
            return pd.DataFrame()

        df = pd.DataFrame(data['list'])
        return df

    def get_quarterly_financials(
        self,
        stock_code: str,
        num_quarters: int = 4
    ) -> Dict[str, List]:
        """
        최근 N개 분기 재무제표 조회

        Args:
            stock_code: 6자리 주식 코드
            num_quarters: 조회할 분기 수

        Returns:
            {
                'quarters': ['2024Q3', '2024Q2', ...],
                'net_income': [1234, 5678, ...],
                'revenue': [9999, 8888, ...],
                'operating_income': [...],
                'total_assets': [...],
                'total_equity': [...]
            }
        """
        corp_code = self.get_corp_code(stock_code)
        if not corp_code:
            return {}

        result = {
            'quarters': [],
            'net_income': [],
            'revenue': [],
            'operating_income': [],
            'total_assets': [],
            'total_equity': []
        }

        # 현재 날짜 기준으로 조회 가능한 분기 계산
        now = datetime.now()
        current_year = now.year
        current_month = now.month

        # 현재 분기 계산 (1월-3월=Q1, 4월-6월=Q2, 7월-9월=Q3, 10월-12월=Q4)
        current_quarter = (current_month - 1) // 3 + 1

        quarters_fetched = 0
        max_attempts = 12  # 최대 12개 분기까지만 시도 (3년치)
        attempts = 0

        # 현재 분기부터 역순으로 조회 (최신부터)
        year = current_year
        quarter = current_quarter

        while quarters_fetched < num_quarters and attempts < max_attempts:
            attempts += 1

            # 분기 → 보고서 코드 매핑
            report_code_map = {
                1: '11013',  # 1분기보고서
                2: '11012',  # 반기보고서
                3: '11014',  # 3분기보고서
                4: '11011'   # 사업보고서
            }

            report_code = report_code_map.get(quarter)
            quarter_label = f'{year}Q{quarter}'

            # DART는 분기 보고서 공시까지 약 45일 소요
            # 현재 분기는 아직 공시 안 되었을 가능성 높음 → 스킵
            is_current_quarter = (year == current_year and quarter == current_quarter)

            if not is_current_quarter:
                try:
                    df = self.get_financial_statement(corp_code, year, report_code)

                    if not df.empty:
                        # 당기순이익
                        net_income_row = df[df['account_nm'].str.contains('당기순이익', na=False)]
                        if not net_income_row.empty:
                            net_income = float(net_income_row.iloc[0]['thstrm_amount'])
                        else:
                            net_income = None

                        # 매출액
                        revenue_row = df[df['account_nm'].str.contains('매출액', na=False)]
                        if not revenue_row.empty:
                            revenue = float(revenue_row.iloc[0]['thstrm_amount'])
                        else:
                            revenue = None

                        # 영업이익
                        op_income_row = df[df['account_nm'].str.contains('영업이익', na=False)]
                        if not op_income_row.empty:
                            op_income = float(op_income_row.iloc[0]['thstrm_amount'])
                        else:
                            op_income = None

                        result['quarters'].append(quarter_label)
                        result['net_income'].append(net_income)
                        result['revenue'].append(revenue)
                        result['operating_income'].append(op_income)

                        quarters_fetched += 1

                except Exception as e:
                    # 에러 로깅은 최대 3번만 (스팸 방지)
                    if attempts <= 3:
                        logger.warning(f"분기 데이터 조회 실패 ({year}, {quarter_label}): {str(e)}")

            # 이전 분기로 이동
            quarter -= 1
            if quarter < 1:
                quarter = 4
                year -= 1

        # 조회 결과 로깅
        if quarters_fetched == 0:
            logger.warning(f"DART API: {stock_code} 재무 데이터 없음 ({attempts}회 시도)")
        elif quarters_fetched < num_quarters:
            logger.info(f"DART API: {stock_code} {quarters_fetched}/{num_quarters}개 분기만 조회됨")

        return result

    def calculate_growth_rate(
        self,
        stock_code: str,
        metric: str = 'net_income'
    ) -> Optional[float]:
        """
        YoY 성장률 계산

        Args:
            stock_code: 6자리 주식 코드
            metric: 'net_income', 'revenue', 'operating_income'

        Returns:
            성장률 (소수, 예: 0.25 = 25%) 또는 None
        """
        if not self.enabled:
            return None

        financials = self.get_quarterly_financials(stock_code, num_quarters=4)

        if metric not in financials or len(financials[metric]) < 4:
            return None

        values = financials[metric]

        # 최신 분기 vs 4분기 전 (YoY)
        latest = values[0]
        year_ago = values[3]

        if latest is None or year_ago is None or year_ago == 0:
            return None

        growth_rate = (latest - year_ago) / abs(year_ago)
        return growth_rate


# 전역 인스턴스
_dart_client: Optional[DartAPI] = None


def get_dart_client() -> DartAPI:
    """전역 DART 클라이언트 반환"""
    global _dart_client
    if _dart_client is None:
        _dart_client = DartAPI()
    return _dart_client
