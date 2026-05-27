import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { MemoryOSClient } from './client.js';

export async function startMcpServer({ token, server }) {
  const client = new MemoryOSClient({ token, server });
  try {
    process.stderr.write(`[Memory OS] Connecting to ${server}...\n`);
    await client.connect();
    process.stderr.write(`[Memory OS] Connected to SSE server at ${server}\n`);
  } catch (e) {
    process.stderr.write(`[Memory OS] Connection Failed: ${e.message}\n`);
    process.exit(1);
  }

  const mcp = new Server(
    { name: 'ai-memory-os', version: '1.0.0' },
    { capabilities: { tools: {} } }
  );

  mcp.setRequestHandler(ListToolsRequestSchema, async () => {
    try {
      return await client.sendRequest('tools/list');
    } catch (err) {
      process.stderr.write(`[Memory OS] listTools error: ${err.message}\n`);
      throw err;
    }
  });

  mcp.setRequestHandler(CallToolRequestSchema, async (req) => {
    const { name, arguments: args } = req.params;
    process.stderr.write(`[Memory OS] calling tool: ${name}(${JSON.stringify(args || {})})\n`);
    try {
      return await client.sendRequest('tools/call', { name, arguments: args });
    } catch (err) {
      process.stderr.write(`[Memory OS] callTool error: ${err.message}\n`);
      throw err;
    }
  });

  const transport = new StdioServerTransport();
  await mcp.connect(transport);
  process.stderr.write('[Memory OS] MCP Server ready (stdio)\n');
}
