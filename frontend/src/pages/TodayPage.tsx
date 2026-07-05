import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { RefreshCw, ChevronDown, ChevronUp, ExternalLink, Info } from 'lucide-react';
import {
  getTodayStatus,
  getTodayRecommendations,
  getTodayNews,
  type ConditionCheck,
  type TodayRecommendation,
} from '../services/api';

// ============================================================
// 공통 유틸 (섹션별 로딩/에러 UI)
// ============================================================

/** 섹션 로딩 스피너 */
function SectionSpinner({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-10 text-gray-500 dark:text-gray-400">
      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600 dark:border-primary-400" />
      <span className="text-sm">{label}</span>
    </div>
  );
}

/** 섹션 에러 + 재시도 */
function SectionError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 py-8 rounded-lg bg-red-50 border border-red-200 dark:bg-red-900/20 dark:border-red-800">
      <p className="text-sm font-medium text-red-700 dark:text-red-400">{message}</p>
      <button
        onClick={onRetry}
        className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-white text-red-700 border border-red-300 hover:bg-red-100 dark:bg-gray-800 dark:text-red-300 dark:border-red-700 dark:hover:bg-gray-700 transition-colors"
      >
        <RefreshCw className="w-4 h-4" />
        다시 시도
      </button>
    </div>
  );
}

/** 빈 상태 */
function EmptyState({ message }: { message: string }) {
  return (
    <div className="py-10 text-center text-sm text-gray-500 dark:text-gray-400">{message}</div>
  );
}

/** 섹션 카드 래퍼 */
function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-6 border border-gray-200 dark:border-gray-700">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">{title}</h2>
      {children}
    </section>
  );
}

// ============================================================
// 1. 작업 상태 스트립
// ============================================================

const JOB_LABELS: Record<string, string> = {
  news_crawl: '뉴스',
  recommendations: '추천',
  paper_reconcile: '정산',
};
const JOB_KEYS = ['news_crawl', 'recommendations', 'paper_reconcile'];

/** 작업 상태 → 색/문구 (색+텍스트로 의미 전달) */
function jobBadgeStyle(status: string | undefined): { text: string; cls: string } {
  if (!status) {
    return {
      text: '수집 중...',
      cls: 'bg-yellow-100 text-yellow-800 border-yellow-300 dark:bg-yellow-900/30 dark:text-yellow-300 dark:border-yellow-700',
    };
  }
  if (status === 'success') {
    return {
      text: '성공',
      cls: 'bg-green-100 text-green-800 border-green-300 dark:bg-green-900/30 dark:text-green-300 dark:border-green-700',
    };
  }
  if (status === 'failure') {
    return {
      text: '실패',
      cls: 'bg-red-100 text-red-800 border-red-300 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700',
    };
  }
  // skipped(already), skipped(weekend) 등
  return {
    text: '건너뜀',
    cls: 'bg-gray-100 text-gray-700 border-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600',
  };
}

function StatusStrip() {
  const query = useQuery({
    queryKey: ['todayStatus'],
    queryFn: getTodayStatus,
    // 3개 작업이 모두 기록되기 전엔 30초마다 폴링, 전부 기록되면 중단
    refetchInterval: (q) => {
      const data = q.state.data;
      if (!data) return 30000;
      const allDone = JOB_KEYS.every((k) => data.jobs[k]?.status);
      return allDone ? false : 30000;
    },
  });

  if (query.isLoading) return <SectionSpinner label="작업 상태 확인 중..." />;
  if (query.isError)
    return <SectionError message="작업 상태를 불러올 수 없습니다." onRetry={() => query.refetch()} />;

  const jobs = query.data?.jobs ?? {};

  return (
    <div className="flex flex-wrap gap-3">
      {JOB_KEYS.map((key) => {
        const job = jobs[key];
        const badge = jobBadgeStyle(job?.status);
        return (
          <div
            key={key}
            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-gray-50 dark:bg-gray-700/50 border border-gray-200 dark:border-gray-600"
          >
            <span className="text-sm font-medium text-gray-700 dark:text-gray-200">
              {JOB_LABELS[key]}
            </span>
            <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${badge.cls}`}>
              {badge.text}
            </span>
            {job?.detail && (
              <span className="text-xs text-gray-500 dark:text-gray-400 max-w-[16rem] truncate" title={job.detail}>
                {job.detail}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ============================================================
// 조건 체크리스트 (초록/빨강 박스 — MasterStrategyResults 패턴 참조)
// ============================================================

function ConditionRow({ check }: { check: ConditionCheck }) {
  return (
    <div
      className={`flex items-center justify-between p-3 rounded-lg border-2 ${
        check.passed
          ? 'bg-green-50 border-green-400 dark:bg-green-900/20 dark:border-green-700'
          : 'bg-red-50 border-red-400 dark:bg-red-900/20 dark:border-red-700'
      }`}
    >
      <div className="flex-1 min-w-0">
        <div className="text-sm font-bold text-gray-900 dark:text-gray-100 mb-1">
          {check.condition_name}
          {check.condition_name_en && (
            <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
              ({check.condition_name_en})
            </span>
          )}
        </div>
        <div className="text-xs text-gray-700 dark:text-gray-300 flex flex-wrap items-center gap-2">
          <span className="font-medium">필요:</span>
          <span className="px-2 py-0.5 bg-blue-100 text-blue-900 dark:bg-blue-900/40 dark:text-blue-200 rounded font-mono">
            {check.required_value}
          </span>
          <span>→</span>
          <span className="font-medium">실제:</span>
          <span
            className={`px-2 py-0.5 rounded font-mono font-bold ${
              check.passed
                ? 'bg-green-100 text-green-900 dark:bg-green-900/40 dark:text-green-200'
                : 'bg-red-100 text-red-900 dark:bg-red-900/40 dark:text-red-200'
            }`}
          >
            {check.actual_value || '데이터 없음'}
          </span>
        </div>
      </div>
      <span
        className={`ml-3 shrink-0 text-xs font-bold px-2.5 py-1 rounded-full ${
          check.passed
            ? 'bg-green-500 text-white'
            : 'bg-red-500 text-white'
        }`}
      >
        {check.passed ? '통과' : '미달'}
      </span>
    </div>
  );
}

// ============================================================
// 뉴스 감성 배지 (색+텍스트)
// ============================================================

function sentimentBadge(sentiment: string): { text: string; cls: string } {
  if (sentiment === 'positive') {
    return {
      text: '호재',
      cls: 'bg-green-100 text-green-800 border-green-300 dark:bg-green-900/30 dark:text-green-300 dark:border-green-700',
    };
  }
  if (sentiment === 'negative') {
    return {
      text: '악재',
      cls: 'bg-red-100 text-red-800 border-red-300 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700',
    };
  }
  return {
    text: '중립',
    cls: 'bg-gray-100 text-gray-700 border-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600',
  };
}

function SentimentBadge({ sentiment }: { sentiment: string }) {
  const b = sentimentBadge(sentiment);
  return (
    <span className={`shrink-0 text-xs font-semibold px-2 py-0.5 rounded border ${b.cls}`}>
      {b.text}
    </span>
  );
}

/** ISO 시각 → 로컬 표시 (실패 시 원문 유지) */
function formatDateTime(iso: string): string {
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    return d.toLocaleString('ko-KR', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

// ============================================================
// 2. 추천 카드 (클릭 시 펼침 — 조건 체크리스트 + 종목 뉴스 lazy)
// ============================================================

function RecommendationCard({ rec }: { rec: TodayRecommendation }) {
  const [expanded, setExpanded] = useState(false);

  // 펼칠 때만 해당 종목 뉴스 조회
  const newsQuery = useQuery({
    queryKey: ['todayNews', 'symbol', rec.symbol],
    queryFn: () => getTodayNews(undefined, rec.symbol),
    enabled: expanded,
  });

  const passedNames = rec.passed_conditions.filter((c) => c.passed).map((c) => c.condition_name);

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-hidden">
      {/* 카드 헤더 (클릭 토글) */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full text-left p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="font-semibold text-gray-900 dark:text-gray-100 truncate">{rec.name}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">{rec.symbol}</div>
          </div>
          <div className="text-right shrink-0">
            <div className="text-2xl font-bold text-primary-600 dark:text-primary-400">
              {rec.score?.toFixed(1)}
            </div>
            <div className="text-xs text-gray-400 dark:text-gray-500">점수</div>
          </div>
        </div>

        {/* 통과 조건 배지 */}
        {passedNames.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {passedNames.map((name, i) => (
              <span
                key={i}
                className="text-xs font-medium px-2 py-0.5 rounded bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
              >
                {name}
              </span>
            ))}
          </div>
        )}

        {/* 시그널 배지 */}
        {rec.technical_signals.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {rec.technical_signals.map((sig, i) => (
              <span
                key={i}
                className={`text-xs font-medium px-2 py-0.5 rounded ${
                  sig.passed
                    ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300'
                    : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'
                }`}
              >
                {sig.condition_name}
              </span>
            ))}
          </div>
        )}

        <div className="flex items-center gap-1 mt-3 text-xs text-gray-500 dark:text-gray-400">
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          {expanded ? '접기' : '상세 보기'}
        </div>
      </button>

      {/* 펼침 영역 */}
      {expanded && (
        <div className="border-t border-gray-200 dark:border-gray-700 p-4 space-y-4">
          {/* 조건 체크리스트 전체 */}
          <div>
            <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100 mb-2">조건 체크</h4>
            <div className="space-y-2">
              {[...rec.passed_conditions, ...rec.technical_signals].map((check, idx) => (
                <ConditionRow key={idx} check={check} />
              ))}
              {rec.passed_conditions.length === 0 && rec.technical_signals.length === 0 && (
                <p className="text-xs text-gray-500 dark:text-gray-400">조건 정보가 없습니다.</p>
              )}
            </div>
          </div>

          {/* 해당 종목 뉴스 (lazy) */}
          <div>
            <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100 mb-2">관련 뉴스</h4>
            {newsQuery.isLoading && <SectionSpinner label="뉴스 불러오는 중..." />}
            {newsQuery.isError && (
              <SectionError message="뉴스를 불러올 수 없습니다." onRetry={() => newsQuery.refetch()} />
            )}
            {newsQuery.data && newsQuery.data.articles.length === 0 && (
              <p className="text-xs text-gray-500 dark:text-gray-400">관련 뉴스가 없습니다.</p>
            )}
            {newsQuery.data && newsQuery.data.articles.length > 0 && (
              <ul className="space-y-2">
                {newsQuery.data.articles.map((a, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <SentimentBadge sentiment={a.sentiment} />
                    <div className="min-w-0">
                      <a
                        href={a.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-gray-800 dark:text-gray-200 hover:text-primary-600 dark:hover:text-primary-400 hover:underline"
                      >
                        {a.title}
                      </a>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {a.source} · {formatDateTime(a.published_at)}
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function RecommendationsSection() {
  const query = useQuery({
    queryKey: ['todayRecommendations'],
    queryFn: () => getTodayRecommendations(),
  });

  return (
    <SectionCard title="오늘의 추천">
      {/* 면책 문구 상시 표시 */}
      <div className="flex items-start gap-2 mb-4 p-3 rounded-lg bg-amber-50 border border-amber-200 dark:bg-amber-900/20 dark:border-amber-800">
        <Info className="w-4 h-4 mt-0.5 shrink-0 text-amber-600 dark:text-amber-400" />
        <p className="text-xs text-amber-800 dark:text-amber-300">
          {query.data?.disclaimer || '교육·연구용 정보로 투자 권유가 아닙니다.'}
        </p>
      </div>

      {query.isLoading && <SectionSpinner label="추천 불러오는 중..." />}
      {query.isError && (
        <SectionError message="추천을 불러올 수 없습니다." onRetry={() => query.refetch()} />
      )}
      {query.data && query.data.recommendations.length === 0 && (
        <EmptyState message="오늘 추천이 아직 없습니다 (주말·장 시작 전이거나 수집 중)." />
      )}
      {query.data && query.data.recommendations.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {query.data.recommendations.map((rec) => (
            <RecommendationCard key={rec.symbol} rec={rec} />
          ))}
        </div>
      )}
    </SectionCard>
  );
}

// ============================================================
// 3. 뉴스 피드 (시간 내림차순)
// ============================================================

function NewsSection() {
  const query = useQuery({
    queryKey: ['todayNews', 'all'],
    queryFn: () => getTodayNews(),
  });

  // 시간 내림차순 정렬
  const articles = [...(query.data?.articles ?? [])].sort((a, b) => {
    const ta = new Date(a.published_at).getTime();
    const tb = new Date(b.published_at).getTime();
    if (isNaN(ta) || isNaN(tb)) return 0;
    return tb - ta;
  });

  return (
    <SectionCard title="오늘의 뉴스">
      {query.isLoading && <SectionSpinner label="뉴스 불러오는 중..." />}
      {query.isError && (
        <SectionError message="뉴스를 불러올 수 없습니다." onRetry={() => query.refetch()} />
      )}
      {query.data && articles.length === 0 && <EmptyState message="오늘 수집된 뉴스가 없습니다." />}
      {articles.length > 0 && (
        <ul className="space-y-3">
          {articles.map((a, i) => (
            <li
              key={i}
              className="flex items-start gap-3 pb-3 border-b border-gray-100 dark:border-gray-700 last:border-0 last:pb-0"
            >
              <SentimentBadge sentiment={a.sentiment} />
              <div className="min-w-0 flex-1">
                <a
                  href={a.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-start gap-1 text-sm font-medium text-gray-800 dark:text-gray-200 hover:text-primary-600 dark:hover:text-primary-400 hover:underline"
                >
                  {a.title}
                  <ExternalLink className="w-3.5 h-3.5 mt-0.5 shrink-0 text-gray-400" />
                </a>
                <div className="flex flex-wrap items-center gap-2 mt-1 text-xs text-gray-500 dark:text-gray-400">
                  <span>{a.source}</span>
                  <span>·</span>
                  <span>{formatDateTime(a.published_at)}</span>
                  {a.symbols.map((sym) => (
                    <span
                      key={sym}
                      className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300"
                    >
                      {sym}
                    </span>
                  ))}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}

// ============================================================
// 페이지
// ============================================================

export default function TodayPage() {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">오늘</h1>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          오늘의 수집 상태 · 추천 종목 · 뉴스를 한눈에 확인하세요.
        </p>
      </div>

      <SectionCard title="수집 상태">
        <StatusStrip />
      </SectionCard>

      <RecommendationsSection />

      <NewsSection />
    </div>
  );
}
