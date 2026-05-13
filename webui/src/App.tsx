import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { ToastProvider } from "./contexts/ToastContext";
import { Layout } from "./components/Layout";
import { DashboardPage } from "./pages/Dashboard";
import { MonitoringPage } from "./pages/Monitoring";
import { AuditLogsPage } from "./pages/AuditLogs";
import { ProvidersPage } from "./pages/Providers";
import { LLMEnginePage } from "./pages/LLMEngine";
import { TenantsPage } from "./pages/Tenants";
import { UsersPage } from "./pages/Users";
import { ReflectionPage } from "./pages/Reflection";
import { ConfigPage } from "./pages/Config";
export default function App(){
return(<BrowserRouter><AuthProvider><ToastProvider><AppShell/></ToastProvider></AuthProvider></BrowserRouter>)}
function AppShell(){
const { isLoading } = useAuth();
if (isLoading) return <div style={{color:'#00E5FF',fontFamily:'Orbitron',display:'flex',alignItems:'center',justifyContent:'center',height:'100vh',background:'#030A15',fontSize:18}}>LOADING COMMAND DECK...</div>;
// Dev mode: skip auth
return(<Layout><Routes>
<Route path="/" element={<DashboardPage/>}/>
<Route path="/monitoring" element={<MonitoringPage/>}/>
<Route path="/audit" element={<AuditLogsPage/>}/>
<Route path="/providers" element={<ProvidersPage/>}/>
<Route path="/llm-engine" element={<LLMEnginePage/>}/>
<Route path="/tenants" element={<TenantsPage/>}/>
<Route path="/users" element={<UsersPage/>}/>
<Route path="/reflection" element={<ReflectionPage/>}/>
<Route path="/config" element={<ConfigPage/>}/>
</Routes></Layout>)}