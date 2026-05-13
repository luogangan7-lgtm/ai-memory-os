// ── Toast Context ─────────────────────────────────────────────────────
import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from "react";

interface ToastItem {
  id: number;
  message: string;
  type: "ok" | "err";
}

interface ToastContextType {
  toasts: ToastItem[];
  toast: (message: string, type?: "ok" | "err") => void;
}

const ToastContext = createContext<ToastContextType | null>(null);

let nextId = 0;

// eslint-disable-next-line react-refresh/only-export-components
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const toast = useCallback((message: string, type: "ok" | "err" = "ok") => {
    const id = nextId++;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3500);
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, toast }}>
      {children}
      {/* Toast container */}
      <div className="toast-container">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.type}`}>
            <span>{t.type === "ok" ? "✅" : "❌"}</span> {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useToast(): ToastContextType {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
