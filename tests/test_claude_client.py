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
    assert c._totals() == {"input": 20, "output": 10, "cache_read": 0, "cache_write": 4}
    c.reset_totals()
    assert set(c._totals().values()) == {0}


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


# --- temperature -------------------------------------------------------------------

@pytest.fixture
def temp_state(monkeypatch):
    monkeypatch.setattr(c, "_temperature_rejected", False)
    monkeypatch.delenv("CLAUDE_TEMPERATURE", raising=False)


def test_temperature_is_opt_in(fake_client, monkeypatch, temp_state):
    calls = fake_client(FakeStream("{}"), FakeStream("{}"), FakeStream("{}"))
    c.call([], [])
    assert "temperature" not in calls[0]                       # API default unless asked
    monkeypatch.setenv("CLAUDE_TEMPERATURE", "0.3")
    c.call([], [])
    assert calls[1]["temperature"] == 0.3
    monkeypatch.setenv("CLAUDE_TEMPERATURE", "none")
    c.call([], [])
    assert "temperature" not in calls[2]


def test_model_that_rejects_temperature_is_retried_without_it(fake_client, monkeypatch, temp_state):
    err = anthropic.BadRequestError("`temperature` is not supported for this model",
                                    response=httpx.Response(400, request=httpx.Request("POST", "http://x")), body=None)
    monkeypatch.setenv("CLAUDE_TEMPERATURE", "0.5")
    calls = fake_client(err, FakeStream('{"ok": 1}'), FakeStream("{}"))
    assert c.call([], []) == '{"ok": 1}'
    assert "temperature" in calls[0] and "temperature" not in calls[1]
    c.call([], [])
    assert "temperature" not in calls[2]                 # remembered for later calls


def test_other_bad_requests_are_not_swallowed(fake_client, temp_state):
    err = anthropic.BadRequestError("prompt is too long", response=httpx.Response(400, request=httpx.Request("POST", "http://x")), body=None)
    fake_client(err)
    with pytest.raises(anthropic.BadRequestError):
        c.call([], [])


# --- per-thread totals -----------------------------------------------------------------

def test_totals_are_per_thread(fake_client):
    import threading
    fake_client(FakeStream("{}"), FakeStream("{}"))
    c.call([], [])
    seen = {}

    def worker():
        seen["before"] = dict(c._totals())
        c.call([], [])
        seen["after"] = dict(c._totals())

    t = threading.Thread(target=worker); t.start(); t.join()
    assert set(seen["before"].values()) == {0}                       # a new thread starts at zero
    assert seen["after"]["input"] == 10 and c._totals()["input"] == 10   # and does not touch this thread's total


# --- Batch API ------------------------------------------------------------------------

def _entry(cid, text=None, stop="end_turn", rtype="succeeded", error=None):
    usage = types.SimpleNamespace(input_tokens=100, output_tokens=40, cache_read_input_tokens=0, cache_creation_input_tokens=0)
    if rtype == "succeeded":
        msg = types.SimpleNamespace(content=[types.SimpleNamespace(type="text", text=text)], usage=usage, stop_reason=stop)
        return types.SimpleNamespace(custom_id=cid, result=types.SimpleNamespace(type=rtype, message=msg))
    return types.SimpleNamespace(custom_id=cid, result=types.SimpleNamespace(type=rtype, error=error))


class FakeBatches:
    def __init__(self, entries, polls_until_done=2):
        self.entries, self.polls, self.created = entries, polls_until_done, None
        self.counts = types.SimpleNamespace(succeeded=0, processing=1, errored=0, expired=0)

    def _batch(self, status):
        return types.SimpleNamespace(id="batch_1", processing_status=status, request_counts=self.counts)

    def create(self, requests):
        self.created = requests
        return self._batch("in_progress")

    def retrieve(self, batch_id):
        self.polls -= 1
        return self._batch("ended" if self.polls <= 0 else "in_progress")

    def results(self, batch_id):
        return iter(self.entries)


def _install_batches(monkeypatch, entries):
    monkeypatch.setattr(c.time, "sleep", lambda s: None)
    c.reset_totals()
    batches = FakeBatches(entries)
    monkeypatch.setattr(c, "_client", types.SimpleNamespace(messages=types.SimpleNamespace(batches=batches)))
    return batches


def test_call_batch_collects_results_per_request(monkeypatch, debug_dir, temp_state):
    batches = _install_batches(monkeypatch, [
        _entry("a", '```json\n{"x": 1}\n```'),
        _entry("b", '{"cut": ', stop="max_tokens"),
        _entry("c", "not json"),
        _entry("d", rtype="errored", error="overloaded"),
        _entry("e", rtype="expired"),
    ])
    reqs = {k: ([{"type": "text", "text": "sys"}], [{"role": "user", "content": k}]) for k in "abcde"}
    out = c.call_batch(reqs, label="B", poll_seconds=0)

    assert out["a"] == '{"x": 1}'
    assert isinstance(out["b"], c.TruncatedOutputError)
    assert isinstance(out["c"], ValueError) and "invalid JSON" in str(out["c"])
    assert isinstance(out["d"], RuntimeError) and "overloaded" in str(out["d"])
    assert isinstance(out["e"], RuntimeError) and "expired" in str(out["e"])
    created = batches.created
    assert [r["custom_id"] for r in created] == list("abcde")
    assert created[0]["params"]["model"] == c.get_model() and "temperature" not in created[0]["params"]
    assert c._totals()["input"] == 300                                  # three completed responses were counted
    assert len(list(debug_dir.iterdir())) == 2                            # truncated + invalid JSON were saved


def _status_error(status, message):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return anthropic.APIStatusError(message, response=httpx.Response(status, request=request), body=None)


def test_server_errors_are_retried(fake_client):
    calls = fake_client(_status_error(529, "Overloaded"), _status_error(500, "boom"), FakeStream('{"ok": 1}'))
    assert c.call([], []) == '{"ok": 1}' and len(calls) == 3


def test_client_errors_are_not_retried(fake_client):
    calls = fake_client(_status_error(403, "forbidden"), FakeStream("{}"))
    with pytest.raises(anthropic.APIStatusError):
        c.call([], [])
    assert len(calls) == 1


def test_call_batch_can_resume_an_existing_batch(monkeypatch, temp_state):
    batches = _install_batches(monkeypatch, [_entry("a", '{"x": 1}'), _entry("other_paper", '{"y": 2}')])
    out = c.call_batch({"a": ([], [])}, label="B", poll_seconds=0, batch_id="batch_1")
    assert out == {"a": '{"x": 1}'} and batches.created is None        # nothing submitted, unrelated ids ignored


def test_call_batch_survives_a_connection_error_while_polling(monkeypatch, temp_state):
    batches = _install_batches(monkeypatch, [_entry("a", '{"x": 1}')])
    real, state = batches.retrieve, {"failed": False}

    def flaky(batch_id):
        if not state["failed"]:
            state["failed"] = True
            raise anthropic.APIConnectionError(request=httpx.Request("GET", "https://api.anthropic.com"))
        return real(batch_id)
    batches.retrieve = flaky
    assert c.call_batch({"a": ([], [])}, label="B", poll_seconds=0) == {"a": '{"x": 1}'}
