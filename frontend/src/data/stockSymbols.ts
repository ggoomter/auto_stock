// 주요 종목 데이터베이스 (한글명 포함)
//
// ⚠️ 주의: 수동으로 작성한 샘플 데이터 (88개 종목)
//
// 📊 데이터 출처:
// - 수동으로 선별한 미국 60개 + 한국 28개 주요 종목
// - 개별 종목 + 인덱스 ETF + 인버스/레버리지 ETF 포함
// - 자동완성 검색 기능을 위한 최소 데이터셋
//
// 🔌 실제 서비스 구축 시:
// - 전체 종목 리스트 API 연동 필요
// - 추천: FMP API, IEX Cloud, Yahoo Finance
// - 상세 가이드: 프로젝트 루트의 DATA_SOURCES.md 참고

export interface StockSymbol {
  symbol: string;
  nameKo: string;
  nameEn: string;
  market: 'US' | 'KR';
  sector?: string;
}

export const stockSymbols: StockSymbol[] = [
  // 미국 주요 기술주
  { symbol: 'AAPL', nameKo: '애플', nameEn: 'Apple Inc.', market: 'US', sector: 'Technology' },
  { symbol: 'MSFT', nameKo: '마이크로소프트', nameEn: 'Microsoft Corporation', market: 'US', sector: 'Technology' },
  { symbol: 'GOOGL', nameKo: '구글', nameEn: 'Alphabet Inc.', market: 'US', sector: 'Technology' },
  { symbol: 'AMZN', nameKo: '아마존', nameEn: 'Amazon.com Inc.', market: 'US', sector: 'Consumer Cyclical' },
  { symbol: 'NVDA', nameKo: '엔비디아', nameEn: 'NVIDIA Corporation', market: 'US', sector: 'Technology' },
  { symbol: 'TSLA', nameKo: '테슬라', nameEn: 'Tesla Inc.', market: 'US', sector: 'Automotive' },
  { symbol: 'META', nameKo: '메타', nameEn: 'Meta Platforms Inc.', market: 'US', sector: 'Technology' },
  { symbol: 'NFLX', nameKo: '넷플릭스', nameEn: 'Netflix Inc.', market: 'US', sector: 'Entertainment' },
  { symbol: 'AMD', nameKo: 'AMD', nameEn: 'Advanced Micro Devices', market: 'US', sector: 'Technology' },
  { symbol: 'INTC', nameKo: '인텔', nameEn: 'Intel Corporation', market: 'US', sector: 'Technology' },

  // 미국 주요 금융/소비재
  { symbol: 'JPM', nameKo: 'JP모건', nameEn: 'JPMorgan Chase & Co.', market: 'US', sector: 'Financial' },
  { symbol: 'BAC', nameKo: '뱅크오브아메리카', nameEn: 'Bank of America', market: 'US', sector: 'Financial' },
  { symbol: 'WMT', nameKo: '월마트', nameEn: 'Walmart Inc.', market: 'US', sector: 'Retail' },
  { symbol: 'V', nameKo: '비자', nameEn: 'Visa Inc.', market: 'US', sector: 'Financial' },
  { symbol: 'MA', nameKo: '마스터카드', nameEn: 'Mastercard Inc.', market: 'US', sector: 'Financial' },
  { symbol: 'DIS', nameKo: '디즈니', nameEn: 'The Walt Disney Company', market: 'US', sector: 'Entertainment' },
  { symbol: 'NKE', nameKo: '나이키', nameEn: 'Nike Inc.', market: 'US', sector: 'Consumer Cyclical' },
  { symbol: 'MCD', nameKo: '맥도날드', nameEn: "McDonald's Corporation", market: 'US', sector: 'Consumer Cyclical' },
  { symbol: 'KO', nameKo: '코카콜라', nameEn: 'The Coca-Cola Company', market: 'US', sector: 'Consumer Defensive' },
  { symbol: 'PEP', nameKo: '펩시', nameEn: 'PepsiCo Inc.', market: 'US', sector: 'Consumer Defensive' },

  // 미국 에너지/제약
  { symbol: 'XOM', nameKo: '엑슨모빌', nameEn: 'Exxon Mobil Corporation', market: 'US', sector: 'Energy' },
  { symbol: 'CVX', nameKo: '쉐브론', nameEn: 'Chevron Corporation', market: 'US', sector: 'Energy' },
  { symbol: 'JNJ', nameKo: '존슨앤존슨', nameEn: 'Johnson & Johnson', market: 'US', sector: 'Healthcare' },
  { symbol: 'PFE', nameKo: '화이자', nameEn: 'Pfizer Inc.', market: 'US', sector: 'Healthcare' },
  { symbol: 'MRNA', nameKo: '모더나', nameEn: 'Moderna Inc.', market: 'US', sector: 'Healthcare' },

  // 한국 주요 종목 - 전자/IT
  { symbol: '005930.KS', nameKo: '삼성전자', nameEn: 'Samsung Electronics', market: 'KR', sector: 'Technology' },
  { symbol: '000660.KS', nameKo: 'SK하이닉스', nameEn: 'SK Hynix', market: 'KR', sector: 'Technology' },
  { symbol: '066570.KS', nameKo: 'LG전자', nameEn: 'LG Electronics', market: 'KR', sector: 'Technology' },
  { symbol: '006400.KS', nameKo: '삼성SDI', nameEn: 'Samsung SDI', market: 'KR', sector: 'Technology' },
  { symbol: '035420.KS', nameKo: '네이버', nameEn: 'NAVER Corporation', market: 'KR', sector: 'Technology' },
  { symbol: '035720.KS', nameKo: '카카오', nameEn: 'Kakao Corporation', market: 'KR', sector: 'Technology' },

  // 한국 주요 종목 - 자동차
  { symbol: '005380.KS', nameKo: '현대차', nameEn: 'Hyundai Motor', market: 'KR', sector: 'Automotive' },
  { symbol: '000270.KS', nameKo: '기아', nameEn: 'Kia Corporation', market: 'KR', sector: 'Automotive' },
  { symbol: '012330.KS', nameKo: '현대모비스', nameEn: 'Hyundai Mobis', market: 'KR', sector: 'Automotive' },

  // 한국 주요 종목 - 화학/에너지
  { symbol: '051910.KS', nameKo: 'LG화학', nameEn: 'LG Chem', market: 'KR', sector: 'Basic Materials' },
  { symbol: '096770.KS', nameKo: 'SK이노베이션', nameEn: 'SK Innovation', market: 'KR', sector: 'Energy' },
  { symbol: '009830.KS', nameKo: '한화솔루션', nameEn: 'Hanwha Solutions', market: 'KR', sector: 'Energy' },

  // 한국 주요 종목 - 금융/보험
  { symbol: '055550.KS', nameKo: '신한지주', nameEn: 'Shinhan Financial Group', market: 'KR', sector: 'Financial' },
  { symbol: '086790.KS', nameKo: '하나금융지주', nameEn: 'Hana Financial Group', market: 'KR', sector: 'Financial' },
  { symbol: '105560.KS', nameKo: 'KB금융', nameEn: 'KB Financial Group', market: 'KR', sector: 'Financial' },
  { symbol: '032830.KS', nameKo: '삼성생명', nameEn: 'Samsung Life Insurance', market: 'KR', sector: 'Financial' },

  // 한국 주요 종목 - 건설/유틸리티
  { symbol: '000720.KS', nameKo: '현대건설', nameEn: 'Hyundai E&C', market: 'KR', sector: 'Construction' },
  { symbol: '028260.KS', nameKo: '삼성물산', nameEn: 'Samsung C&T', market: 'KR', sector: 'Construction' },
  { symbol: '047040.KS', nameKo: '대우건설', nameEn: 'Daewoo E&C', market: 'KR', sector: 'Construction' },
  { symbol: '015760.KS', nameKo: '한국전력', nameEn: 'KEPCO', market: 'KR', sector: 'Utilities' },

  // 한국 주요 종목 - 바이오/제약
  { symbol: '068270.KS', nameKo: '셀트리온', nameEn: 'Celltrion', market: 'KR', sector: 'Healthcare' },
  { symbol: '207940.KS', nameKo: '삼성바이오로직스', nameEn: 'Samsung Biologics', market: 'KR', sector: 'Healthcare' },
  { symbol: '326030.KS', nameKo: 'SK바이오팜', nameEn: 'SK Biopharmaceuticals', market: 'KR', sector: 'Healthcare' },

  // 한국 주요 종목 - 유통/소비재
  { symbol: '051900.KS', nameKo: 'LG생활건강', nameEn: 'LG H&H', market: 'KR', sector: 'Consumer Defensive' },
  { symbol: '097950.KS', nameKo: 'CJ제일제당', nameEn: 'CJ CheilJedang', market: 'KR', sector: 'Consumer Defensive' },
  { symbol: '139480.KS', nameKo: '이마트', nameEn: 'E-Mart', market: 'KR', sector: 'Retail' },

  // 한국 주요 종목 - 엔터테인먼트
  { symbol: '035900.KS', nameKo: 'JYP Ent.', nameEn: 'JYP Entertainment', market: 'KR', sector: 'Entertainment' },
  { symbol: '041510.KS', nameKo: 'SM', nameEn: 'SM Entertainment', market: 'KR', sector: 'Entertainment' },
  { symbol: '352820.KS', nameKo: '하이브', nameEn: 'HYBE', market: 'KR', sector: 'Entertainment' },

  // 미국 주요 인덱스 ETF (롱)
  { symbol: 'SPY', nameKo: 'S&P 500 ETF', nameEn: 'SPDR S&P 500 ETF', market: 'US', sector: 'Index ETF' },
  { symbol: 'QQQ', nameKo: '나스닥 100 ETF', nameEn: 'Invesco QQQ Trust', market: 'US', sector: 'Index ETF' },
  { symbol: 'DIA', nameKo: '다우존스 ETF', nameEn: 'SPDR Dow Jones Industrial Average ETF', market: 'US', sector: 'Index ETF' },
  { symbol: 'IWM', nameKo: '러셀 2000 ETF', nameEn: 'iShares Russell 2000 ETF', market: 'US', sector: 'Index ETF' },
  { symbol: 'VTI', nameKo: '미국 전체 시장 ETF', nameEn: 'Vanguard Total Stock Market ETF', market: 'US', sector: 'Index ETF' },

  // 미국 인버스 & 레버리지 ETF (숏/하락장 대응)
  { symbol: 'SQQQ', nameKo: '나스닥 3배 인버스', nameEn: 'ProShares UltraPro Short QQQ', market: 'US', sector: 'Leveraged ETF' },
  { symbol: 'SPXU', nameKo: 'S&P 500 3배 인버스', nameEn: 'ProShares UltraPro Short S&P500', market: 'US', sector: 'Leveraged ETF' },
  { symbol: 'SH', nameKo: 'S&P 500 인버스', nameEn: 'ProShares Short S&P500', market: 'US', sector: 'Inverse ETF' },
  { symbol: 'PSQ', nameKo: '나스닥 인버스', nameEn: 'ProShares Short QQQ', market: 'US', sector: 'Inverse ETF' },
  { symbol: 'DOG', nameKo: '다우존스 인버스', nameEn: 'ProShares Short Dow30', market: 'US', sector: 'Inverse ETF' },
  { symbol: 'SDOW', nameKo: '다우존스 3배 인버스', nameEn: 'ProShares UltraPro Short Dow30', market: 'US', sector: 'Leveraged ETF' },

  // 미국 섹터 ETF
  { symbol: 'XLF', nameKo: '금융 섹터 ETF', nameEn: 'Financial Select Sector SPDR', market: 'US', sector: 'Sector ETF' },
  { symbol: 'XLE', nameKo: '에너지 섹터 ETF', nameEn: 'Energy Select Sector SPDR', market: 'US', sector: 'Sector ETF' },
  { symbol: 'XLK', nameKo: '기술 섹터 ETF', nameEn: 'Technology Select Sector SPDR', market: 'US', sector: 'Sector ETF' },
  { symbol: 'XLV', nameKo: '헬스케어 섹터 ETF', nameEn: 'Health Care Select Sector SPDR', market: 'US', sector: 'Sector ETF' },
  { symbol: 'XLI', nameKo: '산업 섹터 ETF', nameEn: 'Industrial Select Sector SPDR', market: 'US', sector: 'Sector ETF' },

  // 미국 채권 & 안전자산 ETF
  { symbol: 'TLT', nameKo: '미국 20년 국채 ETF', nameEn: 'iShares 20+ Year Treasury Bond ETF', market: 'US', sector: 'Bond ETF' },
  { symbol: 'GLD', nameKo: '골드 ETF', nameEn: 'SPDR Gold Shares', market: 'US', sector: 'Commodity ETF' },
  { symbol: 'SLV', nameKo: '실버 ETF', nameEn: 'iShares Silver Trust', market: 'US', sector: 'Commodity ETF' },
  { symbol: 'USO', nameKo: '원유 ETF', nameEn: 'United States Oil Fund', market: 'US', sector: 'Commodity ETF' },

  // 한국 인덱스 ETF
  { symbol: '069500.KS', nameKo: 'KODEX 200', nameEn: 'KODEX KOSPI 200', market: 'KR', sector: 'Index ETF' },
  { symbol: '102110.KS', nameKo: 'TIGER 200', nameEn: 'TIGER KOSPI 200', market: 'KR', sector: 'Index ETF' },
  { symbol: '122630.KS', nameKo: 'KODEX 레버리지', nameEn: 'KODEX Leverage', market: 'KR', sector: 'Leveraged ETF' },
  { symbol: '114800.KS', nameKo: 'KODEX 인버스', nameEn: 'KODEX Inverse', market: 'KR', sector: 'Inverse ETF' },
  { symbol: '233740.KS', nameKo: 'KODEX 코스닥150 레버리지', nameEn: 'KODEX KOSDAQ 150 Leverage', market: 'KR', sector: 'Leveraged ETF' },

  // 한국 섹터 ETF
  { symbol: '091180.KS', nameKo: 'TIGER 은행', nameEn: 'TIGER Banks', market: 'KR', sector: 'Sector ETF' },
  { symbol: '091230.KS', nameKo: 'TIGER 반도체', nameEn: 'TIGER Semiconductors', market: 'KR', sector: 'Sector ETF' },
  { symbol: '227540.KS', nameKo: 'TIGER 2차전지테마', nameEn: 'TIGER Battery Theme', market: 'KR', sector: 'Sector ETF' },
];

// 검색 함수: 한글, 영문, 심볼로 검색
export function searchStocks(query: string): StockSymbol[] {
  if (!query || query.trim() === '') {
    return stockSymbols.slice(0, 10); // 기본 10개 표시
  }

  const searchTerm = query.toLowerCase().trim();

  return stockSymbols.filter(stock => {
    return (
      stock.symbol.toLowerCase().includes(searchTerm) ||
      stock.nameKo.toLowerCase().includes(searchTerm) ||
      stock.nameEn.toLowerCase().includes(searchTerm)
    );
  }).slice(0, 10); // 최대 10개까지만
}
