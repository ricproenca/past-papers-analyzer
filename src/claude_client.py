import json
import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path

import anthropic

DEFAULT_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = int(os.environ.get("CLAUDE_MAX_TOKENS", "32768"))

_client = None
_client_lock = threading.Lock()
_local = threading.local()          # token totals are per thread, so parallel papers don't mix
_temperature_rejected = False       # set when the model refuses a temperature parameter


class TruncatedOutputError(RuntimeError):
    """The response hit max_tokens. Retrying the same request would truncate again."""


def _totals() -> dict:
    if not hasattr(_local, "totals"):
        _local.totals = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
    return _local.totals


def save_debug(label: str, text: str) -> Path:
    """Persist a raw model response so a paid-for call is never lost."""
    debug_dir = Path(os.environ.get("CLAUDE_DEBUG_DIR", "output/debug"))
    debug_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9]+", "_", label or "call").strip("_")
    path = debug_dir / f"{datetime.now():%Y%m%d_%H%M%S_%f}_{slug}.txt"
    path.write_text(text, encoding="utf-8")
    return path


def get_model() -> str:
    # Read at call time, not import time: extract.py sets CLAUDE_MODEL from the
    # --model flag after this module has already been imported.
    return os.environ.get("CLAUDE_MODEL") or DEFAULT_MODEL


def get_temperature() -> float | None:
    """Sampling temperature, or None to use the API default (what we do by default).

    Measured on one paper, temperature 0 made the model trim context sentences from
    questions (3 of 3 runs) while the API default kept the text intact (2 of 2 runs),
    so the parameter is opt-in: set CLAUDE_TEMPERATURE=<number> to force it."""
    raw = os.environ.get("CLAUDE_TEMPERATURE", "").strip().lower()
    if _temperature_rejected or raw in ("", "none", "off"):
        return None
    return float(raw)


def get_client() -> anthropic.Anthropic:
    global _client
    with _client_lock:
        if _client is None:
            _client = anthropic.Anthropic()
        return _client


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _record_usage(usage, label: str, quiet: bool = False) -> None:
    inp = usage.input_tokens or 0
    out = usage.output_tokens or 0
    cr = getattr(usage, "cache_read_input_tokens", None) or 0
    cw = getattr(usage, "cache_creation_input_tokens", None) or 0
    t = _totals()
    t["input"] += inp
    t["output"] += out
    t["cache_read"] += cr
    t["cache_write"] += cw
    if not quiet:
        tag = f"[{label}]" if label else "[call]"
        print(f"{tag} tokens — in={inp} out={out} cache_read={cr} cache_write={cw}")


def reset_totals() -> None:
    for k in _totals():
        _totals()[k] = 0


def print_totals() -> None:
    t = _totals()
    print(
        f"[total] tokens — in={t['input']} out={t['output']} "
        f"cache_read={t['cache_read']} cache_write={t['cache_write']}"
    )


def _params(system: list, messages: list) -> dict:
    params = {"model": get_model(), "max_tokens": MAX_TOKENS, "system": system, "messages": messages}
    temperature = get_temperature()
    if temperature is not None:
        params["temperature"] = temperature
    return params


def _is_server_error(e: Exception) -> bool:
    """5xx / overloaded errors (also raised mid-stream): transient, worth a retry."""
    return isinstance(e, anthropic.APIStatusError) and (
        (getattr(e, "status_code", 0) or 0) >= 500 or "overloaded" in str(e).lower())


def _is_temperature_error(e: Exception) -> bool:
    return isinstance(e, anthropic.BadRequestError) and "temperature" in str(e).lower()


def _parse_json_response(text: str, stop_reason: str | None, label: str) -> str:
    """Validate one model response and return the clean JSON text."""
    if stop_reason == "max_tokens":
        path = save_debug(label, text)
        raise TruncatedOutputError(
            f"{label or 'Call'}: output hit the {MAX_TOKENS}-token limit and was cut off "
            f"(raw response saved to {path}). Raise CLAUDE_MAX_TOKENS and re-run."
        )
    text = _strip_fences(text)
    json.loads(text)
    return text


def call(system: list, messages: list, label: str = "", max_retries: int = 3) -> str:
    global _temperature_rejected
    client = get_client()
    last_error = None
    last_raw = None
    for attempt in range(max_retries):
        try:
            with client.messages.stream(**_params(system, messages)) as stream:
                text = stream.get_final_text()
                response = stream.get_final_message()
            # Count tokens for every completed call, including ones that fail below.
            _record_usage(response.usage, label)
            last_raw = text
            return _parse_json_response(text, response.stop_reason, label)
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
        except anthropic.BadRequestError as e:
            if _is_temperature_error(e) and not _temperature_rejected:
                _temperature_rejected = True
                print("Model rejected the temperature parameter; continuing without it.")
                last_error = e
                continue
            raise
        except anthropic.APIStatusError as e:
            if not _is_server_error(e):
                raise
            last_error = e
            wait = 2 ** attempt
            print(f"Server error, retrying in {wait}s... ({e})")
            time.sleep(wait)
    if last_raw is not None and isinstance(last_error, ValueError):
        path = save_debug(label, last_raw)
        print(f"Last raw response saved to {path}")
    raise last_error


def call_batch(requests: dict, label: str = "Batch", poll_seconds: float = 30.0, batch_id: str | None = None) -> dict:
    """Run many (system, messages) requests through the Message Batches API
    (half price, completes asynchronously).

    `requests` maps a custom id (letters, digits, '_' and '-') to (system, messages).
    Returns {id: json_text | Exception}; one failed item never fails the others.
    With `batch_id`, nothing is submitted: that existing batch is polled and its
    results collected (results stay available for 29 days), so an interrupted run
    can be resumed without paying again. A connection error while polling is retried."""
    client = get_client()
    if batch_id:
        batch = client.messages.batches.retrieve(batch_id)
        print(f"[{label}] resuming batch {batch.id} ({batch.processing_status})")
    else:
        batch = client.messages.batches.create(requests=[
            {"custom_id": cid, "params": _params(system, messages)}
            for cid, (system, messages) in requests.items()
        ])
        print(f"[{label}] batch {batch.id} submitted with {len(requests)} request(s); polling every {poll_seconds:g}s...")
    while batch.processing_status != "ended":
        time.sleep(poll_seconds)
        try:
            batch = client.messages.batches.retrieve(batch.id)
        except anthropic.APIConnectionError as e:
            print(f"[{label}] connection error while polling batch {batch.id}, still waiting... ({e})")
            continue
        c = batch.request_counts
        print(f"[{label}] {batch.processing_status}: {c.succeeded} succeeded, {c.processing} processing, "
              f"{c.errored} errored, {c.expired} expired")

    results: dict = {}
    for entry in client.messages.batches.results(batch.id):
        cid, result = entry.custom_id, entry.result
        if cid not in requests:
            continue                          # a resumed batch may hold papers not asked for now
        if result.type != "succeeded":
            detail = getattr(getattr(result, "error", None), "error", None) or getattr(result, "error", None) or result.type
            results[cid] = RuntimeError(f"batch request {result.type}: {detail}")
            continue
        message = result.message
        _record_usage(message.usage, f"{label} {cid}", quiet=True)
        text = "".join(b.text for b in message.content if getattr(b, "type", "") == "text")
        try:
            results[cid] = _parse_json_response(text, message.stop_reason, f"{label} {cid}")
        except (json.JSONDecodeError, TruncatedOutputError) as e:
            if isinstance(e, json.JSONDecodeError):
                path = save_debug(f"{label} {cid}", text)
                e = ValueError(f"Claude returned invalid JSON: {e} (raw response saved to {path})")
            results[cid] = e
    print_totals()
    return results
