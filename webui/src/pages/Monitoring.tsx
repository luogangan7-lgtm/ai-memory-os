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
    x: { ticks: { color: "#4A6080", font: { size: 10 } }, grid: { color: "rgba(0,229,255,0.05)" } },
    y: { ticks: { color: "#4A6080", font: { size: 10 } }, grid: { color: "rgba(0,229,255,0.05)" }, beginAtZero: true },
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
      .catch(() => setErr("加载监控数据失败"));
  }, []);

  const tokenVals = d?.token_values || [];
  const writeVals = d?.writes_values || [];
  const totalTokens = tokenVals.reduce((a, b) => a + b, 0);
  const totalWrites = writeVals.reduce((a, b) => a + b, 0);
  const tenants: TopTenant[] = d?.top_tenants || [];
  const latencyBuckets = d?.latency_buckets || [];

  return (
    <div>
      <div className="page-title">遥测监控</div>
      <div className="page-sub">Token usage · 写入吞吐 · Top tenants</div>

      {err && (
        <div className="card" style={{ borderColor: "var(--red, #f87171)", color: "#f87171" }}>
          {err}
        </div>
      )}

      <div className="stats-grid">
        <div className="stat-card amber">
          <div className="stat-label">12h Token 用量</div>
          <div className="stat-value">{totalTokens.toLocaleString()}</div>
          <div className="stat-sub">最近 12 小时聚合</div>
        </div>
        <div className="stat-card teal">
          <div className="stat-label">12h 记忆写入</div>
          <div className="stat-value">{totalWrites.toLocaleString()}</div>
          <div className="stat-sub">memories 表新增</div>
        </div>
        <div className="stat-card violet">
          <div className="stat-label">活跃租户</div>
          <div className="stat-value">{tenants.length.toLocaleString()}</div>
          <div className="stat-sub">Top 10 内统计</div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18, marginBottom: 22 }}>
        <div className="card" style={{ marginBottom: 0 }}>
          <div className="card-head">
            <div className="card-title">
              <div className="card-icon ci-amber">⚡</div>
              Token 用量趋势
            </div>
          </div>
          <div className="chart-wrap">
            <Line options={chartOpts} data={lineData(d?.token_labels || [], tokenVals, "rgb(245,158,11)")} />
          </div>
        </div>
        <div className="card" style={{ marginBottom: 0 }}>
          <div className="card-head">
            <div className="card-title">
              <div className="card-icon ci-teal">📈</div>
              写入吞吐
            </div>
          </div>
          <div className="chart-wrap">
            <Line options={chartOpts} data={lineData(d?.writes_labels || [], writeVals, "rgb(0,229,255)")} />
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <div className="card-title">
            <div className="card-icon ci-violet">🏆</div>
            Top Tenants
          </div>
        </div>
        {tenants.length === 0 ? (
          <div style={{ padding: "20px 8px", color: "var(--muted, #4A6080)", fontSize: 13 }}>
            暂无租户数据
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>租户</th>
                <th style={{ textAlign: "right" }}>记忆数</th>
                <th style={{ textAlign: "right" }}>Token 用量</th>
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
        <div className="card">
          <div className="card-head">
            <div className="card-title">
              <div className="card-icon ci-emerald">⏱️</div>
              延迟分布 (ms)
            </div>
          </div>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
            {latencyBuckets.map((v, i) => (
              <div key={i} className="stat-card emerald" style={{ minWidth: 120 }}>
                <div className="stat-label">P{[50, 75, 95, 99][i] ?? i}</div>
                <div className="stat-value">{v}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
