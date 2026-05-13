// ── Login Overlay ─────────────────────────────────────────────────────
import { useState } from "react";
import { useAuth } from "../contexts/AuthContext";

export function LoginOverlay() {
  const { login, error: authError } = useAuth();
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const pwd = password.trim();
    if (!pwd) {
      setLocalError("请输入密码");
      return;
    }
    setLocalError(null);
    setLoading(true);
    try {
      await login(pwd);
    } catch {
      setLocalError(authError || "验证失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-overlay">
      <div className="login-box">
        <div className="login-logo">🧠</div>
        <div className="login-title">COMMAND DECK LOGIN</div>
        <div className="login-sub">请输入管理员凭据以连接 AI MEMORY OS 网关</div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>安全密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="输入管理员密码..."
              className="form-input"
              autoFocus
            />
          </div>
          <button
            type="submit"
            className="btn btn-teal w-full mt-4"
            disabled={loading}
          >
            {loading ? "验证中..." : "🔓 验证凭据"}
          </button>
        </form>
        {(localError || authError) && (
          <div className="login-error">{localError || authError}</div>
        )}
      </div>
    </div>
  );
}
