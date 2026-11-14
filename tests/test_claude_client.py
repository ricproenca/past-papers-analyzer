import types

import anthropic
import httpx
import pytest

from src import claude_client as c


class FakeStream:
    def __init__(self, text, stop="end_turn"):
        self.text, self.stop = text, stop

    def __enter__(self): return self
    def __exit__(self, *a): return False
    def get_final_text(self): return self.text

    def get_final_message(self):
        usage = types.SimpleNamespace(input_tokens=10, output_tokens=5,
                                      cache_read_input_tokens=None, cache_creation_input_tokens=2)
        return types.SimpleNamespace(usage=usage, stop_reason=self.stop)


@pytest.fixture
def fake_client(monkeypatch):
    """Install a client whose successive stream() calls yield the given items
    (a FakeStream, or an exception to raise)."""
    monkeypatch.setattr(c.time, "sleep", lambda s: None)
    c.reset_totals()

    def install(*script):
        calls = []
        items = list(script)

        def stream(**kwargs):
            calls.append(kwargs)
            item = items.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

        monkeypatch.setattr(c, "_client", types.SimpleNamespace(messages=types.SimpleNamespace(stream=stream)))
        return calls
    return install


@pytest.mark.parametrize("raw", ['{"a": 1}', '```json\n{"a": 1}\n```', '```\n{"a": 1}\n```', '  {"a": 1}  '])
def test_strip_fences(raw):
    assert c._strip_fences(raw) == '{"a": 1}'


def test_model_is_read_at_call_time(monkeypatch):
    monkeypatch.delenv("CLAUDE_MODEL", raising=False)
    assert c.get_model() == c.DEFAULT_MODEL
    monkeypatch.setenv("CLAUDE_MODEL", "other-model")
    assert c.get_model() == "other-model"


def test_call_uses_model_and_returns_clean_json(fake_client, monkeypatch):
    monkeypatch.setenv("CLAUDE_MODEL", "other-model")
    calls = fake_client(FakeStream('```json\n{"ok": true}\n```'))
    assert c.call([], [], label="T") == '{"ok": true}'
    assert len(calls) == 1 and calls[0]["model"] == "other-model"


def test_usage_is_accumulated_and_reset(fake_client):
    fake_client(FakeStream("{}"), FakeStream("{}"))
    c.call([], []); c.call([], [])
    assert c._totals == {"input": 20, "output": 10, "cache_read": 0, "cache_write": 4}
    c.reset_totals()
    assert set(c._totals.values()) == {0}


def test_truncated_output_is_not_retried_and_is_saved(fake_client, debug_dir):
    calls = fake_client(FakeStream('{"a": 1', stop="max_tokens"))
    with pytest.raises(c.TruncatedOutputError, match="CLAUDE_MAX_TOKENS"):
        c.call([], [], label="Phase 1+2")
    assert len(calls) == 1
    (saved,) = debug_dir.glob("*Phase_1_2.txt")
    assert saved.read_text() == '{"a": 1'


def test_invalid_json_retries_then_saves_last_response(fake_client, debug_dir):
    calls = fake_client(*[FakeStream("not json") for _ in range(3)])
    with pytest.raises(ValueError, match="invalid JSON"):
        c.call([], [], label="J")
    assert len(calls) == 3
    assert [p.read_text() for p in debug_dir.glob("*_J.txt")] == ["not json"]


def test_invalid_json_then_success(fake_client):
    calls = fake_client(FakeStream("oops"), FakeStream('{"ok": 1}'))
    assert c.call([], []) == '{"ok": 1}' and len(calls) == 2


def test_connection_error_is_retried(fake_client):
    err = anthropic.APIConnectionError(request=httpx.Request("POST", "http://x"))
    calls = fake_client(err, err, FakeStream("{}"))
    assert c.call([], []) == "{}" and len(calls) == 3


def test_gives_up_after_max_retries(fake_client):
    err = anthropic.APIConnectionError(request=httpx.Request("POST", "http://x"))
    calls = fake_client(err, err)
    with pytest.raises(anthropic.APIConnectionError):
        c.call([], [], max_retries=2)
    assert len(calls) == 2
