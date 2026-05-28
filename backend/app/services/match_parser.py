"""Extract the structured `{matches: [...]}` JSON block the LLM appends to its answer.

The system prompt (see `prompts.py`) instructs the model to conclude its answer
with a fenced ```json``` block containing a `matches` array. The model is
mostly reliable, but it can:

  - drop the fence and emit raw JSON
  - emit extra prose around the JSON
  - put the JSON mid-answer instead of at the end

We accept all three. Anything we can't parse cleanly we leave as a no-op
(empty list + unmodified answer) — the caller still has `sources` to fall
back on for the matches sidebar.
"""
from __future__ import annotations

import json
import logging
import re
from typing import List, Tuple

from backend.app.models.api import Match

logger = logging.getLogger(__name__)

_FENCED_JSON_RE = re.compile(r"```json\s*([\s\S]*?)```", re.IGNORECASE)


def extract_matches(answer: str) -> Tuple[str, List[Match]]:
    """Pull the matches JSON out of an LLM answer.

    Returns `(cleaned_answer, matches)`. `cleaned_answer` has the JSON block
    removed so it can be shown to the user directly. `matches` is the parsed
    list (empty if nothing parseable was found).
    """
    if not answer:
        return answer, []

    span, payload = _find_json_payload(answer)
    if span is None or payload is None:
        return answer, []

    parsed = _safe_json_loads(payload)
    if not isinstance(parsed, dict):
        return answer, []

    raw_matches = parsed.get("matches")
    if not isinstance(raw_matches, list):
        return answer, []

    matches = _coerce_matches(raw_matches)

    start, end = span
    cleaned = (answer[:start] + answer[end:]).strip()
    return cleaned, matches


def _find_json_payload(answer: str) -> Tuple[Tuple[int, int] | None, str | None]:
    """Locate the matches JSON in the answer. Returns (span, payload_text)."""
    fenced = _FENCED_JSON_RE.search(answer)
    if fenced:
        return (fenced.start(), fenced.end()), fenced.group(1)

    # No fence — find the last "matches" key, then walk back to its enclosing
    # brace and forward to the matching close brace.
    lower = answer.lower()
    key_idx = lower.rfind('"matches"')
    if key_idx == -1:
        return None, None

    open_idx = answer.rfind("{", 0, key_idx)
    if open_idx == -1:
        return None, None

    close_idx = _matching_brace(answer, open_idx)
    if close_idx == -1:
        return None, None

    return (open_idx, close_idx + 1), answer[open_idx : close_idx + 1]


def _matching_brace(text: str, open_idx: int) -> int:
    depth = 0
    for i in range(open_idx, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _safe_json_loads(payload: str):
    try:
        return json.loads(payload)
    except json.JSONDecodeError as e:
        logger.debug("match JSON payload was not valid JSON: %s", e)
        return None


def _coerce_matches(raw: list) -> List[Match]:
    matches: List[Match] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        # Must have at least a title or company to be worth showing.
        title = _str_or_none(item.get("title"))
        company = _str_or_none(item.get("company"))
        if not (title or company):
            continue

        try:
            matches.append(
                Match(
                    title=title or company or "Opportunity",
                    company=company,
                    requirements=_coerce_str_list(item.get("requirements")),
                    score=_clamp_score(item.get("score")),
                    source_file=_str_or_none(item.get("source_file")),
                    document_id=_str_or_none(item.get("document_id")),
                )
            )
        except Exception as e:
            logger.debug("skipping malformed match entry: %s", e)
    return matches


def _str_or_none(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _coerce_str_list(v) -> List[str]:
    if not isinstance(v, list):
        return []
    out: List[str] = []
    for x in v:
        if x is None:
            continue
        s = str(x).strip()
        if s:
            out.append(s)
    return out


def _clamp_score(v) -> int:
    try:
        n = int(round(float(v)))
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, n))
