# Cortex Design System v6

> 本文档描述 Cortex UI 的设计系统规范，供开发者和 AI Agent 参考。

---

## 设计原则

- **Linear matte 磨砂**：深色底 + grain 噪点，无 glow/glassmorphism
- **单色系**：没有彩色 accent，只有 teal 用于语义高亮（管线完成、FREE badge）
- **中英双语**：中文主标，English 辅助技术标识
- **暗色默认**：`#08080B` 背景，亮色 opt-in via `data-theme="light"`

---

## Design Tokens（CSS Variables）

定义在 `webui/src/index.css` → `:root { ... }` 块

### 颜色（暗色默认）

```css
--v6-bg: #08080B           /* 主背景 */
--v6-bg-elev: #101013      /* 卡片背景 */
--v6-bg-sunken: #050507    /* 凹陷/sunken 背景 */
--v6-fg: #ECECF0           /* 主文字 */
--v6-fg-muted: #7A7A82     /* 次文字 */
--v6-fg-faint: #4E4E55     /* 最淡文字 */
--v6-border: #1A1A1F       /* 边框 */
--v6-border-strong: #26262C /* 强调边框 */
--v6-accent: #ECECF0       /* 强调色（等同 fg，单色系）*/
--v6-accent-soft: rgba(236, 236, 240, 0.06)
--v6-danger: #E5484D       /* 危险/错误 */

/* 亮色 opt-in */
/* :root[data-theme="light"] { --v6-bg: #FCFCFD; ... } */
```

### 语义高亮色（非 accent，仅用于特定场景）

```css
/* 仅用于：FREE badge、管线完成数字、connected dot、onboarding done */
#2DBFA8    /* teal */
#E5A23B    /* amber (warning) */
```

### 字体

```css
--v6-font-sans: 'Geist', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif
--v6-font-mono: 'Geist Mono', ui-monospace, monospace
```

Google Fonts 已在 `index.css` @import。

### 间距 / 圆角 / 动效

```css
--v6-radius-sm: 6px
--v6-radius-md: 8px
--v6-radius-lg: 12px
--v6-radius-xl: 16px
--v6-ease: cubic-bezier(0.16, 1, 0.3, 1)
```

---

## 组件规范

### Card（基础容器）

```html
<div class="v6-card">
  <div class="v6-card__head">
    <div class="v6-card__title">
      中文名称 English
      <span class="v6-card__title-hint">辅助信息</span>
    </div>
    <!-- 右侧可放按钮 / subtabs / llmpill 等 -->
  </div>
  <!-- 内容 -->
</div>
```

### Table

```html
<table class="v6-table">
  <thead><tr><th>名称 Name</th><th>时间 Time</th></tr></thead>
  <tbody>
    <tr><td>内容</td><td class="v6-font-mono">2024-01-01</td></tr>
  </tbody>
</table>
```

### Button

```html
<button class="v6-btn">默认 Ghost</button>
<button class="v6-btn v6-btn--primary">主要操作 Primary</button>
<button class="v6-btn v6-btn--ghost">次要 Ghost</button>
<button class="v6-btn v6-btn--danger v6-btn--xs">删除 Delete</button>
```

### Metric Tiles（数字展示）

3D hover 效果需要在 React 里绑定 `onPointerMove` / `onPointerLeave`：

```tsx
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

<div class="v6-metric-grid">
  <div class="v6-metric-tile" onPointerMove={handleTilt} onPointerLeave={resetTilt}>
    <div class="v6-metric-tile__label">指标名 Name</div>
    <div class="v6-metric-tile__value">342</div>
    <div class="v6-metric-tile__sub">辅助信息</div>
  </div>
</div>
```

`--done` 类给数字加 teal 颜色：`class="v6-metric-tile__value v6-metric-tile__value--done"`

### Section Label

```html
<div class="v6-section-label">
  <span>分区名 · Section Name</span>
  <span class="v6-section-label__count">副信息</span>
</div>
```

### Empty State

```html
<div class="v6-empty">暂无数据 · No data yet</div>
```

### Status Bar

```html
<div class="v6-statusbar">加载中 Loading…</div>
<div class="v6-statusbar v6-statusbar--ok">成功 Success</div>
<div class="v6-statusbar v6-statusbar--err">失败 Failed: reason</div>
```

---

## 管理端旧样式映射表

迁移时的对照关系：

| 旧 class | 新 class/方式 |
|---|---|
| `.card` | `.v6-card` |
| `.card-title` | `.v6-card__title`（字符串加英文，双语） |
| `.table` | `.v6-table` |
| `.btn` | `.v6-btn` |
| `.btn-teal` / `.btn-primary` | `.v6-btn--primary` |
| `.btn-ghost` | `.v6-btn--ghost` |
| `.stat-card` | `.v6-metric-tile`（需加 3D pointer handler）|
| `.stat-value` | `.v6-metric-tile__value` |
| `.stat-label` | `.v6-metric-tile__label` |
| `.page-title` | `<h1>` + `font: 600 22px var(--v6-font-sans); color: var(--v6-fg)` |
| `var(--teal)` | `#2DBFA8`（仅语义高亮场景）|
| `var(--text)` | `var(--v6-fg)` |
| `var(--muted)` | `var(--v6-fg-muted)` |
| `var(--border)` | `var(--v6-border)` |
| `var(--void)` | `var(--v6-bg)` |
| `var(--surface)` | `var(--v6-bg-elev)` |
| `box-shadow: 0 0 20px rgba(0,240,212,.4)` | 删除，不用 glow |
| `backdrop-filter: blur(...)` | 删除 |

---

## 品牌元素

### CortexMark

```tsx
import { CortexMark } from '../components/CortexMark';
<CortexMark size={22} breathing />  // breathing=true 激活呼吸动画
```

### 品牌名排版

```html
<!-- 顶栏 brand area -->
<div style="display:flex;align-items:center;gap:12px">
  <CortexMark size={22} breathing />
  <span style="font:600 17px var(--v6-font-sans);color:var(--v6-fg);letter-spacing:-0.02em">
    Cortex
  </span>
</div>
```

---

## 构建命令

```bash
# 前端（每次改完都要做）
cd /Volumes/data/ai-memory-os/webui
npm run build
rsync -av --delete dist/ ../webui-dist/

# 后端（改了 Python 文件才需要）
docker compose up -d --build backend

# 验证
curl http://127.0.0.1:8003/health
```
