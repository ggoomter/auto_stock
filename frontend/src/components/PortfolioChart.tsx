import { useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine, Area, ComposedChart } from 'recharts';

interface EquityPoint {
  date: string;
  value: number;
}

interface PricePoint {
  date: string;
  close: number;
}

interface Trade {
  entry_date: string;
  exit_date: string;
  pnl_pct: number;
}

interface PortfolioChartProps {
  equityCurve: EquityPoint[];
  priceData?: PricePoint[];
  trades?: Trade[];
  initialCapital: number;
  currency?: string;
}

type ViewMode = 'all' | 'weekly' | 'monthly' | 'trades';

export default function PortfolioChart({
  equityCurve,
  priceData,
  trades = [],
  initialCapital,
  currency = 'KRW'
}: PortfolioChartProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('weekly');

  // 데이터 병합 (날짜 기준)
  const allData = equityCurve.map(equity => {
    const price = priceData?.find(p => p.date === equity.date);
    const buyTrade = trades.find(t => t.entry_date === equity.date);
    const sellTrade = trades.find(t => t.exit_date === equity.date);

    return {
      date: equity.date,
      portfolio: Math.round(equity.value),
      price: price?.close,
      isBuy: buyTrade ? true : false,
      isSell: sellTrade ? true : false,
      sellPnl: sellTrade?.pnl_pct
    };
  });

  // 뷰 모드에 따라 데이터 필터링/집계
  const getFilteredData = () => {
    switch (viewMode) {
      case 'trades':
        // 거래일만 표시
        return allData.filter(d => d.isBuy || d.isSell);

      case 'weekly':
        // 주간 마지막 날 데이터만 (금요일 또는 주의 마지막 거래일)
        const weeklyData: typeof allData = [];
        let currentWeek: string | null = null;
        let weekData: typeof allData[0] | null = null;

        allData.forEach((d, idx) => {
          const date = new Date(d.date);
          const weekKey = `${date.getFullYear()}-W${Math.ceil(date.getDate() / 7)}-${date.getMonth()}`;

          if (weekKey !== currentWeek) {
            if (weekData) weeklyData.push(weekData);
            currentWeek = weekKey;
            weekData = d;
          } else {
            weekData = d; // 주의 마지막 데이터로 업데이트
          }

          // 마지막 데이터
          if (idx === allData.length - 1 && weekData) {
            weeklyData.push(weekData);
          }
        });

        return weeklyData;

      case 'monthly':
        // 월간 마지막 날 데이터만
        const monthlyData: typeof allData = [];
        let currentMonth: string | null = null;
        let monthData: typeof allData[0] | null = null;

        allData.forEach((d, idx) => {
          const date = new Date(d.date);
          const monthKey = `${date.getFullYear()}-${date.getMonth()}`;

          if (monthKey !== currentMonth) {
            if (monthData) monthlyData.push(monthData);
            currentMonth = monthKey;
            monthData = d;
          } else {
            monthData = d; // 월의 마지막 데이터로 업데이트
          }

          // 마지막 데이터
          if (idx === allData.length - 1 && monthData) {
            monthlyData.push(monthData);
          }
        });

        return monthlyData;

      case 'all':
      default:
        return allData;
    }
  };

  const mergedData = getFilteredData();

  const formatCurrency = (value: number) => {
    if (currency === 'KRW') {
      return `${Math.round(value).toLocaleString()}원`;
    } else {
      return `$${value.toFixed(0)}`;
    }
  };

  const formatYAxis = (value: number) => {
    if (currency === 'KRW') {
      if (value >= 1000000) {
        return `${(value / 1000000).toFixed(1)}M`;
      }
      return `${(value / 1000).toFixed(0)}K`;
    } else {
      if (value >= 1000) {
        return `$${(value / 1000).toFixed(1)}K`;
      }
      return `$${value.toFixed(0)}`;
    }
  };

  // 커스텀 도트 (매수/매도 표시)
  const CustomDot = (props: any) => {
    const { cx, cy, payload } = props;

    if (payload.isBuy) {
      return (
        <g>
          <circle cx={cx} cy={cy} r={6} fill="#10b981" stroke="#fff" strokeWidth={2} />
          <text x={cx} y={cy - 12} textAnchor="middle" fill="#10b981" fontSize={10} fontWeight="bold">
            매수
          </text>
        </g>
      );
    }

    if (payload.isSell) {
      const color = payload.sellPnl >= 0 ? '#10b981' : '#ef4444';
      return (
        <g>
          <circle cx={cx} cy={cy} r={6} fill={color} stroke="#fff" strokeWidth={2} />
          <text x={cx} y={cy - 12} textAnchor="middle" fill={color} fontSize={10} fontWeight="bold">
            매도
          </text>
        </g>
      );
    }

    return null;
  };

  // 커스텀 툴팁
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const returnPct = ((data.portfolio - initialCapital) / initialCapital) * 100;

      return (
        <div className="bg-white border-2 border-gray-300 rounded-lg p-3 shadow-lg">
          <p className="text-xs text-gray-600 font-medium mb-2">{data.date}</p>

          <div className="space-y-1">
            <div className="flex items-center justify-between gap-4">
              <span className="text-xs text-gray-600">포트폴리오:</span>
              <span className="text-sm font-bold text-blue-700">{formatCurrency(data.portfolio)}</span>
            </div>

            <div className="flex items-center justify-between gap-4">
              <span className="text-xs text-gray-600">수익률:</span>
              <span className={`text-sm font-bold ${returnPct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {returnPct >= 0 ? '+' : ''}{returnPct.toFixed(2)}%
              </span>
            </div>

            {data.price && (
              <div className="flex items-center justify-between gap-4 pt-2 border-t border-gray-200 mt-2">
                <span className="text-xs text-gray-600">주가:</span>
                <span className="text-sm font-medium text-gray-800">
                  {currency === 'KRW' ? `${Math.round(data.price).toLocaleString()}원` : `$${data.price.toFixed(2)}`}
                </span>
              </div>
            )}

            {data.isBuy && (
              <div className="bg-green-50 border border-green-200 rounded px-2 py-1 mt-2">
                <span className="text-xs font-bold text-green-700">📈 매수 시점</span>
              </div>
            )}

            {data.isSell && (
              <div className={`${data.sellPnl >= 0 ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'} border rounded px-2 py-1 mt-2`}>
                <span className={`text-xs font-bold ${data.sellPnl >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                  📉 매도 ({data.sellPnl >= 0 ? '+' : ''}{data.sellPnl.toFixed(2)}%)
                </span>
              </div>
            )}
          </div>
        </div>
      );
    }

    return null;
  };

  return (
    <div className="bg-white rounded-lg border-2 border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-gray-900">
          💰 포트폴리오 가치 변화 (시작: {formatCurrency(initialCapital)})
        </h3>

        {/* 뷰 모드 선택 */}
        <div className="flex gap-2">
          <button
            onClick={() => setViewMode('trades')}
            className={`px-3 py-1 text-sm rounded-lg border-2 transition-all ${
              viewMode === 'trades'
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400'
            }`}
          >
            거래일만 ({trades.length}개)
          </button>
          <button
            onClick={() => setViewMode('weekly')}
            className={`px-3 py-1 text-sm rounded-lg border-2 transition-all ${
              viewMode === 'weekly'
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400'
            }`}
          >
            주간 (~{Math.ceil(allData.length / 5)}개)
          </button>
          <button
            onClick={() => setViewMode('monthly')}
            className={`px-3 py-1 text-sm rounded-lg border-2 transition-all ${
              viewMode === 'monthly'
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400'
            }`}
          >
            월간 (~{Math.ceil(allData.length / 20)}개)
          </button>
          <button
            onClick={() => setViewMode('all')}
            className={`px-3 py-1 text-sm rounded-lg border-2 transition-all ${
              viewMode === 'all'
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400'
            }`}
          >
            전체 ({allData.length}개)
          </button>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={400}>
        <ComposedChart data={mergedData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11 }}
            tickFormatter={(value) => {
              const date = new Date(value);
              return `${date.getMonth() + 1}/${date.getDate()}`;
            }}
          />
          <YAxis
            yAxisId="left"
            tick={{ fontSize: 11 }}
            tickFormatter={formatYAxis}
            label={{ value: '포트폴리오 가치', angle: -90, position: 'insideLeft', style: { fontSize: 12 } }}
          />
          {priceData && (
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fontSize: 11 }}
              label={{ value: '주가', angle: 90, position: 'insideRight', style: { fontSize: 12 } }}
            />
          )}
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: 12 }}
            iconType="line"
          />

          {/* 초기 자본 기준선 */}
          <ReferenceLine
            yAxisId="left"
            y={initialCapital}
            stroke="#6b7280"
            strokeDasharray="5 5"
            label={{ value: '초기 자본', position: 'right', fill: '#6b7280', fontSize: 11 }}
          />

          {/* 포트폴리오 가치 */}
          <Area
            yAxisId="left"
            type="monotone"
            dataKey="portfolio"
            fill="#3b82f6"
            fillOpacity={0.1}
            stroke="none"
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="portfolio"
            stroke="#3b82f6"
            strokeWidth={3}
            name="포트폴리오 가치"
            dot={<CustomDot />}
            activeDot={{ r: 6 }}
          />

          {/* 주가 (있으면) */}
          {priceData && (
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="price"
              stroke="#f59e0b"
              strokeWidth={2}
              strokeDasharray="5 5"
              name="주가"
              dot={false}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>

      {/* 범례 설명 */}
      <div className="mt-4 flex flex-wrap gap-4 text-xs text-gray-600">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-blue-600 rounded"></div>
          <span>포트폴리오 가치 ({mergedData.length}개 데이터 포인트)</span>
        </div>
        {priceData && (
          <div className="flex items-center gap-2">
            <div className="w-3 h-0.5 bg-amber-500"></div>
            <span>주가 추이</span>
          </div>
        )}
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-green-500 rounded-full border-2 border-white"></div>
          <span>매수/매도 시점</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-0.5 bg-gray-500 border-t border-dashed"></div>
          <span>초기 자본 ({formatCurrency(initialCapital)})</span>
        </div>
      </div>

      {/* 뷰 모드 설명 */}
      <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="text-xs text-blue-800">
          <strong>💡 뷰 모드 설명:</strong>
          <ul className="list-disc list-inside mt-1 space-y-1">
            <li><strong>거래일만:</strong> 실제 매수/매도가 발생한 날짜만 표시 (가장 간결)</li>
            <li><strong>주간:</strong> 각 주의 마지막 거래일 데이터만 표시 (권장, 1년 ≈ 52개)</li>
            <li><strong>월간:</strong> 각 월의 마지막 거래일 데이터만 표시 (1년 = 12개)</li>
            <li><strong>전체:</strong> 모든 거래일 표시 (1년 ≈ 250개, 느릴 수 있음)</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
