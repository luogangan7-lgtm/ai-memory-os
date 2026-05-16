export interface ModelInfo{id:string;name:string;size?:string;type:'chat'|'embedding'|'rerank'|'vision'|'reasoning';recommended?:boolean;ctx?:number;price?:string}
export interface ProviderInfo{id:string;name:string;nameZh:string;region:'cn'|'intl'|'local';baseUrl:string;models:ModelInfo[];features:string[]}
export const PROVIDERS:ProviderInfo[]=[
{id:'deepseek',name:'DeepSeek',nameZh:'深度求索',region:'cn',baseUrl:'https://api.deepseek.com/v1',features:['Chat','Reasoning'],models:[
{id:'deepseek-chat',name:'DeepSeek-V3',type:'chat',recommended:true,ctx:64000,price:'¥1/¥2/M'},
{id:'deepseek-reasoner',name:'DeepSeek-R1',type:'chat',ctx:64000,price:'¥2/¥4/M'},
]},
{id:'alibaba',name:'Alibaba Cloud',nameZh:'阿里云百炼',region:'cn',baseUrl:'https://dashscope.aliyuncs.com/compatible-mode/v1',features:['Chat','Vision','Embedding','Rerank','Audio','Reasoning'],models:[
{id:'qwen-plus',name:'Qwen-Plus',type:'chat',recommended:true,ctx:131072,price:'¥0.8/¥2/M'},
{id:'qwen-turbo',name:'Qwen-Turbo',type:'chat',ctx:131072,price:'¥0.3/¥1/M'},
{id:'qwen-max',name:'Qwen-Max',type:'chat',ctx:131072,price:'¥2/¥6/M'},
{id:'text-embedding-v3',name:'Text-Embedding-V3',type:'embedding',recommended:true,price:'¥0.07/M'},
{id:'gte-rerank',name:'GTE-Rerank',type:'rerank',recommended:true,price:'¥0.3/M'},
]},
{id:'zhipu',name:'Zhipu AI',nameZh:'智谱AI',region:'cn',baseUrl:'https://open.bigmodel.cn/api/paas/v4',features:['Chat','Vision','Embedding','Reasoning'],models:[
{id:'glm-4-flash',name:'GLM-4 Flash',type:'chat',recommended:true,ctx:128000,price:'¥0/M'},
{id:'glm-4',name:'GLM-4',type:'chat',ctx:128000,price:'¥2/¥8/M'},
{id:'embedding-2',name:'Embedding-2',type:'embedding',recommended:true},
]},
{id:'anthropic',name:'Anthropic',nameZh:'Anthropic',region:'intl',baseUrl:'https://api.anthropic.com/v1',features:['Chat','Vision','Reasoning'],models:[
{id:'claude-3-5-sonnet-20241022',name:'Claude 3.5 Sonnet',type:'chat',recommended:true,ctx:200000,price:'$3/$15/M'},
{id:'claude-3-5-haiku-20241022',name:'Claude 3.5 Haiku',type:'chat',ctx:200000,price:'$0.25/$1.25/M'},
]},
{id:'openai',name:'OpenAI',nameZh:'OpenAI',region:'intl',baseUrl:'https://api.openai.com/v1',features:['Chat','Vision','Reasoning','Embedding','Audio'],models:[
{id:'gpt-4o-mini',name:'GPT-4o Mini',type:'chat',recommended:true,ctx:128000,price:'$0.15/$0.6/M'},
{id:'gpt-4o',name:'GPT-4o',type:'chat',ctx:128000,price:'$2.5/$10/M'},
{id:'text-embedding-3-small',name:'Text-Embedding-3-Small',type:'embedding',recommended:true,price:'$0.02/M'},
]},
{id:'google',name:'Google',nameZh:'Google',region:'intl',baseUrl:'https://generativelanguage.googleapis.com/v1beta/openai',features:['Chat','Vision','Reasoning'],models:[
{id:'gemini-3.1-pro-preview',name:'Gemini-3.1-Pro',type:'chat',recommended:true,ctx:1048576,price:'$2/$10/M'},
{id:'gemini-3-flash',name:'Gemini-3-Flash',type:'chat',ctx:1048576,price:'$0.50/$2/M'},
{id:'gemini-2.5-pro',name:'Gemini-2.5-Pro',type:'chat',ctx:1048576,price:'$2.50/$15/M'},
{id:'gemini-2.5-flash',name:'Gemini-2.5-Flash',type:'chat',ctx:1048576,price:'$0.15/$0.60/M'},
]},
{id:'mistral',name:'Mistral AI',nameZh:'Mistral',region:'intl',baseUrl:'https://api.mistral.ai/v1',features:['Chat','Embedding'],models:[
{id:'mistral-large-latest',name:'Mistral-Large',type:'chat',recommended:true,ctx:131000,price:'$2/$6/M'},
{id:'mistral-small-latest',name:'Mistral-Small',type:'chat',ctx:32000,price:'$0.20/$0.60/M'},
{id:'codestral-latest',name:'Codestral',type:'chat',ctx:256000,price:'$0.30/$0.90/M'},
{id:'mistral-embed',name:'Mistral-Embed',type:'embedding',price:'$0.10/M'},
]},
{id:'cohere',name:'Cohere',nameZh:'Cohere',region:'intl',baseUrl:'https://api.cohere.com/v2',features:['Chat','Embedding','Rerank'],models:[
{id:'command-a',name:'Command-A',type:'chat',recommended:true,ctx:256000},
{id:'command-r7b',name:'Command-R7B',type:'chat',ctx:128000},
{id:'embed-english-v3',name:'Embed-English-V3',type:'embedding'},
{id:'embed-multilingual-v3',name:'Embed-Multilingual-V3',type:'embedding',recommended:true},
{id:'rerank-v3.5',name:'Rerank-V3.5',type:'rerank',recommended:true},
]},
{id:'xai',name:'xAI',nameZh:'xAI',region:'intl',baseUrl:'https://api.x.ai/v1',features:['Chat'],models:[
{id:'grok-4',name:'Grok-4',type:'chat',recommended:true,ctx:1000000},
{id:'grok-4-mini',name:'Grok-4-Mini',type:'chat',ctx:1000000},
]},
{id:'groq',name:'Groq',nameZh:'Groq',region:'intl',baseUrl:'https://api.groq.com/openai/v1',features:['Chat'],models:[
{id:'meta-llama/llama-4-scout-17b-16e-instruct',name:'Llama-4-Scout-17B',type:'chat',recommended:true,ctx:131072},
{id:'meta-llama/llama-4-maverick-17b-128e-instruct',name:'Llama-4-Maverick-17B',type:'chat',ctx:131072},
]},
{id:'together',name:'Together AI',nameZh:'Together',region:'intl',baseUrl:'https://api.together.xyz/v1',features:['Chat','Embedding'],models:[
{id:'meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8',name:'Llama-4-Maverick',type:'chat',recommended:true,ctx:131072},
{id:'deepseek-ai/DeepSeek-V3',name:'DeepSeek-V3',type:'chat',ctx:131072},
{id:'Qwen/Qwen2.5-72B-Instruct-Turbo',name:'Qwen2.5-72B',type:'chat',ctx:32768},
]},
{id:'ollama',name:'Ollama',nameZh:'Ollama(本地)',region:'local',baseUrl:'http://localhost:11434/v1',features:['Chat','Embedding'],models:[
{id:'qwen3:14b',name:'Qwen3-14B',type:'chat',recommended:true,size:'~8.5GB'},
{id:'qwen3:8b',name:'Qwen3-8B',type:'chat',size:'~5GB'},
{id:'deepseek-r1:14b',name:'DeepSeek-R1-14B',type:'reasoning',size:'~9GB'},
{id:'llama3.3:70b',name:'Llama3.3-70B',type:'chat',size:'~40GB'},
{id:'nomic-embed-text',name:'Nomic-Embed',type:'embedding',size:'~274MB'},
]},
];
export function getRecommendations(purpose:'classifier'|'reflection'|'embedding'|'rerank'):{p:string;m:string;label:string;reason:string}[]{
const result:{p:string;m:string;label:string;reason:string}[]=[];
const allChat=PROVIDERS.filter(p=>p.features.includes("Chat")||p.features.includes("Reasoning")).flatMap(p=>p.models.filter(m=>m.type==="chat"||m.type==="reasoning").map(m=>({provider:p,m})));
const allEmb=PROVIDERS.filter(p=>p.features.includes("Embedding")).flatMap(p=>p.models.filter(m=>m.type==="embedding").map(m=>({provider:p,m})));
const allRerank=PROVIDERS.filter(p=>p.features.includes("Rerank")).flatMap(p=>p.models.filter(m=>m.type==="rerank").map(m=>({provider:p,m})));
if(purpose==="classifier"){
const cheapest=[...allChat].sort((a,b)=>(parseFloat(a.m.price?.split("/")[0]?.replace("$","")?.replace("¥","")||"99"))-(parseFloat(b.m.price?.split("/")[0]?.replace("$","")?.replace("¥","")||"99"))).slice(0,3);
for(const x of cheapest)result.push({p:x.provider.id,m:x.m.id,label:"最低成本",reason:"输入价格: "+(x.m.price||"免费")})}
if(purpose==="reflection"){
const biggest=[...allChat].sort((a,b)=>(b.m.ctx||0)-(a.m.ctx||0)).slice(0,3);
for(const x of biggest)result.push({p:x.provider.id,m:x.m.id,label:"最大上下文",reason:(x.m.ctx||0)/1000+"k token"})}
if(purpose==="embedding"){for(const x of allEmb.slice(0,3))result.push({p:x.provider.id,m:x.m.id,label:"向量化推荐",reason:x.m.price||"推荐"})}
if(purpose==="rerank"){for(const x of allRerank.slice(0,3))result.push({p:x.provider.id,m:x.m.id,label:"重排序推荐",reason:x.m.price||"推荐"})}
return result}export function getLocalProviders(){return PROVIDERS.filter(p=>p.region==='local')}
