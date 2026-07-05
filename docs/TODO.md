# TODO — 남은 작업 (2026-07-06 기준)

Phase 1~4 완료 후 이월된 작업 목록. 우선순위순.

## 높음 (다음 작업 후보)

1. **장중 10분 주기 포트폴리오 스냅샷 루프** (스펙 4.2.4 미구현) — 현재 스냅샷은 자동매매 엔진이 돌 때만 저장됨. 엔진 미가동 일자는 수익 곡선에 공백. `daily_jobs`에 스냅샷 루프 추가.
2. **`/compare-strategies`·`/llm-strategy` 엔드포인트 수리** — 내부 API 계약 불일치(존재하지 않는 생성자 인자·메서드 시그니처)로 호출 즉시 500. 사용하려면 `/master-strategy`와 동일 계약으로 재작성 필요. (전략 비교 화면이 이 API에 의존)
3. **커스텀 전략 파서 재작성** — `parser.py`가 스텁 수준(광고하는 AND/OR/괄호 문법 대부분 미구현). 커스텀 전략의 신뢰성 전제.
4. **몬테카를로 재작성** — 리샘플 후 지표·시그널 재계산 구조로 (현재 비활성화됨, 사유 주석 참조).

## 중간

5. LIVE 매매 개방 전 필수: paper/live 체결 테이블 분리(모드 컬럼), 브로커 `buy_stock/sell_stock` 구현, `/trading/start` 인증, 시장가 주문 삼항식 버그(`broker_api.py`).
6. Chanos 전략 — backtest 엔진에 숏 로직 구현 후 재등록.
7. KRX 일반 계정 확보 시 `.env`에 KRX_ID/PW — KRX 벌크 데이터(PBR 포함) 우선 사용됨. 현재는 네이버 폴백(PER·ROE만).
8. daily_pnl·승률 등 당일 지표가 메모리(trade_history) 의존 — 재시작 시 리셋. DB 기반 복원.
9. 추천 RSI(Cutler)와 차트 RSI(Wilder, pandas-ta) 수치 불일치 — 지표 계산 일원화.
10. 종목별 뉴스 페이지 수집 + 관심·보유·추천 종목 우선 뉴스 (스펙 5.3 잔여).
11. `/today/recommendations` 응답에 종목 뉴스 조인 (현재 프론트가 별도 호출).

## 낮음 (정리·품질)

12. 한국 종목 판별 로직 4곳 복제(routes.py 2곳·paper_execution·TS 프론트) — 유틸 통합.
13. 죽은 프론트 컴포넌트 3개(StrategyForm·ImprovedStrategyForm·StrategyBuilder, ~847줄) 제거, 차트 라이브러리 4종 → 통일, 다크모드 전면 정비, 접근성(aria) 도입.
14. 루트 산재 `test_*.py` 30여 개 → tests/legacy 이동 또는 삭제.
15. ComparisonPage의 AVAILABLE_STRATEGIES에 서버에 없는 전략(dalio/soros/druckenmiller) 나열 — 서버 목록 연동.
16. `main.py` 글로벌 예외 핸들러의 `G:` 드라이브 하드코딩 제거, 예외 문자열 응답 노출 중단.
17. 뉴스 크롤러 EUC-KR → cp949 승격(확장 음절), price-history OHLC NaN dropna, StockChart 이벤트 필터-기간 동기화, StockChart console.log 제거.
18. Pydantic v2 deprecation(config.py class Config) 정리.
19. `backend/.env`의 DART 키 재발급 권장(평문 로컬 노출 이력).

## 참고

- 상세 이월 내역: `.superpowers/sdd/progress.md` (로컬, gitignore)
- 스펙: `docs/superpowers/specs/2026-07-02-simulation-news-recommendation-design.md`
- 계획: `docs/superpowers/plans/` (Phase 1~4)
