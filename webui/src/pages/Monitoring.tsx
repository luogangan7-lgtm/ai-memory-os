import { useEffect, useState } from "react";
import { Chart, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Filler, Tooltip } from "chart.js";
import { Line } from "react-chartjs-2";
import { getMonitoring } from "../api/endpoints";
import type { MonitoringData, TopTenant } from "../api/types";

Chart.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Filler, Tooltip);

const chartOpts = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    x: { ticks: { color: "var(--v6-fg-muted)", font: { size: 10 } }, grid: { color: "rgba(45,191,168,0.05)" } },
    y: { ticks: { color: "var(--v6-fg-muted)", font: { size: 10 } }, grid: { color: "rgba(45,191,168,0.05)" }, beginAtZero: true },
  },
};

function lineData(labels: string[], values: number[], color: string) {
  return {
    labels,
    datasets: [
      {
        data: values,
        borderColor: color,
        backgroundColor: color.replace(")", ",0.08)").replace("rgb", "rgba"),
        tension: 0.4,
        fill: true,
        pointRadius: 3,
        pointBackgroundColor: color,
      },
    ],
  };
}

export function MonitoringPage() {
  const [d, setD] = useState<MonitoringData | null>(null);
  const [err, setErr] = useState<string>("");

  useEffect(() => {
    getMonitoring()
      .then(setD)
      .catch(() => setErr("加载监控数据失败 Failed to load monitoring data"));
  }, []);

  const tokenVals = d?.token_values || [];
  const writeVals = d?.writes_values || [];
  const totalTokens = tokenVals.reduce((a, b) => a + b, 0);
  const totalWrites = writeVals.reduce((a, b) => a + b, 0);
  const tenants: TopTenant[] = d?.top_tenants || [];
  const latencyBuckets = d?.latency_buckets || [];

  const handleTilt = (e: React.PointerEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    const r = el.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width - 0.5;
    const y = (e.clientY - r.top) / r.height - 0.5;
    el.style.transform = `perspective(700px) rotateX(${y * -6}deg) rotateY(${x * 6}deg) translateY(-4px)`;
  };
  const resetTilt = (e: React.PointerEvent<HTMLDivElement>) => {
    e.currentTarget.style.transform = '';
  };

  return (
    <div>
      <h1 style={{font:"600 22px var(--v6-font-sans)",color:"var(--v6-fg)",marginBottom:4}}>遥测监控 Telemetry</h1>
      <div style={{color:"var(--v6-fg-muted)",fontSize:13,marginBottom:24}}>系统性能指标与用量分析 · System performance metrics and usage analytics</div>

      {err && (
        <div className="v6-statusbar v6-statusbar--err" style={{ marginBottom: 20 }}>
          {err}
        </div>
      )}

      <div className="v6-metric-grid" style={{ marginBottom: 22 }}>
        <div className="v6-metric-tile" onPointerMove={handleTilt} onPointerLeave={resetTilt}>
          <div className="v6-metric-tile__label">12h Token 用量 Token Usage</div>
          <div className="v6-metric-tile__value">{totalTokens.toLocaleString()}</div>
          <div className="v6-metric-tile__sub">最近 12 小时聚合 Last 12h aggregate</div>
        </div>
        <div className="v6-metric-tile" onPointerMove={handleTilt} onPointerLeave={resetTilt}>
          <div className="v6-metric-tile__label">12h 记忆写入 Memory Writes</div>
          <div className="v6-metric-tile__value">{totalWrites.toLocaleString()}</div>
          <div className="v6-metric-tile__sub">新增记忆数 New memories</div>
        </div>
        <div className="v6-metric-tile" onPointerMove={handleTilt} onPointerLeave={resetTilt}>
          <div className="v6-metric-tile__label">活跃租户 Active Tenants</div>
          <div className="v6-metric-tile__value">{tenants.length.toLocaleString()}</div>
          <div className="v6-metric-tile__sub">Top 10 内统计 Top 10 statistics</div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18, marginBottom: 22 }}>
        <div className="v6-card" style={{ marginBottom: 0 }}>
          <div className="v6-card__head">
            <div className="v6-card__title">
              Token 用量趋势 Token Usage Trend
            </div>
          </div>
          <div className="chart-wrap" style={{ height: 260 }}>
            <Line options={chartOpts} data={lineData(d?.token_labels || [], tokenVals, "#E5A23B")} />
          </div>
        </div>
        <div className="v6-card" style={{ marginBottom: 0 }}>
          <div className="v6-card__head">
            <div className="v6-card__title">
              写入吞吐 Write Throughput
            </div>
          </div>
          <div className="chart-wrap" style={{ height: 260 }}>
            <Line options={chartOpts} data={lineData(d?.writes_labels || [], writeVals, "#2DBFA8")} />
          </div>
        </div>
      </div>

      <div className="v6-card" style={{ marginBottom: 22 }}>
        <div className="v6-card__head">
          <div className="v6-card__title">
            Top 租户 Top Tenants
          </div>
        </div>
        {tenants.length === 0 ? (
          <div className="v6-empty">
            暂无租户数据 · No tenant data yet
          </div>
        ) : (
          <table className="v6-table">
            <thead>
              <tr>
                <th>租户 Tenant</th>
                <th style={{ textAlign: "right" }}>记忆数 Memories</th>
                <th style={{ textAlign: "right" }}>Token 用量 Token Usage</th>
              </tr>
            </thead>
            <tbody>
              {tenants.map((t) => (
                <tr key={t.team_id}>
                  <td>{t.team_id}</td>
                  <td style={{ textAlign: "right" }}>{t.memory_count.toLocaleString()}</td>
                  <td style={{ textAlign: "right" }}>{t.token_usage.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {latencyBuckets.length > 0 && (
        <div className="v6-card">
          <div className="v6-card__head">
            <div className="v6-card__title">
              延迟分布 Latency Distribution (ms)
            </div>
          </div>
          <div className="v6-metric-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))' }}>
            {latencyBuckets.map((v, i) => (
              <div key={i} className="v6-metric-tile" onPointerMove={handleTilt} onPointerLeave={resetTilt}>
                <div className="v6-metric-tile__label">P{[50, 75, 95, 99][i] ?? i}</div>
                <div className="v6-metric-tile__value">{v}</div>
                <div className="v6-metric-tile__sub">毫秒 ms</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
