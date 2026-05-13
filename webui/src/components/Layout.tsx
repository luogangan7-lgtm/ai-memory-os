// ── Layout (Topbar + Sidebar + Page Container) ────────────────────────
import type { ReactNode } from "react";
import { NeuralBackground } from "./NeuralBackground";
import { Topbar } from "./Topbar";

import { Sidebar } from "./Sidebar";

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="layout-root">
      <NeuralBackground />
      <Topbar />
      <div className="layout-body">
        <Sidebar />
        <main className="layout-main">{children}</main>
      </div>
    </div>
  );
}
