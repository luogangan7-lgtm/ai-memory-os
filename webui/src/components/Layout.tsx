// ── Layout (Topbar + Sidebar + Page Container) ────────────────────────────
import type { ReactNode } from "react";
import { Topbar } from "./Topbar";
import { Sidebar } from "./Sidebar";

interface LayoutProps { children: ReactNode }

export function Layout({ children }: LayoutProps) {
  return (
    // The admin shell uses v6 CSS variables directly — the 11 inner pages
    // still carry their own cyberpunk Tailwind classes, and that's fine.
    // They will be migrated progressively; the shell provides the frame.
    <div style={{
      height: '100vh',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      background: 'var(--v6-bg)',
      color: 'var(--v6-fg)',
      fontFamily: 'var(--v6-font-sans)',
    }}>
      <Topbar />
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Sidebar />
        <main style={{
          flex: 1,
          overflowY: 'auto',
          padding: '28px 32px',
          scrollbarWidth: 'thin',
        }}>
          {children}
        </main>
      </div>
    </div>
  );
}
