# AI Memory OS - Ollama Local Model Wizard
from __future__ import annotations
import subprocess, platform, os, sys

def detect_ollama() -> dict:
    try:
        r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        models = []
        for line in r.stdout.strip().split(chr(10))[1:]:
            parts = line.split()
            if parts: models.append(parts[0])
        return {"installed": True, "models": models}
    except: return {"installed": False, "models": [], "install_hint": install_hint()}

def install_hint() -> str:
    p = platform.system()
    if p == "Darwin": return "brew install ollama"
    if p == "Linux": return "curl -fsSL https://ollama.com/install.sh | sh"
    if p == "Windows": return "Download from https://ollama.com/download/windows"
    return "See https://ollama.com"

RECOMMENDED_MODELS = {
    "embedding": [
        {"name": "nomic-embed-text", "size": "274MB", "dim": 768, "reason": "Lightweight, good quality"},
        {"name": "bge-m3", "size": "2.2GB", "dim": 1024, "reason": "Best multilingual embedding"},
        {"name": "mxbai-embed-large", "size": "670MB", "dim": 1024, "reason": "Large, high quality English"},
    ],
    "rerank": [
        {"name": "qwen3:0.6b", "size": "456MB", "reason": "Tiny, fast, use as reranker"},
    ],
    "chat": [
        {"name": "qwen3:8b", "size": "5.2GB", "reason": "Balanced quality/speed"},
        {"name": "llama3.2:3b", "size": "2.0GB", "reason": "Lightweight general purpose"},
    ],
}

def pull_model(model_name: str):
    subprocess.run(["ollama", "pull", model_name], check=True)
