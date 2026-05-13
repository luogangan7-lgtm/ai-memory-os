import { test, expect } from '@playwright/test';

const PAGES = [
  { name: 'Dashboard', path: '/', checks: ['COMMAND DECK', 'GLOBAL MEMORIES', 'ACTIVE TENANTS'] },
  { name: 'Monitoring', path: '/monitoring', checks: ['TELEMETRY'] },
  { name: 'AuditLogs', path: '/audit', checks: ['AUDIT TRAIL'] },
  { name: 'Providers', path: '/providers', checks: ['SYSTEM COMPUTE'] },
  { name: 'LLMEngine', path: '/llm-engine', checks: ['LLM ENGINE'] },
  { name: 'Tenants', path: '/tenants', checks: ['TENANT MATRIX'] },
  { name: 'Users', path: '/users', checks: ['USER REGISTRY'] },
  { name: 'Reflection', path: '/reflection', checks: ['KNOWLEDGE SYNTHESIS'] },
  { name: 'Config', path: '/config', checks: ['SYSTEM CONFIG'] },
];

test.describe('AI Memory OS — E2E Smoke Suite', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://127.0.0.1:5173/');
    await page.evaluate(() => {
      localStorage.setItem('admin_token', 'test-token');
      localStorage.setItem('mos_admin_token', 'test-token');
    });
    await page.reload();
    await page.waitForSelector('text=COMMAND DECK', { timeout: 10000 });
  });

  for (const p of PAGES) {
    test(`${p.name} page renders correctly`, async ({ page }) => {
      if (p.path !== '/') await page.goto(`http://127.0.0.1:5173${p.path}`);
      for (const text of p.checks) {
        await expect(page.locator(`text=${text}`).first()).toBeVisible({ timeout: 5000 });
      }
    });
  }

  test('R3F canvas renders with WebGL context', async ({ page }) => {
    await page.goto('http://127.0.0.1:5173/');
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
    await expect(page.locator('text=AI MEMORY OS')).toBeVisible();
    await expect(page.locator('text=ADMIN')).toBeVisible();
  });

  test('Sidebar has all navigation sections', async ({ page }) => {
    await expect(page.locator('text=总览')).toBeVisible();
    await expect(page.locator('text=配置')).toBeVisible();
    await expect(page.locator('text=管理').first()).toBeVisible();
    await expect(page.locator('text=认知调优')).toBeVisible();
  });

  test('responsive on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('http://127.0.0.1:5173/');
    await page.waitForTimeout(1000);
    await expect(page.locator('text=AI MEMORY OS')).toBeVisible();
  });
});
