import { useState, useEffect, useCallback } from 'react';
import { getSubscription } from '../api/endpoints';
import type { SubscriptionInfo } from '../api/types';

export function PlanPanel() {
  const [sub, setSub] = useState<SubscriptionInfo | null>(null);

  const load = useCallback(async () => {
    try { const r = await getSubscription(); setSub(r); }
    catch {}
  }, []);
  useEffect(() => { load(); }, [load]);

  const plan = sub?.plan || 'free';
  const callsUsed = sub?.mcp_call_count || 0;
  const limit = sub?.mcp_call_limit ?? 50;
  const pct = plan === 'free' ? Math.min(100, (callsUsed / limit) * 100) : 0;

  return (
    <div>
      <h1 style={{ font: '600 22px var(--v6-font-sans)', color: 'var(--v6-fg)', marginBottom: 4 }}>
        订阅管理 Plan
      </h1>
      <div style={{ color: 'var(--v6-fg-muted)', fontSize: 13, marginBottom: 24 }}>
        升级 Pro 解锁无限 MCP 调用和更多功能
      </div>

      {/* Current plan status */}
      <div className="v6-card" style={{ marginBottom: 20 }}>
        <div className="v6-card__head">
          <div className="v6-card__title">当前套餐</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0' }}>
          <span style={{
            fontSize: 13, fontWeight: 700, padding: '4px 14px', borderRadius: 6,
            background: plan === 'pro' ? 'rgba(16,185,129,.15)' : plan === 'exempt' ? 'rgba(59,130,246,.15)' : 'var(--v6-bg-sunken)',
            color: plan === 'pro' ? '#10b981' : plan === 'exempt' ? '#3b82f6' : 'var(--v6-fg-muted)',
          }}>
            {plan === 'pro' ? 'Pro 专业版' : plan === 'exempt' ? '白名单 Exempt' : '免费体验 Free'}
          </span>
          {plan === 'free' && (
            <span style={{ fontSize: 12, color: 'var(--v6-fg-muted)' }}>
              MCP {callsUsed}/{limit} 次
              {callsUsed >= limit && <span style={{ marginLeft: 6, color: 'var(--v6-danger)', fontWeight: 600 }}>已用尽</span>}
            </span>
          )}
          {plan === 'pro' && sub?.days_remaining != null && (
            <span style={{ fontSize: 12, color: 'var(--v6-teal)' }}>剩余 {sub.days_remaining} 天</span>
          )}
        </div>
        {plan === 'free' && (
          <div style={{ marginTop: 12 }}>
            <div style={{ height: 6, background: 'var(--v6-bg-surface)', borderRadius: 3, overflow: 'hidden' }}>
              <div style={{
                width: pct + '%', height: '100%',
                background: pct >= 80 ? 'var(--v6-danger)' : 'var(--v6-teal)',
                borderRadius: 3, transition: 'width .3s',
              }} />
            </div>
          </div>
        )}
      </div>

      {/* Upgrade — contact admin */}
      {plan !== 'exempt' && plan !== 'pro' && (
        <div className="v6-card" style={{ textAlign: 'center', padding: 28, marginBottom: 20 }}>
          <div style={{ fontSize: 32, marginBottom: 10 }}>💎</div>
          <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--v6-fg)', marginBottom: 4 }}>Pro 专业版</div>
          <div style={{ fontSize: 36, fontWeight: 800, color: 'var(--v6-teal)', marginBottom: 4 }}>¥29</div>
          <div style={{ fontSize: 12, color: 'var(--v6-fg-muted)', marginBottom: 20 }}>RMB · 月付 · 30 天</div>
          <div style={{ padding: '14px 18px', background: 'var(--v6-bg-sunken)', borderRadius: 8, fontSize: 12, lineHeight: 1.8, color: 'var(--v6-fg-muted)', marginBottom: 16 }}>
            需要订阅请联系系统管理员<br />
            📧 <a href="mailto:luolimoa@gmail.com" style={{ color: 'var(--v6-teal)' }}>luolimoa@gmail.com</a><br />
            📞 <a href="tel:16607396444" style={{ color: 'var(--v6-teal)' }}>16607396444</a>
          </div>
        </div>
      )}

      {/* Already Pro or Exempt */}
      {(plan === 'pro' || plan === 'exempt') && (
        <div className="v6-card">
          <div style={{ fontSize: 13, color: 'var(--v6-fg-muted)' }}>
            {plan === 'pro' ? '你已开通 Pro 订阅，享受无限 MCP 调用。' : '白名单用户，无限额度。'}
          </div>
        </div>
      )}
    </div>
  );
}
