// 캔들스틱 커스텀 shape 컴포넌트
interface CandlestickProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  payload?: any;
}

export const Candlestick = ({ x = 0, y = 0, width = 0, height = 0, payload }: CandlestickProps) => {
  if (!payload) return null;

  const { open, high, low, close } = payload;

  // 상승(양봉) = 빨간색, 하락(음봉) = 파란색
  const isUp = close >= open;
  const color = isUp ? '#EF4444' : '#3B82F6'; // red-500 : blue-500
  const fill = isUp ? '#EF4444' : '#3B82F6';

  // 캔들 바디의 위치와 크기 계산
  const candleHeight = Math.abs(close - open);
  const candleY = Math.min(open, close);

  // 최소 높이 보장 (십자형 캔들)
  const minHeight = 1;
  const displayHeight = Math.max(candleHeight, minHeight);

  return (
    <g>
      {/* 위꼬리 (High ~ max(open, close)) */}
      <line
        x1={x + width / 2}
        y1={y + height - ((high - low) > 0 ? ((high - low) / (high - low)) * height : 0)}
        x2={x + width / 2}
        y2={y + height - ((Math.max(open, close) - low) / (high - low)) * height}
        stroke={color}
        strokeWidth={1}
      />

      {/* 캔들 바디 */}
      <rect
        x={x + width * 0.2}
        y={y + height - ((Math.max(open, close) - low) / (high - low)) * height}
        width={width * 0.6}
        height={((candleHeight) / (high - low)) * height || minHeight}
        fill={fill}
        stroke={color}
        strokeWidth={1}
      />

      {/* 아래꼬리 (min(open, close) ~ Low) */}
      <line
        x1={x + width / 2}
        y1={y + height - ((Math.min(open, close) - low) / (high - low)) * height}
        x2={x + width / 2}
        y2={y + height}
        stroke={color}
        strokeWidth={1}
      />
    </g>
  );
};

// 캔들 패턴 감지 함수
export const detectCandlePattern = (data: any[], index: number): string | null => {
  if (index < 1) return null;

  const current = data[index];
  const prev = data[index - 1];

  const { open, high, low, close } = current;
  const body = Math.abs(close - open);
  const upperShadow = high - Math.max(open, close);
  const lowerShadow = Math.min(open, close) - low;
  const totalRange = high - low;

  // 망치형 (Hammer) - 긴 아래꼬리, 작은 몸통
  if (
    lowerShadow > body * 2 &&
    upperShadow < body * 0.3 &&
    close < prev.close // 하락 추세 중
  ) {
    return '🔨 망치형 (반등 신호)';
  }

  // 역망치형 (Inverted Hammer) - 긴 위꼬리, 작은 몸통
  if (
    upperShadow > body * 2 &&
    lowerShadow < body * 0.3 &&
    close < prev.close // 하락 추세 중
  ) {
    return '🔨 역망치형 (반등 가능)';
  }

  // 피뢰침형 (Shooting Star) - 긴 위꼬리, 작은 몸통
  if (
    upperShadow > body * 2 &&
    lowerShadow < body * 0.3 &&
    close > prev.close // 상승 추세 중
  ) {
    return '⚡ 피뢰침형 (하락 전환)';
  }

  // 교수형 (Hanging Man) - 긴 아래꼬리, 작은 몸통
  if (
    lowerShadow > body * 2 &&
    upperShadow < body * 0.3 &&
    close > prev.close // 상승 추세 중
  ) {
    return '⚡ 교수형 (하락 주의)';
  }

  // 도지 (Doji) - 시가와 종가가 거의 같음
  if (body < totalRange * 0.1) {
    return '➕ 도지 (추세 전환 가능)';
  }

  // 장대양봉
  if (close > open && body > totalRange * 0.7 && close > prev.close * 1.03) {
    return '📈 장대양봉 (강한 상승)';
  }

  // 장대음봉
  if (close < open && body > totalRange * 0.7 && close < prev.close * 0.97) {
    return '📉 장대음봉 (강한 하락)';
  }

  return null;
};
