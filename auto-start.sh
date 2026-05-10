#!/bin/bash
# AI Memory OS — Auto-start after reboot
# Run this once: ./auto-start.sh install
# Then server auto-starts on every boot

DIR="$(cd "$(dirname "$0")" && pwd)"

install_linux() {
    cat > /tmp/memory-os.service << EOF
[Unit]
Description=AI Memory OS
After=docker.service network.target
Wants=docker.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$DIR
ExecStart=$DIR/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
Environment=PYTHONPATH=$DIR/backend
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    sudo mv /tmp/memory-os.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable memory-os
    sudo systemctl start memory-os
    echo "Installed. Server will auto-start on boot."
}

install_mac() {
    cat > ~/Library/LaunchAgents/com.memoryos.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.memoryos</string>
    <key>ProgramArguments</key>
    <array>
        <string>$DIR/.venv/bin/python</string>
        <string>-m</string><string>uvicorn</string>
        <string>main:app</string>
        <string>--host</string><string>0.0.0.0</string>
        <string>--port</string><string>8000</string>
    </array>
    <key>WorkingDirectory</key><string>$DIR</string>
    <key>EnvironmentVariables</key>
    <dict><key>PYTHONPATH</key><string>$DIR/backend</string></dict>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
</dict></plist>
EOF
    launchctl load ~/Library/LaunchAgents/com.memoryos.plist
    echo "Installed. Server will auto-start on login."
}

case "${1:-install}" in
    install)
        case "$(uname -s)" in
            Linux) install_linux ;;
            Darwin) install_mac ;;
            *) echo "Unsupported OS. Use 'python deploy.py --daemon' manually." ;;
        esac
        ;;
    uninstall)
        sudo systemctl disable memory-os 2>/dev/null
        launchctl unload ~/Library/LaunchAgents/com.memoryos.plist 2>/dev/null
        echo "Removed."
        ;;
    *)
        echo "Usage: ./auto-start.sh [install|uninstall]"
        ;;
esac
