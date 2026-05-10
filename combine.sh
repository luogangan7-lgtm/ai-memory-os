#!/bin/bash
echo "Combine AI Memory OS parts..."
cat AI-Memory-OS-1.0.0-arm64.dmg.part_* > AI-Memory-OS-1.0.0-arm64.dmg
cat AI-Memory-OS-1.0.0-x64.dmg.part_* > AI-Memory-OS-1.0.0-x64.dmg
echo "Done! You can now open the .dmg files."
chmod +x AI-Memory-OS-1.0.0-arm64.dmg AI-Memory-OS-1.0.0-x64.dmg
