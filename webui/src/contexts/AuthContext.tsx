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
  login: (password: string) => Promise<void>;
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

  const login = useCallback(async (password: string) => {
    setError(null);
    try {
      const data = await apiLogin(password);
      localStorage.setItem("admin_token", data.api_key);
      localStorage.setItem("mos_admin_token", data.api_key);
      setToken(data.api_key);
    } catch (e: unknown) {
      const msg =
        e instanceof Error ? e.message : "网关连接失败，请检查后端服务";
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
        isAuthenticated: token.length > 0,
        isLoading,
        login,
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
