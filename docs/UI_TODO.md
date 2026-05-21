# Cortex UI 待完成任务清单

> 本文档供 AI Agent (Codex + DeepSeek) 独立执行。
> **必须先阅读**：
> - [docs/UI_DESIGN_SYSTEM.md](./UI_DESIGN_SYSTEM.md) — 设计规范
> - [docs/AGENT_RULES.md](./AGENT_RULES.md) — 强制守则，声明完成前必须满足验收标准
> - [docs/KNOWN_ISSUES.md](./KNOWN_ISSUES.md) — 当前已知缺陷

**每个任务完成后必须提供**：改动文件列表 + 验收命令输出 + 已知限制声明。  
"Build 成功"不等于"功能完成"。

---

## 当前状态总结

**用户端 `/app/`**：已完成 v6 重构  
**管理端 `/manage/`**：外壳（Topbar/Sidebar/Layout）已 v6，11 个页面**内容仍是旧 cyberpunk 风格**  
**Landing/Auth**：已完成  
**品牌**：Cortex，CortexMark logo，暗色默认，双语（中文主标 + English）

---

## 任务优先级

### P0 — 影响真实用户体验（先做）

#### T1：管理端 11 页内容迁移（最大工作量）

**文件路径**：`webui/src/pages/`  
**涉及文件**：Dashboard.tsx, Monitoring.tsx, AuditLogs.tsx, Providers.tsx, Tenants.tsx, Users.tsx, Memories.tsx, Reflection.tsx, Graph.tsx, Config.tsx

**迁移规则**（每个页面都要做）：
1. 用 `v6-card` 替代 `.card`
2. 用 `v6-table` 替代 `.table`
3. 用 `v6-btn` 替代 `.btn`
4. 用 `v6-metric-tile` 替代 `.stat-card`（4-up 数据 tile）
5. 用 `v6-section-label` 替代 section 分隔标题
6. 用 CSS variables（`var(--v6-fg)` 等）替代旧 `var(--teal)` / `var(--text)` / `var(--muted)`
7. 去掉所有 emoji 标题（用文字），改双语格式（中文主标 + English hint）
8. 去掉 `box-shadow: 0 0 20px rgba(0,240,212,.4)` 类光晕样式

**优先顺序**：Dashboard → Memories → Tenants → Providers → 其他

**T1 验收标准（每个页面都要验证）**：
```bash
# 1. 访问对应页面
# 2. 检查：没有 teal/violet glow，没有 backdrop-filter blur
# 3. 检查：数据来自真实 API（Network tab 可见 XHR 请求）
# 4. 检查：表格行删除/操作功能正常（能点击，API 有响应）
# 5. 检查：响应式不溢出（缩小浏览器到 800px）
```
**禁止**：把真实数据换成 hardcoded 数组来"让页面看起来有内容"。

**Dashboard.tsx 特殊要求**：
- 4 个 stat card 改用 `.v6-metric-tile`，带 3D hover（参考 OverviewPanel 的 `onPointerMove` handleTilt 实现）
- 图表组件（如果有）暂时保留或用空 placeholder 替代
- 顶部 title 改双语："控制台 Dashboard"

**Memories.tsx 特殊要求**：
- 与用户端 MemoryPanel 类似，但展示所有租户的记忆
- 用 `.v6-table` + 分页（admin 看到的记忆更多）
- 筛选器用 `.v6-chips`

---

#### T2：Landing Hero Spline 3D 嵌入

**⚠️ 前置条件**：需要用户提供 Spline 场景 URL。没有 URL 时**不要用假 canvas 或 placeholder div 声称已实现**。

**文件**：`webui/src/pages/UserApp.tsx` → `LoginOverlay` → Landing 模式

**要求**：
- 在 Hero 区域（`.v6-hero`）加一个 Spline 3D 装饰
- 使用 `@splinetool/runtime`（需要 `npm install @splinetool/runtime`）
- Spline 场景 URL 由用户提供（目前用占位）
- 如果没有 URL，用 CSS 伪 3D 动效（已有 grain + ambient glow，可以加一个浮动几何体）
- 位置：Hero 标题右侧或背景层，不遮挡文字

**代码参考**：
```tsx
import { Application } from '@splinetool/runtime';
// 在 useEffect 里初始化 canvas
```

**T2 验收标准**：
```bash
# 只有拿到 Spline URL 后才能验收
# 验收方式：浏览器打开 /app/，Hero 区域有 3D 场景渲染（不是黑色空白）
# 检查：页面加载时间 < 5 秒（Spline 不能严重拖慢 LCP）
# 检查：Spline canvas 不遮挡"Get started"等操作按钮
# 如果没有 URL，实现 CSS-only 动效代替，明确标注"Spline 待接入"
```

---

### P1 — 完善体验（次优先）

#### T3：管理端 Providers.tsx 深度重构

**当前状态**：用旧 cyberpunk 风格展示 24 个 provider 的配置  
**目标**：与用户端 MyLLMPanel 类似的 provider 卡片网格  
**要求**：
- provider 卡片网格（`.v6-provider-grid`）
- 每张卡显示：provider 名、region 标签、模型数、signup URL
- 点击卡片展开 model 列表（`.v6-model-row`）
- free badge（`.v6-freebadge`）标注免费模型
- 双语：所有 label 中英混合

**复用**：`webui/src/data/models.ts` 的 `PROVIDERS` 数据（已包含 `signupUrl`、`free` 字段）

**T3 验收标准**：
```bash
# 访问 /manage/ → 导航到 "模型配置 Providers"
# 1. provider 卡片网格正常显示（至少 10 张卡）
# 2. 点击某张卡 → model 列表展开，显示真实 model 数据（来自 models.ts）
# 3. FREE badge 正确显示在免费模型上（如 GLM-4-Flash, Groq Llama-4）
# 4. "Get key ↗" 链接跳转到正确的 provider 网站
# 禁止：用空卡片 placeholder 凑数
```

---

#### T4：主题切换按钮

**文件**：`webui/src/components/Topbar.tsx`（管理端）和 `webui/src/pages/UserApp.tsx` → Dashboard → v6-app__nav（用户端）

**要求**：
- 顶栏右侧加一个 sun/moon 图标按钮
- 点击在 `<html>` 上切换 `data-theme="dark"` / `data-theme="light"`
- 默认暗色（已是 :root 默认值）
- CSS 已在 index.css 里定义了 `:root[data-theme="light"]`

**代码**：
```tsx
const toggleTheme = () => {
  const html = document.documentElement;
  const current = html.getAttribute('data-theme');
  html.setAttribute('data-theme', current === 'light' ? 'dark' : 'light');
};
```

**T4 验收标准**：
```bash
# 1. 顶栏有 sun/moon 图标按钮
# 2. 点击 → 背景从 #08080B 变为 #FCFCFD（或反向）
# 3. 再点击 → 变回来
# 4. 刷新页面后恢复暗色默认（除非 localStorage 保存了偏好）
# 注意：不是用 CSS class 切换，而是 data-theme 属性驱动 CSS variables
```

---

#### T5：Memory Panel 深度重构（master-detail drawer）

**文件**：`webui/src/pages/UserApp.tsx` → `MemoryPanel`

**当前状态**：Memories/Files 二级 subtab，紧凑列表行，3 行 clamp 内容  
**目标改动**：
1. 点击任意 memory 行 → 右侧打开 **Detail Drawer**
2. Drawer 内容：完整 content（不 clamp）+ chunks 数量 + related memories + [Copy ID] [Delete] 操作
3. Drawer 可以是侧滑面板（从右边 40% 宽度）
4. 键盘支持：j/k 导航，Esc 关 drawer

**CSS 需要新增**：
```css
.v6-drawer {
  position: fixed;
  top: 0; right: 0;
  width: 42%;
  height: 100%;
  background: var(--v6-bg-elev);
  border-left: 1px solid var(--v6-border);
  z-index: 50;
  overflow-y: auto;
  padding: 24px;
  transform: translateX(100%);
  transition: transform 0.25s var(--v6-ease);
}
.v6-drawer--open { transform: translateX(0); }
```

**Backend API 依赖**（必须验证以下 API 真实可用，不能假设已实现）：

```bash
# 先验证这两个 API 是否存在并返回真实数据
curl -H "Authorization: Bearer <user_token>" http://127.0.0.1:8003/memory/<real_memory_id>
# 期望：{"id":"...","title":"...","content":"完整内容（不截断）","source_type":"..."}

curl -H "Authorization: Bearer <user_token>" http://127.0.0.1:8003/memory/<real_memory_id>/chunks
# 如果返回 404 → 需要新增这个 endpoint
# 期望：[{"chunk_index":0,"content":"...","token_count":128,"qdrant_point_id":"..."}]
```

**T5 验收标准**：
```bash
# 1. 点击记忆列表任意一行 → 右侧滑出 drawer（宽度约 40%）
# 2. drawer 内显示：完整 content（不 clamp）+ chunks 列表 + [Copy ID] [Delete]
# 3. 按 Esc 键关闭 drawer
# 4. 点 Delete → 确认后 API 调用 DELETE /memory/{id}，列表刷新，drawer 关闭
# 5. 刷新页面后 drawer 不再显示（状态不持久化到 URL）
# 禁止：drawer 里显示 "chunks: (loading...)" 永不加载，或显示假数据
```

---

#### T6：Canvas Panel 动态更新

**文件**：`webui/src/pages/UserApp.tsx` → `CanvasPanel`

**当前状态**：手动刷新，static mermaid 渲染  
**目标**：
1. 5s polling 自动刷新（与 OverviewPanel 的 setInterval 机制一致）
2. completed_steps / next_steps 在 mermaid 图下面拆出来作 **checklist** 展示
3. Mermaid 图只作 overview 用，checklist 才是用户真正能交互的

**⚠️ 注意**：这是 Issue-05 的修复，见 KNOWN_ISSUES.md  

**T6 验收标准**：
```bash
# 准备：先让 Agent 调用 memory_task_canvas_update 写入一些内容

# 1. 打开 Canvas tab，记录当前 completed_steps 和 next_steps 数量
# 2. 通过 MCP 让 Agent 再调用一次 canvas_update，加一个 next step
# 3. 不手动刷新页面，等待 5-10 秒
# 4. Canvas 内容自动更新 → 动态刷新实现成功

# 5. 检查 checklist：completed_steps 显示为带删除线的绿色条目
# 6. 检查 checklist：next_steps 显示为待完成条目（○ 符号）
# 7. 验证数据来自 DB：
docker exec ai-memory-os-postgres-1 psql -U memoryos -d memory_os \
  -c "SELECT agent_id, completed_steps, next_steps FROM task_canvas WHERE team_id='<your_team_id>';"
# 确认 DB 里的 JSON 数据和页面显示一致
```

**代码参考（checklist 渲染）**：
```tsx
const currentCanvas = canvases.find(c => c.agent_id === activeAgent);
const completed: string[] = JSON.parse(currentCanvas?.completed_steps || '[]');
const nextSteps: string[] = JSON.parse(currentCanvas?.next_steps || '[]');

// 渲染：
<div className="v6-canvas-checklist">
  {completed.map((s, i) => <div key={i} className="v6-canvas-step done">✓ {s}</div>)}
  {nextSteps.map((s, i) => <div key={i} className="v6-canvas-step todo">○ {s}</div>)}
</div>
```

**CSS 需要新增**：
```css
.v6-canvas-step { padding: 6px 0; font-size: 12.5px; font-family: var(--v6-font-mono); }
.v6-canvas-step.done { color: #2DBFA8; text-decoration: line-through; opacity: 0.7; }
.v6-canvas-step.todo { color: var(--v6-fg); }
```

---

### P2 — 文档和收尾

#### T7：README.md / README_CN.md 品牌同步

**要求**：
- 标题改为 `# Cortex — Long-term Memory OS for AI Agents`
- 副标题加 `formerly AI Memory OS`
- 关键 URL 保持不变（GitHub repo 名 ai-memory-os 不变）
- 所有正文里的 "AI Memory OS" 改为 "Cortex"，除非是技术文档

---

#### T8：ConnectPanel System Prompts 完善

**文件**：`webui/src/pages/UserApp.tsx` → `ConnectPanel` → `SYSTEM_PROMPTS`

**当前状态**：3 种提示词（standard/concise/dev），主要是工具调用列表  
**目标**：
- 加 **场景驱动**内容（不只是"调用 memory_xxx"）
- 每种提示词加入具体场景示例：
  - standard: "用户提问技术问题时 → 先 memory_search，再回答"
  - dev: "发现重要代码约定 → memory_store(tags: ['约定'])"
- 语气更像"给 AI 的行为指南"，不是"API 文档"

---

#### T9：管理端登录页也用 Cortex brand

**当前状态**：访问 `/manage/` 未登录时也显示 `LoginOverlay`（来自 UserApp.tsx），但是 `isUserApp = false` 分支，直接显示登录框，没有 landing

**目标**：
- Admin 登录框改用 Cortex Topbar 品牌（CortexMark + Cortex + 管理后台 Admin）
- 登录框样式继续用 v6-authcard
- 不需要 Landing 页（管理员知道要做什么）

---

## 构建流程

每次修改后执行：
```bash
cd /Volumes/data/ai-memory-os/webui
npm run build
rsync -av --delete dist/ ../webui-dist/
```

后端改动（routes.py 等）需要：
```bash
docker compose up -d --build backend
```

---

## CSS 组件参考

所有 v6 组件在：
- `webui/src/css/login-v2.css` — Landing/Auth 组件
- `webui/src/css/app-v2.css` — Dashboard/Panel 组件

已有组件（直接使用，不要重复定义）：
- `.v6-card` / `.v6-card__head` / `.v6-card__title` / `.v6-card__title-hint`
- `.v6-btn` / `.v6-btn--primary` / `.v6-btn--ghost` / `.v6-btn--danger` / `.v6-btn--xs`
- `.v6-table` (th/td with v6 token colors)
- `.v6-list` / `.v6-list__item` / `.v6-list__item-{head,main,title,meta,body,aside}`
- `.v6-tag` (inline mono badge)
- `.v6-freebadge` (teal FREE 标识)
- `.v6-pricebadge` (neutral 价格标识)
- `.v6-chips` / `.v6-chip` (filter pill row)
- `.v6-metric-grid` / `.v6-metric-tile` (3D hover tiles)
- `.v6-health-list` / `.v6-health-item` (status rows)
- `.v6-section-label` / `.v6-section-label__count`
- `.v6-subtabs` / `.v6-subtab` (segmented control)
- `.v6-toolbar` / `.v6-input-global`
- `.v6-statusbar` / `.v6-statusbar--ok` / `.v6-statusbar--err`
- `.v6-empty` (empty state)
- `.v6-onboarding` / `.v6-onboarding__step` (onboarding checklist)
- `.v6-provider-grid` / `.v6-provider-card` (provider picker)
- `.v6-model-row` / `.v6-freebadge` / `.v6-pricebadge` (model list)
- `.v6-byok` (BYOK banner)
- `.v6-metric-tile__value--done` (teal 数字)

---

## 双语规范（必须遵守）

| 位置 | 格式 | 示例 |
|---|---|---|
| Card 主标题 | `中文名称 English` + hint `中英辅助` | `系统概览 Overview` hint: `每5秒刷新` |
| Section label | `中文名 · English` | `系统健康 · Health` |
| Tab bar | `中文 English` | `概览 Overview` |
| Metric label | `中文 English` | `总记忆 Memories` |
| 按钮 | `中文 English` | `保存 Save` `刷新 Refresh` |
| 状态消息 | `中文 English` | `已保存 Saved` `连接成功 Connected` |
| 技术词 | 保留英文 | `LLM  MCP  API  Pipeline  Backend  Agent` |

---

## 注意事项

1. **不要改 `webui/src/data/models.ts` 里的 provider.id / model.id / baseUrl**，管理端保存的配置依赖这些值
2. **不要改 `webui/src/css/layout.css` 里的 .card / .btn 等旧 class**，11 个管理端页面还在用
3. **每个 build 后必须 rsync 到 webui-dist**，backend 通过 volume mount 服务静态文件
4. **所有新 CSS 加到 `app-v2.css`**，不要散落在 inline style 里
5. **管理端 11 页迁移时**，先只改 class names 和颜色变量，不改功能逻辑
