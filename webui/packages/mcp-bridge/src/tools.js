export const TOOLS = [
  { name:'memory_search', description:'从 AI Memory OS 知识库中语义检索相关记忆。在开始回答用户问题之前，应优先调用此工具获取背景知识。', inputSchema:{ type:'object', properties:{ query:{ type:'string',description:'检索关键词或语义描述' }, limit:{ type:'integer',default:5 }, filter_type:{ type:'string',default:'all' } }, required:['query'] } },
  { name:'memory_store', description:'将重要信息、结论、用户偏好、代码片段存入 AI Memory OS。对话中获得重要信息时应主动调用。', inputSchema:{ type:'object', properties:{ content:{ type:'string',description:'要存储的内容，支持 Markdown' }, title:{ type:'string',description:'记忆标题，不超过80字' }, tags:{ type:'array',items:{ type:'string' } }, importance:{ type:'string',enum:['low','normal','high','critical'],default:'normal' } }, required:['content','title'] } },
  { name:'memory_list', description:'列出最近存入的记忆。', inputSchema:{ type:'object', properties:{ limit:{ type:'integer',default:10 }, offset:{ type:'integer',default:0 } } } },
  { name:'memory_delete', description:'删除指定 ID 的记忆。', inputSchema:{ type:'object', properties:{ memory_id:{ type:'string',description:'记忆 ID' } }, required:['memory_id'] } },
  { name:'memory_status', description:'查询知识库统计：总记忆数、最后更新时间。', inputSchema:{ type:'object', properties:{} } },
];

function fmtSearch(d) {
  const r = d?.results || d?.memories || [];
  if (!r.length) return 'No memories found.';
  return r.map((m, i) => `[${i+1}] ${m.title}\n${m.content?.substring(0,500)}\nID: ${m.id||m.memory_id}${m.score?` [${(m.score*100).toFixed(0)}%]`:''}`).join('\n\n---\n\n');
}
function fmtStore(d) { return `Stored. ID: ${d?.id||d?.memory_id||'N/A'}`; }
function fmtList(d) { const m = d?.memories||[]; return m.length ? m.map((x,i) => `[${i+1}] ${x.title} | ID:${x.id}`).join('\n') : 'Empty.'; }
function fmtStatus(d) { return `Total: ${d?.total_memories||0} | Docs: ${d?.total_documents||0} | Updated: ${d?.last_updated||'N/A'}`; }

export async function executeTool(name, args, client) {
  try {
    switch (name) {
      case 'memory_search': return { content: [{ type:'text', text: fmtSearch(await client.search(args)) }] };
      case 'memory_store': return { content: [{ type:'text', text: fmtStore(await client.store(args)) }] };
      case 'memory_list': return { content: [{ type:'text', text: fmtList(await client.list(args)) }] };
      case 'memory_delete': await client.delete(args); return { content: [{ type:'text', text: `Deleted ${args.memory_id}` }] };
      case 'memory_status': return { content: [{ type:'text', text: fmtStatus(await client.status()) }] };
      default: throw new Error(`Unknown tool: ${name}`);
    }
  } catch (err) { return { content: [{ type:'text', text: `Error: ${err.message}` }], isError: true }; }
}
