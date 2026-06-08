"""LLM 호출 + 안전한 JSON 파싱 헬퍼.

버그1 수정: 검증된 현재 모델 문자열 사용 (claude-sonnet-4-6).
버그2 수정: LLM이 ```json 펜스나 설명을 붙여도 안 깨지는 파서.
"""
import json
import re
from langchain_anthropic import ChatAnthropic

# 검증된 현재 모델 (2026): 협상·큐레이션 품질/비용 균형이 좋은 Sonnet 4.6.
# 더 어려운 추론이 필요하면 "claude-opus-4-8" 로 교체.
MODEL = "claude-sonnet-4-6"

_llm = ChatAnthropic(model=MODEL, max_tokens=2000, temperature=0.3)


def ask_llm(prompt: str) -> str:
    """단발 프롬프트 → 텍스트 응답."""
    return _llm.invoke(prompt).content


def ask_llm_json(prompt: str, fallback=None):
    """LLM에게 JSON을 받되, 펜스/설명이 섞여도 안전하게 파싱.

    1) 전체를 그대로 파싱 시도
    2) 실패하면 ```json ... ``` 블록 추출
    3) 그래도 실패하면 첫 [ 또는 { 부터 매칭되는 끝까지 추출
    4) 끝내 실패하면 fallback 반환 (그래프가 안 죽게)
    """
    raw = _llm.invoke(prompt).content.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    fence = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except json.JSONDecodeError:
            pass

    match = re.search(r"(\[.*\]|\{.*\})", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    return fallback if fallback is not None else []
