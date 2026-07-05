import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';

// 토스트 타입 정의
type ToastType = 'success' | 'error' | 'warning';

interface ToastItem {
  id: number;
  type: ToastType;
  message: string;
}

interface ToastContextValue {
  success: (message: string) => void;
  error: (message: string) => void;
  warning: (message: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

// 자동 소멸 시간(ms)
const AUTO_DISMISS_MS = 4000;

// 타입별 색상 (tailwind success/danger/warning 토큰 + 다크 변형 병기)
const TYPE_STYLES: Record<ToastType, string> = {
  success:
    'bg-success/10 border-success text-green-800 dark:bg-success/20 dark:text-green-200',
  error:
    'bg-danger/10 border-danger text-red-800 dark:bg-danger/20 dark:text-red-200',
  warning:
    'bg-warning/10 border-warning text-amber-800 dark:bg-warning/20 dark:text-amber-100',
};

function ToastCard({
  toast,
  onClose,
}: {
  toast: ToastItem;
  onClose: (id: number) => void;
}) {
  const [visible, setVisible] = useState(false);

  // 마운트 직후 트랜지션용 상태 전환
  useEffect(() => {
    const raf = requestAnimationFrame(() => setVisible(true));
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <div
      role="alert"
      className={`pointer-events-auto flex items-start gap-3 rounded-lg border-l-4 px-4 py-3 shadow-lg transition-all duration-300 ease-out ${
        TYPE_STYLES[toast.type]
      } ${visible ? 'translate-x-0 opacity-100' : 'translate-x-4 opacity-0'}`}
    >
      <p className="flex-1 whitespace-pre-line text-sm font-medium">
        {toast.message}
      </p>
      <button
        type="button"
        onClick={() => onClose(toast.id)}
        aria-label="닫기"
        className="ml-2 shrink-0 text-lg leading-none opacity-60 hover:opacity-100"
      >
        ×
      </button>
    </div>
  );
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const remove = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (type: ToastType, message: string) => {
      // 고유 id 생성 (시각 + 난수)
      const id = Date.now() + Math.random();
      setToasts((prev) => [...prev, { id, type, message }]);
      setTimeout(() => remove(id), AUTO_DISMISS_MS);
    },
    [remove]
  );

  const value: ToastContextValue = {
    success: (message) => push('success', message),
    error: (message) => push('error', message),
    warning: (message) => push('warning', message),
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      {/* 우상단 고정 스택 */}
      <div className="pointer-events-none fixed right-4 top-4 z-[100] flex w-full max-w-sm flex-col gap-2">
        {toasts.map((toast) => (
          <ToastCard key={toast.id} toast={toast} onClose={remove} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

// 토스트 훅
export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return ctx;
}
