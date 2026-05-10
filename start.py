#!/usr/bin/env python3
"""AI Memory OS - Zero-Dependency Launcher (SQLite mode)"""
import os, sys, subprocess, webbrowser, time
BASE = os.path.dirname(os.path.abspath(__file__))

print("=" * 50)
print("  AI Memory OS - Quick Start (No Docker)")
print("=" * 50)

# Check Python
print(f"Python: {sys.version.split()[0]}")

# Setup venv
venv = os.path.join(BASE, ".venv")
if not os.path.exists(venv):
    print("Creating virtual environment...")
    subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)

pip = os.path.join(venv, "bin" if os.name != "nt" else "Scripts", "pip")
python = os.path.join(venv, "bin" if os.name != "nt" else "Scripts", "python")

print("Installing dependencies...")
subprocess.run([pip, "install", "-q", "fastapi", "uvicorn", "pydantic", "pydantic-settings", "httpx", "python-jose", "passlib", "python-multipart", "numpy", "scikit-learn", "PyPDF2"], check=True)

# Start server in SQLite-only mode
print("Starting server on http://localhost:8000")
env = os.environ.copy()
env["PYTHONPATH"] = os.path.join(BASE, "backend")
env["MEMORY_OS_STANDALONE"] = "1"

proc = subprocess.Popen([python, "standalone_server.py"], cwd=BASE, env=env)
time.sleep(3)

url = "http://localhost:8000/app/"
print(f"\n  Open: {url}")
webbrowser.open(url)
print("\n  Press Ctrl+C to stop")

try:
    while True: time.sleep(1)
except KeyboardInterrupt:
    proc.terminate()
    print("Stopped.")
