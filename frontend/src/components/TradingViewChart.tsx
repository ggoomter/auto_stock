import { useEffect, useRef } from 'react';
import { createChart, ColorType, IChartApi, ISeriesApi } from 'lightweight-charts';

interface ChartData {
  time: string;
  open?: number;
  high?: number;
  low?: number;
  close?: number;
  value?: number; // For Line/Area charts
}

interface TradingViewChartProps {
  data: ChartData[];
  type?: 'candlestick' | 'line' | 'area';
  colors?: {
    backgroundColor?: string;
    lineColor?: string;
    textColor?: string;
    areaTopColor?: string;
    areaBottomColor?: string;
    upColor?: string;
    downColor?: string;
  };
  height?: number;
}

export default function TradingViewChart({ 
  data, 
  type = 'candlestick', 
  colors = {}, 
  height = 400 
}: TradingViewChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  const {
    backgroundColor = 'transparent',
    textColor = '#333',
    lineColor = '#2962FF',
    areaTopColor = '#2962FF',
    areaBottomColor = 'rgba(41, 98, 255, 0.28)',
    upColor = '#26a69a',
    downColor = '#ef5350',
  } = colors;

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const handleResize = () => {
      chartRef.current?.applyOptions({ width: chartContainerRef.current?.clientWidth });
    };

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: backgroundColor },
        textColor,
      },
      width: chartContainerRef.current.clientWidth,
      height,
      grid: {
        vertLines: { color: 'rgba(197, 203, 206, 0.2)' },
        horzLines: { color: 'rgba(197, 203, 206, 0.2)' },
      },
      rightPriceScale: {
        borderColor: 'rgba(197, 203, 206, 0.8)',
      },
      timeScale: {
        borderColor: 'rgba(197, 203, 206, 0.8)',
      },
    });

    chartRef.current = chart;
    let series: ISeriesApi<any>;

    // 데이터 변환 및 정렬
    const formattedData = data.map(d => ({
      ...d,
      time: d.time.split('T')[0], // YYYY-MM-DD
    })).sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());

    if (type === 'candlestick') {
      series = chart.addCandlestickSeries({
        upColor,
        downColor,
        borderVisible: false,
        wickUpColor: upColor,
        wickDownColor: downColor,
      });
      series.setData(formattedData);
    } else if (type === 'area') {
      series = chart.addAreaSeries({
        topColor: areaTopColor,
        bottomColor: areaBottomColor,
        lineColor,
        lineWidth: 2,
      });
      series.setData(formattedData);
    } else {
      series = chart.addLineSeries({
        color: lineColor,
        lineWidth: 2,
      });
      series.setData(formattedData);
    }

    chart.timeScale().fitContent();

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data, type, backgroundColor, textColor, lineColor, areaTopColor, areaBottomColor, upColor, downColor, height]);

  return (
    <div ref={chartContainerRef} className="w-full" style={{ height }} />
  );
}
