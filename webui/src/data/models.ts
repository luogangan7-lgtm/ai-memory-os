export interface ModelInfo {
  id: string;
  name: string;
  size?: string;
  type: 'chat' | 'embedding' | 'rerank' | 'vision' | 'reasoning' | 'audio';
  recommended?: boolean;
  ctx?: number;
  price?: string;
  /** Provider offers a permanent or near-permanent free tier for this model. */
  free?: boolean;
  /** Short qualifier shown next to the model (e.g. "200K context", "rate-limited"). */
  note?: string;
}

export interface ProviderInfo {
  id: string;
  name: string;
  nameZh: string;
  region: 'cn' | 'intl' | 'local';
  baseUrl: string;
  models: ModelInfo[];
  features: string[];
  /** Direct link to the "Get API key" page for this provider. */
  signupUrl?: string;
}

// NOTE for maintainers: do NOT change existing provider.id / model.id / baseUrl —
// the admin Providers page and saved user LLM configs key off these. New models
// may be APPENDED to a provider's `models` array; existing entries may gain
// optional fields (free / note) but their identifiers must stay stable.
//
// Last reviewed: 2026-05. Verify each vendor's docs before relying on "free" /
// pricing for production decisions; vendors change tiers monthly.

export const PROVIDERS: ProviderInfo[] = [
  {
    id: 'deepseek', name: 'DeepSeek', nameZh: '深度求索', region: 'cn',
    baseUrl: 'https://api.deepseek.com/v1',
    signupUrl: 'https://platform.deepseek.com/api_keys',
    features: ['Chat', 'Reasoning'],
    models: [
      { id: 'deepseek-v4-flash', name: 'DeepSeek V4 Flash', type: 'chat', recommended: true, ctx: 65536, price: '¥1.0/M' },
      { id: 'deepseek-v4-pro', name: 'DeepSeek V4 Pro', type: 'chat', ctx: 65536, price: '¥4.0/M' },
      { id: 'deepseek-chat', name: 'DeepSeek V3.2', type: 'chat', ctx: 128000, price: '¥1.99/M', note: '当前主力对话' },
      { id: 'deepseek-reasoner', name: 'DeepSeek R1', type: 'reasoning', ctx: 64000, price: '¥4.0/M', note: '推理强化' },
    ],
  },
  {
    id: 'alibaba', name: 'Alibaba Cloud', nameZh: '阿里云百炼', region: 'cn',
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    signupUrl: 'https://bailian.console.aliyun.com/?apiKey=1',
    features: ['Chat', 'Vision', 'Embedding', 'Rerank', 'Audio', 'Reasoning'],
    models: [
      { id: 'qwen3.6-plus', name: 'Qwen3.6 Plus', type: 'chat', recommended: true, ctx: 128000, price: '¥0.8/M' },
      { id: 'qwen3.6-flash', name: 'Qwen3.6 Flash', type: 'chat', ctx: 128000, price: '¥0.2/M' },
      { id: 'qwen3.6-max-preview', name: 'Qwen3.6 Max Preview', type: 'chat', ctx: 32000, price: '¥2.5/M' },
      { id: 'qwen3.5-omni-plus', name: 'Qwen3.5 Omni Plus', type: 'chat', ctx: 32000, price: '¥0.5/M' },
      { id: 'qwen-flash', name: 'Qwen Flash', type: 'chat', free: true, ctx: 128000, note: '百炼限流免费' },
      { id: 'text-embedding-v3', name: 'Text-Embedding-V3', type: 'embedding', recommended: true, price: '¥0.70/M' },
      { id: 'qwen3-rerank', name: 'Qwen3-Rerank', type: 'rerank', recommended: true, price: '¥0.5/M' },
    ],
  },
  {
    id: 'zhipu', name: 'Zhipu AI', nameZh: '智谱 AI', region: 'cn',
    baseUrl: 'https://open.bigmodel.cn/api/paas/v4',
    signupUrl: 'https://open.bigmodel.cn/usercenter/apikeys',
    features: ['Chat', 'Vision', 'Embedding', 'Reasoning', 'Rerank'],
    models: [
      { id: 'glm-5', name: 'GLM-5', type: 'chat', recommended: true, ctx: 128000, price: '¥2.0/M', note: '旗舰' },
      { id: 'glm-4.7', name: 'GLM-4.7', type: 'chat', free: true, ctx: 128000, note: '永久免费 (legacy id)' },
      { id: 'glm-5-turbo', name: 'GLM-5 Turbo', type: 'chat', ctx: 128000, price: '¥0.5/M' },
      { id: 'glm-5.1', name: 'GLM-5.1', type: 'chat', ctx: 128000, price: '¥1.0/M' },
      { id: 'glm-4.7-flash', name: 'GLM-4.7 Flash', type: 'chat', free: true, ctx: 200000, note: '200K 永久免费 (2026-01)' },
      { id: 'glm-4-flash', name: 'GLM-4 Flash', type: 'chat', free: true, ctx: 128000, note: '永久免费' },
      { id: 'glm-4-flash-250414', name: 'GLM-4 Flash 250414', type: 'chat', free: true, ctx: 128000, note: '高频版免费' },
      { id: 'embedding-3', name: 'Embedding-3', type: 'embedding', recommended: true },
      { id: 'glm-4-rerank', name: 'GLM-4 Rerank', type: 'rerank', recommended: true },
    ],
  },
  {
    id: 'anthropic', name: 'Anthropic', nameZh: 'Anthropic', region: 'intl',
    baseUrl: 'https://api.anthropic.com/v1',
    signupUrl: 'https://console.anthropic.com/settings/keys',
    features: ['Chat', 'Vision', 'Reasoning'],
    models: [
      { id: 'claude-opus-4-7', name: 'Claude Opus 4.7', type: 'chat', recommended: true, ctx: 1000000, price: '$5/$25/M', note: '旗舰' },
      { id: 'claude-sonnet-4-6', name: 'Claude Sonnet 4.6', type: 'chat', ctx: 1000000, price: '$3/$15/M' },
      { id: 'claude-haiku-4-5-20251001', name: 'Claude Haiku 4.5', type: 'chat', ctx: 200000, price: '$1/$5/M' },
    ],
  },
  {
    id: 'openai', name: 'OpenAI', nameZh: 'OpenAI', region: 'intl',
    baseUrl: 'https://api.openai.com/v1',
    signupUrl: 'https://platform.openai.com/api-keys',
    features: ['Chat', 'Vision', 'Reasoning', 'Embedding', 'Audio'],
    models: [
      { id: 'gpt-4o', name: 'GPT-4o', type: 'chat', ctx: 128000, price: '$5.0/$15/M' },
      { id: 'gpt-4o-mini', name: 'GPT-4o Mini', type: 'chat', recommended: true, ctx: 128000, price: '$0.15/$0.6/M' },
      { id: 'o1', name: 'o1', type: 'reasoning', ctx: 200000, price: '$15.0/M' },
      { id: 'o3-mini', name: 'o3 Mini', type: 'reasoning', ctx: 200000, price: '$1.1/M' },
      { id: 'text-embedding-3-small', name: 'Text-Embedding-3-Small', type: 'embedding', recommended: true, price: '$0.02/M' },
      { id: 'text-embedding-3-large', name: 'Text-Embedding-3-Large', type: 'embedding', price: '$0.13/M' },
    ],
  },
  {
    id: 'google', name: 'Google', nameZh: 'Google Gemini', region: 'intl',
    baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai',
    signupUrl: 'https://aistudio.google.com/apikey',
    features: ['Chat', 'Vision', 'Reasoning'],
    models: [
      { id: 'gemini-3.1-pro-preview', name: 'Gemini-3.1-Pro', type: 'chat', recommended: true, ctx: 1048576, price: '$2/$10/M' },
      { id: 'gemini-3-flash', name: 'Gemini-3-Flash', type: 'chat', ctx: 1048576, price: '$0.50/$2/M' },
      { id: 'gemini-2.5-pro', name: 'Gemini-2.5-Pro', type: 'chat', free: true, ctx: 1048576, note: '100 req/day 免费' },
      { id: 'gemini-2.5-flash', name: 'Gemini-2.5-Flash', type: 'chat', free: true, ctx: 1048576, note: '250 req/day 免费' },
      { id: 'gemini-2.5-flash-lite', name: 'Gemini-2.5-Flash-Lite', type: 'chat', free: true, ctx: 1048576, note: '1000 req/day 免费' },
    ],
  },
  {
    id: 'mistral', name: 'Mistral AI', nameZh: 'Mistral', region: 'intl',
    baseUrl: 'https://api.mistral.ai/v1',
    signupUrl: 'https://console.mistral.ai/api-keys',
    features: ['Chat', 'Embedding'],
    models: [
      { id: 'mistral-large-latest', name: 'Mistral-Large', type: 'chat', recommended: true, ctx: 131000, price: '$2/$6/M' },
      { id: 'mistral-small-latest', name: 'Mistral-Small', type: 'chat', ctx: 32000, price: '$0.20/$0.60/M' },
      { id: 'codestral-latest', name: 'Codestral', type: 'chat', ctx: 256000, price: '$0.30/$0.90/M', note: '代码' },
      { id: 'mistral-embed', name: 'Mistral-Embed', type: 'embedding', price: '$0.10/M' },
    ],
  },
  {
    id: 'cohere', name: 'Cohere', nameZh: 'Cohere', region: 'intl',
    baseUrl: 'https://api.cohere.com/v2',
    signupUrl: 'https://dashboard.cohere.com/api-keys',
    features: ['Chat', 'Embedding', 'Rerank'],
    models: [
      { id: 'command-a', name: 'Command-A', type: 'chat', recommended: true, ctx: 256000 },
      { id: 'command-r7b', name: 'Command-R7B', type: 'chat', free: true, ctx: 128000, note: 'Trial 免费' },
      { id: 'embed-english-v3', name: 'Embed-English-V3', type: 'embedding' },
      { id: 'embed-multilingual-v3', name: 'Embed-Multilingual-V3', type: 'embedding', recommended: true },
      { id: 'rerank-v3.5', name: 'Rerank-V3.5', type: 'rerank', recommended: true },
    ],
  },
  {
    id: 'xai', name: 'xAI', nameZh: 'xAI Grok', region: 'intl',
    baseUrl: 'https://api.x.ai/v1',
    signupUrl: 'https://console.x.ai/team',
    features: ['Chat'],
    models: [
      { id: 'grok-4', name: 'Grok-4', type: 'chat', recommended: true, ctx: 1000000 },
      { id: 'grok-4-mini', name: 'Grok-4-Mini', type: 'chat', ctx: 1000000 },
    ],
  },
  {
    id: 'groq', name: 'Groq', nameZh: 'Groq', region: 'intl',
    baseUrl: 'https://api.groq.com/openai/v1',
    signupUrl: 'https://console.groq.com/keys',
    features: ['Chat'],
    models: [
      { id: 'meta-llama/llama-4-scout-17b-16e-instruct', name: 'Llama-4-Scout-17B', type: 'chat', free: true, recommended: true, ctx: 131072, note: '免费 + 极速推理' },
      { id: 'meta-llama/llama-4-maverick-17b-128e-instruct', name: 'Llama-4-Maverick-17B', type: 'chat', free: true, ctx: 131072, note: '免费 + 极速推理' },
    ],
  },
  {
    id: 'together', name: 'Together AI', nameZh: 'Together', region: 'intl',
    baseUrl: 'https://api.together.xyz/v1',
    signupUrl: 'https://api.together.xyz/settings/api-keys',
    features: ['Chat', 'Embedding'],
    models: [
      { id: 'meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8', name: 'Llama-4-Maverick', type: 'chat', recommended: true, ctx: 131072 },
      { id: 'deepseek-ai/DeepSeek-V3', name: 'DeepSeek-V3', type: 'chat', ctx: 131072 },
      { id: 'Qwen/Qwen2.5-72B-Instruct-Turbo', name: 'Qwen2.5-72B', type: 'chat', ctx: 32768 },
    ],
  },
  {
    id: 'ollama', name: 'Ollama', nameZh: 'Ollama(本地)', region: 'local',
    baseUrl: 'http://localhost:11434/v1',
    features: ['Chat', 'Embedding'],
    models: [
      { id: 'qwen3:14b', name: 'Qwen3-14B', type: 'chat', free: true, recommended: true, size: '~8.5GB', note: '本地免费' },
      { id: 'qwen3:8b', name: 'Qwen3-8B', type: 'chat', free: true, size: '~5GB' },
      { id: 'deepseek-r1:14b', name: 'DeepSeek-R1-14B', type: 'reasoning', free: true, size: '~9GB' },
      { id: 'llama3.3:70b', name: 'Llama3.3-70B', type: 'chat', free: true, size: '~40GB' },
      { id: 'nomic-embed-text', name: 'Nomic-Embed', type: 'embedding', free: true, size: '~274MB' },
    ],
  },
  {
    id: 'minimax', name: 'MiniMax', nameZh: '海螺 MiniMax', region: 'cn',
    baseUrl: 'https://api.minimax.chat/v1',
    signupUrl: 'https://platform.minimaxi.com/login',
    features: ['Chat'],
    models: [
      { id: 'MiniMax-M2.7', name: 'MiniMax M2.7', type: 'chat', recommended: true, ctx: 1000000, price: '¥1.0/M', note: '1M 上下文' },
      { id: 'MiniMax-M2.5', name: 'MiniMax M2.5', type: 'chat', ctx: 8192, price: '¥0.5/M' },
      { id: 'MiniMax-M2.7-highspeed', name: 'MiniMax M2.7 (Highspeed)', type: 'chat', ctx: 245760, price: '¥0.1/M', note: '高速版' },
      { id: 'MiniMax-M2', name: 'MiniMax M2', type: 'chat', ctx: 8192, price: '¥0.8/M' },
    ],
  },
  {
    id: 'doubao', name: 'Doubao', nameZh: '字节豆包', region: 'cn',
    baseUrl: 'https://ark.cn-beijing.volces.com/api/v3',
    signupUrl: 'https://www.volcengine.com/product/doubao',
    features: ['Chat', 'Embedding'],
    models: [
      { id: 'doubao-1-5-pro-32k', name: 'Doubao 1.5 Pro', type: 'chat', recommended: true, ctx: 32768, price: '¥0.8/M' },
      { id: 'doubao-1-5-lite-32k', name: 'Doubao 1.5 Lite', type: 'chat', ctx: 32768, price: '¥0.3/M' },
      { id: 'doubao-embedding', name: 'Doubao Embedding', type: 'embedding', recommended: true, price: '¥0.1/M' },
    ],
  },
  {
    id: 'baidu', name: 'Baidu Ernie', nameZh: '百度文心', region: 'cn',
    baseUrl: 'https://qianfan.baidubce.com/v2',
    signupUrl: 'https://console.bce.baidu.com/qianfan/ais/console/applicationConsole/application',
    features: ['Chat', 'Embedding', 'Rerank'],
    models: [
      { id: 'ernie-4.5-8k', name: 'ERNIE 4.5', type: 'chat', recommended: true, ctx: 8192, price: '¥1.6/M' },
      { id: 'ernie-4.5-turbo-8k', name: 'ERNIE 4.5 Turbo', type: 'chat', ctx: 8192, price: '¥0.8/M' },
      { id: 'ernie-lite-8k', name: 'ERNIE Lite', type: 'chat', free: true, ctx: 8192, note: '永久免费' },
      { id: 'bce-embedding-v1', name: 'BCE Embedding', type: 'embedding', recommended: true, price: '¥0.5/M' },
      { id: 'bce-reranker-base_v1', name: 'BCE Reranker', type: 'rerank', recommended: true, price: '¥0.5/M' },
    ],
  },
  {
    id: 'hunyuan', name: 'Tencent Hunyuan', nameZh: '腾讯混元', region: 'cn',
    baseUrl: 'https://api.hunyuan.cloud.tencent.com/v1',
    signupUrl: 'https://console.cloud.tencent.com/hunyuan/api-key',
    features: ['Chat', 'Embedding'],
    models: [
      { id: 'hunyuan-turbos', name: 'Hunyuan Turbo S', type: 'chat', recommended: true, ctx: 32768, price: '¥0.8/M' },
      { id: 'hunyuan-lite', name: 'Hunyuan Lite', type: 'chat', free: true, ctx: 256000, note: '永久免费 256K' },
      { id: 'hunyuan-embedding', name: 'Hunyuan Embedding', type: 'embedding', recommended: true, price: '¥0.7/M' },
    ],
  },
  {
    id: 'spark', name: 'iFlytek Spark', nameZh: '讯飞星火', region: 'cn',
    baseUrl: 'https://spark-api-open.xf-yun.com/v1',
    features: ['Chat'],
    models: [
      { id: '4.0Ultra', name: 'Spark 4.0 Ultra', type: 'chat', recommended: true, ctx: 8192, price: '¥4.0/M' },
      { id: 'x1', name: 'Spark X1', type: 'chat', ctx: 8192, price: '¥4.0/M' },
      { id: 'generalv3.5', name: 'Spark 3.5', type: 'chat', ctx: 8192, price: '¥1.2/M' },
    ],
  },
  {
    id: 'stepfun', name: 'Stepfun', nameZh: '阶跃星辰', region: 'cn',
    baseUrl: 'https://api.stepfun.com/v1',
    features: ['Chat'],
    models: [
      { id: 'step-2-16k', name: 'Step 2', type: 'chat', recommended: true, ctx: 16384, price: '¥3.8/M' },
      { id: 'step-1-8k', name: 'Step 1', type: 'chat', ctx: 8192, price: '¥1.2/M' },
      { id: 'step-1-flash', name: 'Step 1 Flash', type: 'chat', ctx: 8192, price: '¥0.2/M', note: '低价' },
    ],
  },
  {
    id: 'yi', name: '01.AI', nameZh: '零一万物', region: 'cn',
    baseUrl: 'https://api.lingyiwanwu.com/v1',
    features: ['Chat'],
    models: [
      { id: 'yi-lightning', name: 'Yi Lightning', type: 'chat', recommended: true, ctx: 16384, price: '¥0.14/M' },
      { id: 'yi-medium', name: 'Yi Medium', type: 'chat', ctx: 16384, price: '¥2.5/M' },
      { id: 'yi-large', name: 'Yi Large', type: 'chat', ctx: 32768, price: '¥20.0/M' },
    ],
  },
  {
    id: 'elevenlabs', name: 'ElevenLabs', nameZh: 'ElevenLabs', region: 'intl',
    baseUrl: 'https://api.elevenlabs.io/v1',
    features: ['Audio'],
    models: [
      { id: 'eleven_v3', name: 'Eleven V3', type: 'audio', recommended: true, price: '$0.02/M' },
      { id: 'eleven_multilingual_v2', name: 'Multilingual V2', type: 'audio', price: '$0.015/M' },
      { id: 'eleven_flash_v2_5', name: 'Flash V2.5', type: 'audio', price: '$0.005/M' },
      { id: 'eleven_turbo_v2_5', name: 'Turbo V2.5', type: 'audio', price: '$0.005/M' },
    ],
  },
  {
    id: 'moonshot', name: 'Moonshot', nameZh: '月之暗面 Kimi', region: 'cn',
    baseUrl: 'https://api.moonshot.cn/v1',
    signupUrl: 'https://platform.moonshot.cn/console/api-keys',
    features: ['Chat'],
    models: [
      { id: 'moonshot-v1-8k', name: 'Kimi v1 (8K)', type: 'chat', recommended: true, ctx: 8192, price: '¥1.2/M' },
      { id: 'moonshot-v1-32k', name: 'Kimi v1 (32K)', type: 'chat', ctx: 32768, price: '¥2.4/M' },
      { id: 'moonshot-v1-128k', name: 'Kimi v1 (128K)', type: 'chat', ctx: 131072, price: '¥8.0/M', note: '长上下文' },
    ],
  },
  {
    id: 'tencentci', name: 'Tencent CI', nameZh: '腾讯云数据万象', region: 'cn',
    baseUrl: 'https://ci.tencentcloudapi.com/v1',
    features: ['Vision'],
    models: [
      { id: 'ci-vision-pro', name: 'CI Vision Pro', type: 'vision', recommended: true, price: '¥2.0/M' },
      { id: 'ci-vision-lite', name: 'CI Vision Lite', type: 'vision', price: '¥0.5/M' },
    ],
  },
  {
    id: 'siliconflow', name: 'SiliconFlow', nameZh: '硅基流动', region: 'cn',
    baseUrl: 'https://api.siliconflow.cn/v1',
    signupUrl: 'https://cloud.siliconflow.cn/account/ak',
    features: ['Chat', 'Embedding', 'Rerank'],
    models: [
      { id: 'BAAI/bge-m3', name: 'BGE-M3', type: 'embedding', recommended: true, price: '¥0.1/M' },
      { id: 'BAAI/bge-large-zh-v1.5', name: 'BGE-Large-ZH', type: 'embedding', price: '¥0.1/M' },
      { id: 'BAAI/bge-reranker-v2-m3', name: 'BGE-Reranker-V2', type: 'rerank', recommended: true, price: '¥0.2/M' },
      { id: 'deepseek-ai/DeepSeek-V3', name: 'DeepSeek-V3 (Silicon)', type: 'chat', ctx: 131072, price: '¥1.0/M' },
      { id: 'Qwen/Qwen2.5-7B-Instruct', name: 'Qwen2.5 7B', type: 'chat', free: true, ctx: 32768, note: '开源永久免费' },
      { id: 'THUDM/glm-4-9b-chat', name: 'GLM-4 9B', type: 'chat', free: true, ctx: 32768, note: '开源永久免费' },
      { id: 'internlm/internlm2_5-7b-chat', name: 'InternLM 2.5 7B', type: 'chat', free: true, ctx: 32768, note: '开源永久免费' },
      { id: 'meta-llama/Meta-Llama-3.1-8B-Instruct', name: 'Llama 3.1 8B', type: 'chat', free: true, ctx: 8192, note: '开源永久免费' },
    ],
  },
  {
    id: 'jina', name: 'Jina AI', nameZh: 'Jina AI', region: 'intl',
    baseUrl: 'https://api.jina.ai/v1',
    signupUrl: 'https://jina.ai/?sui=apikey',
    features: ['Embedding', 'Rerank'],
    models: [
      { id: 'jina-embeddings-v3', name: 'Jina Embeddings V3', type: 'embedding', recommended: true, price: '$0.02/M' },
      { id: 'jina-reranker-v2-base-multilingual', name: 'Jina Reranker V2', type: 'rerank', recommended: true, price: '$0.02/M' },
    ],
  },
];

export function getRecommendations(
  purpose: 'classifier' | 'reflection' | 'embedding' | 'rerank'
): { p: string; m: string; label: string; reason: string }[] {
  const result: { p: string; m: string; label: string; reason: string }[] = [];
  const allChat = PROVIDERS
    .filter((p) => p.features.includes('Chat') || p.features.includes('Reasoning'))
    .flatMap((p) => p.models.filter((m) => m.type === 'chat' || m.type === 'reasoning').map((m) => ({ provider: p, m })));
  const allEmb = PROVIDERS
    .filter((p) => p.features.includes('Embedding'))
    .flatMap((p) => p.models.filter((m) => m.type === 'embedding').map((m) => ({ provider: p, m })));
  const allRerank = PROVIDERS
    .filter((p) => p.features.includes('Rerank'))
    .flatMap((p) => p.models.filter((m) => m.type === 'rerank').map((m) => ({ provider: p, m })));
  if (purpose === 'classifier') {
    const cheapest = [...allChat].sort((a, b) => {
      const pa = a.m.free ? 0 : parseFloat(a.m.price?.split('/')[0]?.replace(/[$¥]/g, '') || '99');
      const pb = b.m.free ? 0 : parseFloat(b.m.price?.split('/')[0]?.replace(/[$¥]/g, '') || '99');
      return pa - pb;
    }).slice(0, 3);
    for (const x of cheapest) result.push({ p: x.provider.id, m: x.m.id, label: '最低成本', reason: x.m.free ? '免费' : (x.m.price || '—') });
  }
  if (purpose === 'reflection') {
    const biggest = [...allChat].sort((a, b) => (b.m.ctx || 0) - (a.m.ctx || 0)).slice(0, 3);
    for (const x of biggest) result.push({ p: x.provider.id, m: x.m.id, label: '最大上下文', reason: (x.m.ctx || 0) / 1000 + 'k token' });
  }
  if (purpose === 'embedding') {
    for (const x of allEmb.slice(0, 3)) result.push({ p: x.provider.id, m: x.m.id, label: '向量化推荐', reason: x.m.price || '推荐' });
  }
  if (purpose === 'rerank') {
    for (const x of allRerank.slice(0, 3)) result.push({ p: x.provider.id, m: x.m.id, label: '重排序推荐', reason: x.m.price || '推荐' });
  }
  return result;
}

export function getLocalProviders() {
  return PROVIDERS.filter((p) => p.region === 'local');
}
