#!/usr/bin/env python3
"""Example: Connect your agent to AI Memory OS.
1. Set your API key and server URL below
2. Run: python example.py
"""

# ── CONFIGURATION ──
SERVER_URL = "http://localhost:8000"     # Change to your server IP
API_KEY = "mos_your_api_key_here"        # Get this from the web UI

# ── USAGE ──
from memory_os_sdk import MemoryOSClient

client = MemoryOSClient(url=SERVER_URL, api_key=API_KEY)

# Store a memory
client.store("Getting Started", "Memory OS helps agents remember knowledge across conversations.")

# Search memories
for result in client.search("getting started guide"):
    print(f"  Score: {result.score:.3f} | {result.memory.title}")
    print(f"  Content: {result.memory.content[:100]}...")
    print()

print("Done! Your agent can now store and retrieve knowledge.")
