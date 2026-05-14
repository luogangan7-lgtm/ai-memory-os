export interface ModelInfo{id:string;name:string;size?:string;type:'chat'|'embedding'|'rerank'|'vision'|'reasoning';recommended?:boolean;ctx?:number}
export interface ProviderInfo{id:string;name:string;nameZh:string;region:'cn'|'intl'|'local';baseUrl:string;models:ModelInfo[];features:string[]}
export const PROVIDERS:ProviderInfo[]=[
{id:'alibaba',name:'Alibaba Cloud',nameZh:'阿里云百炼',region:'cn',baseUrl:'https://dashscope.aliyuncs.com/compatible-mode/v1',features:['Embedding','Rerank','Chat','Vision','Audio'],models:[
{id:'qwen3-max',name:'Qwen3-Max',type:'chat',recommended:true,ctx:131072},
{id:'qwen3-plus',name:'Qwen3-Plus',type:'chat',ctx:131072},
{id:'qwen3-turbo',name:'Qwen3-Turbo',type:'chat',ctx:131072},
{id:'qwen-max',name:'Qwen-Max',type:'chat',ctx:32768},
{id:'qwen-plus',name:'Qwen-Plus',type:'chat',ctx:131072},
{id:'qwen-turbo',name:'Qwen-Turbo',type:'chat',ctx:131072},
{id:'qwen-vl-max',name:'Qwen-VL-Max',type:'vision',ctx:32768},
{id:'qwen-coder-plus',name:'Qwen-Coder-Plus',type:'chat',ctx:131072},
{id:'text-embedding-v3',name:'Text Embedding V3',type:'embedding'},
{id:'gte-rerank',name:'GTE-Rerank',type:'rerank'},
{id:'qwen3-omni-flash',name:'Qwen3-Omni-Flash',type:'chat',ctx:32768},
]},
{id:'deepseek',name:'DeepSeek',nameZh:'深度求索',region:'cn',baseUrl:'https://api.deepseek.com/v1',features:['Chat','Reasoning'],models:[
{id:'deepseek-chat',name:'DeepSeek-V3',type:'chat',recommended:true,ctx:65536},
{id:'deepseek-reasoner',name:'DeepSeek-R1',type:'reasoning',recommended:true,ctx:65536},
]},
{id:'zhipu',name:'Zhipu AI',nameZh:'智谱AI',region:'cn',baseUrl:'https://open.bigmodel.cn/api/paas/v4',features:['Chat','Vision','Embedding'],models:[
{id:'glm-4-plus',name:'GLM-4-Plus',type:'chat',recommended:true,ctx:128000},
{id:'glm-4-flash',name:'GLM-4-Flash',type:'chat',ctx:128000},
{id:'glm-4-long',name:'GLM-4-Long',type:'chat',ctx:1000000},
{id:'glm-4v-plus',name:'GLM-4V-Plus',type:'vision',ctx:32768},
{id:'glm-4-air',name:'GLM-4-Air',type:'chat',ctx:128000},
{id:'embedding-3',name:'Embedding-3',type:'embedding'},
]},
{id:'moonshot',name:'Moonshot AI',nameZh:'月之暗面',region:'cn',baseUrl:'https://api.moonshot.cn/v1',features:['Chat','Vision'],models:[
{id:'moonshot-v1-auto',name:'Kimi-Auto',type:'chat',recommended:true,ctx:128000},
{id:'moonshot-v1-8k',name:'Kimi-8K',type:'chat',ctx:8192},
{id:'moonshot-v1-32k',name:'Kimi-32K',type:'chat',ctx:32768},
{id:'moonshot-v1-128k',name:'Kimi-128K',type:'chat',ctx:128000},
]},
{id:'minimax',name:'MiniMax',nameZh:'MiniMax',region:'cn',baseUrl:'https://api.minimax.chat/v1',features:['Chat','Voice'],models:[
{id:'abab7-chat',name:'ABAB7-Chat',type:'chat',recommended:true,ctx:245760},
{id:'abab6.5s-chat',name:'ABAB6.5s-Chat',type:'chat',ctx:245760},
]},
{id:'baichuan',name:'Baichuan AI',nameZh:'百川智能',region:'cn',baseUrl:'https://api.baichuan-ai.com/v1',features:['Chat'],models:[
{id:'baichuan4',name:'Baichuan4',type:'chat',recommended:true,ctx:32768},
{id:'baichuan3-turbo',name:'Baichuan3-Turbo',type:'chat',ctx:32768},
]},
{id:'yi',name:'01.AI',nameZh:'零一万物',region:'cn',baseUrl:'https://api.lingyiwanwu.com/v1',features:['Chat','Vision'],models:[
{id:'yi-large',name:'Yi-Large',type:'chat',recommended:true,ctx:32768},
{id:'yi-medium',name:'Yi-Medium',type:'chat',ctx:16384},
{id:'yi-lightning',name:'Yi-Lightning',type:'chat',ctx:16384},
{id:'yi-vision',name:'Yi-Vision',type:'vision',ctx:16384},
]},
{id:'stepfun',name:'StepFun',nameZh:'阶跃星辰',region:'cn',baseUrl:'https://api.stepfun.com/v1',features:['Chat','Vision'],models:[
{id:'step-2-16k',name:'Step-2-16K',type:'chat',recommended:true,ctx:16384},
{id:'step-1.5v-mini',name:'Step-1.5V-Mini',type:'vision',ctx:8192},
]},
{id:'tencent',name:'Tencent Cloud',nameZh:'腾讯混元',region:'cn',baseUrl:'https://api.hunyuan.cloud.tencent.com/v1',features:['Chat','Embedding'],models:[
{id:'hunyuan-turbos-latest',name:'Hunyuan-TurboS',type:'chat',recommended:true,ctx:28672},
{id:'hunyuan-large',name:'Hunyuan-Large',type:'chat',ctx:32768},
{id:'hunyuan-lite',name:'Hunyuan-Lite',type:'chat',ctx:262144},
]},
{id:'bytedance',name:'ByteDance',nameZh:'字节豆包',region:'cn',baseUrl:'https://ark.cn-beijing.volces.com/api/v3',features:['Chat','Embedding'],models:[
{id:'doubao-pro-256k',name:'Doubao-Pro-256K',type:'chat',recommended:true,ctx:262144},
{id:'doubao-lite-128k',name:'Doubao-Lite-128K',type:'chat',ctx:131072},
]},
{id:'openai',name:'OpenAI',nameZh:'OpenAI',region:'intl',baseUrl:'https://api.openai.com/v1',features:['Chat','Vision','Embedding','Audio'],models:[
{id:'gpt-4.5-preview',name:'GPT-4.5 Preview',type:'chat',recommended:true,ctx:128000},
{id:'gpt-4o',name:'GPT-4o',type:'chat',recommended:true,ctx:128000},
{id:'gpt-4o-mini',name:'GPT-4o Mini',type:'chat',ctx:128000},
{id:'gpt-4.1',name:'GPT-4.1',type:'chat',ctx:1000000},
{id:'o3',name:'o3',type:'reasoning',ctx:200000},
{id:'o4-mini',name:'o4-mini',type:'reasoning',ctx:200000},
{id:'gpt-4.1-nano',name:'GPT-4.1 Nano',type:'chat',ctx:1000000},
{id:'text-embedding-3-large',name:'Text Embedding 3 Large',type:'embedding'},
{id:'text-embedding-3-small',name:'Text Embedding 3 Small',type:'embedding'},
]},
{id:'anthropic',name:'Anthropic',nameZh:'Anthropic',region:'intl',baseUrl:'https://api.anthropic.com/v1',features:['Chat','Vision'],models:[
{id:'claude-sonnet-4-20250514',name:'Claude 4 Sonnet',type:'chat',recommended:true,ctx:200000},
{id:'claude-haiku-3.5',name:'Claude 3.5 Haiku',type:'chat',ctx:200000},
{id:'claude-opus-4',name:'Claude 4 Opus',type:'chat',ctx:200000},
]},
{id:'google',name:'Google',nameZh:'Google',region:'intl',baseUrl:'https://generativelanguage.googleapis.com/v1beta/openai',features:['Chat','Vision'],models:[
{id:'gemini-2.5-pro',name:'Gemini 2.5 Pro',type:'chat',recommended:true,ctx:1048576},
{id:'gemini-2.5-flash',name:'Gemini 2.5 Flash',type:'chat',ctx:1048576},
{id:'gemini-2.0-flash',name:'Gemini 2.0 Flash',type:'chat',ctx:1048576},
]},
{id:'mistral',name:'Mistral AI',nameZh:'Mistral',region:'intl',baseUrl:'https://api.mistral.ai/v1',features:['Chat','Embedding'],models:[
{id:'mistral-large-latest',name:'Mistral Large',type:'chat',recommended:true,ctx:128000},
{id:'mistral-small-latest',name:'Mistral Small',type:'chat',ctx:32768},
{id:'codestral-latest',name:'Codestral',type:'chat',ctx:256000},
]},
{id:'cohere',name:'Cohere',nameZh:'Cohere',region:'intl',baseUrl:'https://api.cohere.com/v2',features:['Chat','Embedding','Rerank'],models:[
{id:'command-r-plus',name:'Command R+',type:'chat',recommended:true,ctx:128000},
{id:'command-r',name:'Command R',type:'chat',ctx:128000},
{id:'embed-english-v3',name:'Embed English V3',type:'embedding'},
{id:'rerank-v3.5',name:'Rerank V3.5',type:'rerank'},
]},
{id:'xai',name:'xAI',nameZh:'xAI',region:'intl',baseUrl:'https://api.x.ai/v1',features:['Chat'],models:[
{id:'grok-3',name:'Grok-3',type:'chat',recommended:true,ctx:131072},
]},
{id:'perplexity',name:'Perplexity',nameZh:'Perplexity',region:'intl',baseUrl:'https://api.perplexity.ai',features:['Chat'],models:[
{id:'sonar-pro',name:'Sonar Pro',type:'chat',recommended:true,ctx:127000},
{id:'sonar',name:'Sonar',type:'chat',ctx:127000},
]},
{id:'ollama',name:'Ollama',nameZh:'Ollama(本地)',region:'local',baseUrl:'http://localhost:11434/v1',features:['Chat','Embedding'],models:[
{id:'llama3.3:70b',name:'Llama 3.3 70B',type:'chat',recommended:true,size:'~40GB'},
{id:'llama3.2:3b',name:'Llama 3.2 3B',type:'chat',size:'~2GB'},
{id:'qwen2.5:72b',name:'Qwen 2.5 72B',type:'chat',size:'~43GB'},
{id:'qwen2.5:7b',name:'Qwen 2.5 7B',type:'chat',recommended:true,size:'~4.7GB'},
{id:'mistral:7b',name:'Mistral 7B',type:'chat',size:'~4.1GB'},
{id:'deepseek-r1:14b',name:'DeepSeek R1 14B',type:'reasoning',size:'~9GB'},
{id:'nomic-embed-text',name:'Nomic Embed',type:'embedding',size:'~274MB'},
]},
];

export function getRecommendations(purpose:'classifier'|'reflection'|'embedding'|'rerank'){const r:Record<string,{p:string;m:string}[]>={classifier:[{p:'deepseek',m:'deepseek-chat'},{p:'openai',m:'gpt-4o-mini'},{p:'alibaba',m:'qwen3-turbo'}],reflection:[{p:'deepseek',m:'deepseek-reasoner'},{p:'openai',m:'gpt-4o'},{p:'anthropic',m:'claude-sonnet-4-20250514'}],embedding:[{p:'alibaba',m:'text-embedding-v3'},{p:'openai',m:'text-embedding-3-large'}],rerank:[{p:'alibaba',m:'gte-rerank'},{p:'cohere',m:'rerank-v3.5'}]};return r[purpose]||[]}
export function getLocalProviders(){return PROVIDERS.filter(p=>p.region==='local')}
