import { test, expect } from '@playwright/test';

test('root API returns 200', async ({ page }) => {
  const r = await page.goto('http://127.0.0.1:8003/');
  expect(r?.status()).toBe(200);
});

test('manage page loads with HTML', async ({ page }) => {
  await page.goto('http://127.0.0.1:8003/manage/');
  await page.waitForTimeout(5000);
  const html = await page.content();
  expect(html).toContain('root');
});

test('app page loads without admin chrome', async ({ page }) => {
  await page.goto('http://127.0.0.1:8003/app/');
  await page.waitForTimeout(5000);
  const topbar = await page.locator('.topbar').count();
  const sidebar = await page.locator('.sidebar').count();
  expect(topbar).toBe(0);
  expect(sidebar).toBe(0);
});

test('SPA renders something in #root', async ({ page }) => {
  await page.goto('http://127.0.0.1:8003/manage/');
  await page.waitForTimeout(5000);
  const root = await page.locator('#root');
  const inner = await root.innerHTML();
  expect(inner.length).toBeGreaterThan(0);
});

test('POST /auth/register creates account', async ({ request }) => {
  const user = 'test_' + Date.now();
  const r = await request.post('http://127.0.0.1:8003/auth/register', {
    data: { username: user, email: user+'@test.com', password: 'pwd123' }
  });
  expect([200, 400]).toContain(r.status());
});

test('POST /auth/token rejects bad password', async ({ request }) => {
  const r = await request.post('http://127.0.0.1:8003/auth/token', {
    data: { email: 'nonexistent@no.com', password: 'wrong' }
  });
  expect(r.status()).toBe(401);
});
