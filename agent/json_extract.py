"""
Robust JSON extraction from Claude text blocks.
Claude sometimes prepends prose before a ```json ... ``` fence — handle all variants.
"""
import json
import re


def extract_json(text: str) -> dict | None:
    """
    Try to extract a JSON object from a Claude text response.
    Handles:
      1. Bare JSON (no prose, no fences)
      2. ```json ... ``` fence anywhere in text
      3. ``` ... ``` fence anywhere in text
      4. First {...} JSON object found anywhere in text
    Returns parsed dict or None.
    """
    text = text.strip()

    # 1. Bare JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Extract from ```json ... ``` or ``` ... ``` fences (anywhere in text)
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1))
        except json.JSONDecodeError:
            pass

    # 3. Find the first {...} spanning the rest of the text
    brace_start = text.find("{")
    if brace_start != -1:
        depth = 0
        for i, ch in enumerate(text[brace_start:], start=brace_start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[brace_start : i + 1])
                    except json.JSONDecodeError:
                        break

    return None
