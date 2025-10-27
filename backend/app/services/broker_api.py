"""
증권사 API 연동
- 한국투자증권 (KIS)
- 키움증권 (준비중)
"""
import os
import requests
from typing import Dict, List, Optional
from datetime import datetime
from ..core.logging_config import logger


class KoreaInvestmentAPI:
    """한국투자증권 Open API"""

    def __init__(self):
        self.app_key = os.getenv("KIS_APP_KEY")
        self.app_secret = os.getenv("KIS_APP_SECRET")
        self.account_no = os.getenv("KIS_ACCOUNT_NO")
        self.base_url = os.getenv("KIS_BASE_URL", "https://openapi.koreainvestment.com:9443")

        # 실전 vs 모의
        self.is_real = os.getenv("KIS_REAL_TRADING", "false").lower() == "true"
        self.access_token: Optional[str] = None

        if not all([self.app_key, self.app_secret, self.account_no]):
            logger.warning("한국투자증권 API 키가 설정되지 않았습니다.")

    def is_enabled(self) -> bool:
        """API가 활성화되어 있는지 확인"""
        return all([self.app_key, self.app_secret, self.account_no])

    async def get_access_token(self) -> Optional[str]:
        """
        접근 토큰 발급

        Returns:
            access_token
        """
        if not self.is_enabled():
            return None

        try:
            url = f"{self.base_url}/oauth2/tokenP"
            headers = {"content-type": "application/json"}
            body = {
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.app_secret
            }

            response = requests.post(url, json=body, headers=headers)
            response.raise_for_status()
            data = response.json()

            self.access_token = data['access_token']
            logger.info("한국투자증권 토큰 발급 완료")
            return self.access_token

        except Exception as e:
            logger.error(f"토큰 발급 실패: {e}")
            return None

    async def get_current_price(self, symbol: str) -> Optional[float]:
        """
        현재가 조회

        Args:
            symbol: 종목코드 (6자리, 예: 005930 = 삼성전자)

        Returns:
            현재가
        """
        if not self.access_token:
            await self.get_access_token()

        try:
            url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price"
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "FHKST01010100"  # 주식현재가 시세
            }
            params = {
                "FID_COND_MRKT_DIV_CODE": "J",  # 주식
                "FID_INPUT_ISCD": symbol
            }

            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            if data['rt_cd'] == '0':
                return float(data['output']['stck_prpr'])  # 주식현재가
            else:
                logger.error(f"현재가 조회 실패: {data['msg1']}")
                return None

        except Exception as e:
            logger.error(f"현재가 조회 오류: {e}")
            return None

    async def place_order(
        self,
        symbol: str,
        order_type: str,  # "buy" or "sell"
        quantity: int,
        price: Optional[float] = None  # None = 시장가
    ) -> Optional[Dict]:
        """
        주문 실행

        Args:
            symbol: 종목코드 (6자리)
            order_type: "buy" 또는 "sell"
            quantity: 주문 수량
            price: 지정가 (None이면 시장가)

        Returns:
            주문 결과
        """
        if not self.access_token:
            await self.get_access_token()

        try:
            # 실전 vs 모의 tr_id
            if order_type == "buy":
                tr_id = "TTTC0802U" if self.is_real else "VTTC0802U"
            else:
                tr_id = "TTTC0801U" if self.is_real else "VTTC0801U"

            url = f"{self.base_url}/uapi/domestic-stock/v1/trading/order-cash"
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": tr_id
            }

            # 계좌번호 분리 (앞 8자리 + 뒤 2자리)
            account_no_prefix = self.account_no[:8]
            account_no_suffix = self.account_no[8:]

            body = {
                "CANO": account_no_prefix,
                "ACNT_PRDT_CD": account_no_suffix,
                "PDNO": symbol,  # 종목코드
                "ORD_DVSN": "01" if price else "01",  # 00=시장가, 01=지정가
                "ORD_QTY": str(quantity),
                "ORD_UNPR": str(int(price)) if price else "0"  # 주문단가
            }

            response = requests.post(url, json=body, headers=headers)
            response.raise_for_status()
            data = response.json()

            if data['rt_cd'] == '0':
                logger.info(f"주문 성공: {symbol} {order_type} {quantity}주 @ {price or '시장가'}")
                return {
                    "order_no": data['output']['ODNO'],  # 주문번호
                    "symbol": symbol,
                    "order_type": order_type,
                    "quantity": quantity,
                    "price": price,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                logger.error(f"주문 실패: {data['msg1']}")
                return None

        except Exception as e:
            logger.error(f"주문 오류: {e}")
            return None

    async def get_balance(self) -> Optional[Dict]:
        """
        계좌 잔고 조회

        Returns:
            {
                "cash": 1000000,
                "total_value": 1500000,
                "positions": [...]
            }
        """
        if not self.access_token:
            await self.get_access_token()

        try:
            url = f"{self.base_url}/uapi/domestic-stock/v1/trading/inquire-balance"
            headers = {
                "content-type": "application/json",
                "authorization": f"Bearer {self.access_token}",
                "appkey": self.app_key,
                "appsecret": self.app_secret,
                "tr_id": "TTTC8434R" if self.is_real else "VTTC8434R"
            }

            account_no_prefix = self.account_no[:8]
            account_no_suffix = self.account_no[8:]

            params = {
                "CANO": account_no_prefix,
                "ACNT_PRDT_CD": account_no_suffix,
                "AFHR_FLPR_YN": "N",  # 시간외단일가여부
                "OFL_YN": "",
                "INQR_DVSN": "01",  # 조회구분
                "UNPR_DVSN": "01",
                "FUND_STTL_ICLD_YN": "N",
                "FNCG_AMT_AUTO_RDPT_YN": "N",
                "PRCS_DVSN": "00",
                "CTX_AREA_FK100": "",
                "CTX_AREA_NK100": ""
            }

            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            if data['rt_cd'] == '0':
                output1 = data['output1']  # 종목별 잔고
                output2 = data['output2'][0]  # 계좌 요약

                positions = []
                for item in output1:
                    if int(item['hldg_qty']) > 0:  # 보유 수량이 있는 경우만
                        positions.append({
                            "symbol": item['pdno'],  # 종목코드
                            "name": item['prdt_name'],  # 종목명
                            "quantity": int(item['hldg_qty']),  # 보유수량
                            "avg_price": float(item['pchs_avg_pric']),  # 매입평균가
                            "current_price": float(item['prpr']),  # 현재가
                            "pnl": float(item['evlu_pfls_amt']),  # 평가손익
                            "pnl_pct": float(item['evlu_pfls_rt'])  # 평가손익률
                        })

                return {
                    "cash": float(output2['dnca_tot_amt']),  # 예수금총액
                    "total_value": float(output2['tot_evlu_amt']),  # 총평가금액
                    "total_pnl": float(output2['evlu_pfls_smtl_amt']),  # 평가손익합계
                    "positions": positions
                }
            else:
                logger.error(f"잔고 조회 실패: {data['msg1']}")
                return None

        except Exception as e:
            logger.error(f"잔고 조회 오류: {e}")
            return None


# 미국 주식용 (준비중)
class IBKRApi:
    """Interactive Brokers API (미국 주식)"""
    # TODO: IBKR API 연동
    pass


# 싱글톤
_kis_api = None


def get_broker_api(broker: str = "kis") -> Optional[KoreaInvestmentAPI]:
    """증권사 API 싱글톤"""
    global _kis_api

    if broker == "kis":
        if _kis_api is None:
            _kis_api = KoreaInvestmentAPI()
        return _kis_api
    else:
        logger.error(f"지원하지 않는 증권사: {broker}")
        return None
