// ── Auth Context ──────────────────────────────────────────────────────
import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  type ReactNode,
} from "react";
import { login as apiLogin } from "../api/endpoints";

interface AuthState {
  token: string;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (id: string, password: string) => Promise<void>;
  signup: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  error: string | null;
}

const AuthContext = createContext<AuthState | null>(null);

function getStoredToken(): string {
  return (
    localStorage.getItem("admin_token") ||
    localStorage.getItem("mos_admin_token") ||
    ""
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string>(getStoredToken);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const t = getStoredToken();
    setToken(t);
    setIsLoading(false);
  }, []);

  const login = useCallback(async (id: string, password: string) => {
    setError(null);
    try {
      // In User App, we use email/username login
      const isUserApp = window.location.hash.includes("/app") || window.location.pathname.startsWith("/app");
      const data = await apiLogin(id, password, isUserApp);
      localStorage.setItem("admin_token", (data.api_key || data.access_token || ""));
      localStorage.setItem("mos_admin_token", (data.api_key || data.access_token || ""));
      setToken((data.api_key || data.access_token || ""));
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "验证失败";
      setError(msg);
      throw e;
    }
  }, []);

  const signup = useCallback(async (username: string, email: string, password: string) => {
    setError(null);
    try {
      const { signup: apiSignup } = await import("../api/endpoints");
      await apiSignup(username, email, password);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "注册失败";
      setError(msg);
      throw e;
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("admin_token");
    localStorage.removeItem("mos_admin_token");
    setToken("");
  }, []);

  return (
    <AuthContext.Provider
      value={{
        token,
        isAuthenticated: !!token && token.length > 0,
        isLoading,
        login,
        signup,
        logout,
        error,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
