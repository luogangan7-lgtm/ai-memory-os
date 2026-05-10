#!/usr/bin/env python3
"""AI Memory OS — Launcher (Cross-Platform)"""
import os, sys, platform, subprocess, time, webbrowser

BASE = os.path.dirname(os.path.abspath(__file__))
NT = os.name == "nt"
OK, WARN, ERR, DIM, BOLD, RST = ('',)*6

def step(msg): print(f"  {msg}")

def ok(msg): print(f"  [OK] {msg}")

def fail(msg, exit_code=1):
    print(f"  [FAIL] {msg}")
    if exit_code: sys.exit(exit_code)

def main():
    print("=" * 50)
    print("  AI Memory OS — Launcher")
    print("=" * 50)
    print(f"  Platform: {platform.system()} {platform.release()}")
    print()
    # 1. Docker
    step("Checking Docker...")
    try:
        subprocess.run(["docker","info"],capture_output=True,timeout=10,check=True)
        ok("Docker ready")
    except: fail("Docker not found — install from https://docker.com")
    # 2. Services
    step("Starting services (Qdrant, PostgreSQL, Neo4j, MinIO, Redis)...")

    mode = os.environ.get("MEMORY_OS_MODE", "dev")


    if "--daemon" in sys.argv:
        start_daemon()
        return

    if "--quick" in sys.argv or os.environ.get("MEMORY_OS_MODE") == "quick":
        quick_start()
        return

    if not check_docker():
        print("  Docker not found.")
        print("  Option 1: Install Docker and retry.")
        print("  Option 2: Run 'python deploy.py --quick' for zero-dependency mode.")
        sys.exit(1)

    if mode == "prod":
        print("  Production mode: using docker-compose.prod.yml")
        compose_cmd = ["docker", "compose", "-f", "docker-compose.yml", "-f", "docker-compose.prod.yml", "up", "-d"]
    else:
        compose_cmd = ["docker", "compose", "up", "-d"]

    r = subprocess.run(compose_cmd, cwd=BASE, capture_output=True, text=True)
    if r.returncode != 0:
        if "already" in r.stderr: ok("Services already running")
        else: fail(f"docker compose failed:\n{r.stderr}")
    else: ok("Services started")
    # 3. Wait
    step("Waiting for PostgreSQL..."); time.sleep(4); ok("Ready")
    # 4. Venv
    step("Setting up Python environment...")
    if not os.path.exists(os.path.join(BASE, ".venv")):
        subprocess.run([sys.executable,"-m","venv",".venv"], cwd=BASE, check=True)
    pip = os.path.join(BASE, ".venv", "Scripts" if NT else "bin", "pip")
    subprocess.run([pip,"install","-q","-r","backend/requirements.txt"], cwd=BASE)
    ok("Dependencies ready")
    # 5. Start API
    step("Starting API server on http://localhost:8000")
    python = os.path.join(BASE, ".venv", "Scripts" if NT else "bin", "python")
    env = os.environ.copy()
    env["PYTHONPATH"] = "backend"
    if platform.system() != "Darwin": env["MEMORY_OS_BM25"] = "1"
    proc = subprocess.Popen(
        [python, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=BASE, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(3)
    ok("API server running (PID {})".format(proc.pid))
    # 6. Browser
    step("Opening admin panel...")
    url = "http://localhost:8000/admin/ui/"
    webbrowser.open(url)
    print()
    print("=" * 50)
    print("  AI Memory OS is running!")
    print()
    print("  Admin UI:   " + url)
    print("  API:        http://localhost:8000")
    print("  Neo4j:      http://localhost:7474 (neo4j/password)")
    print("  MinIO:      http://localhost:9001 (admin/password)")
    print()
    print("  Press Ctrl+C to stop")
    print("=" * 50)
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        proc.terminate()
        subprocess.run(["docker","compose","down"], cwd=BASE, capture_output=True)
        print("Stopped.")


# Also: standalone mode
def quick_start():
    """Docker-free mode - runs standalone server with in-memory storage."""
    import subprocess, webbrowser
    venv_python = os.path.join(BASE, ".venv", "bin" if os.name != "nt" else "Scripts", "python")
    if not os.path.exists(venv_python):
        subprocess.run([sys.executable, "-m", "venv", ".venv"], cwd=BASE, check=True)
        subprocess.run([os.path.join(BASE, ".venv", "bin", "pip"), "install", "-q", "fastapi", "uvicorn", "pydantic", "pydantic-settings", "httpx", "python-jose", "python-multipart", "numpy", "scikit-learn"], cwd=BASE, check=True)
    
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(BASE, "backend")
    proc = subprocess.Popen([venv_python, os.path.join(BASE, "standalone_server.py")], cwd=BASE, env=env)
    time.sleep(3)
    url = "http://localhost:8080/app/"
    webbrowser.open(url)
    print(f"Quick mode: {url}")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        proc.terminate()

# Daemon mode: run server in background

def check_docker():
    """Check if Docker is installed and running."""
    try:
        subprocess.run(["docker","info"], capture_output=True, timeout=10, check=True)
        return True
    except: return False

def get_ip():
    """Get the local network IP."""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except: return "localhost"

def start_daemon():
    """Start server as background daemon on Linux/macOS."""
    if NT:
        print("Windows: use deploy.bat or run in a terminal")
        return
    
    import subprocess
    venv_python = os.path.join(BASE, ".venv", "bin", "python")
    
    # Start full server
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.join(BASE, "backend")
    
    log = open(os.path.join(BASE, "server.log"), "a")
    proc = subprocess.Popen(
        [venv_python, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=BASE, env=env, stdout=log, stderr=log,
        start_new_session=True
    )
    
    with open(os.path.join(BASE, "server.pid"), "w") as f:
        f.write(str(proc.pid))
    
    print(f"Server started (PID: {proc.pid})")
    print(f"Logs: {os.path.join(BASE, 'server.log')}")
    print(f"Stop: kill {proc.pid}")

if __name__ == "__main__":
    main()
