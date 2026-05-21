import sys
sys.path.append("/Volumes/data/ai-memory-os")
import asyncio
from backend.manager.registry import ModelRegistry

async def main():
    reg = ModelRegistry.get_instance()
    engine_data = reg.load_llm_engine_config()
    print("=== LLM Engine configuration ===")
    for k, v in engine_data.items():
        print(f"  {k}: {v}")
        
    print("\n=== Provider configs ===")
    for name, prov in reg.configs.items():
        print(f"  Provider: {name}")
        print(f"    API Base: {prov.api_base}")
        print(f"    API Key (first 5 chars): {prov.api_key[:5] if prov.api_key else 'None'}")
        print(f"    Models: {prov.enabled_models}")

if __name__ == "__main__":
    asyncio.run(main())
