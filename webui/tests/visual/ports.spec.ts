import { test, expect } from '@playwright/test';

const ports = [8003, 5173];

for (const port of ports) {
  test(`[Port ${port}] User App page loads and renders root`, async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('pageerror', exception => {
      consoleErrors.push(exception.message);
    });
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto(`http://127.0.0.1:${port}/app/`);
    await page.waitForTimeout(3000);
    
    const root = page.locator('#root');
    await expect(root).toBeVisible();
    const innerHTML = await root.innerHTML();
    expect(innerHTML.length).toBeGreaterThan(0);
    
    // Ensure no critical JavaScript exceptions
    expect(consoleErrors).toEqual([]);
  });

  test(`[Port ${port}] Admin UI page loads and renders root`, async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('pageerror', exception => {
      consoleErrors.push(exception.message);
    });
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto(`http://127.0.0.1:${port}/manage/`);
    await page.waitForTimeout(3000);
    
    const root = page.locator('#root');
    await expect(root).toBeVisible();
    const innerHTML = await root.innerHTML();
    expect(innerHTML.length).toBeGreaterThan(0);

    // Ensure no critical JavaScript exceptions
    expect(consoleErrors).toEqual([]);
  });
}
