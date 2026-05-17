# AI Memory OS — ElevenLabs Provider

from backend.providers.base import BaseProvider, ModelInfo, ModelCapability
import httpx

ELEVENLABS_CATALOG = [
    ModelInfo(id="eleven_v3", display_name="Eleven V3", provider="elevenlabs",
              capabilities=[ModelCapability.AUDIO], pricing_per_1m_tokens=0.02),
    ModelInfo(id="eleven_multilingual_v2", display_name="Multilingual V2", provider="elevenlabs",
              capabilities=[ModelCapability.AUDIO], pricing_per_1m_tokens=0.015),
    ModelInfo(id="eleven_flash_v2_5", display_name="Flash V2.5", provider="elevenlabs",
              capabilities=[ModelCapability.AUDIO], pricing_per_1m_tokens=0.005),
    ModelInfo(id="eleven_turbo_v2_5", display_name="Turbo V2.5", provider="elevenlabs",
              capabilities=[ModelCapability.AUDIO], pricing_per_1m_tokens=0.005),
]

class ElevenLabsProvider(BaseProvider):
    provider_name = "elevenlabs"

    async def validate(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                headers = {"xi-api-key": self.config.api_key}
                resp = await client.get("https://api.elevenlabs.io/v1/models", headers=headers)
                return resp.status_code == 200
        except:
            return False

    async def discover_models(self) -> list[ModelInfo]:
        return ELEVENLABS_CATALOG

    def supports(self, capability: ModelCapability) -> bool:
        return capability == ModelCapability.AUDIO
