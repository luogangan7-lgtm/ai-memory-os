// ── Sidebar Navigation ────────────────────────────────────────────────
import { NavLink } from "react-router-dom";

const NAV_SECTIONS = [
  {
    label: "总览",
    items: [
      { to: "/", label: "控制台", icon: "📊" },
      { to: "/monitoring", label: "监控", icon: "📈" },
      { to: "/audit", label: "审计日志", icon: "📋" },
    ],
  },
  {
    label: "配置",
    items: [
      { to: "/providers", label: "系统算力", icon: "🔌" },
      { to: "/llm-engine", label: "LLM 引擎", icon: "🤖", badge: "NEW" },
    ],
  },
  {
    label: "管理",
    items: [
      { to: "/tenants", label: "租户管理", icon: "🏢" },
      { to: "/users", label: "用户管理", icon: "👤" },
    ],
  },
  {
    label: "认知调优",
    items: [
      { to: "/reflection", label: "知识整合", icon: "🔮" },
      { to: "/config", label: "系统参数", icon: "⚙️" },
    ],
  },
];

export function Sidebar() {
  return (
    <nav className="sidebar">
      {NAV_SECTIONS.map((section) => (
        <div key={section.label}>
          <div className="nav-section">{section.label}</div>
          {section.items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `nav-item${isActive ? " active" : ""}`
              }
            >
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
              {item.badge && <span className="nav-new">{item.badge}</span>}
            </NavLink>
          ))}
        </div>
      ))}
    </nav>
  );
}
