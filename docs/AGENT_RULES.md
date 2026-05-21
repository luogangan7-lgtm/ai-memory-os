# AI Agent 开发守则

> 本文档对所有 AI Agent（Codex、Claude、Cursor 等）具有**强制约束力**。
> 违反规则的实现将被视为无效，需要重做。

---

## 核心原则：不欺骗

**"功能已实现"的唯一定义**：用户能用、数据真实写入/读取、无 hardcoded 假数据。

**以下情况不算"已实现"**：
- UI 显示了数据，但数据是 `useState([mockData1, mockData2])` 硬编码的
- 函数体里写了 `// TODO: implement` 然后 `return []`
- API 调用用 `setTimeout` 模拟延迟后返回假数据
- Build 成功但页面全是空内容
- `console.log("功能已实现")` 就声称完成

---

## 每个任务完成前的强制 Checklist

### ✅ UI 类任务（改样式）

- [ ] 旧 class 完全替换，没有遗留的 `.card`, `.btn-teal`, `var(--teal)` 等
- [ ] 在**浏览器**访问该页面，截图或描述实际显示效果
- [ ] 没有 JS 报错（`console.error` 为空）
- [ ] 响应式：窗口缩小到 760px 宽度时不溢出

### ✅ API 类任务（改 backend）

- [ ] 提供 `curl` 命令和真实返回结果（不是空 `{}`）
- [ ] 数据真实写入 DB：`docker exec ai-memory-os-postgres-1 psql -U memoryos -d memory_os -c "SELECT ..."` 能看到数据
- [ ] 错误处理：传入错误参数时返回合理的错误信息，不是 500 崩溃

### ✅ 功能集成任务（前后端联调）

- [ ] 从 UI 操作 → 触发 API → DB 写入，全链路验证
- [ ] 刷新页面后数据依然存在（不是只在内存里）
- [ ] 多租户隔离：A 用户的数据 B 用户看不到

---

## 禁止行为

### 禁止-01：硬编码假数据

```typescript
// ❌ 禁止
const [memories, setMemories] = useState([
  { id: '1', title: '示例记忆', content: '这是假数据' },
  { id: '2', title: 'Sample Memory', content: 'This is fake' },
]);

// ✅ 必须从 API 获取
const [memories, setMemories] = useState([]);
useEffect(() => {
  fetch('/memory/recent').then(r => r.json()).then(setMemories);
}, []);
```

### 禁止-02：空函数假装实现

```python
# ❌ 禁止
@router.post("/api/new-feature")
async def new_feature(data: dict):
    # TODO: implement
    return {"status": "ok"}

# ✅ 必须真正实现或明确告知"这个 endpoint 只是骨架，功能待实现"
```

### 禁止-03：修改验证逻辑而不是修复问题

```python
# ❌ 禁止（为了让测试通过而修改测试）
async def test_connection():
    # 把条件改宽，让所有 key 都"通过"
    return {"connected": True}

# ✅ 必须真正发请求给 provider
```

### 禁止-04：只改前端 console.log 说后端已修复

```typescript
// ❌ 禁止
const handleSave = async () => {
  console.log('Saved to database');  // 骗人的
  setSaved(true);
};

// ✅ 必须实际调用 API
const handleSave = async () => {
  const r = await fetch('/api/save', { method: 'POST', body: JSON.stringify(data) });
  if (!r.ok) throw new Error(await r.text());
};
```

### 禁止-05：用 setTimeout 模拟 API 响应

```typescript
// ❌ 禁止
const fetchData = () => {
  setTimeout(() => {
    setData([{ fake: 'data' }]);
  }, 500);
};

// ✅ 必须真实 fetch
```

---

## 声明完成任务的格式要求

每次声明某个任务完成时，**必须提供以下格式的报告**：

```markdown
## 任务 T1：管理端 Dashboard 迁移

**完成状态**：✅ 已完成

**改动文件**：
- webui/src/pages/Dashboard.tsx（class 迁移）
- webui/src/css/app-v2.css（新增 .admin-stat-grid class）

**前端验证**：
- 访问 http://localhost:8003/manage/
- 截图/描述：[具体描述页面显示效果，包括数据来源]

**API 验证**（如有）：
```bash
curl -H "Authorization: Bearer <admin_token>" http://127.0.0.1:8003/stats
# 返回：{"total":342,"new_today":12,"active_agents":["cursor","claude"],...}
```

**已知限制**（如有）：
- [如果有部分功能没实现，在这里明确说明，不要隐瞒]
```

**没有提供以上格式的声明不被接受。**

---

## 功能验收表（由 Owner 核验）

| 任务 | 声明完成 | Owner 验收 | 问题记录 |
|---|---|---|---|
| T1-Dashboard | - | - | - |
| T1-Memories | - | - | - |
| T1-Tenants | - | - | - |
| T1-Providers | - | - | - |
| T2-Spline | - | - | - |
| T3-Admin Providers | - | - | - |
| T4-Theme toggle | - | - | - |
| T5-Memory Drawer | - | - | - |
| T6-Canvas Dynamic | - | - | - |
| Issue-02-LLM Test | - | - | - |
| Issue-03-Token Tracking | - | - | - |
| Issue-04-Pipeline 24h | - | - | - |

---

## 技术红线（绝对不能碰）

1. **不能修改 `webui/src/data/models.ts` 里的 `provider.id` / `model.id` / `baseUrl`**  
   → 已有用户配置会失效

2. **不能删除 `webui/src/css/layout.css` 里的任何 class**  
   → 11 个管理端页面还在用

3. **不能改 webui-dist 里的文件**  
   → 这是 build 产物，必须通过 `npm run build + rsync` 生成

4. **不能在 docker-compose.yml 里改已有的 `service_name:`**  
   → 会破坏正在运行的容器

5. **不能 `git push --force`**  
   → 会破坏历史

6. **不能修改 backend 里的数据库 schema（drop/alter 现有表）**  
   → 生产数据会丢失；如需加字段用 `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
