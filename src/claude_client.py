import json
import os
import re
import time

import anthropic

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
MAX_TOKENS = int(os.environ.get("CLAUDE_MAX_TOKENS", "32768"))

_client = None
_totals = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _record_usage(usage, label: str) -> None:
    inp = usage.input_tokens or 0
    out = usage.output_tokens or 0
    cr = getattr(usage, "cache_read_input_tokens", None) or 0
    cw = getattr(usage, "cache_creation_input_tokens", None) or 0
    _totals["input"] += inp
    _totals["output"] += out
    _totals["cache_read"] += cr
    _totals["cache_write"] += cw
    tag = f"[{label}]" if label else "[call]"
    print(f"{tag} tokens — in={inp} out={out} cache_read={cr} cache_write={cw}")


def print_totals() -> None:
    t = _totals
    print(
        f"[total] tokens — in={t['input']} out={t['output']} "
        f"cache_read={t['cache_read']} cache_write={t['cache_write']}"
    )


def call(system: list, messages: list, label: str = "", max_retries: int = 3) -> str:
    client = get_client()
    last_error = None
    for attempt in range(max_retries):
        try:
            with client.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=messages,
            ) as stream:
                text = stream.get_final_text()
                response = stream.get_final_message()
            text = _strip_fences(text)
            json.loads(text)
            _record_usage(response.usage, label)
            return text
        except (anthropic.RateLimitError, anthropic.APIConnectionError) as e:
            last_error = e
            wait = 2 ** attempt
            kind = "Rate limited" if isinstance(e, anthropic.RateLimitError) else "Connection error"
            print(f"{kind}, retrying in {wait}s... ({e})")
            time.sleep(wait)
        except json.JSONDecodeError as e:
            last_error = ValueError(f"Claude returned invalid JSON: {e}")
            wait = 2 ** attempt
            print(f"Invalid JSON, retrying in {wait}s... ({e})")
            time.sleep(wait)
    raise last_error
