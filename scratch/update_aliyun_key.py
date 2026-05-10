import json, os
from pathlib import Path

config_path = Path.home() / ".codex" / "memory-os" / "providers.json"
config_path.parent.mkdir(parents=True, exist_ok=True)

if config_path.exists():
    data = json.loads(config_path.read_text())
else:
    data = {}

data["alibaba"] = {
    "provider_type": "alibaba",
    "api_key": "sk-placeholder-aliyun",
    "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "enabled_capabilities": ["llm", "embedding", "rerank"],
    "enabled_models": {
        "llm": "qwen-turbo",
        "embedding": "text-embedding-v3",
        "rerank": "gte-rerank"
    }
}

config_path.write_text(json.dumps(data, indent=2))
print(f"Updated config at {config_path}")
