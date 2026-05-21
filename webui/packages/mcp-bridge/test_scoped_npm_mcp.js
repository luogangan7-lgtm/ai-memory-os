import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const apiKey = "mos_placeholder_admin_key";

async function main() {
    console.log("Starting MCP connection via npm package @ai-memory-os/mcp...");
    const transport = new StdioClientTransport({
        command: "npx",
        args: ["--yes", "@ai-memory-os/mcp@latest", "--token", apiKey, "--server", "http://127.0.0.1:8003"],
        env: process.env
    });

    const client = new Client(
        { name: "npm-test-client", version: "1.0.0" },
        { capabilities: {} }
    );

    try {
        await client.connect(transport);
        console.log("✅ MCP Client connected successfully!");

        const tools = await client.listTools();
        console.log(`✅ Retrieved ${tools.tools.length} tools`);
        for (const tool of tools.tools) {
            console.log(`  - ${tool.name}`);
        }
        
        console.log("\n✅ Connectivity test completed successfully.");
    } catch (e) {
        console.error("❌ Test failed:", e);
    } finally {
        process.exit(0);
    }
}

main().catch(console.error);
