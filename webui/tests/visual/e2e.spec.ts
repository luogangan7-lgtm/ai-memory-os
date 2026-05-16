import { test, expect } from '@playwright/test';

const PAGES = [
  { name: 'Dashboard', path: '/', checks: ['控制台', '全局记忆', '活跃租户'] },
  { name: 'Monitoring', path: '/monitoring', checks: ['遥测监控'] },
  { name: 'AuditLogs', path: '/audit', checks: ['审计日志'] },
  { name: 'Providers', path: '/providers', checks: ['模型配置中心'] },
  { name: 'Tenants', path: '/tenants', checks: ['租户管理'] },
  { name: 'Users', path: '/users', checks: ['用户管理'] },
  { name: 'Reflection', path: '/reflection', checks: ['知识整合'] },
  { name: 'Config', path: '/config', checks: ['系统配置'] },
];

test.describe('AI Memory OS — E2E Smoke Suite', () => {
  test.beforeEach(async ({ page }) => { await page.goto('http://127.0.0.1:8003/manage/#/'); await page.waitForTimeout(2000); });
  for(const p of PAGES) {
    test(`${p.name} page renders correctly`, async ({ page }) => {
      if (p.path !== '/') await page.goto(`http://127.0.0.1:8003/manage/#${p.path}`);
      for (const text of p.checks) {
        await expect(page.locator(`text=${text}`).first()).toBeVisible({ timeout: 5000 });
      }
    });
  }

  test('R3F canvas renders with WebGL context', async ({ page }) => {
    await page.goto('http://127.0.0.1:8003/manage/#/');
    await page.waitForTimeout(2000);
    const canvasCount = await page.evaluate(() => document.querySelectorAll('canvas').length);
    expect(canvasCount).toBeGreaterThanOrEqual(1);
    const hasWebGL = await page.evaluate(() => {
      const c = document.querySelector('canvas');
      return !!(c?.getContext('webgl2'));
    });
    expect(hasWebGL).toBe(true);
  });

  test('Topbar shows logo and health indicator', async ({ page }) => {
    await expect(page.locator('.logo-text')).toBeVisible();
    await expect(page.locator('.admin-badge')).toBeVisible();
  });

  test('Sidebar has all navigation sections', async ({ page }) => {
    await expect(page.locator('text=总览')).toBeVisible();
    await expect(page.locator('text=模型配置')).toBeVisible();
    await expect(page.locator('.admin-badge').first()).toBeVisible();
    await expect(page.locator('text=认知调优')).toBeVisible();
  });

  test('responsive on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('http://127.0.0.1:8003/manage/#/');
    await page.waitForTimeout(1000);
    await expect(page.locator('.logo-text')).toBeVisible();
  });
});
