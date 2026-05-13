// ── Topbar (Health Indicator + Logo + Admin Badge) ────────────────────
import { useEffect, useState } from "react";
import { getHealth } from "../api/endpoints";
import type { ServiceHealth } from "../api/types";
import { useAuth } from "../contexts/AuthContext";

export function Topbar() {
  const { logout } = useAuth();
  const [healthy, setHealthy] = useState(true);
  const [statusText, setStatusText] = useState("检测中...");

  useEffect(() => {
    let mounted = true;
    

    async function check() {
      try {
        const data = await getHealth();
        if (!mounted) return;
        const svc = data.services as ServiceHealth;
        const allOk = Object.values(svc).every(Boolean);
        setHealthy(allOk);
        setStatusText(allOk ? "系统正常" : "部分离线");
      } catch {
        if (!mounted) return;
        setHealthy(false);
        setStatusText("服务离线");
      }
    }

    check();
    const timer = setInterval(check, 12000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  return (
    <header className="topbar">
      <div className="topbar-left">
        <div className="logo-orb">🧠</div>
        <span className="logo-text">AI MEMORY OS</span>
        <span className="admin-badge">ADMIN</span>
      </div>
      <div className="topbar-right">
        <div className="health-indicator">
          <div className={`health-dot ${healthy ? "" : "err"}`} />
          <span className="health-text">{statusText}</span>
        </div>
        <span className="topbar-location">LOCALHOST ONLY</span>
        <button className="topbar-logout" onClick={logout} title="退出登录">
          ⏻
        </button>
      </div>
    </header>
  );
}
