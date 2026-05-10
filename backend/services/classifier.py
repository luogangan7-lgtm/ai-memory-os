# AI Memory OS — Knowledge Auto-Classifier
# Inspired by Qian Xuesen's 11-domain science & technology framework.
# Automatically assigns category/subcategory/topic to each memory using LLM + keyword rules.

from __future__ import annotations
import re
from typing import Optional

# ── Top-level category definitions ──────────────────────────────────────────
CATEGORIES = {
    "自然科学": ["物理", "化学", "生物", "天文", "地球", "材料", "量子", "粒子", "基因", "进化", "生态"],
    "社会科学": ["历史", "哲学", "政治", "经济", "法律", "心理", "社会", "文化", "教育", "管理", "商业", "金融"],
    "数学科学": ["数学", "统计", "概率", "代数", "几何", "微积分", "拓扑", "数论", "算法"],
    "系统科学": ["系统", "控制论", "信息论", "复杂性", "涌现", "自组织", "反馈", "钱学森"],
    "工程技术": ["工程", "计算机", "AI", "人工智能", "机器学习", "深度学习", "编程", "代码", "软件", "硬件",
                  "机械", "电子", "电气", "建筑", "能源", "航空", "航天", "互联网", "数据库", "网络", "安全"],
    "人体科学": ["医学", "健康", "运动", "营养", "生理", "解剖", "药物", "疾病", "心理健康", "中医"],
    "思维科学": ["认知", "学习", "记忆", "创新", "思维", "逻辑", "决策", "创造力", "元认知"],
    "人文艺术": ["文学", "音乐", "绘画", "艺术", "设计", "影视", "电影", "诗歌", "小说", "哲学"],
    "个人记忆": ["我", "今天", "昨天", "记得", "聊天", "对话", "日记", "感受", "想法"],
}

# Sub-category hints per category
SUBCATEGORY_HINTS = {
    "工程技术": {
        "AI科学": ["AI", "人工智能", "机器学习", "深度学习", "神经网络", "LLM", "大模型", "GPT", "transformer"],
        "软件工程": ["编程", "代码", "软件", "开发", "bug", "API", "框架", "数据库"],
        "硬件工程": ["硬件", "芯片", "CPU", "GPU", "电路", "传感器"],
        "网络安全": ["安全", "加密", "攻击", "防护", "漏洞", "认证"],
        "航空航天": ["航空", "航天", "火箭", "卫星", "飞机"],
    },
    "社会科学": {
        "经济与金融": ["经济", "金融", "货币", "股票", "投资", "市场", "贸易"],
        "历史与文明": ["历史", "朝代", "文明", "战争", "帝国"],
        "哲学与伦理": ["哲学", "伦理", "道德", "价值观", "意义"],
        "心理学": ["心理", "情绪", "行为", "认知", "精神"],
        "法律与治理": ["法律", "政策", "政治", "治理", "民主"],
    },
    "自然科学": {
        "物理学": ["物理", "力学", "电磁", "量子", "相对论", "热力学"],
        "化学": ["化学", "分子", "原子", "反应", "元素", "有机"],
        "生命科学": ["生物", "细胞", "基因", "进化", "生态", "微生物"],
        "地球科学": ["地球", "气候", "地质", "海洋", "大气", "环境"],
    },
}


def classify_by_keywords(text: str) -> tuple[str, str, str]:
    """Fast keyword-based classification. Returns (category, subcategory, topic)."""
    text_lower = text.lower()
    combined = text.lower()

    best_cat = "未分类"
    best_score = 0

    for cat, keywords in CATEGORIES.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > best_score:
            best_score = score
            best_cat = cat

    # Determine subcategory
    best_sub = ""
    if best_cat in SUBCATEGORY_HINTS:
        best_sub_score = 0
        for sub, keywords in SUBCATEGORY_HINTS[best_cat].items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > best_sub_score:
                best_sub_score = score
                best_sub = sub

    # Extract a simple topic (first meaningful noun phrase, max 10 chars)
    topic = _extract_topic(text)

    return best_cat, best_sub, topic


def _extract_topic(text: str) -> str:
    """Extract a short topic label from text."""
    # Try to get title if text starts with a heading-like phrase
    first_line = text.strip().split("\n")[0][:50]
    # Remove common prefixes
    cleaned = re.sub(r"^[#\-\*\s]+", "", first_line).strip()
    return cleaned[:20] if cleaned else ""


async def classify_with_llm(text: str, registry) -> tuple[str, str, str]:
    """Use LLM to classify text into category/subcategory/topic.
    Falls back to keyword classification if LLM unavailable."""
    try:
        # Build category list for the prompt
        cat_list = "、".join(CATEGORIES.keys()) + "、未分类"
        prompt = f"""请对以下内容进行知识分类，只返回JSON，不要解释。

内容（前200字）：
{text[:200]}

要求：
1. category：从以下选择：{cat_list}
2. subcategory：在category下自主命名一个子类（例如"AI科学"、"量子物理"、"行为经济学"），不超过8个字
3. topic：提取最核心的主题词，不超过10个字

返回格式（严格JSON）：
{{"category": "...", "subcategory": "...", "topic": "..."}}"""

        response = await registry.chat([
            {"role": "system", "content": "你是一个知识分类专家，严格按JSON格式回复。"},
            {"role": "user", "content": prompt}
        ])

        # Parse JSON from response
        import json
        # Extract JSON from response (may have extra text)
        match = re.search(r'\{[^}]+\}', response, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return (
                data.get("category", "未分类"),
                data.get("subcategory", ""),
                data.get("topic", "")
            )
    except Exception as e:
        print(f"DEBUG: LLM classification failed: {e}, falling back to keywords", flush=True)

    # Fallback to keyword-based classification
    return classify_by_keywords(text)


async def classify_memory(content: str, title: str = "", registry=None) -> dict:
    """Classify a memory and return category/subcategory/topic dict."""
    text = f"{title}\n{content}" if title else content

    if registry:
        try:
            cat, sub, topic = await classify_with_llm(text, registry)
        except Exception:
            cat, sub, topic = classify_by_keywords(text)
    else:
        cat, sub, topic = classify_by_keywords(text)

    return {
        "category": cat,
        "subcategory": sub or _auto_subcategory(cat, text),
        "topic": topic or _extract_topic(text),
    }


def _auto_subcategory(category: str, text: str) -> str:
    """Auto-generate a subcategory from text when LLM is unavailable."""
    hints = SUBCATEGORY_HINTS.get(category, {})
    for sub, kws in hints.items():
        if any(kw in text for kw in kws):
            return sub
    return ""

async def detect_new_categories(pg_repo, team_id: str = "default") -> list[dict]:
    """Find clusters of '未分类' memories that might form new categories."""
    async with pg_repo.pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT topic, count(*) as cnt FROM memories "
            "WHERE team_id=$1 AND category='未分类' AND topic != '' "
            "GROUP BY topic HAVING count(*) >= 3 ORDER BY cnt DESC",
            team_id)
        return [{"topic": r["topic"], "count": r["cnt"]} for r in rows]
