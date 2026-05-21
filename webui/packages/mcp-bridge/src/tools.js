export const TOOLS = [
  { name:'memory_search', description:'从 AI Memory OS 知识库中语义检索相关记忆。在开始回答用户问题之前，应优先调用此工具获取背景知识。', inputSchema:{ type:'object', properties:{ query:{ type:'string',description:'检索关键词或语义描述' }, limit:{ type:'integer',default:5 }, filter_type:{ type:'string',default:'all' } }, required:['query'] } },
  { name:'memory_store', description:'将重要信息、结论、用户偏好、代码片段存入 AI Memory OS。对话中获得重要信息时应主动调用。', inputSchema:{ type:'object', properties:{ content:{ type:'string',description:'要存储的内容，支持 Markdown' }, title:{ type:'string',description:'记忆标题，不超过80字' }, tags:{ type:'array',items:{ type:'string' } }, importance:{ type:'string',enum:['low','normal','high','critical'],default:'normal' } }, required:['content','title'] } },
  { name:'memory_list', description:'列出最近存入的记忆。', inputSchema:{ type:'object', properties:{ limit:{ type:'integer',default:10 }, offset:{ type:'integer',default:0 } } } },
  { name:'memory_delete', description:'删除指定 ID 的记忆。', inputSchema:{ type:'object', properties:{ memory_id:{ type:'string',description:'记忆 ID' } }, required:['memory_id'] } },
  { name:'memory_status', description:'查询知识库统计：总记忆数、最后更新时间。', inputSchema:{ type:'object', properties:{} } },
  { name:'memory_reflect', description:'手动触发后台认知优化：自动晋升、衰减、去重、记忆整合。', inputSchema:{ type:'object', properties:{} } },
  { name:'memory_get_persona', description:'获取 Persona 配置信息', inputSchema:{ type:'object', properties:{} } },
  { name:'memory_task_canvas_get', description:'获取 Task Canvas 的 Mermaid 图', inputSchema:{ type:'object', properties:{ task_id:{ type:'string', default:'main' }, agent_id:{ type:'string', description:'Agent 标识' } }, required:['agent_id'] } },
  { name:'memory_task_canvas_update', description:'更新 Task Canvas 的 Mermaid 图与进度', inputSchema:{ type:'object', properties:{ task_id:{ type:'string' }, agent_id:{ type:'string', description:'Agent 标识' }, mermaid:{ type:'string' }, title:{ type:'string' }, completed:{ type:'array', items:{ type:'string' } }, next:{ type:'array', items:{ type:'string' } } }, required:['task_id', 'agent_id', 'mermaid'] } },
];

function fmtSearch(d) {
  const r = Array.isArray(d) ? d : (d?.results || d?.memories || []);
  if (!r.length) return 'No memories found.';
  return r.map((item, i) => {
    const m = item.memory || item;
    const score = item.score !== undefined ? item.score : m.score;
    return `[${i+1}] ${m.title || 'Untitled'}\n${(m.content || item.chunk_text || '').substring(0,500)}\nID: ${m.id || item.id || m.memory_id || 'N/A'}${score ? ` [${(score*100).toFixed(0)}%]` : ''}`;
  }).join('\n\n---\n\n');
}
function fmtStore(d) { return `Stored. ID: ${d?.id||d?.memory_id||'N/A'}`; }
function fmtList(d) { const m = Array.isArray(d) ? d : (d?.memories||[]); return m.length ? m.map((x,i) => `[${i+1}] ${x.title||'Untitled'} | ID:${x.id}`).join('\n') : 'Empty.'; }
function fmtStatus(d) { return `Total: ${d?.total_memories||0} | Docs: ${d?.total_documents||0} | Updated: ${d?.last_updated||'N/A'}`; }
function fmtPersona(d) { return d?.persona_md || '用户画像尚未生成，请继续与 AI 对话以积累更多记忆。'; }
function fmtCanvas(d) { return d?.canvas_mermaid ? `Canvas: ${d.canvas_mermaid}` : 'No canvas found.'; }

export async function executeTool(name, args, client) {
  try {
    switch (name) {
      case 'memory_search': return { content: [{ type:'text', text: fmtSearch(await client.search(args)) }] };
      case 'memory_store': return { content: [{ type:'text', text: fmtStore(await client.store(args)) }] };
      case 'memory_list': return { content: [{ type:'text', text: fmtList(await client.list(args)) }] };
      case 'memory_delete': await client.delete(args); return { content: [{ type:'text', text: `Deleted ${args.memory_id}` }] };
      case 'memory_status': return { content: [{ type:'text', text: fmtStatus(await client.status()) }] };
      case 'memory_reflect': await client.reflect(); return { content: [{ type:'text', text: '后台认知优化已触发：自动晋升、衰减、去重任务已启动。' }] };
      case 'memory_get_persona': return { content: [{ type:'text', text: fmtPersona(await client.getPersona()) }] };
      case 'memory_task_canvas_get': return { content: [{ type:'text', text: fmtCanvas(await client.getCanvas(args)) }] };
      case 'memory_task_canvas_update': await client.updateCanvas(args); return { content: [{ type:'text', text: 'Canvas updated' }] };
      default: throw new Error(`Unknown tool: ${name}`);
    }
  } catch (err) { return { content: [{ type:'text', text: `Error: ${err.message}` }], isError: true }; }
}
