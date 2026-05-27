import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const apiKey = "mos_lm_322cb707fb2c72868f830c5dccee8e2e";
const serverUrl = "https://luolimo.pics";

async function main() {
    console.log("Starting local MCP bridge test...");
    console.log(`Connecting to remote Memory OS via bridge at: ${serverUrl}`);
    
    // Launch node locally, passing the absolute path to the bridge CLI
    const transport = new StdioClientTransport({
        command: "node",
        args: ["bin/cli.js", "--token", apiKey, "--server", serverUrl],
        env: process.env
    });

    const client = new Client(
        { name: "test-client", version: "1.0.0" },
        { capabilities: {} }
    );

    try {
        await client.connect(transport);
        console.log("✅ Local MCP Bridge connected to server successfully!");

        console.log("\nTesting tool call (memory_feedback)...");
        const fbRes = await client.callTool({
            name: "memory_feedback",
            arguments: {
                skill_id: "3f87fb8e-dbe6-4bf4-9e86-bb09d9844253",
                outcome: "success",
                context: "Auto-test verification of schema"
            }
        });
        console.log("\n✅ Tool call (memory_feedback) response:", JSON.stringify(fbRes, null, 2));

    } catch (e) {
        console.error("❌ Test failed:", e);
    } finally {
        process.exit(0);
    }
}

main().catch(console.error);
