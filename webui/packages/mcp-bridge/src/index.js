import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { MemoryOSClient } from './client.js';
import { TOOLS, executeTool } from './tools.js';

export async function startMcpServer({ token, server }) {
  const client = new MemoryOSClient({ token, server });
  try { const s = await client.status(); process.stderr.write(`[Memory OS] Connected to ${server} | ${s.total_memories||0} memories\n`); }
  catch (e) { process.stderr.write(`[Memory OS] Warning: ${e.message}\n`); }

  const mcp = new Server({ name:'ai-memory-os', version:'1.0.0' }, { capabilities: { tools: {} } });
  mcp.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: TOOLS }));
  mcp.setRequestHandler(CallToolRequestSchema, async (req) => {
    const { name, arguments: args } = req.params;
    process.stderr.write(`[Memory OS] ${name}(${JSON.stringify(args)})\n`);
    return executeTool(name, args || {}, client);
  });
  const transport = new StdioServerTransport();
  await mcp.connect(transport);
  process.stderr.write('[Memory OS] MCP Server ready (stdio)\n');
}
