import { useState } from 'react';
import { RefreshCw, Download, CheckCircle, AlertCircle } from 'lucide-react';

export default function NewsFetchButton() {
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');

  const handleFetchNews = async () => {
    setLoading(true);
    setStatus('idle');
    setMessage('');

    try {
      const response = await fetch('http://localhost:8000/events/update/manual', {
        method: 'POST',
      });

      const data = await response.json();

      if (data.success) {
        setStatus('success');
        setMessage('최신 뉴스 수집을 시작했습니다! 1-2분 후 새로고침하세요.');
      } else {
        setStatus('error');
        setMessage('뉴스 수집 실패: ' + (data.detail || '알 수 없는 오류'));
      }
    } catch (error) {
      setStatus('error');
      setMessage('서버 연결 실패. 백엔드가 실행 중인지 확인하세요.');
      console.error('News fetch error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card bg-gradient-to-r from-blue-50 to-purple-50 border-2 border-blue-300 p-4">
      <div className="flex items-center gap-3">
        <div className="flex-1">
          <h3 className="text-base font-bold text-gray-900 flex items-center gap-2 mb-1">
            <Download className="w-5 h-5 text-blue-600" />
            최신 뉴스 가져오기
          </h3>
          <p className="text-sm text-gray-600">
            News API에서 최신 금융 뉴스를 수집합니다
          </p>
        </div>

        <button
          onClick={handleFetchNews}
          disabled={loading}
          className="btn btn-primary flex items-center gap-2 whitespace-nowrap disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          {loading ? '수집 중...' : '뉴스 수집'}
        </button>
      </div>

      {/* 상태 메시지 */}
      {status !== 'idle' && (
        <div
          className={`mt-3 p-3 rounded-lg border flex items-start gap-2 ${
            status === 'success'
              ? 'bg-green-50 border-green-300 text-green-800'
              : 'bg-red-50 border-red-300 text-red-800'
          }`}
        >
          {status === 'success' ? (
            <CheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          ) : (
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          )}
          <div className="flex-1">
            <p className="text-sm font-medium">{message}</p>
            {status === 'success' && (
              <p className="text-xs mt-1 opacity-80">
                백그라운드에서 뉴스를 수집하고 있습니다. 완료되면 이벤트 목록에 추가됩니다.
              </p>
            )}
          </div>
        </div>
      )}

      {/* 사용 안내 */}
      <details className="mt-3">
        <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-800">
          💡 사용 방법 보기
        </summary>
        <div className="mt-2 text-xs text-gray-600 space-y-1 bg-white p-3 rounded border border-gray-200">
          <p><strong>1. News API 키 필요:</strong> backend/.env 파일에 NEWS_API_KEY 설정</p>
          <p><strong>2. 백엔드 실행:</strong> FastAPI 서버가 실행 중이어야 합니다</p>
          <p><strong>3. 수집 범위:</strong> 최근 1일간의 금융/경제 뉴스</p>
          <p><strong>4. 완료 후:</strong> 페이지 새로고침하면 차트에 새 이벤트 표시</p>
          <p className="mt-2 pt-2 border-t border-gray-200">
            <strong>무료 플랜:</strong> News API 하루 100회 호출 가능
          </p>
        </div>
      </details>
    </div>
  );
}
