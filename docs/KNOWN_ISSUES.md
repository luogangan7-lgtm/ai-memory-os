# 当前已知功能缺陷 / 未真正实现的功能

> **重要**：这份文档记录的是**现在就存在**的问题，不是 UI 样式问题，是**功能没有实际工作**的问题。
> AI Agent 在开发时**不得声称已修复**这里列出的问题，除非提供下方每条的验证步骤证明。

---

## 🔴 P0 — 功能完全未实现

### Issue-01：Connect Panel 复制按钮有时无效

**现象**：非 HTTPS 环境下 `navigator.clipboard.writeText` 静默失败，用户点了没反应  
**当前代码**：已加 `document.execCommand('copy')` fallback（`webui/src/pages/UserApp.tsx` ConnectPanel `copy()` 函数）  
**验证方法**：
```bash
# 1. 在普通 HTTP 访问（非 localhost）
# 2. 点击 "MCP Token 凭证" 旁的 "复制 Copy" 按钮
# 3. 检查按钮是否变成 "已复制 ✓"
# 4. 打开记事本粘贴，确认内容是 token 字符串
```
**注意**：`已复制 ✓` 显示只说明代码执行了，不代表真的复制到剪贴板。必须用粘贴测试。

---

### Issue-02：MyLLM "测试连接 Test" 只是 ping，不是真实调用

**现象**：测试按钮调用 `/api/user/llm/test`，这个 endpoint 只检查 API key 格式是否像 key，并不真正发一个 LLM 请求  
**期望行为**：真正发一个 "Hello" 消息给 LLM，显示响应时间和返回片段  
**当前 backend**：`/api/user/llm/test` 在 `backend/api/user_providers.py`，只做格式校验  
**验证方法**：
```bash
# 填入一个**错误**的 API key（如 sk-wrong123）
# 点 "测试连接 Test"
# 如果显示 "连接成功 Connected ✓" — 说明测试是假的（只校验格式）
# 正确行为应该是：返回 "连接失败 Failed: 401 Unauthorized" 或类似错误
```
**修复要求**：backend `/api/user/llm/test` 必须真正发一个 `POST /chat/completions` 请求，返回实际 LLM 响应或错误信息。

---

### Issue-03：UsagePanel token 数据可能永远是 0

**现象**：LLM 页面底部的 "用量与计费 Usage & Billing" 对很多用户显示 "暂无使用记录"  
**根因**：`user_token_usage` 表只在走 Cortex `/v1/chat/completions` 代理时才写入。直接配置 API key 后 MCP Agent 的调用**不经过代理**，token 不被记录。  
**影响范围**：绝大多数 MCP 接入用户（通过 cursor/claude desktop 等调用 provider API），token 都不会被记录  
**验证方法**：
```bash
# 1. 配置 LLM，通过 MCP 让 agent 执行一些操作（memory_search 等）
# 2. 查看 LLM 页面 Usage 区块
# 3. 如果仍然是 "暂无使用记录" —— token 没有被记录，Issue 存在
```
**这个问题是架构层面的**，需要评估是否要添加 LLM proxy 必经层来记录 token。短期修复：在 MCP handler 里估算 token 并写入记录。

---

### Issue-04：Overview 仪表盘 Pipeline 数据依赖 in-flight 状态

**现象**：Pipeline 状态（5 个 tile）显示的是当前队列状态，但不是 24h 内的历史统计  
**当前 API**：`/api/user/llm/pipeline/status` 返回的 `counts` 是当前队列里的计数，不是历史  
**期望行为**：显示过去 24h 内：done 了多少个、failed 了多少个  
**验证方法**：
```bash
# 1. 几分钟后刷新仪表盘
# 2. 如果 "管线完成 Done" 数字等于当前队列里的 done 数（可能很小）而不是 24h 累计 —— Issue 存在
# 正确行为：应该是累计增长的数字，不会因为 pipeline 清队列而归零
```
**修复要求**：`/api/user/llm/pipeline/status` 加 24h 统计字段，或新加 `/api/user/pipeline/stats` endpoint。

---

## 🟡 P1 — 功能部分实现（表面可用，但有严重缺失）

### Issue-05：Canvas Panel 只能手动刷新

**现象**：`任务画布 Canvas` 需要手动点 "刷新 Refresh" 才更新  
**期望行为**：Agent 写入 canvas 后，用户不用刷新就能看到  
**验证方法**：
```bash
# 1. 打开 Canvas tab，记录当前内容
# 2. 让 Agent 调用 memory_task_canvas_update 更新画布
# 3. 等待 10 秒，不手动刷新
# 4. 如果内容没变化 —— 动态更新未实现
```

---

### Issue-06：Health 检查只检查 HTTP 200，不检查数据库

**现象**：Overview 仪表盘 "系统健康 Health" 显示 "Backend 服务正常"，但只检查 `/health` 返回 200  
**潜在问题**：Postgres / Qdrant / Neo4j 连接断开时，`/health` 可能仍返回 200  
**验证方法**：
```bash
# 检查 backend 的 /health endpoint 是否真的测试 DB 连接
curl http://127.0.0.1:8003/health
# 如果只返回 {"status": "ok"} 而没有数据库连接状态 —— 是假的 health check
# 正确行为：应该包含 postgres_ok, qdrant_ok, neo4j_ok 等字段
```

---

### Issue-07：Overview "活跃 Agent" 统计可能不准

**现象**：Overview 的 "活跃 Agents" 数字来自 `memories.agent_id` 过去 7 天的 DISTINCT 值  
**问题**：`agent_id` 是 MCP 调用时传入的，格式不一（有时是 "cursor", 有时是 UUID），同一个 Cursor 用户可能被统计为多个 Agent  
**验证方法**：
```bash
# 查看 active_agents 数组里的值
curl -H "Authorization: Bearer <token>" http://127.0.0.1:8003/stats
# 如果出现类似 ["4f67a93a-6810-41dc-...", "cursor", "default"] 这样的混乱值 —— Issue 存在
```

---

## 🟢 已修复（但需要保持）

- ✅ Connect Panel 复制按钮加了 execCommand fallback
- ✅ UsagePanel 过滤了 0 token 的行，显示 empty state
- ✅ backend `/user/stats` 移除了假数据 fallback
- ✅ Canvas mermaid 主题改为 v6 颜色
- ✅ `/health` 和 `/api/health` 在 SPA fallback 之前注册（不再被 index.html 拦截）

---

## 对 AI Agent 的强制要求

在修复上述 Issue 时，**必须提供以下证明之一**，否则声明"已修复"无效：

1. **curl 命令输出**：能看到真实返回数据（不是 `{}` 或 `{"status":"ok"}`）
2. **浏览器 Network tab 截图**：能看到实际 API 响应
3. **数据库查询**：`docker exec postgres psql -c "SELECT ..."` 能看到写入的真实数据

**禁止的证明方式**：
- ❌ "我已经修改了代码，功能应该正常工作"
- ❌ "Build 成功，没有错误" （Build 成功 ≠ 功能正常）
- ❌ "UI 显示正常了"（UI 可以假，数据库不会骗人）
