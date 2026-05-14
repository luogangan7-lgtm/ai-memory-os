import { test, expect } from "@playwright/test";

test.describe("Command Deck — Smoke Tests", () => {
  test("app renders without crashing", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("canvas")).toBeVisible({ timeout: 10000 });
  });

  test("displays AI 记忆体 title", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("text=AI 记忆体")).toBeVisible();
  });

  test("Three.js canvas has valid WebGL context", async ({ page }) => {
    await page.goto("/");
    const hasWebGL = await page.evaluate(() => {
      const canvas = document.querySelector("canvas");
      if (!canvas) return false;
      const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
      return gl !== null;
    });
    expect(hasWebGL).toBe(true);
  });

  test("page is responsive on mobile viewport", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/");
    await expect(page.locator("canvas")).toBeVisible();
    await expect(page.locator("text=AI 记忆体")).toBeVisible();
  });
});
