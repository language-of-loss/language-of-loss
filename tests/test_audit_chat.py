import csv
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import audit_chat as A

DOC = Path(__file__).resolve().parents[1] / "docs" / "audit_prompts.md"
PASSAGES = [dict(passage_id="AP-1", lang="hi", passage_text="माँ को गए पाँच बरस हो गए।"),
            dict(passage_id="AP-2", lang="en", passage_text="My father passed away last spring."),
            dict(passage_id="AP-3", lang="en", passage_text="I still set two cups of tea.")]


class Mock(A.Provider):
    name, model = "mock", "mock-1"

    def __init__(self, rating='{"rating": 5}', refuse=()):
        self.calls, self.rating, self.refuse = [], rating, set(refuse)

    def complete(self, user, schema=None, kind="reply"):
        self.calls.append((kind, schema, user))
        meta = dict(served_model="mock-1", stop_reason="end_turn", usage={})
        if any(r in user for r in self.refuse):
            return None, dict(meta, stop_reason="refusal")
        return (self.rating if kind == "rating" else "I'm so sorry for your loss."), meta


def write_passages(tmp_path, rows=PASSAGES):
    path = tmp_path / "passages.csv"
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["passage_id", "lang", "passage_text"])
        w.writeheader()
        w.writerows(rows)
    return path


def test_dry_run_three_passages(tmp_path):
    mock = Mock()
    scores, replies = A.run(PASSAGES, mock, tmp_path / "cache", tmp_path / "log.jsonl")
    assert len(mock.calls) == 3 * 2 * 2 and len(scores) == len(replies) == 6
    assert {(s["passage_id"], s["cue"]) for s in scores} == {(p["passage_id"], c) for p in PASSAGES for c in A.CUES}
    assert all(s["rating"] == 5 and s["system"] == "mock:mock-1" for s in scores)
    hi = [u for k, s, u in mock.calls if "माँ" in u]
    assert all("पढ़िए" in u or "साझा" in u for u in hi) and sum("भारत में है" in u for u in hi) == 2
    assert all((s is not None) == (k == "rating") for k, s, _ in mock.calls)
    log = [json.loads(line) for line in open(tmp_path / "log.jsonl")]
    assert len(log) == 12 and {x["culture_cue"] for x in log} == {True, False}
    assert all(x["prompt_hash"] and x["date"] and x["model_requested"] == "mock-1" for x in log)
    text = (tmp_path / "log.jsonl").read_text()
    assert "माँ" not in text and "sorry" not in text
    A.run(PASSAGES, mock, tmp_path / "cache", tmp_path / "log.jsonl")
    assert len(mock.calls) == 12


def test_cue_changes_prompt_and_hash():
    with_cue = A.build_prompt("rating", "en", "india", "X")
    assert "Context: the writer is in India." in with_cue and "India" not in A.build_prompt("rating", "en", "none", "X")
    assert A.prompt_hash("reply", "hi", "india") != A.prompt_hash("reply", "hi", "none")


def test_refusal_and_invalid_rating(tmp_path):
    scores, replies = A.run(PASSAGES[1:2], Mock(refuse=["passed away"]), tmp_path / "c", tmp_path / "l.jsonl")
    assert all(s["rating"] == "" and s["stop_reason"] == "refusal" for s in scores)
    with pytest.raises(ValueError):
        A.run(PASSAGES[:1], Mock(rating='{"rating": 9}'), tmp_path / "c2", tmp_path / "l2.jsonl")
    assert not list((tmp_path / "c2").glob("*.json"))


def test_guard_plan_and_cost(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("LLM_MODEL", "model-a")
    path = write_passages(tmp_path, PASSAGES * 2)
    with pytest.raises(SystemExit) as e:
        A.main(["--passages", str(path), "--cache-dir", str(tmp_path / "c")])
    assert "--confirm" in str(e.value)
    out = capsys.readouterr().out
    assert "6 passages x 2 prompts x 2 cue conditions x 1 sample(s) = 24 requests" in out and "cost estimate" in out
    pl = A.plan(PASSAGES, "model-a", 2, tmp_path / "c", "api", "medium", price=(4.0, 20.0))
    assert pl["requests"] == 24 and pl["to_send"] == 24 and pl["cost_estimate_usd"] > 0
    A.main(["--passages", str(path), "--plan-only", "--cache-dir", str(tmp_path / "c")])


@pytest.mark.skipif(not DOC.exists(), reason="docs/audit_prompts.md is not in the public release")
def test_prompts_are_documented_verbatim():
    doc = DOC.read_text(encoding="utf-8")
    for lang, p in A.PROMPTS.items():
        assert p["rating"] in doc and p["reply"] in doc and p["cue"].rstrip() in doc, lang


def api_env(monkeypatch, create):
    sdk = SimpleNamespace(__version__="0.0", Client=lambda api_key: SimpleNamespace(beta=SimpleNamespace(
        messages=SimpleNamespace(create=create))))
    monkeypatch.setitem(sys.modules, "fake_llm_sdk", sdk)
    for k, v in (("LLM_PROVIDER", "fake_llm_sdk"), ("LLM_MODEL", "model-a"), ("LLM_API_KEY", "test-key-not-real")):
        monkeypatch.setenv(k, v)


def test_api_request_shape(monkeypatch):
    resp = SimpleNamespace(model="model-a", stop_reason="end_turn", _request_id="r",
                           usage=SimpleNamespace(input_tokens=1, output_tokens=1, iterations=[]),
                           content=[SimpleNamespace(type="text", text='{"rating": 4}')])
    sent = {}
    api_env(monkeypatch, lambda **k: sent.update(k) or resp)
    p = A.ApiProvider(fallbacks=False)
    text, meta = p.complete("U", A.RATING_SCHEMA, "rating")
    assert text == '{"rating": 4}' and "system" not in sent and "fallbacks" not in sent
    assert sent["output_config"]["format"]["schema"] == A.RATING_SCHEMA and sent["max_tokens"] == 2000
    p._api.fallbacks = True
    sent.clear()
    p.complete("U", None, "reply")
    assert sent["fallbacks"] == "default" and "format" not in sent["output_config"]
