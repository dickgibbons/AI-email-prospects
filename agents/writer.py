"""WriterAgent — calls Claude to generate the next touch email for a prospect."""

from __future__ import annotations

import json
import logging
import re

import anthropic

from config import settings, prompts

log = logging.getLogger(__name__)


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


def generate_touch(prospect: dict, research: dict) -> dict:
    """Generate subject + body for the next touch.

    Returns dict with keys: subject, body.
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    user_prompt = prompts.build_generate_user_prompt(prospect, research)

    response = client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=8192,
        system=prompts.GENERATE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    text = response.content[0].text if response.content else ""
    result = _parse_json_response(text)

    if not result.get("subject") or not result.get("body"):
        log.warning(
            "Generate returned incomplete output for %s (touch %d)",
            prospect.get("name"),
            prospect.get("lastTouchSent", 0) + 1,
        )
        if not result.get("subject"):
            result["subject"] = f"Following up — {prospect.get('company', '')}"
        if not result.get("body"):
            result["body"] = text[:2000]

    touch_num = prospect.get("lastTouchSent", 0) + 1
    log.info(
        "Generated touch %d for %s at %s",
        touch_num,
        prospect.get("name"),
        prospect.get("company"),
    )
    return result
