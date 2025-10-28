import { useState, useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine, ComposedChart, Bar, Cell } from 'recharts';
import { Eye, EyeOff, BarChart3, TrendingUp, Maximize2, X } from 'lucide-react';
import { globalEvents, companyEvents, eventColors, eventIcons, type GlobalEvent } from '../data/globalEvents';
import { detectCandlePattern } from './Candlestick';

interface StockChartProps {
  symbol: string;
  startDate: string;
  endDate: string;
}

export default function StockChart({ symbol, startDate, endDate }: StockChartProps) {
  const [showGlobalEvents, setShowGlobalEvents] = useState(true);
  const [showCompanyEvents, setShowCompanyEvents] = useState(true);
  const [eventCategory, setEventCategory] = useState<string>('all');
  const [chartType, setChartType] = useState<'line' | 'candlestick'>('line');
  const [timeframe, setTimeframe] = useState<'daily' | 'weekly' | 'monthly'>('daily');
  const [chartPeriod, setChartPeriod] = useState<'6months' | '1year' | '3years' | '5years' | 'all'>('5years');
  const [hoveredEventIdx, setHoveredEventIdx] = useState<number | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // 샘플 주가 데이터 생성 (실제로는 API에서 가져와야 함)
  const stockData = useMemo(() => {
    const end = new Date();
    const start = new Date();

    // 차트 기간 설정
    switch (chartPeriod) {
      case '6months':
        start.setMonth(start.getMonth() - 6);
        break;
      case '1year':
        start.setFullYear(start.getFullYear() - 1);
        break;
      case '3years':
        start.setFullYear(start.getFullYear() - 3);
        break;
      case '5years':
        start.setFullYear(start.getFullYear() - 5);
        break;
      case 'all':
        start.setFullYear(start.getFullYear() - 20); // 2005년부터
        break;
    }

    const days = Math.floor((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));

    // 시간프레임에 따라 데이터 간격 조정
    const interval = timeframe === 'daily' ? 1 : timeframe === 'weekly' ? 7 : 30;

    // 시간프레임에 따라 간격 결정
    let dataInterval = 1; // 일봉 기본
    if (timeframe === 'weekly') dataInterval = 7;
    if (timeframe === 'monthly') dataInterval = 30;

    // 기본 날짜 생성
    const dateSet = new Set<string>();
    for (let i = 0; i <= days; i += dataInterval) {
      const date = new Date(start);
      date.setDate(date.getDate() + i);
      dateSet.add(date.toISOString().split('T')[0]);
    }

    // 이벤트 날짜도 포함 (차트에 세로선 표시를 위해)
    globalEvents.forEach(event => {
      const eventDate = new Date(event.date);
      if (eventDate >= start && eventDate <= end) {
        dateSet.add(event.date);
      }
    });

    // 종목별 이벤트도 포함
    if (companyEvents[symbol]) {
      companyEvents[symbol].forEach(event => {
        const eventDate = new Date(event.date);
        if (eventDate >= start && eventDate <= end) {
          dateSet.add(event.date);
        }
      });
    }

    // Set을 배열로 변환하고 정렬
    const allDates = Array.from(dateSet).sort();

    // 주가 데이터 생성 (종목별 시작 가격)
    const data = [];
    const startPrices: Record<string, number> = {
      'AAPL': 180,
      'TSLA': 250,
      'NVDA': 500,
      'MSFT': 380,
      'GOOGL': 140,
      'AMZN': 170,
      'META': 480,
    };

    let basePrice = startPrices[symbol] || 150;

    for (const dateStr of allDates) {
      // 랜덤 워크로 주가 시뮬레이션 (일일 변동 -3% ~ +3%)
      const dailyChangePercent = (Math.random() - 0.5) * 0.06; // -3% ~ +3%
      basePrice = basePrice * (1 + dailyChangePercent);

      // 극단적인 가격 방지 (시작가의 30% ~ 300% 범위로 제한)
      const initialPrice = startPrices[symbol] || 150;
      basePrice = Math.max(initialPrice * 0.3, Math.min(initialPrice * 3, basePrice));

      // OHLC 데이터 생성
      const close = Number(basePrice.toFixed(2));
      const intraday = close * 0.015; // 장중 변동 ±1.5%
      const open = Number((close + (Math.random() - 0.5) * intraday).toFixed(2));
      const highExtra = Math.random() * intraday * 0.8;
      const lowExtra = Math.random() * intraday * 0.8;
      const high = Number((Math.max(open, close) + highExtra).toFixed(2));
      const low = Number((Math.min(open, close) - lowExtra).toFixed(2));

      // 데이터 유효성 검증
      if (isNaN(close) || isNaN(open) || isNaN(high) || isNaN(low)) {
        console.error('Invalid price data:', { close, open, high, low, date: dateStr });
        continue;
      }

      if (close < 0 || open < 0 || high < 0 || low < 0) {
        console.error('Negative price detected:', { close, open, high, low, date: dateStr });
        continue;
      }

      data.push({
        date: dateStr,
        open: open,
        high: high,
        low: low,
        close: close,
        price: close, // 라인 차트용
      });
    }

    return data;
  }, [timeframe, chartPeriod, symbol]);

  // 날짜 범위 내 이벤트 필터링
  const filteredEvents = useMemo(() => {
    const end = new Date();
    const start = new Date();

    // 차트 기간에 맞춰 이벤트 필터링
    switch (chartPeriod) {
      case '6months':
        start.setMonth(start.getMonth() - 6);
        break;
      case '1year':
        start.setFullYear(start.getFullYear() - 1);
        break;
      case '3years':
        start.setFullYear(start.getFullYear() - 3);
        break;
      case '5years':
        start.setFullYear(start.getFullYear() - 5);
        break;
      case 'all':
        start.setFullYear(start.getFullYear() - 20);
        break;
    }

    const events: GlobalEvent[] = [];

    if (showGlobalEvents) {
      events.push(...globalEvents.filter(e => {
        const eventDate = new Date(e.date);
        return eventDate >= start && eventDate <= end;
      }));
    }

    if (showCompanyEvents && companyEvents[symbol]) {
      events.push(...companyEvents[symbol].filter(e => {
        const eventDate = new Date(e.date);
        return eventDate >= start && eventDate <= end;
      }));
    }

    // 카테고리 필터
    let filteredList = events;
    if (eventCategory !== 'all') {
      filteredList = events.filter(e => e.category === eventCategory);
    }

    console.log('📊 이벤트 필터 상태:', {
      카테고리: eventCategory,
      전체이벤트수: events.length,
      필터후이벤트수: filteredList.length,
      이벤트목록: filteredList.map(e => `${e.date} - ${e.title}`),
      글로벌표시: showGlobalEvents,
      종목표시: showCompanyEvents,
    });

    console.log('📊 차트 데이터 날짜 범위:', {
      시작: stockData[0]?.date,
      끝: stockData[stockData.length - 1]?.date,
      총개수: stockData.length,
    });

    return filteredList.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  }, [showGlobalEvents, showCompanyEvents, eventCategory, symbol, chartPeriod, stockData]);

  const categories = [
    { value: 'all', label: '전체' },
    { value: 'crisis', label: '위기' },
    { value: 'election', label: '선거' },
    { value: 'policy', label: '정책' },
    { value: 'pandemic', label: '팬데믹' },
    { value: 'war', label: '전쟁' },
    { value: 'tech', label: '기술' },
  ];

  // 캔들 패턴 감지
  const candlePatterns = useMemo(() => {
    return stockData.map((d, i) => ({
      ...d,
      pattern: detectCandlePattern(stockData, i),
    }));
  }, [stockData]);

  // 캔들스틱 커스텀 툴팁
  const CandlestickTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-3 border border-gray-300 rounded shadow-lg text-xs">
          <p className="font-semibold mb-1">{new Date(data.date).toLocaleDateString()}</p>
          <div className="space-y-1">
            <p><span className="font-medium">시가:</span> ${data.open?.toFixed(2)}</p>
            <p><span className="font-medium">고가:</span> ${data.high?.toFixed(2)}</p>
            <p><span className="font-medium">저가:</span> ${data.low?.toFixed(2)}</p>
            <p><span className="font-medium">종가:</span> ${data.close?.toFixed(2)}</p>
            {data.pattern && (
              <p className="mt-2 pt-2 border-t border-gray-200 text-primary-600 font-semibold">
                {data.pattern}
              </p>
            )}
          </div>
        </div>
      );
    }
    return null;
  };

  // Y축 도메인 계산
  const yDomain = useMemo(() => {
    const allPrices = stockData.flatMap(d => [d.high, d.low]).filter(p => typeof p === 'number' && !isNaN(p));
    if (allPrices.length === 0) return [0, 100];
    const min = Math.min(...allPrices);
    const max = Math.max(...allPrices);
    const padding = (max - min) * 0.05;
    return [min - padding, max + padding];
  }, [stockData]);

  // 캔들스틱 Shape 컴포넌트
  const CandleShape = (props: any) => {
    const { x, y, width, height, payload } = props;
    if (!payload || !payload.open || !payload.high || !payload.low || !payload.close) return null;

    const { open, high, low, close } = payload;

    // 유효하지 않은 데이터 체크
    if (typeof open !== 'number' || typeof high !== 'number' ||
        typeof low !== 'number' || typeof close !== 'number') {
      return null;
    }

    const isUp = close >= open;
    const color = isUp ? '#EF4444' : '#3B82F6';

    const [minPrice, maxPrice] = yDomain;
    const priceRange = maxPrice - minPrice;

    if (priceRange === 0) return null;

    // 캔들 바디
    const candleTop = Math.max(open, close);
    const candleBottom = Math.min(open, close);

    // Y 좌표 계산 (반전 필요)
    const highY = y + height * (1 - (high - minPrice) / priceRange);
    const lowY = y + height * (1 - (low - minPrice) / priceRange);
    const topY = y + height * (1 - (candleTop - minPrice) / priceRange);
    const bottomY = y + height * (1 - (candleBottom - minPrice) / priceRange);

    return (
      <g>
        {/* 위꼬리 */}
        <line
          x1={x + width / 2}
          y1={highY}
          x2={x + width / 2}
          y2={topY}
          stroke={color}
          strokeWidth={1}
        />

        {/* 캔들 바디 */}
        <rect
          x={x + width * 0.25}
          y={topY}
          width={width * 0.5}
          height={Math.max(bottomY - topY, 1)}
          fill={color}
          stroke={color}
          strokeWidth={1}
        />

        {/* 아래꼬리 */}
        <line
          x1={x + width / 2}
          y1={bottomY}
          x2={x + width / 2}
          y2={lowY}
          stroke={color}
          strokeWidth={1}
        />
      </g>
    );
  };

  return (
    <>
      <div className="card">
        <div className="flex flex-col gap-3 mb-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold">{symbol} 주가 차트</h3>

            <div className="flex items-center gap-2">
              {/* 전체화면 버튼 */}
              <button
                onClick={() => setIsFullscreen(true)}
                className="flex items-center gap-1 px-3 py-2 bg-primary-600 text-white rounded hover:bg-primary-700 transition-colors text-sm font-medium"
                title="차트 확대"
              >
                <Maximize2 className="w-4 h-4" />
                확대
              </button>
            {/* 차트 기간 선택 */}
            <select
              value={chartPeriod}
              onChange={(e) => setChartPeriod(e.target.value as any)}
              className="input text-sm px-3 py-1"
            >
              <option value="6months">최근 6개월</option>
              <option value="1year">최근 1년</option>
              <option value="3years">최근 3년</option>
              <option value="5years">최근 5년 (권장) ⭐</option>
              <option value="all">전체 (2005~)</option>
            </select>
            {/* 시간프레임 선택 */}
            <div className="flex gap-1 bg-gray-100 p-1 rounded">
              <button
                onClick={() => setTimeframe('daily')}
                className={`px-3 py-1 text-sm rounded transition-colors ${
                  timeframe === 'daily'
                    ? 'bg-white text-primary-700 shadow font-semibold'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                일봉
              </button>
              <button
                onClick={() => setTimeframe('weekly')}
                className={`px-3 py-1 text-sm rounded transition-colors ${
                  timeframe === 'weekly'
                    ? 'bg-white text-primary-700 shadow font-semibold'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                주봉
              </button>
              <button
                onClick={() => setTimeframe('monthly')}
                className={`px-3 py-1 text-sm rounded transition-colors ${
                  timeframe === 'monthly'
                    ? 'bg-white text-primary-700 shadow font-semibold'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                월봉
              </button>
            </div>

            {/* 차트 타입 선택 */}
            <div className="flex gap-1 bg-gray-100 p-1 rounded">
              <button
                onClick={() => setChartType('line')}
                className={`flex items-center gap-1 px-3 py-1 text-sm rounded transition-colors ${
                  chartType === 'line'
                    ? 'bg-white text-primary-700 shadow'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <TrendingUp className="w-4 h-4" />
                라인
              </button>
              <button
                onClick={() => setChartType('candlestick')}
                className={`flex items-center gap-1 px-3 py-1 text-sm rounded transition-colors ${
                  chartType === 'candlestick'
                    ? 'bg-white text-primary-700 shadow'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <BarChart3 className="w-4 h-4" />
                캔들
              </button>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* 이벤트 토글 */}
          <button
            onClick={() => setShowGlobalEvents(!showGlobalEvents)}
            className={`flex items-center gap-1 px-3 py-1 text-sm rounded transition-colors ${
              showGlobalEvents
                ? 'bg-blue-100 text-blue-700'
                : 'bg-gray-100 text-gray-500'
            }`}
          >
            {showGlobalEvents ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
            글로벌 이벤트
          </button>

          <button
            onClick={() => setShowCompanyEvents(!showCompanyEvents)}
            className={`flex items-center gap-1 px-3 py-1 text-sm rounded transition-colors ${
              showCompanyEvents
                ? 'bg-green-100 text-green-700'
                : 'bg-gray-100 text-gray-500'
            }`}
          >
            {showCompanyEvents ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
            종목 이벤트
          </button>
          {/* 카테고리 필터 */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-600 font-medium">이벤트 필터:</span>
            {categories.map(cat => (
              <button
                key={cat.value}
                onClick={() => setEventCategory(cat.value)}
                className={`px-2 py-1 text-xs rounded transition-colors ${
                  eventCategory === cat.value
                    ? 'bg-primary-600 text-white font-semibold'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {cat.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 차트 */}
      <ResponsiveContainer width="100%" height={700}>
        {chartType === 'line' ? (
          <LineChart data={stockData} margin={{ top: 120, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12 }}
              tickFormatter={(date) => {
                const d = new Date(date);
                if (timeframe === 'monthly' || chartPeriod === '5years' || chartPeriod === 'all') {
                  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}`;
                } else if (timeframe === 'weekly' || chartPeriod === '3years') {
                  return `${d.getFullYear()}.${d.getMonth() + 1}.${d.getDate()}`;
                }
                return `${d.getMonth() + 1}/${d.getDate()}`;
              }}
            />
            <YAxis
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => `$${value}`}
              domain={yDomain}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'white',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                fontSize: '12px',
              }}
              labelFormatter={(date) => {
                const d = new Date(date);
                return `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일`;
              }}
              formatter={(value: number) => [`$${value.toFixed(2)}`, '종가']}
            />
            <Legend />

            {/* 이벤트 세로선 - 일반 (호버되지 않은 것) */}
            {filteredEvents.map((event, idx) => {
              if (hoveredEventIdx === idx) return null; // 호버된 것은 나중에 렌더링

              const symbolSpecificImpact = event.symbolImpacts?.[symbol];
              const finalImpact = symbolSpecificImpact || event.impact;
              const impactColor = finalImpact === 'negative' ? '#EF4444' :
                                  finalImpact === 'positive' ? '#10B981' :
                                  eventColors[event.category];
              const verticalLevel = idx % 3;

              return (
                <ReferenceLine
                  key={idx}
                  x={event.date}
                  stroke={impactColor}
                  strokeDasharray="3 3"
                  strokeWidth={2}
                  label={({ viewBox }: any) => {
                    const { x, y } = viewBox;
                    const labelY = y - 20 - (verticalLevel * 30);

                    return (
                      <g
                        style={{ cursor: 'pointer' }}
                        onMouseEnter={() => setHoveredEventIdx(idx)}
                        onMouseLeave={() => setHoveredEventIdx(null)}
                      >
                        <rect
                          x={x - 60}
                          y={labelY - 12}
                          width={120}
                          height={24}
                          fill="white"
                          stroke={impactColor}
                          strokeWidth={1.5}
                          rx={4}
                          opacity={0.95}
                        />
                        <text
                          x={x - 50}
                          y={labelY + 4}
                          fontSize={11}
                          fill={impactColor}
                          fontWeight="bold"
                          textAnchor="start"
                        >
                          {eventIcons[event.category]}
                        </text>
                        <text
                          x={x - 35}
                          y={labelY + 4}
                          fontSize={10}
                          fill={impactColor}
                          fontWeight="600"
                          textAnchor="start"
                        >
                          {event.title.length > 12 ? event.title.substring(0, 12) + '...' : event.title}
                        </text>
                        <line
                          x1={x}
                          y1={labelY + 12}
                          x2={x}
                          y2={y}
                          stroke={impactColor}
                          strokeWidth={1}
                          opacity={0.3}
                        />
                      </g>
                    );
                  }}
                />
              );
            })}

            {/* 이벤트 세로선 - 호버된 것 (최상단) */}
            {hoveredEventIdx !== null && (() => {
              const idx = hoveredEventIdx;
              const event = filteredEvents[idx];
              const symbolSpecificImpact = event.symbolImpacts?.[symbol];
              const finalImpact = symbolSpecificImpact || event.impact;
              const impactColor = finalImpact === 'negative' ? '#EF4444' :
                                  finalImpact === 'positive' ? '#10B981' :
                                  eventColors[event.category];
              const verticalLevel = idx % 3;

              return (
                <ReferenceLine
                  key={`hovered-${idx}`}
                  x={event.date}
                  stroke={impactColor}
                  strokeDasharray="3 3"
                  strokeWidth={3}
                  label={({ viewBox }: any) => {
                    const { x, y } = viewBox;
                    const labelY = y - 20 - (verticalLevel * 30);

                    return (
                      <g
                        style={{ cursor: 'pointer' }}
                        onMouseEnter={() => setHoveredEventIdx(idx)}
                        onMouseLeave={() => setHoveredEventIdx(null)}
                      >
                        {event.title.length > 12 && (
                          <>
                            <rect
                              x={x - 80}
                              y={labelY - 45}
                              width={160}
                              height={28}
                              fill="#1f2937"
                              rx={6}
                              opacity={0.95}
                            />
                            <text
                              x={x}
                              y={labelY - 26}
                              fontSize={11}
                              fill="white"
                              fontWeight="600"
                              textAnchor="middle"
                            >
                              {event.title}
                            </text>
                          </>
                        )}
                        <rect
                          x={x - 60}
                          y={labelY - 12}
                          width={120}
                          height={24}
                          fill="white"
                          stroke={impactColor}
                          strokeWidth={2.5}
                          rx={4}
                          opacity={0.95}
                          style={{ filter: 'drop-shadow(0 4px 6px rgba(0,0,0,0.3))' }}
                        />
                        <text
                          x={x - 50}
                          y={labelY + 4}
                          fontSize={12}
                          fill={impactColor}
                          fontWeight="bold"
                          textAnchor="start"
                        >
                          {eventIcons[event.category]}
                        </text>
                        <text
                          x={x - 35}
                          y={labelY + 4}
                          fontSize={11}
                          fill={impactColor}
                          fontWeight="600"
                          textAnchor="start"
                        >
                          {event.title.length > 12 ? event.title.substring(0, 12) + '...' : event.title}
                        </text>
                        <line
                          x1={x}
                          y1={labelY + 12}
                          x2={x}
                          y2={y}
                          stroke={impactColor}
                          strokeWidth={2}
                          opacity={0.6}
                        />
                      </g>
                    );
                  }}
                />
              );
            })()}

            <Line
              type="monotone"
              dataKey="price"
              stroke="#0ea5e9"
              strokeWidth={2}
              dot={false}
              name={`${symbol} 종가`}
            />
          </LineChart>
        ) : (
          <ComposedChart data={candlePatterns} margin={{ top: 120, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12 }}
              tickFormatter={(date) => {
                const d = new Date(date);
                if (timeframe === 'monthly' || chartPeriod === '5years' || chartPeriod === 'all') {
                  return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}`;
                } else if (timeframe === 'weekly' || chartPeriod === '3years') {
                  return `${d.getFullYear()}.${d.getMonth() + 1}.${d.getDate()}`;
                }
                return `${d.getMonth() + 1}/${d.getDate()}`;
              }}
            />
            <YAxis
              tick={{ fontSize: 12 }}
              tickFormatter={(value) => `$${value}`}
              domain={yDomain}
            />
            <Tooltip content={<CandlestickTooltip />} />
            <Legend />

            {/* 이벤트 세로선 - 일반 (호버되지 않은 것) */}
            {filteredEvents.map((event, idx) => {
              if (hoveredEventIdx === idx) return null; // 호버된 것은 나중에 렌더링

              const symbolSpecificImpact = event.symbolImpacts?.[symbol];
              const finalImpact = symbolSpecificImpact || event.impact;
              const impactColor = finalImpact === 'negative' ? '#EF4444' :
                                  finalImpact === 'positive' ? '#10B981' :
                                  eventColors[event.category];
              const verticalLevel = idx % 3;

              return (
                <ReferenceLine
                  key={idx}
                  x={event.date}
                  stroke={impactColor}
                  strokeDasharray="3 3"
                  strokeWidth={2}
                  label={({ viewBox }: any) => {
                    const { x, y } = viewBox;
                    const labelY = y - 20 - (verticalLevel * 30);

                    return (
                      <g
                        style={{ cursor: 'pointer' }}
                        onMouseEnter={() => setHoveredEventIdx(idx)}
                        onMouseLeave={() => setHoveredEventIdx(null)}
                      >
                        <rect
                          x={x - 60}
                          y={labelY - 12}
                          width={120}
                          height={24}
                          fill="white"
                          stroke={impactColor}
                          strokeWidth={1.5}
                          rx={4}
                          opacity={0.95}
                        />
                        <text
                          x={x - 50}
                          y={labelY + 4}
                          fontSize={11}
                          fill={impactColor}
                          fontWeight="bold"
                          textAnchor="start"
                        >
                          {eventIcons[event.category]}
                        </text>
                        <text
                          x={x - 35}
                          y={labelY + 4}
                          fontSize={10}
                          fill={impactColor}
                          fontWeight="600"
                          textAnchor="start"
                        >
                          {event.title.length > 12 ? event.title.substring(0, 12) + '...' : event.title}
                        </text>
                        <line
                          x1={x}
                          y1={labelY + 12}
                          x2={x}
                          y2={y}
                          stroke={impactColor}
                          strokeWidth={1}
                          opacity={0.3}
                        />
                      </g>
                    );
                  }}
                />
              );
            })}

            {/* 이벤트 세로선 - 호버된 것 (최상단) */}
            {hoveredEventIdx !== null && (() => {
              const idx = hoveredEventIdx;
              const event = filteredEvents[idx];
              const symbolSpecificImpact = event.symbolImpacts?.[symbol];
              const finalImpact = symbolSpecificImpact || event.impact;
              const impactColor = finalImpact === 'negative' ? '#EF4444' :
                                  finalImpact === 'positive' ? '#10B981' :
                                  eventColors[event.category];
              const verticalLevel = idx % 3;

              return (
                <ReferenceLine
                  key={`hovered-${idx}`}
                  x={event.date}
                  stroke={impactColor}
                  strokeDasharray="3 3"
                  strokeWidth={3}
                  label={({ viewBox }: any) => {
                    const { x, y } = viewBox;
                    const labelY = y - 20 - (verticalLevel * 30);

                    return (
                      <g
                        style={{ cursor: 'pointer' }}
                        onMouseEnter={() => setHoveredEventIdx(idx)}
                        onMouseLeave={() => setHoveredEventIdx(null)}
                      >
                        {event.title.length > 12 && (
                          <>
                            <rect
                              x={x - 80}
                              y={labelY - 45}
                              width={160}
                              height={28}
                              fill="#1f2937"
                              rx={6}
                              opacity={0.95}
                            />
                            <text
                              x={x}
                              y={labelY - 26}
                              fontSize={11}
                              fill="white"
                              fontWeight="600"
                              textAnchor="middle"
                            >
                              {event.title}
                            </text>
                          </>
                        )}
                        <rect
                          x={x - 60}
                          y={labelY - 12}
                          width={120}
                          height={24}
                          fill="white"
                          stroke={impactColor}
                          strokeWidth={2.5}
                          rx={4}
                          opacity={0.95}
                          style={{ filter: 'drop-shadow(0 4px 6px rgba(0,0,0,0.3))' }}
                        />
                        <text
                          x={x - 50}
                          y={labelY + 4}
                          fontSize={12}
                          fill={impactColor}
                          fontWeight="bold"
                          textAnchor="start"
                        >
                          {eventIcons[event.category]}
                        </text>
                        <text
                          x={x - 35}
                          y={labelY + 4}
                          fontSize={11}
                          fill={impactColor}
                          fontWeight="600"
                          textAnchor="start"
                        >
                          {event.title.length > 12 ? event.title.substring(0, 12) + '...' : event.title}
                        </text>
                        <line
                          x1={x}
                          y1={labelY + 12}
                          x2={x}
                          y2={y}
                          stroke={impactColor}
                          strokeWidth={2}
                          opacity={0.6}
                        />
                      </g>
                    );
                  }}
                />
              );
            })()}

            {/* 캔들스틱 */}
            <Bar
              dataKey="high"
              shape={<CandleShape />}
              name={`${symbol} 캔들`}
            />
          </ComposedChart>
        )}
      </ResponsiveContainer>

      {/* 이벤트 타임라인 */}
      {filteredEvents.length > 0 && (
        <div className="mt-6 bg-gradient-to-r from-blue-50 to-purple-50 p-4 rounded-lg border border-blue-200">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
              📅 주요 이벤트 타임라인 ({filteredEvents.length}개)
            </h4>
            <div className="text-xs text-gray-600 bg-white px-3 py-1 rounded-full">
              {eventCategory === 'all' ? '전체 카테고리' : categories.find(c => c.value === eventCategory)?.label}
            </div>
          </div>
          <div className="relative">
            {/* 타임라인 선 */}
            <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-300"></div>

            <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
              {filteredEvents.map((event, idx) => (
                <div key={idx} className="relative flex items-start gap-3 pl-10">
                  {/* 타임라인 점 */}
                  <div
                    className="absolute left-2.5 w-3 h-3 rounded-full border-2 border-white"
                    style={{ backgroundColor: eventColors[event.category] }}
                  />

                  {/* 이벤트 카드 */}
                  <div className="flex-1 bg-white rounded-lg shadow-sm border p-3 hover:shadow-md transition-shadow">
                    <div className="flex items-start gap-3">
                      <span className="text-2xl flex-shrink-0">{eventIcons[event.category]}</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <span className="text-xs font-bold text-gray-900">{event.date}</span>
                          <span
                            className="text-xs px-2 py-0.5 rounded-full text-white font-medium"
                            style={{ backgroundColor: eventColors[event.category] }}
                          >
                            {categories.find(c => c.value === event.category)?.label}
                          </span>
                          <span
                            className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                              event.impact === 'positive'
                                ? 'bg-green-100 text-green-700'
                                : event.impact === 'negative'
                                ? 'bg-red-100 text-red-700'
                                : 'bg-gray-100 text-gray-700'
                            }`}
                          >
                            {event.impact === 'positive' ? '📈 긍정' : event.impact === 'negative' ? '📉 부정' : '중립'}
                          </span>
                        </div>
                        <p className="text-sm font-semibold text-gray-900 mb-1">{event.title}</p>
                        <p className="text-xs text-gray-600">{event.description}</p>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {filteredEvents.length === 0 && (showGlobalEvents || showCompanyEvents) && (
        <div className="mt-4 text-center py-8 bg-gray-50 rounded border-2 border-dashed border-gray-300">
          <p className="text-sm font-medium text-gray-700">📅 선택한 조건에 해당하는 이벤트가 없습니다</p>
          <p className="text-xs text-gray-500 mt-1">
            {eventCategory === 'pandemic' && '💡 팬데믹 이벤트를 보려면 차트 기간을 "최근 5년" 이상으로 설정하세요 (2020년 이벤트)'}
            {eventCategory === 'crisis' && '💡 위기 이벤트를 보려면 차트 기간을 "최근 5년" 이상으로 설정하세요 (2020년 코로나 폭락, 2023년 SVB 등)'}
            {eventCategory === 'election' && '💡 선거 이벤트를 보려면 차트 기간을 "전체"로 설정하세요 (2016년 트럼프, 2020년 바이든 등)'}
            {eventCategory === 'all' && '차트 기간을 더 길게 설정하거나 다른 카테고리를 선택해보세요'}
          </p>
        </div>
      )}

      {/* 캔들 패턴 감지 결과 */}
      {chartType === 'candlestick' && (
        <div className="mt-4 bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-lg p-4">
          <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-purple-600" />
            감지된 캔들 패턴
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {candlePatterns
              .filter(d => d.pattern)
              .slice(-8) // 최근 8개만
              .reverse()
              .map((d, idx) => (
                <div key={idx} className="bg-white rounded p-2 border border-purple-100 text-xs">
                  <p className="text-gray-500 mb-1">{new Date(d.date).toLocaleDateString()}</p>
                  <p className="font-semibold text-purple-700">{d.pattern}</p>
                </div>
              ))}
          </div>
          {candlePatterns.filter(d => d.pattern).length === 0 && (
            <p className="text-sm text-gray-600">현재 감지된 특별한 캔들 패턴이 없습니다</p>
          )}
          <div className="mt-3 pt-3 border-t border-purple-200 text-xs text-gray-600">
            <p className="font-semibold mb-1">📚 캔들 패턴 가이드:</p>
            <ul className="space-y-1 ml-4">
              <li><span className="font-medium">🔨 망치형:</span> 하락 추세 중 긴 아래꼬리 → 반등 신호</li>
              <li><span className="font-medium">⚡ 피뢰침형:</span> 상승 추세 중 긴 위꼬리 → 하락 전환</li>
              <li><span className="font-medium">➕ 도지:</span> 시가=종가 → 추세 전환 가능</li>
              <li><span className="font-medium">📈 장대양봉:</span> 큰 양봉 → 강한 상승 압력</li>
              <li><span className="font-medium">📉 장대음봉:</span> 큰 음봉 → 강한 하락 압력</li>
            </ul>
          </div>
        </div>
      )}
    </div>

    {/* 전체화면 모달 */}
    {isFullscreen && (
      <div
        className="fixed inset-0 bg-black bg-opacity-70 z-50 flex items-center justify-center p-4"
        onClick={() => setIsFullscreen(false)}
      >
        <div
          className="bg-white rounded-lg shadow-2xl w-full h-[90vh] max-w-[95vw] overflow-auto"
          onClick={(e) => e.stopPropagation()}
        >
          {/* 모달 헤더 */}
          <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between z-10">
            <h3 className="text-xl font-bold text-gray-900">{symbol} 주가 차트 (확대 모드)</h3>
            <button
              onClick={() => setIsFullscreen(false)}
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors text-gray-700 font-medium"
            >
              <X className="w-5 h-5" />
              닫기
            </button>
          </div>

          {/* 차트 컨트롤 */}
          <div className="px-6 py-4 bg-gray-50 border-b border-gray-200">
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-2">
                  {/* 차트 기간 선택 */}
                  <select
                    value={chartPeriod}
                    onChange={(e) => setChartPeriod(e.target.value as any)}
                    className="input text-sm px-3 py-1"
                  >
                    <option value="6months">최근 6개월</option>
                    <option value="1year">최근 1년</option>
                    <option value="3years">최근 3년</option>
                    <option value="5years">최근 5년 (권장) ⭐</option>
                    <option value="all">전체 (2005~)</option>
                  </select>

                  {/* 시간프레임 선택 */}
                  <div className="flex gap-1 bg-gray-100 p-1 rounded">
                    <button
                      onClick={() => setTimeframe('daily')}
                      className={`px-3 py-1 text-sm rounded transition-colors ${
                        timeframe === 'daily'
                          ? 'bg-white text-primary-700 shadow font-semibold'
                          : 'text-gray-600 hover:text-gray-900'
                      }`}
                    >
                      일봉
                    </button>
                    <button
                      onClick={() => setTimeframe('weekly')}
                      className={`px-3 py-1 text-sm rounded transition-colors ${
                        timeframe === 'weekly'
                          ? 'bg-white text-primary-700 shadow font-semibold'
                          : 'text-gray-600 hover:text-gray-900'
                      }`}
                    >
                      주봉
                    </button>
                    <button
                      onClick={() => setTimeframe('monthly')}
                      className={`px-3 py-1 text-sm rounded transition-colors ${
                        timeframe === 'monthly'
                          ? 'bg-white text-primary-700 shadow font-semibold'
                          : 'text-gray-600 hover:text-gray-900'
                      }`}
                    >
                      월봉
                    </button>
                  </div>

                  {/* 차트 타입 선택 */}
                  <div className="flex gap-1 bg-gray-100 p-1 rounded">
                    <button
                      onClick={() => setChartType('line')}
                      className={`flex items-center gap-1 px-3 py-1 text-sm rounded transition-colors ${
                        chartType === 'line'
                          ? 'bg-white text-primary-700 shadow'
                          : 'text-gray-600 hover:text-gray-900'
                      }`}
                    >
                      <TrendingUp className="w-4 h-4" />
                      라인
                    </button>
                    <button
                      onClick={() => setChartType('candlestick')}
                      className={`flex items-center gap-1 px-3 py-1 text-sm rounded transition-colors ${
                        chartType === 'candlestick'
                          ? 'bg-white text-primary-700 shadow'
                          : 'text-gray-600 hover:text-gray-900'
                      }`}
                    >
                      <BarChart3 className="w-4 h-4" />
                      캔들
                    </button>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3 flex-wrap">
                {/* 이벤트 토글 */}
                <button
                  onClick={() => setShowGlobalEvents(!showGlobalEvents)}
                  className={`flex items-center gap-1 px-3 py-1 text-sm rounded transition-colors ${
                    showGlobalEvents
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-gray-100 text-gray-500'
                  }`}
                >
                  {showGlobalEvents ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                  글로벌 이벤트
                </button>

                <button
                  onClick={() => setShowCompanyEvents(!showCompanyEvents)}
                  className={`flex items-center gap-1 px-3 py-1 text-sm rounded transition-colors ${
                    showCompanyEvents
                      ? 'bg-green-100 text-green-700'
                      : 'bg-gray-100 text-gray-500'
                  }`}
                >
                  {showCompanyEvents ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                  종목 이벤트
                </button>

                {/* 카테고리 필터 */}
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-600 font-medium">이벤트 필터:</span>
                  {categories.map(cat => (
                    <button
                      key={cat.value}
                      onClick={() => setEventCategory(cat.value)}
                      className={`px-2 py-1 text-xs rounded transition-colors ${
                        eventCategory === cat.value
                          ? 'bg-primary-600 text-white font-semibold'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      {cat.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* 확대된 차트 */}
          <div className="px-6 py-6">
            <ResponsiveContainer width="100%" height={window.innerHeight * 0.65}>
              {chartType === 'line' ? (
                <LineChart data={stockData} margin={{ top: 120, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(date) => {
                      const d = new Date(date);
                      if (timeframe === 'monthly' || chartPeriod === '5years' || chartPeriod === 'all') {
                        return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}`;
                      } else if (timeframe === 'weekly' || chartPeriod === '3years') {
                        return `${d.getFullYear()}.${d.getMonth() + 1}.${d.getDate()}`;
                      }
                      return `${d.getMonth() + 1}/${d.getDate()}`;
                    }}
                  />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => `$${value}`}
                    domain={yDomain}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'white',
                      border: '1px solid #e5e7eb',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                    labelFormatter={(date) => {
                      const d = new Date(date);
                      return `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일`;
                    }}
                    formatter={(value: number) => [`$${value.toFixed(2)}`, '종가']}
                  />
                  <Legend />

                  {/* 이벤트 세로선 */}
                  {filteredEvents.map((event, idx) => {
                    if (hoveredEventIdx === idx) return null;

                    const symbolSpecificImpact = event.symbolImpacts?.[symbol];
                    const finalImpact = symbolSpecificImpact || event.impact;
                    const impactColor = finalImpact === 'negative' ? '#EF4444' :
                                        finalImpact === 'positive' ? '#10B981' :
                                        eventColors[event.category];
                    const verticalLevel = idx % 3;

                    return (
                      <ReferenceLine
                        key={idx}
                        x={event.date}
                        stroke={impactColor}
                        strokeDasharray="3 3"
                        strokeWidth={2}
                        label={({ viewBox }: any) => {
                          const { x, y } = viewBox;
                          const labelY = y - 20 - (verticalLevel * 30);

                          return (
                            <g
                              style={{ cursor: 'pointer' }}
                              onMouseEnter={() => setHoveredEventIdx(idx)}
                              onMouseLeave={() => setHoveredEventIdx(null)}
                            >
                              <rect
                                x={x - 60}
                                y={labelY - 12}
                                width={120}
                                height={24}
                                fill="white"
                                stroke={impactColor}
                                strokeWidth={1.5}
                                rx={4}
                                opacity={0.95}
                              />
                              <text
                                x={x - 50}
                                y={labelY + 4}
                                fontSize={11}
                                fill={impactColor}
                                fontWeight="bold"
                                textAnchor="start"
                              >
                                {eventIcons[event.category]}
                              </text>
                              <text
                                x={x - 35}
                                y={labelY + 4}
                                fontSize={10}
                                fill={impactColor}
                                fontWeight="600"
                                textAnchor="start"
                              >
                                {event.title.length > 12 ? event.title.substring(0, 12) + '...' : event.title}
                              </text>
                              <line
                                x1={x}
                                y1={labelY + 12}
                                x2={x}
                                y2={y}
                                stroke={impactColor}
                                strokeWidth={1}
                                opacity={0.3}
                              />
                            </g>
                          );
                        }}
                      />
                    );
                  })}

                  {hoveredEventIdx !== null && (() => {
                    const idx = hoveredEventIdx;
                    const event = filteredEvents[idx];
                    const symbolSpecificImpact = event.symbolImpacts?.[symbol];
                    const finalImpact = symbolSpecificImpact || event.impact;
                    const impactColor = finalImpact === 'negative' ? '#EF4444' :
                                        finalImpact === 'positive' ? '#10B981' :
                                        eventColors[event.category];
                    const verticalLevel = idx % 3;

                    return (
                      <ReferenceLine
                        key={`hovered-${idx}`}
                        x={event.date}
                        stroke={impactColor}
                        strokeDasharray="3 3"
                        strokeWidth={3}
                        label={({ viewBox }: any) => {
                          const { x, y } = viewBox;
                          const labelY = y - 20 - (verticalLevel * 30);

                          return (
                            <g
                              style={{ cursor: 'pointer' }}
                              onMouseEnter={() => setHoveredEventIdx(idx)}
                              onMouseLeave={() => setHoveredEventIdx(null)}
                            >
                              {event.title.length > 12 && (
                                <>
                                  <rect
                                    x={x - 80}
                                    y={labelY - 45}
                                    width={160}
                                    height={28}
                                    fill="#1f2937"
                                    rx={6}
                                    opacity={0.95}
                                  />
                                  <text
                                    x={x}
                                    y={labelY - 26}
                                    fontSize={11}
                                    fill="white"
                                    fontWeight="600"
                                    textAnchor="middle"
                                  >
                                    {event.title}
                                  </text>
                                </>
                              )}
                              <rect
                                x={x - 60}
                                y={labelY - 12}
                                width={120}
                                height={24}
                                fill="white"
                                stroke={impactColor}
                                strokeWidth={2.5}
                                rx={4}
                                opacity={0.95}
                                style={{ filter: 'drop-shadow(0 4px 6px rgba(0,0,0,0.3))' }}
                              />
                              <text
                                x={x - 50}
                                y={labelY + 4}
                                fontSize={12}
                                fill={impactColor}
                                fontWeight="bold"
                                textAnchor="start"
                              >
                                {eventIcons[event.category]}
                              </text>
                              <text
                                x={x - 35}
                                y={labelY + 4}
                                fontSize={11}
                                fill={impactColor}
                                fontWeight="600"
                                textAnchor="start"
                              >
                                {event.title.length > 12 ? event.title.substring(0, 12) + '...' : event.title}
                              </text>
                              <line
                                x1={x}
                                y1={labelY + 12}
                                x2={x}
                                y2={y}
                                stroke={impactColor}
                                strokeWidth={2}
                                opacity={0.6}
                              />
                            </g>
                          );
                        }}
                      />
                    );
                  })()}

                  <Line
                    type="monotone"
                    dataKey="price"
                    stroke="#0ea5e9"
                    strokeWidth={2}
                    dot={false}
                    name={`${symbol} 종가`}
                  />
                </LineChart>
              ) : (
                <ComposedChart data={candlePatterns} margin={{ top: 120, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(date) => {
                      const d = new Date(date);
                      if (timeframe === 'monthly' || chartPeriod === '5years' || chartPeriod === 'all') {
                        return `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, '0')}`;
                      } else if (timeframe === 'weekly' || chartPeriod === '3years') {
                        return `${d.getFullYear()}.${d.getMonth() + 1}.${d.getDate()}`;
                      }
                      return `${d.getMonth() + 1}/${d.getDate()}`;
                    }}
                  />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => `$${value}`}
                    domain={yDomain}
                  />
                  <Tooltip content={<CandlestickTooltip />} />
                  <Legend />

                  {/* 이벤트 세로선 */}
                  {filteredEvents.map((event, idx) => {
                    if (hoveredEventIdx === idx) return null;

                    const symbolSpecificImpact = event.symbolImpacts?.[symbol];
                    const finalImpact = symbolSpecificImpact || event.impact;
                    const impactColor = finalImpact === 'negative' ? '#EF4444' :
                                        finalImpact === 'positive' ? '#10B981' :
                                        eventColors[event.category];
                    const verticalLevel = idx % 3;

                    return (
                      <ReferenceLine
                        key={idx}
                        x={event.date}
                        stroke={impactColor}
                        strokeDasharray="3 3"
                        strokeWidth={2}
                        label={({ viewBox }: any) => {
                          const { x, y } = viewBox;
                          const labelY = y - 20 - (verticalLevel * 30);

                          return (
                            <g
                              style={{ cursor: 'pointer' }}
                              onMouseEnter={() => setHoveredEventIdx(idx)}
                              onMouseLeave={() => setHoveredEventIdx(null)}
                            >
                              <rect
                                x={x - 60}
                                y={labelY - 12}
                                width={120}
                                height={24}
                                fill="white"
                                stroke={impactColor}
                                strokeWidth={1.5}
                                rx={4}
                                opacity={0.95}
                              />
                              <text
                                x={x - 50}
                                y={labelY + 4}
                                fontSize={11}
                                fill={impactColor}
                                fontWeight="bold"
                                textAnchor="start"
                              >
                                {eventIcons[event.category]}
                              </text>
                              <text
                                x={x - 35}
                                y={labelY + 4}
                                fontSize={10}
                                fill={impactColor}
                                fontWeight="600"
                                textAnchor="start"
                              >
                                {event.title.length > 12 ? event.title.substring(0, 12) + '...' : event.title}
                              </text>
                              <line
                                x1={x}
                                y1={labelY + 12}
                                x2={x}
                                y2={y}
                                stroke={impactColor}
                                strokeWidth={1}
                                opacity={0.3}
                              />
                            </g>
                          );
                        }}
                      />
                    );
                  })}

                  {hoveredEventIdx !== null && (() => {
                    const idx = hoveredEventIdx;
                    const event = filteredEvents[idx];
                    const symbolSpecificImpact = event.symbolImpacts?.[symbol];
                    const finalImpact = symbolSpecificImpact || event.impact;
                    const impactColor = finalImpact === 'negative' ? '#EF4444' :
                                        finalImpact === 'positive' ? '#10B981' :
                                        eventColors[event.category];
                    const verticalLevel = idx % 3;

                    return (
                      <ReferenceLine
                        key={`hovered-${idx}`}
                        x={event.date}
                        stroke={impactColor}
                        strokeDasharray="3 3"
                        strokeWidth={3}
                        label={({ viewBox }: any) => {
                          const { x, y } = viewBox;
                          const labelY = y - 20 - (verticalLevel * 30);

                          return (
                            <g
                              style={{ cursor: 'pointer' }}
                              onMouseEnter={() => setHoveredEventIdx(idx)}
                              onMouseLeave={() => setHoveredEventIdx(null)}
                            >
                              {event.title.length > 12 && (
                                <>
                                  <rect
                                    x={x - 80}
                                    y={labelY - 45}
                                    width={160}
                                    height={28}
                                    fill="#1f2937"
                                    rx={6}
                                    opacity={0.95}
                                  />
                                  <text
                                    x={x}
                                    y={labelY - 26}
                                    fontSize={11}
                                    fill="white"
                                    fontWeight="600"
                                    textAnchor="middle"
                                  >
                                    {event.title}
                                  </text>
                                </>
                              )}
                              <rect
                                x={x - 60}
                                y={labelY - 12}
                                width={120}
                                height={24}
                                fill="white"
                                stroke={impactColor}
                                strokeWidth={2.5}
                                rx={4}
                                opacity={0.95}
                                style={{ filter: 'drop-shadow(0 4px 6px rgba(0,0,0,0.3))' }}
                              />
                              <text
                                x={x - 50}
                                y={labelY + 4}
                                fontSize={12}
                                fill={impactColor}
                                fontWeight="bold"
                                textAnchor="start"
                              >
                                {eventIcons[event.category]}
                              </text>
                              <text
                                x={x - 35}
                                y={labelY + 4}
                                fontSize={11}
                                fill={impactColor}
                                fontWeight="600"
                                textAnchor="start"
                              >
                                {event.title.length > 12 ? event.title.substring(0, 12) + '...' : event.title}
                              </text>
                              <line
                                x1={x}
                                y1={labelY + 12}
                                x2={x}
                                y2={y}
                                stroke={impactColor}
                                strokeWidth={2}
                                opacity={0.6}
                              />
                            </g>
                          );
                        }}
                      />
                    );
                  })()}

                  {/* 캔들스틱 */}
                  <Bar
                    dataKey="high"
                    shape={<CandleShape />}
                    name={`${symbol} 캔들`}
                  />
                </ComposedChart>
              )}
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    )}
  </>
  );
}
