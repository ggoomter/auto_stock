"""
한국/미국 주식 종목 데이터베이스

FinanceDataReader를 사용하여 KRX 전체 종목 자동 로드
"""
import pandas as pd
from typing import List, Dict, Optional
import yfinance as yf
from ..core.logging_config import logger
from datetime import datetime, timedelta
import threading


class StockDatabase:
    """종목 데이터베이스 (한글 검색 지원)"""

    def __init__(self):
        self.korean_stocks = None
        self.us_etfs = self._load_us_etfs()
        self.last_update = None
        self.cache_duration = timedelta(days=1)  # 1일 캐시
        self._loading = False  # 로딩 중 플래그
        self._load_thread = None  # 백그라운드 스레드

        # 백그라운드 스레드에서 비동기 로드
        logger.info("StockDatabase 초기화 시작 (백그라운드 로드)")
        self._start_background_loading()

    def _load_korean_stocks(self) -> pd.DataFrame:
        """
        한국 전체 종목 리스트 로드 (FinanceDataReader 사용)

        자동으로 KOSPI + KOSDAQ + ETF 전체 가져오기
        """
        try:
            import FinanceDataReader as fdr

            logger.info("KRX 전체 종목 리스트 로딩 중...")

            # KOSPI, KOSDAQ, ETF 통합
            all_stocks = []

            # 1. KOSPI 종목
            try:
                kospi = fdr.StockListing('KOSPI')
                kospi['market'] = 'KS'
                all_stocks.append(kospi)
                logger.info(f"KOSPI {len(kospi)}개 종목 로드 완료")
            except Exception as e:
                logger.warning(f"KOSPI 로드 실패: {str(e)}")

            # 2. KOSDAQ 종목
            try:
                kosdaq = fdr.StockListing('KOSDAQ')
                kosdaq['market'] = 'KQ'
                all_stocks.append(kosdaq)
                logger.info(f"KOSDAQ {len(kosdaq)}개 종목 로드 완료")
            except Exception as e:
                logger.warning(f"KOSDAQ 로드 실패: {str(e)}")

            # 3. ETF
            try:
                etf = fdr.StockListing('ETF/KR')
                etf['market'] = 'KS'
                all_stocks.append(etf)
                logger.info(f"ETF {len(etf)}개 종목 로드 완료")
            except Exception as e:
                logger.warning(f"ETF 로드 실패: {str(e)}")

            if not all_stocks:
                logger.error("모든 종목 로드 실패, 기본 데이터 사용")
                return self._load_fallback_stocks()

            # 통합 및 정리
            df = pd.concat(all_stocks, ignore_index=True)

            # 컬럼 정리 (유연하게)
            rename_map = {
                'Code': 'code',
                'Name': 'nameKo',
                'Market': 'marketOld'
            }

            # Sector, Industry 컬럼이 있으면 rename
            if 'Sector' in df.columns:
                rename_map['Sector'] = 'sector'
            if 'Industry' in df.columns:
                rename_map['Industry'] = 'industry'

            df = df.rename(columns=rename_map)

            # Symbol 생성 (Code + .KS or .KQ)
            df['symbol'] = df.apply(
                lambda row: f"{row['code']}.{row['market']}",
                axis=1
            )

            # 영문명은 한글명과 동일 (yfinance가 제공)
            df['nameEn'] = df['nameKo']

            # sector 컬럼이 없으면 빈 문자열로 생성
            if 'sector' not in df.columns:
                df['sector'] = ''

            # 필요한 컬럼만 선택
            df = df[['symbol', 'nameKo', 'nameEn', 'sector']].fillna('')

            logger.info(f"총 {len(df)}개 한국 종목 로드 완료")
            self.last_update = datetime.now()

            return df

        except Exception as e:
            logger.error(f"FinanceDataReader 로드 실패: {str(e)}, 기본 데이터 사용")
            return self._load_fallback_stocks()

    def _load_fallback_stocks(self) -> pd.DataFrame:
        """FinanceDataReader 실패 시 또는 로딩 중 fallback 데이터"""
        stocks = [
            # 주요 종목 (로딩 전 즉시 검색 가능)
            {"symbol": "005930.KS", "nameKo": "삼성전자", "nameEn": "Samsung Electronics", "sector": "Technology"},
            {"symbol": "000660.KS", "nameKo": "SK하이닉스", "nameEn": "SK Hynix", "sector": "Technology"},
            {"symbol": "035420.KS", "nameKo": "네이버", "nameEn": "NAVER", "sector": "Technology"},
            {"symbol": "035720.KS", "nameKo": "카카오", "nameEn": "Kakao", "sector": "Technology"},
            {"symbol": "068270.KS", "nameKo": "셀트리온", "nameEn": "Celltrion", "sector": "Healthcare"},
            {"symbol": "096530.KQ", "nameKo": "씨젠", "nameEn": "Seegene", "sector": "Healthcare"},
            {"symbol": "005380.KS", "nameKo": "현대차", "nameEn": "Hyundai Motor", "sector": "Automotive"},
            {"symbol": "000270.KS", "nameKo": "기아", "nameEn": "Kia", "sector": "Automotive"},
            {"symbol": "051910.KS", "nameKo": "LG화학", "nameEn": "LG Chem", "sector": "Chemicals"},
            {"symbol": "006400.KS", "nameKo": "삼성SDI", "nameEn": "Samsung SDI", "sector": "Battery"},
            {"symbol": "207940.KS", "nameKo": "삼성바이오로직스", "nameEn": "Samsung Biologics", "sector": "Healthcare"},
            {"symbol": "373220.KS", "nameKo": "LG에너지솔루션", "nameEn": "LG Energy Solution", "sector": "Battery"},
            {"symbol": "069500.KS", "nameKo": "KODEX 200", "nameEn": "KODEX KOSPI 200", "sector": "Index ETF"},
            {"symbol": "122630.KS", "nameKo": "KODEX 레버리지", "nameEn": "KODEX Leverage", "sector": "Leveraged ETF"},
        ]
        return pd.DataFrame(stocks)

    def _load_us_etfs(self) -> Dict[str, str]:
        """미국 주요 ETF 한글명 매핑"""
        return {
            "SPY": "S&P 500 ETF",
            "QQQ": "나스닥 100 ETF",
            "DIA": "다우존스 ETF",
            "IWM": "러셀 2000 ETF",
            "VTI": "미국 전체 시장 ETF",
            "SQQQ": "나스닥 3배 인버스",
            "SPXU": "S&P 500 3배 인버스",
            "TQQQ": "나스닥 3배 레버리지",
            "UPRO": "S&P 500 3배 레버리지",
            "SH": "S&P 500 인버스",
            "PSQ": "나스닥 인버스",
            "GLD": "골드 ETF",
            "TLT": "미국 20년 국채 ETF",
        }

    def _start_background_loading(self):
        """백그라운드 스레드에서 한국 주식 데이터 로드"""
        if self.korean_stocks is None and not self._loading and self._load_thread is None:
            self._loading = True

            def _load_in_background():
                try:
                    logger.info("백그라운드에서 한국 주식 데이터 로딩 시작...")
                    self.korean_stocks = self._load_korean_stocks()
                    logger.info(f"백그라운드 로딩 완료: {len(self.korean_stocks)}개 종목")
                except Exception as e:
                    logger.error(f"백그라운드 로딩 실패: {str(e)}")
                    self.korean_stocks = self._load_fallback_stocks()
                finally:
                    self._loading = False

            self._load_thread = threading.Thread(target=_load_in_background, daemon=True)
            self._load_thread.start()
            logger.info("백그라운드 로딩 스레드 시작")

    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """통합 검색 (한글/영문/심볼)"""
        query_lower = query.lower().strip()
        results = []

        # 로딩 중이거나 데이터 없으면 fallback 먼저 검색 (빠른 응답)
        if self.korean_stocks is None or self._loading:
            logger.info("Fallback 데이터로 빠른 검색 (전체 로딩 백그라운드 진행)")
            fallback_data = self._load_fallback_stocks()

            # Fallback에서 검색
            fallback_matches = fallback_data[
                fallback_data['nameKo'].str.contains(query_lower, case=False, na=False) |
                fallback_data['nameEn'].str.contains(query_lower, case=False, na=False) |
                fallback_data['symbol'].str.contains(query.upper(), case=False, na=False)
            ]

            for _, row in fallback_matches.iterrows():
                results.append({
                    "symbol": row['symbol'],
                    "nameKo": row['nameKo'],
                    "nameEn": row['nameEn'],
                    "market": "KR",
                    "sector": row['sector'],
                    "source": "fallback"
                })

            # Fallback에서 찾았으면 바로 반환 (빠른 응답)
            if results:
                return results[:limit]

        # 전체 데이터가 로드되었으면 전체 검색
        if self.korean_stocks is not None and not self._loading:
            kr_matches = self.korean_stocks[
                self.korean_stocks['nameKo'].str.contains(query_lower, case=False, na=False) |
                self.korean_stocks['nameEn'].str.contains(query_lower, case=False, na=False) |
                self.korean_stocks['symbol'].str.contains(query.upper(), case=False, na=False)
            ]
        else:
            # 아직 로딩 중이면 빈 결과
            kr_matches = pd.DataFrame()

        for _, row in kr_matches.iterrows():
            results.append({
                "symbol": row['symbol'],
                "nameKo": row['nameKo'],
                "nameEn": row['nameEn'],
                "market": "KR",
                "sector": row['sector'],
                "source": "database"
            })

        # 2. 미국 주식 심볼 검색 (yfinance)
        query_upper = query.upper()
        if not query_upper.endswith('.KS') and not query_upper.endswith('.KQ'):
            try:
                ticker = yf.Ticker(query_upper)
                info = ticker.info

                if info and info.get('symbol'):
                    # 미국 ETF 한글명 매핑
                    name_ko = self.us_etfs.get(query_upper, info.get('longName', query_upper))

                    results.append({
                        "symbol": query_upper,
                        "nameKo": name_ko,
                        "nameEn": info.get('longName', info.get('shortName', query_upper)),
                        "market": "US",
                        "sector": info.get('sector', info.get('category', 'Unknown')),
                        "industry": info.get('industry', ''),
                        "marketCap": info.get('marketCap', info.get('totalAssets', 0)),
                        "source": "yfinance"
                    })
            except Exception as e:
                logger.debug(f"yfinance 검색 실패 ({query_upper}): {str(e)}")

        # 중복 제거
        seen = set()
        unique_results = []
        for r in results:
            if r['symbol'] not in seen:
                seen.add(r['symbol'])
                unique_results.append(r)

        return unique_results[:limit]


# 전역 인스턴스
_stock_db: Optional[StockDatabase] = None


def get_stock_database() -> StockDatabase:
    """전역 종목 데이터베이스 반환"""
    global _stock_db
    if _stock_db is None:
        try:
            _stock_db = StockDatabase()
        except Exception as e:
            logger.error(f"StockDatabase 초기화 실패: {str(e)}")
            # 초기화 실패 시에도 인스턴스 생성 (fallback 데이터 사용)
            _stock_db = StockDatabase()
    return _stock_db
