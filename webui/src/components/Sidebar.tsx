// ── Sidebar Navigation — Admin ─────────────────────────────────────────────
import { NavLink } from "react-router-dom";

const NAV_SECTIONS = [
  {
    label: "总览 Overview",
    items: [
      { to: "/",           label: "控制台 Dashboard" },
      { to: "/monitoring", label: "监控 Monitoring" },
      { to: "/audit",      label: "审计 Audit Logs" },
    ],
  },
  {
    label: "配置 Config",
    items: [
      { to: "/models", label: "模型配置 Providers" },
    ],
  },
  {
    label: "管理 Manage",
    items: [
      { to: "/tenants",  label: "租户 Tenants" },
      { to: "/users",    label: "用户 Users" },
      { to: "/memories", label: "记忆 Memories" },
    ],
  },
  {
    label: "认知调优 Cognitive",
    items: [
      { to: "/reflection", label: "知识整合 Reflection" },
      { to: "/graph",      label: "知识图谱 Graph", badge: "NEW" },
      { to: "/config",     label: "系统参数 System" },
    ],
  },
];

const navBase: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 0,
  padding: '8px 12px',
  borderRadius: 'var(--v6-radius-md)',
  cursor: 'pointer',
  fontSize: 13,
  fontWeight: 500,
  fontFamily: 'var(--v6-font-sans)',
  color: 'var(--v6-fg-muted)',
  textDecoration: 'none',
  marginBottom: 1,
  transition: 'all 0.15s',
  letterSpacing: '-0.005em',
  whiteSpace: 'nowrap' as const,
};

export function Sidebar() {
  return (
    <nav style={{
      width: 220,
      background: 'var(--v6-bg)',
      borderRight: '1px solid var(--v6-border)',
      padding: '18px 10px',
      flexShrink: 0,
      overflowY: 'auto',
      display: 'flex',
      flexDirection: 'column',
      gap: 4,
    }}>
      {NAV_SECTIONS.map((section) => (
        <div key={section.label} style={{ marginBottom: 18 }}>
          <div style={{
            fontSize: 10,
            fontFamily: 'var(--v6-font-mono)',
            letterSpacing: '0.07em',
            textTransform: 'uppercase',
            color: 'var(--v6-fg-faint)',
            padding: '0 12px',
            marginBottom: 6,
          }}>
            {section.label}
          </div>
          {section.items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              style={({ isActive }) => ({
                ...navBase,
                background: isActive ? 'var(--v6-bg-sunken)' : 'transparent',
                color: isActive ? 'var(--v6-fg)' : 'var(--v6-fg-muted)',
                borderLeft: isActive ? '2px solid var(--v6-fg)' : '2px solid transparent',
              })}
            >
              <span style={{ flex: 1 }}>{item.label}</span>
              {item.badge && (
                <span style={{
                  fontSize: 9,
                  fontFamily: 'var(--v6-font-mono)',
                  fontWeight: 700,
                  padding: '1px 5px',
                  borderRadius: 3,
                  background: 'var(--v6-bg-sunken)',
                  border: '1px solid var(--v6-border-strong)',
                  color: 'var(--v6-fg-muted)',
                  letterSpacing: '0.06em',
                }}>
                  {item.badge}
                </span>
              )}
            </NavLink>
          ))}
        </div>
      ))}
    </nav>
  );
}
