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
  mcpKey: string;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (id: string, password: string) => Promise<void>;
  signup: (username: string, email: string, password: string, code?: string) => Promise<void>;
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

function getStoredMcpKey(): string {
  return localStorage.getItem("mcp_api_key") || "";
}

// eslint-disable-next-line react-refresh/only-export-components
export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string>(getStoredToken);
  const [mcpKey, setMcpKey] = useState<string>(getStoredMcpKey);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setToken(getStoredToken());
    setMcpKey(getStoredMcpKey());
    setIsLoading(false);
  }, []);

  const login = useCallback(async (id: string, password: string) => {
    setError(null);
    try {
      const isUserApp = window.location.hash.includes("/app") || window.location.pathname.startsWith("/app");
      const data = await apiLogin(id, password, isUserApp);
      
      const jwtToken = (data as { access_token?: string; token?: string; api_key?: string }).access_token || (data as { access_token?: string; token?: string; api_key?: string }).token || data.api_key || "";
      const persistentKey = data.api_key || "";
      
      localStorage.setItem("admin_token", jwtToken);
      localStorage.setItem("mos_admin_token", jwtToken);
      localStorage.setItem("mcp_api_key", persistentKey);
      
      setToken(jwtToken);
      setMcpKey(persistentKey);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "验证失败";
      setError(msg);
      throw e;
    }
  }, []);

  const signup = useCallback(async (username: string, email: string, password: string, code?: string) => {
    setError(null);
    try {
      const { signup: apiSignup } = await import("../api/endpoints");
      await apiSignup(username, email, password, code);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "注册失败";
      setError(msg);
      throw e;
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("admin_token");
    localStorage.removeItem("mos_admin_token");
    localStorage.removeItem("mcp_api_key");
    fetch("/auth/logout", {method:"POST",credentials:"include"});
    setToken("");
    setMcpKey("");
  }, []);

  return (
    <AuthContext.Provider
      value={{
        token,
        mcpKey,
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
