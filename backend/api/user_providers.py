# AI Memory OS — User-Pay Model Providers API
from fastapi import APIRouter, Depends, HTTPException, status
import httpx
from backend.auth.middleware import get_user_context
from backend.services.config import settings

router = APIRouter(prefix="/user")

PROVIDER_DEFAULTS = {
    "alibaba": {"url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus"},
    "openai": {"url": "https://api.openai.com/v1", "model": "gpt-4o-mini"},
    "deepseek": {"url": "https://api.deepseek.com/v1", "model": "deepseek-chat"},
    "zhipu": {"url": "https://open.bigmodel.cn/api/paas/v4", "model": "glm-4-flash"},
    "moonshot": {"url": "https://api.moonshot.cn/v1", "model": "moonshot-v1-8k"},
    "anthropic": {"url": "https://api.anthropic.com/v1", "model": "claude-3-5-sonnet-latest"},
    "google": {"url": "https://generativetoolkit.googleapis.com", "model": "gemini-1.5-flash"},
    "ollama": {"url": "http://localhost:11434/v1", "model": "llama3"},
    "custom": {"url": "", "model": ""}
}

@router.get("/providers")
async def get_user_providers(ctx: dict = Depends(get_user_context)):
    """Fetch all configured custom model providers for the authenticated team."""
    from backend.api.routes import pg_repo
    if not pg_repo:
        raise HTTPException(status_code=500, detail="Database connection uninitialized")
    
    team_id = ctx["team_id"]
    try:
        configs = await pg_repo.list_user_provider_configs(team_id)
        # Scrub actual API keys for security, returning only placeholders
        scrubbed = []
        for c in configs:
            key_len = len(c["api_key"])
            key_preview = c["api_key"][:4] + "..." + c["api_key"][-4:] if key_len > 8 else "Configured"
            scrubbed.append({
                "provider_name": c["provider_name"],
                "api_base_url": c["api_base_url"],
                "model_name": c["model_name"],
                "is_active": bool(c["is_active"]),
                "key_preview": key_preview,
                "validated_at": c.get("validated_at")
            })
        return {"providers": scrubbed}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query configurations: {str(e)}")

@router.post("/providers")
async def save_user_provider(payload: dict, ctx: dict = Depends(get_user_context)):
    """Save/update a provider config for the team."""
    from backend.api.routes import pg_repo
    if not pg_repo:
        raise HTTPException(status_code=500, detail="Database connection uninitialized")
    
    team_id = ctx["team_id"]
    provider_name = payload.get("provider_name")
    api_key = payload.get("api_key")
    api_base_url = payload.get("api_base_url")
    model_name = payload.get("model_name")
    is_active = payload.get("is_active", False)
    
    if not provider_name or not api_key:
        raise HTTPException(status_code=400, detail="provider_name and api_key are required fields")

    # Reuse existing symmetric-encrypted key if key is flagged as EXISTING/NO_CHANGE
    if api_key in ("EXISTING", "NO_CHANGE"):
        existing_cfg = await pg_repo.get_user_provider_config(team_id, provider_name)
        if existing_cfg:
            api_key = existing_cfg["api_key"]
        else:
            raise HTTPException(status_code=400, detail="Cannot reuse key: No previous configuration exists.")
    
    # Apply default values if not explicitly provided
    if not api_base_url:
        api_base_url = PROVIDER_DEFAULTS.get(provider_name, {}).get("url", "")
    if not model_name:
        model_name = PROVIDER_DEFAULTS.get(provider_name, {}).get("model", "")
        
    try:
        await pg_repo.save_user_provider_config(
            user_id=team_id,
            provider_name=provider_name,
            api_key=api_key,
            api_base_url=api_base_url,
            model_name=model_name,
            is_active=is_active
        )
        return {"status": "success", "message": f"Provider {provider_name} saved successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save configuration: {str(e)}")

@router.post("/providers/{provider_name}/validate")
async def validate_user_provider(provider_name: str, ctx: dict = Depends(get_user_context)):
    """Validate connection handshake and credentials for a provider by executing a dummy LLM completion request."""
    from backend.api.routes import pg_repo
    if not pg_repo:
        raise HTTPException(status_code=500, detail="Database connection uninitialized")
    
    team_id = ctx["team_id"]
    cfg = await pg_repo.get_user_provider_config(team_id, provider_name)
    if not cfg:
        raise HTTPException(status_code=404, detail="Provider configuration not found. Please save first.")
    
    api_key = cfg["api_key"]
    api_base_url = cfg["api_base_url"] or PROVIDER_DEFAULTS.get(provider_name, {}).get("url", "")
    model_name = cfg["model_name"] or PROVIDER_DEFAULTS.get(provider_name, {}).get("model", "")
    
    if not api_base_url:
        raise HTTPException(status_code=400, detail="Validation failed: API Base URL is empty.")
    
    # Perform raw physical ping / validation via OpenAI-compatible endpoint
    endpoint = f"{api_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(endpoint, json=payload, headers=headers)
            if resp.status_code == 200:
                return {"status": "success", "message": "连接验证成功 (Handshake Success!)"}
            else:
                return {
                    "status": "error",
                    "code": resp.status_code,
                    "message": f"验证失败 (HTTP {resp.status_code}): {resp.text[:200]}"
                }
    except Exception as e:
        return {"status": "error", "message": f"物理连接超时或失败: {str(e)}"}


@router.get("/providers/recommend")
async def get_provider_recommendation(ctx: dict = Depends(get_user_context)):
    """Fetch customized model recommendation based on user configurations."""
    from backend.api.routes import pg_repo
    if not pg_repo:
        return {"recommendation": "系统库未完成就绪，请联系管理员。"}
        
    team_id = ctx["team_id"]
    try:
        configs = await pg_repo.list_user_provider_configs(team_id)
        active_providers = [c["provider_name"] for c in configs if c["is_active"]]
    except Exception:
        active_providers = []
        
    if not active_providers:
        return {
            "recommendation": "💡 您当前尚未激活任何 API 密钥。为了获得极致体验：<br>"
                              "1. <b>国内首选</b>：<strong style='color:var(--cyan);'>DeepSeek</strong> (极高性价比、超强中文推理)。<br>"
                              "2. <b>国际主流</b>：<strong style='color:var(--purple);'>OpenAI (gpt-4o-mini)</strong> 或 <strong style='color:var(--cyan);'>Gemini</strong> 组合。<br>"
                              "配置后，系统会自动根据所配置服务商推荐最优模型组合。"
        }
        
    rec = "✨ <b>检测到您已激活的服务商，已为您自动规划最优算力分配方案：</b><br><br>"
    if "deepseek" in active_providers:
        rec += "· <b>核心逻辑推理 (LLM)</b>: 推荐使用 <strong style='color:var(--cyan);'>deepseek-chat</strong> (极高智力，极致省钱)。<br>"
    elif "openai" in active_providers:
        rec += "· <b>核心逻辑推理 (LLM)</b>: 推荐使用 <strong style='color:var(--purple);'>gpt-4o-mini</strong> (速度极快，上下文稳定)。<br>"
    elif "alibaba" in active_providers:
        rec += "· <b>核心逻辑推理 (LLM)</b>: 推荐使用 <strong style='color:var(--amber);'>qwen-plus</strong> 或 <b>qwen-max</b> (高响应度)。<br>"
    else:
        rec += "· <b>核心逻辑推理 (LLM)</b>: 推荐采用您当前已保存服务商的默认推理模型。<br>"
        
    if "alibaba" in active_providers:
        rec += "· <b>记忆检索向量化 (Embedding)</b>: 自动绑定至 <strong style='color:var(--green);'>text-embedding-v3</strong> (极佳的多语言文本语义映射)。<br>"
    elif "openai" in active_providers:
        rec += "· <b>记忆检索向量化 (Embedding)</b>: 自动绑定至 <strong style='color:var(--green);'>text-embedding-3-small</strong> (标准的 1536 维高质量向量)。<br>"
    else:
        rec += "· <b>记忆检索向量化 (Embedding)</b>: 使用系统全局默认的本地高性能 Embedding 模型。<br>"
        
    return {"recommendation": rec}


@router.get("/usage")
async def get_user_usage(ctx: dict = Depends(get_user_context)):
    """Fetch user's Monthly Token stats and RAG storage volume."""
    from backend.api.routes import pg_repo
    if not pg_repo:
        raise HTTPException(status_code=500, detail="Database connection uninitialized")
        
    team_id = ctx["team_id"]
    agent_id = ctx["agent_id"]
    
    try:
        async with pg_repo.pool.acquire() as conn:
            # 1. Sum prompt, completion and total tokens used by this team
            total_row = await conn.fetchrow("""
                SELECT 
                    COALESCE(SUM(total_tokens), 0) as total_tokens,
                    COALESCE(SUM(tokens_saved_estimate), 0) as tokens_saved
                FROM user_token_usage
                WHERE user_id = $1
            """, team_id)
            
            # 2. Count memories registered for this team/agent
            mem_count = await conn.fetchval("""
                SELECT COUNT(*) FROM memories 
                WHERE team_id = $1 AND (agent_id = $2 OR agent_id = '' OR agent_id IS NULL)
            """, team_id, agent_id)
            
            # 3. Group consumption per-provider
            by_provider_rows = await conn.fetch("""
                SELECT provider_name,
                       COALESCE(SUM(prompt_tokens), 0) as prompt_tokens,
                       COALESCE(SUM(completion_tokens), 0) as completion_tokens,
                       COALESCE(SUM(total_tokens), 0) as total_tokens
                FROM user_token_usage
                WHERE user_id = $1
                GROUP BY provider_name
                ORDER BY total_tokens DESC
            """, team_id)
            
        return {
            "total_tokens": total_row["total_tokens"] if total_row else 0,
            "tokens_saved": total_row["tokens_saved"] if total_row else 0,
            "memory_count": mem_count or 0,
            "by_provider": [dict(r) for r in by_provider_rows]
        }
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to query usage: {e}")
        return {
            "total_tokens": 0,
            "tokens_saved": 0,
            "memory_count": 0,
            "by_provider": []
        }

