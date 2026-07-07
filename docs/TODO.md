# TODO — 남은 작업 (2026-07-06 기준)

Phase 1~4 완료 후 이월된 작업 목록. 우선순위순.

## 높음 (다음 작업 후보)

1. **장중 10분 주기 포트폴리오 스냅샷 루프** (스펙 4.2.4 미구현) — 현재 스냅샷은 자동매매 엔진이 돌 때만 저장됨. 엔진 미가동 일자는 수익 곡선에 공백. `daily_jobs`에 스냅샷 루프 추가.
2. **`/compare-strategies`·`/llm-strategy` 엔드포인트 수리** — 내부 API 계약 불일치(존재하지 않는 생성자 인자·메서드 시그니처)로 호출 즉시 500. 사용하려면 `/master-strategy`와 동일 계약으로 재작성 필요. (전략 비교 화면이 이 API에 의존)
3. **커스텀 전략 파서 재작성** — `parser.py`가 스텁 수준(광고하는 AND/OR/괄호 문법 대부분 미구현). 커스텀 전략의 신뢰성 전제.
4. **몬테카를로 재작성** — 리샘플 후 지표·시그널 재계산 구조로 (현재 비활성화됨, 사유 주석 참조).
5. **생존 편향(survivorship bias) 해소** — 종목 유니버스가 "현재 살아남은 종목" 수동 선정이라 과거 성과가 과대평가됨. 상장폐지 종목 포함한 시점별 유니버스 필요 (KRX 벌크 데이터 확보와 연계).

## 중간

6. LIVE 매매 개방 전 필수: paper/live 체결 테이블 분리(모드 컬럼), 브로커 `buy_stock/sell_stock` 구현, `/trading/start` 인증, 시장가 주문 삼항식 버그(`broker_api.py`).
6-1. 한국 주식 백테스트 초기자본 100만원(`routes.py:377`) — 고가주는 리스크 캡(2%) 적용 시 0~1주만 매수 가능해 결과 왜곡. 최소 1,000만원 이상으로 상향 또는 사용자 입력화.
6-2. super_momentum이 KR 5종목 11년 검증에서 PF 0.58(음의 기대값) — 한국 시장 실전 투입 부적격. 조건 재점검 또는 시장별 활성화 플래그.
6-3-1. **KR 확대 유니버스 노출 관리 재설계** — 5차 검증: 네이버 시총 상위 289종목에서 livermore_atr가 PF 1.06/1.27(양 기간 양수)이나 MDD -31~-49%로 운용 불가. 동시 포지션 수 상한·신호 우선순위·국면별 노출 조절 설계 필요. 데이터 스누핑 누적 주의 — 설계 변경 1~2회 후 페이퍼 전진 검증으로 전환.
6-3. **한국 시장 전략 재설계** — KR 20종목 2차 검증에서 modern_livermore PF 0.70, buffett PF 0.86 모두 음의 기대값, lynch만 PF 1.52(단 CAGR 0.8%). 현재 전략셋으로는 한국 시장 실전 부적격. 상세: `claudedocs/strategy_verification_2026-07-06.md` 2차 검증.
6-4. **위기 매수 프로토콜 2단계** — 1단계(감지·알림·상태 영속화, `crisis_protocol.py`)는 완료. 2단계: 트랜치 발동 시 페이퍼 계좌에 지수 ETF(KODEX200/SPY) 분할 매수 자동 실행 + 예비대 현금 계정 분리 + rearm 시 보유분 정리 로직.
6-4-1. **페이퍼 트레이딩 부분 익절 v2** — v1(2026-07-07 가동)은 전량 청산 규칙만 지원(손절 -8%·샹들리에·200일선 → stop 인상 방식). +20%/50%·+40%/25% 부분 익절은 포지션 수량 분할 모델 필요. 또한 진입 당일 손절 터치는 미정산(reconcile이 익일부터 스캔) — 급락 가드로 완화되나 인지할 것.
6-5. **당일 시세 실시간 반영** — 추천/매도 진단이 일봉 캐시(전일 종가) 기준이라 당일 급락(예: 2026-07-07 SK하이닉스 -9.1%)이 미반영. 장중에는 naver/realtime_data로 당일 가격을 병합하거나 최소한 "전일 종가 기준" 경고를 더 강하게 표시.
7. Chanos 전략 — backtest 엔진에 숏 로직 구현 후 재등록.
8. KRX 일반 계정 확보 시 `.env`에 KRX_ID/PW — KRX 벌크 데이터(PBR 포함) 우선 사용됨. 현재는 네이버 폴백(PER·ROE만).
9. daily_pnl·승률 등 당일 지표가 메모리(trade_history) 의존 — 재시작 시 리셋. DB 기반 복원.
10. 추천 RSI(Cutler)와 차트 RSI(Wilder, pandas-ta) 수치 불일치 — 지표 계산 일원화.
11. 종목별 뉴스 페이지 수집 + 관심·보유·추천 종목 우선 뉴스 (스펙 5.3 잔여).
12. `/today/recommendations` 응답에 종목 뉴스 조인 (현재 프론트가 별도 호출).

## 낮음 (정리·품질)

13. 한국 종목 판별 로직 4곳 복제(routes.py 2곳·paper_execution·TS 프론트) — 유틸 통합.
14. 죽은 프론트 컴포넌트 3개(StrategyForm·ImprovedStrategyForm·StrategyBuilder, ~847줄) 제거, 차트 라이브러리 4종 → 통일, 다크모드 전면 정비, 접근성(aria) 도입.
15. 루트 산재 `test_*.py` 30여 개 → tests/legacy 이동 또는 삭제.
16. ComparisonPage의 AVAILABLE_STRATEGIES에 서버에 없는 전략(dalio/soros/druckenmiller) 나열 — 서버 목록 연동.
17. `main.py` 글로벌 예외 핸들러의 `G:` 드라이브 하드코딩 제거, 예외 문자열 응답 노출 중단.
18. 뉴스 크롤러 EUC-KR → cp949 승격(확장 음절), price-history OHLC NaN dropna, StockChart 이벤트 필터-기간 동기화, StockChart console.log 제거.
19. Pydantic v2 deprecation(config.py class Config) 정리.
20. `backend/.env`의 DART 키 재발급 권장(평문 로컬 노출 이력).
21. backtest.py 잔여 정밀도 이슈 — 부분 청산도 갭 상승 시 시가 체결로(현재 목표가 체결 = 보수적이라 저평가 방향), 부분 청산 trade의 `balance_after` 미계산(0.0), 일별 equity가 당일 체결 전 기준으로 기록됨(1일 지연 근사), `allow_partial_profits` 플래그가 partial_rules에 미반영.

## 참고

- 상세 이월 내역: `.superpowers/sdd/progress.md` (로컬, gitignore)
- 스펙: `docs/superpowers/specs/2026-07-02-simulation-news-recommendation-design.md`
- 계획: `docs/superpowers/plans/` (Phase 1~4)
