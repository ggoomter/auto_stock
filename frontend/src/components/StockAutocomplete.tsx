import { useState, useRef, useEffect } from 'react';
import { Search, TrendingUp, Loader2 } from 'lucide-react';
import { searchStocks as searchStocksAPI, type StockSearchResult } from '../services/api';

interface StockAutocompleteProps {
  value: string;
  onChange: (symbol: string, stockName?: string) => void;
}

export default function StockAutocomplete({ value, onChange }: StockAutocompleteProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState(value);
  const [results, setResults] = useState<StockSearchResult[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [isSearching, setIsSearching] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // 실시간 검색 (debounce 적용)
  useEffect(() => {
    if (!searchQuery || searchQuery.trim().length === 0) {
      setResults([]);
      return;
    }

    setIsSearching(true);
    const timer = setTimeout(async () => {
      try {
        const response = await searchStocksAPI(searchQuery);
        setResults(response.results);
        setSelectedIndex(0);
      } catch (error) {
        console.error('검색 오류:', error);
        setResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 300); // 300ms debounce

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // 외부 클릭 감지
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // 종목 선택
  const selectStock = (stock: StockSearchResult) => {
    setSearchQuery(stock.symbol);
    onChange(stock.symbol, stock.nameKo);
    setIsOpen(false);
    inputRef.current?.blur();
  };

  // 키보드 네비게이션
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) {
      if (e.key === 'ArrowDown' || e.key === 'Enter') {
        setIsOpen(true);
        e.preventDefault();
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, results.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (results[selectedIndex]) {
          selectStock(results[selectedIndex]);
        }
        break;
      case 'Escape':
        setIsOpen(false);
        inputRef.current?.blur();
        break;
    }
  };

  // 검색어 변경
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value.toUpperCase();
    setSearchQuery(newValue);
    setIsOpen(true);
  };

  // 포커스 시 드롭다운 열기
  const handleFocus = () => {
    setIsOpen(true);
  };

  const isSelected = value && value.length > 0;

  return (
    <div className="relative">
      {/* 입력 필드 - 더 강조 */}
      <div className="relative">
        <input
          ref={inputRef}
          type="text"
          className={`input w-full text-xl font-bold pl-12 pr-4 py-4 rounded-lg shadow-md transition-all ${
            isSelected
              ? 'border-green-500 border-4 bg-green-50 shadow-green-200'
              : 'border-indigo-400 border-3 focus:border-indigo-600 focus:ring-4 focus:ring-indigo-200'
          }`}
          value={searchQuery}
          onChange={handleInputChange}
          onFocus={handleFocus}
          onKeyDown={handleKeyDown}
          placeholder="종목 검색 (한글/영문/심볼)..."
          autoComplete="off"
        />
        {isSearching ? (
          <Loader2 className="absolute left-3 top-1/2 -translate-y-1/2 w-6 h-6 text-indigo-500 animate-spin" />
        ) : isSelected ? (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 w-7 h-7 bg-green-500 rounded-full flex items-center justify-center shadow-lg animate-pulse">
            <span className="text-white text-sm font-bold">✓</span>
          </div>
        ) : (
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-6 h-6 text-indigo-500" />
        )}
      </div>

      {/* 자동완성 드롭다운 */}
      {isOpen && results.length > 0 && (
        <div
          ref={dropdownRef}
          className="absolute z-50 w-full mt-1 bg-white border-2 border-blue-300 rounded-lg shadow-xl max-h-80 overflow-y-auto"
        >
          {results.map((stock, index) => (
            <button
              key={stock.symbol}
              type="button"
              onClick={() => selectStock(stock)}
              onMouseEnter={() => setSelectedIndex(index)}
              className={`w-full text-left px-4 py-3 hover:bg-blue-50 transition-colors border-b border-gray-100 last:border-b-0 ${
                index === selectedIndex ? 'bg-blue-100' : ''
              }`}
            >
              <div className="flex items-center gap-3">
                {/* 아이콘 */}
                <div className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center flex-shrink-0">
                  <TrendingUp className="w-4 h-4" />
                </div>

                {/* 종목 정보 */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-gray-900 text-base">{stock.symbol}</span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                        stock.market === 'US'
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-green-100 text-green-700'
                      }`}
                    >
                      {stock.market === 'US' ? '미국' : '한국'}
                    </span>
                  </div>
                  <div className="text-sm text-gray-700 font-medium mt-0.5">{stock.nameKo}</div>
                  <div className="text-xs text-gray-500 truncate">{stock.nameEn}</div>
                </div>

                {/* 섹터 */}
                {stock.sector && (
                  <div className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                    {stock.sector}
                  </div>
                )}
              </div>
            </button>
          ))}
        </div>
      )}

      {/* 검색 결과 없음 */}
      {isOpen && results.length === 0 && searchQuery && (
        <div
          ref={dropdownRef}
          className="absolute z-50 w-full mt-1 bg-white border-2 border-gray-300 rounded-lg shadow-xl p-4 text-center"
        >
          <p className="text-gray-500 text-sm">
            '<span className="font-semibold">{searchQuery}</span>' 검색 결과가 없습니다.
          </p>
          <p className="text-xs text-gray-400 mt-2">
            직접 티커 심볼을 입력하셔도 됩니다.
          </p>
        </div>
      )}

      {/* 선택된 종목 또는 사용 팁 */}
      {isSelected ? (
        <div className="mt-3 p-4 bg-gradient-to-r from-green-50 to-emerald-50 border-3 border-green-400 rounded-lg shadow-md">
          <p className="text-base text-green-800 font-bold flex items-center gap-2">
            <span className="text-2xl">✅</span>
            <span>선택된 종목:</span>
            <span className="text-green-900 text-xl bg-white px-3 py-1 rounded-md shadow">
              {(() => {
                const stock = results.find(s => s.symbol === value);
                return stock ? `${stock.nameKo} (${value})` : value;
              })()}
            </span>
          </p>
        </div>
      ) : (
        <p className="text-sm text-indigo-700 mt-2 bg-indigo-50 px-3 py-2 rounded-md">
          💡 한글(애플, 삼성), 영문(Apple), 심볼(AAPL)로 검색 가능
        </p>
      )}
    </div>
  );
}
