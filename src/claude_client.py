import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

import anthropic

DEFAULT_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = int(os.environ.get("CLAUDE_MAX_TOKENS", "32768"))

_client = None
_totals = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}


class TruncatedOutputError(RuntimeError):
    """The response hit max_tokens. Retrying the same request would truncate again."""


def save_debug(label: str, text: str) -> Path:
    """Persist a raw model response so a paid-for call is never lost."""
    debug_dir = Path(os.environ.get("CLAUDE_DEBUG_DIR", "output/debug"))
    debug_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9]+", "_", label or "call").strip("_")
    path = debug_dir / f"{datetime.now():%Y%m%d_%H%M%S}_{slug}.txt"
    path.write_text(text, encoding="utf-8")
    return path


def get_model() -> str:
    # Read at call time, not import time: extract.py sets CLAUDE_MODEL from the
    # --model flag after this module has already been imported.
    return os.environ.get("CLAUDE_MODEL") or DEFAULT_MODEL


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


def reset_totals() -> None:
    for k in _totals:
        _totals[k] = 0


def print_totals() -> None:
    t = _totals
    print(
        f"[total] tokens — in={t['input']} out={t['output']} "
        f"cache_read={t['cache_read']} cache_write={t['cache_write']}"
    )


def call(system: list, messages: list, label: str = "", max_retries: int = 3) -> str:
    client = get_client()
    last_error = None
    last_raw = None
    for attempt in range(max_retries):
        try:
            with client.messages.stream(
                model=get_model(),
                max_tokens=MAX_TOKENS,
                system=system,
                messages=messages,
            ) as stream:
                text = stream.get_final_text()
                response = stream.get_final_message()
            # Count tokens for every completed call, including ones that fail below.
            _record_usage(response.usage, label)
            last_raw = text
            if response.stop_reason == "max_tokens":
                path = save_debug(label, text)
                raise TruncatedOutputError(
                    f"{label or 'Call'}: output hit the {MAX_TOKENS}-token limit and was cut off "
                    f"(raw response saved to {path}). Raise CLAUDE_MAX_TOKENS and re-run."
                )
            text = _strip_fences(text)
            json.loads(text)
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
    if last_raw is not None and isinstance(last_error, ValueError):
        path = save_debug(label, last_raw)
        print(f"Last raw response saved to {path}")
    raise last_error
