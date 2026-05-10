#!/usr/bin/env python3
"""
AI Memory OS — Launch Script
- Always uses port 8003 (kills any existing process on that port)
- Auto-opens the admin UI in the default browser
- Logs all server output to backend/app.log for remote debugging
"""
import os, sys, signal, socket, time, subprocess, re
from pathlib import Path

BASE = Path(__file__).parent
PID_FILE = BASE / ".server.pid"
PORT_FILE = BASE / ".server.port"
PORT = 8003


def kill_port(port: int) -> None:
    """Kill any process currently listening on the given port."""
    try:
        # lsof works on macOS and Linux
        result = subprocess.check_output(
            ["lsof", "-ti", f":{port}"], text=True
        ).strip()
        if result:
            pids = result.splitlines()
            for pid in pids:
                try:
                    os.kill(int(pid), signal.SIGTERM)
                    print(f"[启动] 已终止占用 {port} 端口的进程 (PID: {pid})")
                except (ProcessLookupError, ValueError):
                    pass
            time.sleep(1)  # Give it time to die
    except subprocess.CalledProcessError:
        pass  # No process on that port, good


def kill_existing() -> None:
    """Kill the previously tracked server process."""
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            os.kill(pid, signal.SIGTERM)
            time.sleep(1)
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        except (ValueError, OSError):
            pass
        PID_FILE.unlink(missing_ok=True)


def get_lan_ip() -> str:
    """Get the LAN IP address, skipping VPN/proxy IPs."""
    ip = "localhost"
    try:
        import netifaces
        for iface in ["en0", "en1", "eth0", "wlan0"]:
            addrs = netifaces.ifaddresses(iface).get(netifaces.AF_INET, [])
            if addrs:
                ip = addrs[0]["addr"]
                break
    except Exception:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            # Skip VPN/proxy fake IPs (e.g. 198.18.x.x)
            if ip.startswith("198.18."):
                try:
                    res = subprocess.check_output(["ifconfig"], text=True)
                    m = re.search(r"inet (192\.168\.\d+\.\d+)", res)
                    if m:
                        ip = m.group(1)
                    else:
                        ip = "localhost"
                except Exception:
                    ip = "localhost"
        except Exception:
            pass
    return ip


def open_browser(url: str) -> None:
    """Open the given URL in the default browser after a short delay."""
    import threading
    def _open():
        time.sleep(2)  # Wait for server to be ready
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", url])
            elif sys.platform.startswith("linux"):
                subprocess.Popen(["xdg-open", url])
            elif sys.platform == "win32":
                subprocess.Popen(["start", url], shell=True)
        except Exception:
            pass
    threading.Thread(target=_open, daemon=True).start()


def main():
    # Step 1: Kill any leftover tracked process
    kill_existing()

    # Step 2: Kill whatever is on port 8003 (ensures we always use this port)
    kill_port(PORT)

    # Step 3: Prepare environment
    py = str(BASE / ".venv" / "bin" / "python3")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BASE)

    # Step 4: Start server, logging to backend/app.log
    log_path = BASE / "backend" / "app.log"
    log_f = open(log_path, "a", buffering=1)  # Line-buffered for real-time logs
    proc = subprocess.Popen(
        [py, "-m", "uvicorn", "backend.main:app",
         "--host", "0.0.0.0", "--port", str(PORT),
         "--log-level", "info"],
        cwd=str(BASE), env=env,
        stdout=log_f, stderr=log_f
    )
    PID_FILE.write_text(str(proc.pid))

    # Step 5: Detect LAN IP
    lan_ip = get_lan_ip()
    manage_url = f"http://localhost:{PORT}/manage/"
    app_url = f"http://{lan_ip}:{PORT}/app/"

    print(f"\n{'='*50}")
    print(f"  AI Memory OS 已启动")
    print(f"{'='*50}")
    print(f"  管理端 (本机):   {manage_url}")
    print(f"  用户端 (局域网): {app_url}")
    print(f"  PID: {proc.pid} | 停止: kill {proc.pid}")
    print(f"  日志: {log_path}")
    print(f"{'='*50}\n")

    # Step 6: Auto-open admin UI in browser
    open_browser(manage_url)

    # Step 7: Wait
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\n[停止] 正在关闭服务器...")
        proc.terminate()
        PID_FILE.unlink(missing_ok=True)
        print("[停止] 已关闭。")


if __name__ == "__main__":
    main()
