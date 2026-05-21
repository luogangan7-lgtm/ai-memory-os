// ── Topbar — Admin Command Deck ───────────────────────────────────────────
import { useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { CortexMark } from "./CortexMark";

export function Topbar() {
  const { logout } = useAuth();
  const [healthy, setHealthy] = useState(true);

  useEffect(() => {
    let mounted = true;
    async function check() {
      try {
        const r = await fetch("/health");
        if (mounted) setHealthy(r.ok);
      } catch {
        if (mounted) setHealthy(false);
      }
    }
    check();
    const t = setInterval(check, 15000);
    return () => { mounted = false; clearInterval(t); };
  }, []);

  return (
    <header style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px',
      height: 58,
      background: 'var(--v6-bg)',
      borderBottom: '1px solid var(--v6-border)',
      flexShrink: 0,
      position: 'sticky',
      top: 0,
      zIndex: 100,
    }}>
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <CortexMark size={22} breathing />
        <span style={{
          fontFamily: 'var(--v6-font-sans)',
          fontWeight: 600,
          fontSize: 17,
          letterSpacing: '-0.02em',
          color: 'var(--v6-fg)',
        }}>
          Cortex
        </span>
        <span style={{
          fontFamily: 'var(--v6-font-mono)',
          fontSize: 10,
          fontWeight: 600,
          padding: '2px 8px',
          borderRadius: 4,
          border: '1px solid var(--v6-border-strong)',
          color: 'var(--v6-fg-muted)',
          letterSpacing: '0.06em',
        }}>
          管理后台 Admin
        </span>
      </div>

      {/* Right: health + logout */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 7,
          fontFamily: 'var(--v6-font-mono)', fontSize: 11,
          color: 'var(--v6-fg-muted)',
        }}>
          <span style={{
            width: 7, height: 7, borderRadius: '50%',
            background: healthy ? '#2DBFA8' : 'var(--v6-danger)',
            display: 'inline-block',
          }} />
          {healthy ? '系统正常 Online' : '连接异常 Offline'}
        </div>

        <button
          onClick={logout}
          style={{
            appearance: 'none',
            background: 'transparent',
            border: '1px solid var(--v6-border)',
            color: 'var(--v6-fg-muted)',
            fontFamily: 'var(--v6-font-mono)',
            fontSize: 11,
            padding: '5px 12px',
            borderRadius: 'var(--v6-radius-md)',
            cursor: 'pointer',
            letterSpacing: '0.04em',
            transition: 'all 0.15s',
          }}
          onMouseEnter={e => {
            (e.target as HTMLButtonElement).style.borderColor = 'var(--v6-border-strong)';
            (e.target as HTMLButtonElement).style.color = 'var(--v6-fg)';
          }}
          onMouseLeave={e => {
            (e.target as HTMLButtonElement).style.borderColor = 'var(--v6-border)';
            (e.target as HTMLButtonElement).style.color = 'var(--v6-fg-muted)';
          }}
        >
          退出 Sign out
        </button>
      </div>
    </header>
  );
}
