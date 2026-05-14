export interface ModelInfo{id:string;name:string;size?:string;type:'chat'|'embedding'|'rerank'|'vision'|'reasoning';recommended?:boolean;ctx?:number}
export interface ProviderInfo{id:string;name:string;nameZh:string;region:'cn'|'intl'|'local';baseUrl:string;models:ModelInfo[];features:string[]}
export const PROVIDERS:ProviderInfo[]=[
{id:'deepseek',name:'DeepSeek',nameZh:'深度求索',region:'cn',baseUrl:'https://api.deepseek.com/v1',features:['Chat','Reasoning'],models:[
{id:'deepseek-v4-pro',name:'DeepSeek-V4-Pro',type:'chat',recommended:true,ctx:131072},
{id:'deepseek-v4-flash',name:'DeepSeek-V4-Flash',type:'chat',ctx:131072},
{id:'deepseek-chat',name:'DeepSeek-V3.2',type:'chat',ctx:131072},
{id:'deepseek-reasoner',name:'DeepSeek-R1',type:'reasoning',recommended:true,ctx:131072},
]},
{id:'alibaba',name:'Alibaba Cloud',nameZh:'阿里云百炼',region:'cn',baseUrl:'https://dashscope.aliyuncs.com/compatible-mode/v1',features:['Chat','Vision','Embedding','Rerank','Audio'],models:[
{id:'qwen3-max',name:'Qwen3-Max',type:'chat',recommended:true,ctx:131072},
{id:'qwen3.6-plus',name:'Qwen3.6-Plus',type:'chat',ctx:131072},
{id:'qwen3.5-plus',name:'Qwen3.5-Plus',type:'chat',ctx:131072},
{id:'qwen3.5-flash',name:'Qwen3.5-Flash',type:'chat',ctx:131072},
{id:'qwen3-turbo',name:'Qwen3-Turbo',type:'chat',ctx:131072},
{id:'qwq-plus',name:'QwQ-Plus',type:'reasoning',recommended:true,ctx:131072},
{id:'qwen-vl-max',name:'Qwen-VL-Max',type:'vision'},
{id:'qwen3-coder-plus',name:'Qwen3-Coder-Plus',type:'chat',ctx:131072},
{id:'text-embedding-v4',name:'Text-Embedding-V4',type:'embedding',recommended:true},
{id:'text-embedding-v3',name:'Text-Embedding-V3',type:'embedding'},
{id:'gte-rerank-v2',name:'GTE-Rerank-V2',type:'rerank',recommended:true},
{id:'gte-rerank',name:'GTE-Rerank',type:'rerank'},
]},
{id:'zhipu',name:'Zhipu AI',nameZh:'智谱AI',region:'cn',baseUrl:'https://open.bigmodel.cn/api/paas/v4',features:['Chat','Vision','Embedding'],models:[
{id:'GLM-4-Plus',name:'GLM-4-Plus',type:'chat',recommended:true,ctx:128000},
{id:'GLM-4-Air-250414',name:'GLM-4-Air',type:'chat',ctx:128000},
{id:'GLM-4-Flash-250414',name:'GLM-4-Flash',type:'chat',ctx:128000},
{id:'GLM-Z1-AirX',name:'GLM-Z1-AirX',type:'reasoning',recommended:true,ctx:128000},
{id:'GLM-Z1-Air',name:'GLM-Z1-Air',type:'reasoning',ctx:128000},
{id:'GLM-Z1-Flash',name:'GLM-Z1-Flash',type:'reasoning',ctx:128000},
{id:'GLM-4V-Plus',name:'GLM-4V-Plus',type:'vision'},
{id:'embedding-3',name:'Embedding-3',type:'embedding',recommended:true},
]},
{id:'moonshot',name:'Moonshot AI',nameZh:'月之暗面Kimi',region:'cn',baseUrl:'https://api.moonshot.cn/v1',features:['Chat','Vision','Reasoning'],models:[
{id:'kimi-k2.5',name:'Kimi-K2.5',type:'chat',recommended:true,ctx:128000},
{id:'kimi-k2-thinking',name:'Kimi-K2-Thinking',type:'reasoning',ctx:128000},
{id:'kimi-k2.5-turbo',name:'Kimi-K2.5-Turbo',type:'chat',ctx:128000},
{id:'moonshot-v1-auto',name:'Kimi-V1-Auto',type:'chat',ctx:128000},
]},
{id:'minimax',name:'MiniMax',nameZh:'MiniMax',region:'cn',baseUrl:'https://api.minimax.chat/v1',features:['Chat','Voice'],models:[
{id:'minimax-m2.5',name:'MiniMax-M2.5',type:'chat',recommended:true,ctx:262144},
{id:'minimax-m2',name:'MiniMax-M2',type:'chat',ctx:262144},
{id:'abab7-chat',name:'ABAB7',type:'chat',ctx:245760},
]},
{id:'openai',name:'OpenAI',nameZh:'OpenAI',region:'intl',baseUrl:'https://api.openai.com/v1',features:['Chat','Vision','Reasoning','Embedding'],models:[
{id:'gpt-5.5',name:'GPT-5.5',type:'chat',recommended:true,ctx:272000},
{id:'gpt-5.4',name:'GPT-5.4',type:'chat',ctx:272000},
{id:'gpt-5.4-mini',name:'GPT-5.4-Mini',type:'chat',ctx:272000},
{id:'gpt-5.4-nano',name:'GPT-5.4-Nano',type:'chat',ctx:272000},
{id:'o3',name:'o3',type:'reasoning',recommended:true,ctx:200000},
{id:'o4-mini',name:'o4-mini',type:'reasoning',ctx:200000},
{id:'gpt-4.1',name:'GPT-4.1',type:'chat',ctx:1000000},
{id:'gpt-4.1-mini',name:'GPT-4.1-Mini',type:'chat',ctx:1000000},
{id:'text-embedding-3-large',name:'Text-Embedding-3-Large',type:'embedding',recommended:true},
{id:'text-embedding-3-small',name:'Text-Embedding-3-Small',type:'embedding'},
]},
{id:'anthropic',name:'Anthropic',nameZh:'Anthropic',region:'intl',baseUrl:'https://api.anthropic.com/v1',features:['Chat','Vision','Reasoning'],models:[
{id:'claude-opus-4-7',name:'Claude-Opus-4.7',type:'chat',recommended:true,ctx:200000},
{id:'claude-sonnet-4-6',name:'Claude-Sonnet-4.6',type:'chat',ctx:200000},
{id:'claude-haiku-4-5',name:'Claude-Haiku-4.5',type:'chat',ctx:200000},
]},
{id:'google',name:'Google',nameZh:'Google',region:'intl',baseUrl:'https://generativelanguage.googleapis.com/v1beta/openai',features:['Chat','Vision','Reasoning'],models:[
{id:'gemini-3.1-pro-preview',name:'Gemini-3.1-Pro',type:'chat',recommended:true,ctx:1048576},
{id:'gemini-3-flash',name:'Gemini-3-Flash',type:'chat',ctx:1048576},
{id:'gemini-2.5-pro',name:'Gemini-2.5-Pro',type:'chat',ctx:1048576},
{id:'gemini-2.5-flash',name:'Gemini-2.5-Flash',type:'chat',ctx:1048576},
]},
{id:'mistral',name:'Mistral AI',nameZh:'Mistral',region:'intl',baseUrl:'https://api.mistral.ai/v1',features:['Chat','Embedding'],models:[
{id:'mistral-large-latest',name:'Mistral-Large',type:'chat',recommended:true,ctx:131000},
{id:'mistral-small-latest',name:'Mistral-Small',type:'chat',ctx:32000},
{id:'codestral-latest',name:'Codestral',type:'chat',ctx:256000},
]},
{id:'cohere',name:'Cohere',nameZh:'Cohere',region:'intl',baseUrl:'https://api.cohere.com/v2',features:['Chat','Embedding','Rerank'],models:[
{id:'command-r7b',name:'Command-R7B',type:'chat',ctx:128000},
{id:'command-a',name:'Command-A',type:'chat',recommended:true,ctx:256000},
{id:'embed-english-v3',name:'Embed-English-V3',type:'embedding'},
{id:'embed-multilingual-v3',name:'Embed-Multilingual-V3',type:'embedding',recommended:true},
{id:'rerank-v3.5',name:'Rerank-V3.5',type:'rerank'},
]},
{id:'xai',name:'xAI',nameZh:'xAI',region:'intl',baseUrl:'https://api.x.ai/v1',features:['Chat'],models:[
{id:'grok-4',name:'Grok-4',type:'chat',recommended:true,ctx:1000000},
{id:'grok-4-mini',name:'Grok-4-Mini',type:'chat',ctx:1000000},
]},
{id:'ollama',name:'Ollama',nameZh:'Ollama(本地)',region:'local',baseUrl:'http://localhost:11434/v1',features:['Chat','Embedding'],models:[
{id:'qwen3:14b',name:'Qwen3-14B',type:'chat',recommended:true,size:'~8.5GB'},
{id:'qwen3:8b',name:'Qwen3-8B',type:'chat',size:'~5GB'},
{id:'deepseek-r1:14b',name:'DeepSeek-R1-14B',type:'reasoning',size:'~9GB'},
{id:'llama3.3:70b',name:'Llama3.3-70B',type:'chat',size:'~40GB'},
{id:'nomic-embed-text',name:'Nomic-Embed-Text',type:'embedding',size:'~274MB'},
{id:'mxbai-embed-large',name:'MxBai-Embed-Large',type:'embedding',size:'~670MB'},
]},
];
export function getRecommendations(purpose:'classifier'|'reflection'|'embedding'|'rerank'){const r:Record<string,{p:string;m:string}[]>={
classifier:[{p:'deepseek',m:'deepseek-v4-flash'},{p:'openai',m:'gpt-5.4-nano'},{p:'alibaba',m:'qwen3.5-flash'}],
reflection:[{p:'deepseek',m:'deepseek-v4-pro'},{p:'openai',m:'gpt-5.4'},{p:'anthropic',m:'claude-sonnet-4-6'}],
embedding:[{p:'alibaba',m:'text-embedding-v4'},{p:'openai',m:'text-embedding-3-large'},{p:'cohere',m:'embed-multilingual-v3'}],
rerank:[{p:'alibaba',m:'gte-rerank-v2'},{p:'cohere',m:'rerank-v3.5'}],
};return r[purpose]||[]}
export function getLocalProviders(){return PROVIDERS.filter(p=>p.region==='local')}
