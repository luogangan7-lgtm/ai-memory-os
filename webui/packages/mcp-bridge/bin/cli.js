#!/usr/bin/env node
import { parseArgs } from 'node:util';
import { startMcpServer } from '../src/index.js';

const { values } = parseArgs({
  options: {
    token:  { type: 'string', short: 't' },
    server: { type: 'string', short: 's', default: 'http://localhost:8003' },
    help:   { type: 'boolean', short: 'h', default: false },
  },
  strict: false,
});

if (values.help || !values.token) {
  console.error(`
AI Memory OS MCP Server
用法: npx @ai-memory-os/mcp --token=<TOKEN> [--server=<URL>]
参数:
  --token, -t   必填。Memory OS API Token
  --server, -s  可选。服务器地址，默认 http://localhost:8003
  --help, -h    显示帮助
环境变量: MOS_TOKEN, MOS_SERVER
`);
  process.exit(values.help ? 0 : 1);
}

const token  = values.token  || process.env.MOS_TOKEN;
const server = values.server || process.env.MOS_SERVER || 'http://localhost:8003';
startMcpServer({ token, server });
