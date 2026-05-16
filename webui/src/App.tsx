import { HashRouter, Routes, Route } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { ToastProvider } from "./contexts/ToastContext";
import { Layout } from "./components/Layout";
import { DashboardPage } from "./pages/Dashboard";
import { MonitoringPage } from "./pages/Monitoring";
import { AuditLogsPage } from "./pages/AuditLogs";
import { ModelConfigPage } from "./pages/Providers";
import { TenantsPage } from "./pages/Tenants";
import { UsersPage } from "./pages/Users";
import { ReflectionPage } from "./pages/Reflection";
import { LoginOverlay } from './pages/UserApp';
import { GraphPage } from "./pages/Graph";
import { ConfigPage } from "./pages/Config";

function AdminRoutes() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/monitoring" element={<MonitoringPage />} />
        <Route path="/audit" element={<AuditLogsPage />} />
        <Route path="/models" element={<ModelConfigPage />} />
        <Route path="/providers" element={<ModelConfigPage />} />
        <Route path="/tenants" element={<TenantsPage />} />
        <Route path="/users" element={<UsersPage />} />
        <Route path="/reflection" element={<ReflectionPage />} />
        <Route path="/graph" element={<GraphPage />} />
        <Route path="/config" element={<ConfigPage />} />
      </Routes>
    </Layout>
  );
}

function AppShell() {
  const { isLoading } = useAuth();
  if (isLoading) return <div className="loading-screen">LOADING...</div>;
  return (
    <Routes>
      <Route path="/app" element={<LoginOverlay />} />
      <Route path="*" element={<AdminRoutes />} />
    </Routes>
  );
}

export default function App() {
  return (
    <HashRouter>
      <AuthProvider>
        <ToastProvider>
          <AppShell />
        </ToastProvider>
      </AuthProvider>
    </HashRouter>
  );
}
