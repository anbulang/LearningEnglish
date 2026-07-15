/*
 * App-level context providers: theme (light/dark), toast notifications, and the
 * confirm dialog. Pages trigger toasts/confirms via the `useToast`/`useConfirm`
 * hooks; the theme is applied to <html data-theme> and persisted.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode
} from "react";
import { Modal } from "./ui";
import { IconCheck, IconShield } from "./icons";

/* ── Theme ────────────────────────────────────────────────────── */

export type Theme = "light" | "dark";
const THEME_STORAGE_KEY = "le-admin-theme";

interface ThemeContextValue {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: "light",
  toggleTheme: () => {},
  setTheme: () => {}
});

export function ThemeProvider({ children, defaultTheme = "light" }: { children: ReactNode; defaultTheme?: Theme }) {
  const [theme, setTheme] = useState<Theme>(() => {
    try {
      const stored = localStorage.getItem(THEME_STORAGE_KEY);
      if (stored === "light" || stored === "dark") {
        return stored;
      }
    } catch {
      /* localStorage unavailable */
    }
    return defaultTheme;
  });

  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.setAttribute("data-theme", theme);
    }
    try {
      localStorage.setItem(THEME_STORAGE_KEY, theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  const toggleTheme = useCallback(() => setTheme((current) => (current === "dark" ? "light" : "dark")), []);
  const value = useMemo<ThemeContextValue>(() => ({ theme, toggleTheme, setTheme }), [theme, toggleTheme]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  return useContext(ThemeContext);
}

/* ── Toast ────────────────────────────────────────────────────── */

const ToastContext = createContext<(message: string) => void>(() => {});

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<{ id: number; message: string } | null>(null);
  const counter = useRef(0);
  const timer = useRef<ReturnType<typeof setTimeout>>();

  const push = useCallback((message: string) => {
    counter.current += 1;
    setToast({ id: counter.current, message });
    if (timer.current) {
      clearTimeout(timer.current);
    }
    timer.current = setTimeout(() => setToast(null), 2600);
  }, []);

  useEffect(() => {
    return () => {
      if (timer.current) {
        clearTimeout(timer.current);
      }
    };
  }, []);

  return (
    <ToastContext.Provider value={push}>
      {children}
      {toast && (
        <div
          role="status"
          aria-live="polite"
          key={toast.id}
          style={{
            position: "fixed",
            bottom: 26,
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 90,
            display: "flex",
            alignItems: "center",
            gap: 9,
            background: "var(--text)",
            color: "var(--surface)",
            fontSize: 13,
            fontWeight: 500,
            padding: "11px 18px",
            borderRadius: 10,
            boxShadow: "var(--shadow-pop)",
            animation: "le-toast-in .18s ease-out"
          }}
        >
          <span style={{ color: "var(--success)", display: "inline-flex" }}>
            <IconCheck size={16} />
          </span>
          {toast.message}
        </div>
      )}
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}

/* ── Confirm ──────────────────────────────────────────────────── */

export interface ConfirmOptions {
  title: string;
  body: ReactNode;
  confirmLabel: string;
  cancelLabel: string;
  onConfirm: () => void;
}

const ConfirmContext = createContext<(options: ConfirmOptions) => void>(() => {});

export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [options, setOptions] = useState<ConfirmOptions | null>(null);
  const ask = useCallback((next: ConfirmOptions) => setOptions(next), []);
  const close = useCallback(() => setOptions(null), []);

  return (
    <ConfirmContext.Provider value={ask}>
      {children}
      <Modal open={options !== null} onClose={close} width={412} zIndex={70} ariaLabel={options?.title}>
        {options && (
          <>
            <div
              style={{
                width: 46,
                height: 46,
                borderRadius: 12,
                background: "var(--danger-subtle)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                marginBottom: 15,
                color: "var(--danger)"
              }}
            >
              <IconShield size={22} />
            </div>
            <div style={{ fontSize: 17, fontWeight: 700, color: "var(--text)" }}>{options.title}</div>
            <div style={{ fontSize: 13, color: "var(--text-2)", marginTop: 9, lineHeight: 1.65 }}>{options.body}</div>
            <div style={{ display: "flex", gap: 10, marginTop: 20 }}>
              <button
                type="button"
                onClick={close}
                className="le-hover-soft"
                style={{
                  flex: 1,
                  height: 38,
                  border: "1px solid var(--border-strong)",
                  borderRadius: 8,
                  background: "var(--surface)",
                  color: "var(--text)",
                  fontSize: 13,
                  fontWeight: 500,
                  cursor: "pointer",
                  fontFamily: "inherit"
                }}
              >
                {options.cancelLabel}
              </button>
              <button
                type="button"
                onClick={() => {
                  const confirmed = options.onConfirm;
                  close();
                  confirmed();
                }}
                style={{
                  flex: 1,
                  height: 38,
                  border: "none",
                  borderRadius: 8,
                  background: "var(--danger)",
                  color: "#fff",
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: "pointer",
                  fontFamily: "inherit"
                }}
              >
                {options.confirmLabel}
              </button>
            </div>
          </>
        )}
      </Modal>
    </ConfirmContext.Provider>
  );
}

export function useConfirm() {
  return useContext(ConfirmContext);
}
