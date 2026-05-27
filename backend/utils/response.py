"""Centralized LLM response cleaning — strips reasoning prefixes from any model.

Supported formats:
  MiniMax-M2.7:  <think>...</think> + actual response
  DeepSeek-R1:   reasoning_content field or <answer>...</answer>
  Qwen think:    similar <think> tags
"""
import re

_THINK_TAG = re.compile(r'<think>.*?</think>\s*', re.DOTALL)


def clean_llm_content(raw: str) -> str:
    """Strip reasoning from LLM output, preserving the actual response."""
    if not raw or not isinstance(raw, str):
        return raw or ""
    content = raw.strip()
    if not content:
        return content
    # Strip <think> tags
    content = _THINK_TAG.sub('', content).strip()
    # Strip "The user asks/wants..." / "Let me think..." reasoning prefixes
    if content and (content.startswith("The ") or content.startswith("Let ")):
        nl = chr(10)
        if nl + nl in content[:600]:
            content = content.split(nl + nl, 1)[-1].strip()
    return content or raw.strip()


def clean_llm_response(data: dict) -> str:
    """Extract and clean content from a full provider response dict."""
    try:
        msg = data["choices"][0]["message"]
        content = msg.get("content", "")
        # DeepSeek-R1: use reasoning_content only if content is empty
        reason = msg.get("reasoning_content", "")
        if reason and not content:
            content = reason
    except (KeyError, IndexError, TypeError):
        return ""
    return clean_llm_content(content)
