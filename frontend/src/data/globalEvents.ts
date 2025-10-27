// 주요 글로벌 경제/정치 이벤트
export interface GlobalEvent {
  date: string;
  title: string;
  description: string;
  category: 'crisis' | 'election' | 'policy' | 'pandemic' | 'war' | 'tech';
  impact: 'positive' | 'negative' | 'neutral';
  // 종목별 영향도 (선택적)
  symbolImpacts?: Record<string, 'positive' | 'negative' | 'neutral'>;
}

export const globalEvents: GlobalEvent[] = [
  // 2008-2010
  { date: '2008-09-15', title: '리먼 브라더스 파산', description: '글로벌 금융위기 시작', category: 'crisis', impact: 'negative' },
  { date: '2008-10-03', title: '미국 구제금융법 통과', description: '7천억 달러 구제금융', category: 'policy', impact: 'positive' },
  { date: '2009-03-09', title: '증시 바닥', description: 'S&P 500 최저점 (666)', category: 'crisis', impact: 'negative' },
  { date: '2010-05-06', title: '그리스 금융위기', description: '유럽 재정위기 시작', category: 'crisis', impact: 'negative' },

  // 2011-2015
  { date: '2011-08-05', title: '미국 신용등급 강등', description: 'S&P, AAA→AA+ 강등', category: 'crisis', impact: 'negative' },
  { date: '2012-06-29', title: 'EU 정상회담', description: '유럽 은행 구제 합의', category: 'policy', impact: 'positive' },
  { date: '2013-05-22', title: '테이퍼링 발표', description: 'Fed 양적완화 축소 시사', category: 'policy', impact: 'negative' },
  { date: '2014-10-29', title: 'QE3 종료', description: '미국 양적완화 종료', category: 'policy', impact: 'neutral' },
  { date: '2015-08-11', title: '중국 위안화 평가절하', description: '신흥국 통화위기', category: 'crisis', impact: 'negative' },

  // 2016-2020
  { date: '2016-06-23', title: '브렉시트 투표', description: '영국 EU 탈퇴 결정', category: 'election', impact: 'negative' },
  {
    date: '2016-11-08',
    title: '트럼프 당선',
    description: '미국 대선, 트럼프 승리 (산업별 영향 상이)',
    category: 'election',
    impact: 'neutral',
    symbolImpacts: {
      'AAPL': 'negative',  // 중국 관세 우려
      'TSLA': 'positive',   // 규제 완화 기대
      'XOM': 'positive',    // 석유/에너지 규제 완화
      'GOOGL': 'neutral',   // 영향 중립
    }
  },
  { date: '2018-03-22', title: '미중 무역전쟁', description: '트럼프 중국 관세 부과', category: 'policy', impact: 'negative' },
  { date: '2019-08-14', title: '미중 무역협상 결렬', description: '관세 추가 인상 발표', category: 'policy', impact: 'negative' },
  { date: '2020-01-30', title: 'WHO 팬데믹 선언', description: 'COVID-19 글로벌 확산', category: 'pandemic', impact: 'negative' },
  { date: '2020-03-23', title: '코로나 증시 폭락', description: 'S&P 500 -34% 폭락', category: 'crisis', impact: 'negative' },
  { date: '2020-03-27', title: 'CARES Act 통과', description: '2조 달러 경기부양', category: 'policy', impact: 'positive' },
  {
    date: '2020-11-03',
    title: '바이든 당선',
    description: '미국 대선, 바이든 승리 (친환경 정책 기대)',
    category: 'election',
    impact: 'neutral',
    symbolImpacts: {
      'AAPL': 'positive',   // 중국 관계 개선 기대
      'TSLA': 'positive',   // 전기차 보조금 확대
      'XOM': 'negative',    // 화석연료 규제 강화
      'NVDA': 'positive',   // 반도체 투자 확대
    }
  },

  // 2021-2023
  { date: '2021-01-27', title: 'GameStop 사태', description: '밈 주식 열풍', category: 'tech', impact: 'neutral' },
  { date: '2021-11-10', title: '인플레이션 급등', description: 'CPI 6.2% 기록', category: 'crisis', impact: 'negative' },
  { date: '2022-02-24', title: '러시아-우크라이나 전쟁', description: '러시아 우크라이나 침공', category: 'war', impact: 'negative' },
  { date: '2022-03-16', title: 'Fed 금리 인상', description: '기준금리 0.25%p 인상', category: 'policy', impact: 'negative' },
  { date: '2022-06-13', title: '인플레이션 40년 최고', description: 'CPI 9.1% 기록', category: 'crisis', impact: 'negative' },
  { date: '2022-11-30', title: 'ChatGPT 출시', description: 'AI 혁명 시작', category: 'tech', impact: 'positive' },
  { date: '2023-03-10', title: 'SVB 파산', description: '실리콘밸리 은행 파산', category: 'crisis', impact: 'negative' },
  { date: '2023-05-01', title: 'Fed 금리 5.0%', description: '기준금리 5.0~5.25%', category: 'policy', impact: 'neutral' },

  // 2024-2025
  { date: '2024-01-01', title: 'AI 반도체 호황', description: 'NVIDIA 사상 최고가', category: 'tech', impact: 'positive' },
  { date: '2024-03-20', title: 'Fed 금리 동결', description: '인플레이션 안정화', category: 'policy', impact: 'positive' },
  {
    date: '2024-11-05',
    title: '트럼프 재선',
    description: '미국 대선, 트럼프 승리 (관세/규제정책 주목)',
    category: 'election',
    impact: 'neutral',
    symbolImpacts: {
      'AAPL': 'negative',  // 중국 공급망 의존, 관세 리스크
      'TSLA': 'positive',   // 일론 머스크 친분, 규제 완화
      'NVDA': 'negative',   // 중국 AI칩 수출 규제 강화 우려
      'MSFT': 'neutral',    // 다각화된 비즈니스
      'GOOGL': 'negative',  // 반독점 규제 강화 가능성
    }
  },
  { date: '2025-01-20', title: '트럼프 취임', description: '제47대 미국 대통령 취임', category: 'election', impact: 'neutral' },
];

// ⚠️ 주의: 이 데이터는 샘플 데모용입니다.
//
// 📊 데이터 출처:
// - 수동으로 작성한 역사적 이벤트 (2008-2025)
// - 실제 API 연동 없음
// - 교육 및 데모 목적으로만 사용
//
// 🔌 실제 서비스 구축 시:
// - 상세 가이드: 프로젝트 루트의 DATA_SOURCES.md 참고
// - API 연동 방법: REAL_DATA_INTEGRATION.md 참고
// - 추천 API: News API, Finnhub, FRED API
//
// ⚠️ 실제 투자 결정에 사용 금지!

// 종목별 주요 이벤트
export const companyEvents: Record<string, GlobalEvent[]> = {
  AAPL: [
    { date: '2007-06-29', title: 'iPhone 출시', description: '첫 아이폰 출시', category: 'tech', impact: 'positive' },
    { date: '2010-04-03', title: 'iPad 출시', description: '태블릿 시장 개척', category: 'tech', impact: 'positive' },
    { date: '2011-10-05', title: '스티브 잡스 사망', description: 'CEO 스티브 잡스 별세', category: 'tech', impact: 'negative' },
    { date: '2014-09-09', title: 'iPhone 6 출시', description: '대화면 아이폰 출시', category: 'tech', impact: 'positive' },
    { date: '2018-08-02', title: '시총 1조 달러 돌파', description: '최초 시총 1조 달러', category: 'tech', impact: 'positive' },
    { date: '2020-01-28', title: 'iPhone 12 5G', description: '5G 아이폰 출시', category: 'tech', impact: 'positive' },
    { date: '2023-06-05', title: 'Vision Pro 공개', description: 'AR/VR 헤드셋 공개', category: 'tech', impact: 'positive' },
  ],
  TSLA: [
    { date: '2010-06-29', title: 'TSLA IPO', description: '나스닥 상장', category: 'tech', impact: 'positive' },
    { date: '2012-06-22', title: 'Model S 출시', description: '첫 양산형 전기차', category: 'tech', impact: 'positive' },
    { date: '2016-03-31', title: 'Model 3 예약 40만대', description: 'Model 3 사전예약 폭발적 반응', category: 'tech', impact: 'positive' },
    { date: '2017-07-28', title: 'Model 3 출시', description: '대중형 전기차 출시', category: 'tech', impact: 'positive' },
    { date: '2018-08-07', title: '일론 머스크 트윗 사태', description: '비상장 전환 트윗 논란', category: 'tech', impact: 'negative' },
    { date: '2019-01-07', title: '상하이 기가팩토리 착공', description: '중국 첫 해외 공장 건설 시작', category: 'tech', impact: 'positive' },
    { date: '2019-12-30', title: '상하이 공장 차량 인도 시작', description: 'Made in China Model 3 첫 인도', category: 'tech', impact: 'positive' },
    { date: '2020-01-29', title: '시총 1,000억 돌파', description: '테슬라 급등', category: 'tech', impact: 'positive' },
    { date: '2020-12-21', title: 'S&P 500 편입', description: 'S&P 500 지수 편입', category: 'tech', impact: 'positive' },
    { date: '2021-03-25', title: '베를린 기가팩토리 발표', description: '독일 공장 건설 계획', category: 'tech', impact: 'positive' },
    { date: '2021-04-26', title: 'Q1 실적 사상 최대', description: '분기 순이익 사상 최고 기록', category: 'tech', impact: 'positive' },
    { date: '2021-10-25', title: '시총 1조 달러', description: '시가총액 1조 달러 돌파', category: 'tech', impact: 'positive' },
    { date: '2022-03-22', title: '베를린·텍사스 공장 오픈', description: '독일/미국 신규 공장 동시 가동', category: 'tech', impact: 'positive' },
    { date: '2022-08-17', title: '3:1 주식 분할', description: '주식 분할로 접근성 향상', category: 'tech', impact: 'neutral' },
    { date: '2023-01-25', title: '2022 배달 목표 달성', description: '연간 130만대 인도', category: 'tech', impact: 'positive' },
    { date: '2023-04-05', title: '멕시코 공장 발표', description: '멕시코 몬테레이 기가팩토리 건설', category: 'tech', impact: 'positive' },
    { date: '2024-04-23', title: 'FSD 12.3 출시', description: '완전자율주행 베타 버전 업데이트', category: 'tech', impact: 'positive' },
    { date: '2024-08-08', title: '로보택시 공개 연기', description: 'Robotaxi 발표 10월로 연기', category: 'tech', impact: 'negative' },
    { date: '2024-10-10', title: 'We, Robot 이벤트', description: '로보택시 Cybercab 공개', category: 'tech', impact: 'positive' },
  ],
  NVDA: [
    { date: '2016-05-06', title: 'GPU 컴퓨팅 성장', description: 'AI용 GPU 수요 급증', category: 'tech', impact: 'positive' },
    { date: '2018-09-13', title: 'RTX 2080 출시', description: '레이트레이싱 GPU 첫 출시', category: 'tech', impact: 'positive' },
    { date: '2020-09-01', title: 'ARM 인수 발표', description: '400억 달러 인수 계획', category: 'tech', impact: 'positive' },
    { date: '2020-09-17', title: 'RTX 30 시리즈 품귀', description: '암호화폐 채굴 수요 폭증', category: 'tech', impact: 'positive' },
    { date: '2022-02-09', title: 'ARM 인수 철회', description: '인수 계획 포기', category: 'tech', impact: 'negative' },
    { date: '2022-05-25', title: 'A100 텐서코어 GPU', description: 'AI 데이터센터용 GPU 강세', category: 'tech', impact: 'positive' },
    { date: '2022-09-20', title: 'RTX 40 시리즈 발표', description: 'Ada Lovelace 아키텍처 공개', category: 'tech', impact: 'positive' },
    { date: '2023-03-21', title: 'GTC 2023 기조연설', description: 'Jensen Huang AI 미래 비전 발표', category: 'tech', impact: 'positive' },
    { date: '2023-05-24', title: 'AI 붐 수혜', description: 'ChatGPT 열풍으로 급등', category: 'tech', impact: 'positive' },
    { date: '2023-08-23', title: 'Q2 실적 폭발', description: '매출 109억 달러, 예상 88% 초과', category: 'tech', impact: 'positive' },
    { date: '2023-11-21', title: 'H100 공급 부족', description: 'AI 칩 수요 급증으로 품귀', category: 'tech', impact: 'positive' },
    { date: '2024-02-21', title: '시총 2조 달러', description: '시가총액 2조 달러 돌파', category: 'tech', impact: 'positive' },
    { date: '2024-03-18', title: 'GTC 2024 Blackwell 발표', description: '차세대 B200 GPU 공개', category: 'tech', impact: 'positive' },
    { date: '2024-06-05', title: '시총 3조 달러 돌파', description: 'Apple 제치고 시총 2위', category: 'tech', impact: 'positive' },
    { date: '2024-06-18', title: '시총 1위 등극', description: 'Microsoft 제치고 세계 1위', category: 'tech', impact: 'positive' },
    { date: '2024-08-28', title: 'Q2 실적 발표', description: '매출 300억 달러 돌파', category: 'tech', impact: 'positive' },
  ],
  MSFT: [
    { date: '2014-02-04', title: '사티아 나델라 CEO', description: '새 CEO 취임', category: 'tech', impact: 'positive' },
    { date: '2018-11-30', title: '시총 1조 달러', description: '애플 이후 두 번째', category: 'tech', impact: 'positive' },
    { date: '2019-10-25', title: 'Azure 성장', description: '클라우드 사업 급성장', category: 'tech', impact: 'positive' },
    { date: '2023-01-23', title: 'OpenAI 100억 투자', description: 'ChatGPT 개발사 투자', category: 'tech', impact: 'positive' },
  ],
  GOOGL: [
    { date: '2015-08-10', title: 'Alphabet 재편', description: '지주회사 체제 전환', category: 'tech', impact: 'neutral' },
    { date: '2020-01-16', title: '시총 1조 달러', description: '시가총액 1조 달러 돌파', category: 'tech', impact: 'positive' },
    { date: '2023-02-06', title: 'Bard 공개', description: 'AI 챗봇 바드 출시', category: 'tech', impact: 'positive' },
  ],
};

// 이벤트 카테고리별 색상
export const eventColors = {
  crisis: '#EF4444',      // 빨강
  election: '#3B82F6',    // 파랑
  policy: '#10B981',      // 초록
  pandemic: '#8B5CF6',    // 보라
  war: '#F59E0B',         // 주황
  tech: '#06B6D4',        // 청록
};

// 이벤트 카테고리별 아이콘
export const eventIcons = {
  crisis: '⚠️',
  election: '🗳️',
  policy: '📜',
  pandemic: '😷',
  war: '⚔️',
  tech: '💡',
};
