#!/bin/bash
# Install Memory Daemon for your agent
echo "Installing Memory Daemon..."
pip install httpx memory-os-sdk

echo ""
echo "Done! Usage:"
echo ""
echo "  # Set your server and key:"
echo "  export MEMORY_OS_URL=http://192.168.1.100:8000"
echo "  export MEMORY_OS_KEY=mos_your_key_here"
echo "  export MEMORY_OS_AGENT=my-agent-name"
echo ""
echo "  # Pipe your agent through it:"
echo "  ./memory_daemon.py"
echo ""
echo "  # Or: agent | memory_daemon.py"
