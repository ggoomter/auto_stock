
    def get_metrics_at_date(
        self,
        stock_code: str,
        target_date: str,
        current_price: float
    ) -> Dict[str, Optional[float]]:
        """
        특정 날짜 시점의 펀더멘털 지표 계산 (백테스트용)

        해당 날짜 기준 가장 최근 공시된 분기 재무제표로 P/E, P/B, ROE 계산

        공시 지연 고려 (45일):
        - 1~5월: 전년도 4Q 사용
        - 6~8월: 당해연도 1Q 사용
        - 9~11월: 당해연도 2Q 사용
        - 12월: 당해연도 3Q 사용

        Args:
            stock_code: 6자리 종목코드 (예: "005930")
            target_date: 백테스트 날짜 (YYYY-MM-DD)
            current_price: 해당 날짜의 종가

        Returns:
            {'PE': P/E비율, 'PB': P/B비율, 'ROE': ROE(%),
             'EPS': 주당순이익, 'BPS': 주당순자산, 'quarter': '2024Q2'}
        """
        try:
            # 1. 날짜 파싱
            target_dt = datetime.strptime(target_date, "%Y-%m-%d")
            year = target_dt.year
            month = target_dt.month

            # 2. 공시 지연 45일 고려하여 사용 가능한 분기 결정
            if month <= 5:
                # 1~5월: 전년도 4Q 사용
                fiscal_year = year - 1
                fiscal_quarter = 4
            elif month <= 8:
                # 6~8월: 당해연도 1Q 사용
                fiscal_year = year
                fiscal_quarter = 1
            elif month <= 11:
                # 9~11월: 당해연도 2Q 사용
                fiscal_year = year
                fiscal_quarter = 2
            else:
                # 12월: 당해연도 3Q 사용
                fiscal_year = year
                fiscal_quarter = 3

            quarter_str = f"{fiscal_year}Q{fiscal_quarter}"

            logger.info(f"📅 {target_date} → {quarter_str} 재무제표 사용 (종목: {stock_code})")

            # 3. 기업코드 조회
            corp_code = self.get_corp_code(stock_code)
            if not corp_code:
                return {'quarter': quarter_str, 'error': '기업코드 없음'}

            # 4. DART API로 해당 분기 재무제표 가져오기
            reprt_code = {1: "11013", 2: "11012", 3: "11014", 4: "11011"}[fiscal_quarter]
            bsns_year = str(fiscal_year)

            df = self.get_financial_statement(corp_code, fiscal_year, reprt_code)

            if df.empty:
                logger.warning(f"DART API 데이터 없음 ({quarter_str})")
                return {'quarter': quarter_str, 'error': '재무제표 없음'}

            # 5. 필요한 지표 추출
            net_income = None
            total_equity = None
            shares = None

            # 순이익 추출
            net_income_row = df[df['account_nm'].str.contains('당기순이익', na=False)]
            if not net_income_row.empty:
                net_income = float(net_income_row.iloc[0]['thstrm_amount'])

            # 자본총계 추출
            equity_row = df[df['account_nm'].str.contains('자본총계', na=False)]
            if not equity_row.empty:
                total_equity = float(equity_row.iloc[0]['thstrm_amount'])

            # 발행주식수 추출 (주식 정보 API)
            try:
                stock_url = "https://opendart.fss.or.kr/api/stockTotqySttus.json"
                stock_params = {
                    'crtfc_key': self.api_key,
                    'corp_code': corp_code,
                    'bsns_year': bsns_year,
                    'reprt_code': reprt_code
                }

                stock_resp = requests.get(stock_url, params=stock_params, timeout=10)
                stock_data = stock_resp.json()

                if stock_data.get('status') == '000' and stock_data.get('list'):
                    shares = float(stock_data['list'][0].get('istc_totqy', 0))
            except Exception as e:
                logger.warning(f"발행주식수 조회 실패: {e}")

            # 6. 지표 계산
            result = {'quarter': quarter_str}

            if net_income and shares:
                eps = net_income / shares
                result['EPS'] = eps
                result['PE'] = current_price / eps if eps > 0 else None
            else:
                result['EPS'] = None
                result['PE'] = None

            if total_equity and shares:
                bps = total_equity / shares
                result['BPS'] = bps
                result['PB'] = current_price / bps if bps > 0 else None
            else:
                result['BPS'] = None
                result['PB'] = None

            if net_income and total_equity:
                result['ROE'] = (net_income / total_equity) * 100 if total_equity > 0 else None
            else:
                result['ROE'] = None

            logger.info(f"✅ {quarter_str} 지표 계산 완료: PE={result.get('PE')}, PB={result.get('PB')}, ROE={result.get('ROE')}")

            return result

        except Exception as e:
            logger.error(f"❌ get_metrics_at_date 오류 ({stock_code}, {target_date}): {e}")
            return {'quarter': 'ERROR', 'error': str(e)}
