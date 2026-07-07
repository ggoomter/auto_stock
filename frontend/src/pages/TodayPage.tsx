import { useEffect, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { RefreshCw, ChevronDown, ChevronUp, ExternalLink, Info, Target } from 'lucide-react';
import {
  getTodayStatus,
  getTodayRecommendations,
  getTodayNews,
  postRefreshRecommendations,
  getRefreshStatus,
  type ConditionCheck,
  type TodayRecommendation,
} from '../services/api';
import { useToast } from '../components/Toast';

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
  crisis_check: '위기감시',
};
const JOB_KEYS = ['news_crawl', 'recommendations', 'paper_reconcile', 'crisis_check'];

/** ISO 시각 → 'HH:MM' (표시용). 파싱 불가 시 null */
function formatTimeHHMM(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const m = iso.match(/T(\d{2}:\d{2})/);
  return m ? m[1] : null;
}

/** ISO 시각 → 'YYYY-MM-DD HH:MM' (분석 기준 시점 표시용 — 연도 포함 명시) */
function formatAnalyzedAt(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const m = iso.match(/^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})/);
  return m ? `${m[1]} ${m[2]}` : iso;
}

/** 작업 detail(JSON 문자열)을 사람이 읽는 요약으로 변환. 실패 시 원문 유지 */
function formatJobDetail(jobKey: string, detail: string | null | undefined): string | null {
  if (!detail) return null;
  try {
    const d = JSON.parse(detail);
    if (d.skipped === 'weekend') return '주말 휴장';
    if (jobKey === 'news_crawl')
      return `수집 ${d.fetched ?? 0}건 · 신규 저장 ${d.inserted ?? 0}건 · 종목 연결 ${d.linked_symbols ?? 0}건`;
    if (jobKey === 'recommendations') {
      const trend = typeof d.trend_rejected === 'number' ? ` · 하락추세 제외 ${d.trend_rejected}개` : '';
      return `후보 ${d.universe ?? '-'}개 · 조건 통과 ${d.filtered ?? '-'}개${trend} · 추천 ${d.saved ?? '-'}개`;
    }
    if (jobKey === 'paper_reconcile')
      return `점검 ${d.checked ?? 0}건 · 청산 ${d.closed ?? 0}건 · 유지 ${d.skipped ?? 0}건`;
    if (jobKey === 'crisis_check') {
      const parts = Object.entries(d).map(([market, v]) => {
        const dd = (v as { drawdown?: number })?.drawdown;
        return typeof dd === 'number' ? `${market} 고점대비 ${(dd * 100).toFixed(1)}%` : `${market} 조회실패`;
      });
      return parts.length > 0 ? parts.join(' · ') : detail;
    }
    return detail;
  } catch {
    return detail; // JSON이 아니면(실패 사유 문자열 등) 원문 표시
  }
}

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
            {formatJobDetail(key, job?.detail) && (
              <span className="text-xs text-gray-500 dark:text-gray-400 max-w-[20rem] truncate" title={job?.detail ?? undefined}>
                {formatJobDetail(key, job?.detail)}
              </span>
            )}
            {formatTimeHHMM(job?.finished_at) && (
              <span className="text-xs text-gray-400 dark:text-gray-500">
                {formatTimeHHMM(job?.finished_at)}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ============================================================
// 지표 한글 해설 — "왜 이 조건을 보는가"를 초보자 눈높이로 설명
// ============================================================

interface IndicatorGuide {
  /** 이 지표가 무엇인지 (조건 체크리스트 각 행 아래 표시) */
  meaning: string;
  /** 통과 시 "왜 추천 근거가 되는지" 문장 (actual_value를 받아 완성) */
  reason: (actual: string) => string;
}

const INDICATOR_GUIDE: Record<string, IndicatorGuide> = {
  PER: {
    meaning:
      'PER(주가수익비율) = 주가 ÷ 주당 연간 이익. 회사가 버는 이익에 비해 주가가 몇 배인지를 나타내며, 낮을수록 이익 대비 주가가 싼 편입니다.',
    reason: (a) => `이익에 비해 주가가 비싸지 않습니다 (PER ${a} — 25배 미만이면 고평가 부담이 적은 구간)`,
  },
  PBR: {
    meaning:
      'PBR(주가순자산비율) = 주가 ÷ 주당 순자산. 회사가 가진 자산 가치 대비 주가 수준으로, 낮을수록 자산 대비 저평가입니다.',
    reason: (a) => `회사 자산 가치 대비 주가가 부담스럽지 않습니다 (PBR ${a})`,
  },
  ROE: {
    meaning:
      'ROE(자기자본이익률) = 순이익 ÷ 자기자본. 회사가 주주 돈으로 1년에 몇 %의 이익을 만드는지로, 높을수록 장사를 잘하는 회사입니다.',
    reason: (a) => `주주 자본으로 이익을 잘 내는 회사입니다 (ROE ${a} — 10% 초과)`,
  },
  GoldenCross: {
    meaning:
      '골든크로스 = 최근 20일 평균 주가가 60일 평균 주가를 위로 뚫는 것. 단기 매수세가 중기 흐름보다 강해졌다는 신호입니다.',
    reason: () => `최근 매수세가 붙으며 20일 평균선이 60일 평균선을 상향 돌파했습니다`,
  },
  RSIRebound: {
    meaning:
      'RSI(상대강도지수)는 최근 14일간 상승·하락 강도로 과열(70↑)/과매도(30↓)를 재는 지표. "과매도 → 회복"은 단기 반등 신호입니다.',
    reason: (a) => `과매도 구간까지 눌렸다가 회복을 시작했습니다 (${a})`,
  },
  NearHigh: {
    meaning:
      '52주 신고가 근접 = 현재 주가가 최근 1년 최고가의 95% 이상. 신고가 부근은 물린 매물(저항)이 적어 추세가 이어지기 쉽습니다.',
    reason: (a) => `1년 최고가 부근이라 매물 저항이 적습니다 (${a})`,
  },
  Trend: {
    meaning:
      '상승 추세 = 종가가 200일 평균선 위. 장기 방향이 위를 향한다는 뜻이며, 이 조건에 미달(하락 추세)한 종목은 추천에서 아예 제외됩니다.',
    reason: (a) => `장기(200일선) 상승 추세가 유지되고 있습니다 (${a})`,
  },
};

/** 통과한 조건들을 한글 문장 목록으로 — "왜 이 종목을 추천하는가" */
function WhyRecommended({ rec }: { rec: TodayRecommendation }) {
  const passed = [...rec.passed_conditions, ...rec.technical_signals].filter((c) => c.passed);
  if (passed.length === 0) return null;
  return (
    <div className="p-3 rounded-lg bg-primary-50 border border-primary-200 dark:bg-primary-900/20 dark:border-primary-800">
      <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100 mb-2">
        왜 이 종목이 추천되었나요?
      </h4>
      <ul className="space-y-1.5">
        {passed.map((c, i) => {
          const guide = INDICATOR_GUIDE[c.condition_name_en ?? ''];
          const text = guide
            ? guide.reason(c.actual_value || '')
            : `${c.condition_name} 조건을 충족했습니다 (${c.actual_value || '-'})`;
          return (
            <li key={i} className="flex gap-2 text-xs text-gray-700 dark:text-gray-300">
              <span className="shrink-0 text-primary-600 dark:text-primary-400 font-bold">✓</span>
              <span>{text}</span>
            </li>
          );
        })}
      </ul>
      <p className="mt-2 text-[11px] text-gray-500 dark:text-gray-400">
        미달 조건은 점수에 반영되지 않았으며, 아래 조건 체크에서 전체 판정을 확인할 수 있습니다.
      </p>
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
        {/* 지표 한글 해설 — 이 조건이 무엇이고 왜 보는지 */}
        {INDICATOR_GUIDE[check.condition_name_en ?? '']?.meaning && (
          <p className="mt-1.5 text-[11px] leading-relaxed text-gray-500 dark:text-gray-400">
            {INDICATOR_GUIDE[check.condition_name_en ?? ''].meaning}
          </p>
        )}
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

        {/* 시그널 배지 — 통과한 신호만 표시 (미달 신호를 나열하면 성립한 것처럼 오독됨) */}
        {rec.technical_signals.filter((s) => s.passed).length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {rec.technical_signals
              .filter((sig) => sig.passed)
              .map((sig, i) => (
                <span
                  key={i}
                  className="text-xs font-medium px-2 py-0.5 rounded bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
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
          {/* 추천 사유 — 통과 지표를 한글 문장으로 풀어 설명 */}
          <WhyRecommended rec={rec} />

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

      {/* 분석 기준 시점 — 실시간이 아니라 '이 시각 데이터로 분석했음'을 명시 */}
      {query.data && (
        <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
          {formatAnalyzedAt(query.data.analyzed_at)
            ? `분석 시점: ${formatAnalyzedAt(query.data.analyzed_at)} — 이 시각 수집 데이터 기준 (실시간 아님)`
            : query.data.date
              ? `기준일: ${query.data.date} (분석 완료 시각 기록 없음)`
              : null}
        </p>
      )}

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
// 히어로: 지금 매수 추천 버튼 (핵심 기능)
// ============================================================

function BuyNowHero() {
  const toast = useToast();
  const queryClient = useQueryClient();
  const [running, setRunning] = useState(false);
  const pollRef = useRef<number | null>(null);

  // 언마운트 시 폴링 정리
  useEffect(() => () => {
    if (pollRef.current !== null) window.clearInterval(pollRef.current);
  }, []);

  const startPolling = () => {
    pollRef.current = window.setInterval(async () => {
      try {
        const st = await getRefreshStatus();
        if (!st.running) {
          if (pollRef.current !== null) window.clearInterval(pollRef.current);
          pollRef.current = null;
          setRunning(false);
          if (st.error) {
            toast.error(`추천 계산 실패: ${st.error}`);
          } else {
            await queryClient.invalidateQueries({ queryKey: ['todayRecommendations'] });
            await queryClient.invalidateQueries({ queryKey: ['todayStatus'] });
            toast.success('지금 매수 추천이 갱신되었습니다.');
          }
        }
      } catch {
        // 일시적 폴링 실패는 무시하고 다음 주기에 재시도
      }
    }, 3000);
  };

  const onClick = async () => {
    try {
      setRunning(true);
      const res = await postRefreshRecommendations();
      if (res.status === 'already_running') {
        toast.warning('이미 계산이 진행 중입니다. 잠시만 기다려주세요.');
      }
      startPolling();
    } catch {
      setRunning(false);
      toast.error('추천 계산을 시작하지 못했습니다. 백엔드 상태를 확인해주세요.');
    }
  };

  return (
    <div className="rounded-2xl border-2 border-primary-500 bg-gradient-to-r from-primary-600 to-primary-700 p-6 shadow-lg">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="text-white">
          <h2 className="text-xl font-bold flex items-center gap-2">
            <Target className="w-6 h-6" />
            지금 매수 추천
          </h2>
          <p className="text-sm text-primary-100 mt-1">
            버튼을 누르면 최신 시세로 즉시 분석합니다 — 시가총액 상위 유니버스 → 펀더멘털
            필터 → 상승 추세 게이트(하락 추세 자동 제외) → 기술 신호 순으로 선별한 상위 10종목.
          </p>
        </div>
        <button
          onClick={onClick}
          disabled={running}
          className={`shrink-0 inline-flex items-center gap-2 px-6 py-3 rounded-xl text-base font-bold transition-colors ${
            running
              ? 'bg-white/30 text-white cursor-not-allowed'
              : 'bg-white text-primary-700 hover:bg-primary-50 shadow'
          }`}
        >
          {running ? (
            <>
              <RefreshCw className="w-5 h-5 animate-spin" />
              분석 중... (약 1분)
            </>
          ) : (
            <>
              <Target className="w-5 h-5" />
              지금 매수 추천 받기
            </>
          )}
        </button>
      </div>
    </div>
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

      <BuyNowHero />

      <RecommendationsSection />

      <SectionCard title="수집 상태">
        <StatusStrip />
      </SectionCard>

      <NewsSection />
    </div>
  );
}
