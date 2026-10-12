import csv
import json
import sys
from types import SimpleNamespace

import pytest

import llm_coder as L
from gold import CODEBOOK, SHEET_COLUMNS

ANSWER = {f: v[0] for f, v in CODEBOOK.items()} | {"notes": ""}


def rows():
    base = dict.fromkeys(SHEET_COLUMNS, "")
    return [dict(base, gold_id="GRF-a", lang="hi", context_before="पहले", clause_text="मुझे उनकी याद आती है",
                 span_text="मुझे उनकी याद आती है ।", context_after="बाद"),
            dict(base, gold_id="GRF-b", lang="en", context_before="", clause_text="I miss her", span_text="I miss her.",
                 context_after="")]


class Fake(L.Provider):
    name, model = "fake", "fake-1"

    def __init__(self, answer=ANSWER):
        self.calls, self.answer = [], answer

    def code(self, system, user, schema):
        self.calls.append(user)
        return dict(self.answer), dict(served_model="fake-1", stop_reason="end_turn", usage={})


def test_schema_enums_are_the_codebook():
    s = L.output_schema()
    assert s["additionalProperties"] is False and set(s["required"]) == set(CODEBOOK) | {"notes"}
    assert all(s["properties"][f]["enum"] == list(v) for f, v in CODEBOOK.items())


def test_clause_goes_untranslated_with_context():
    msg = L.user_message(rows()[0])
    assert "मुझे उनकी याद आती है" in msg and "पहले" in msg and "Hindi (Devanagari)" in msg
    assert "(none)" in L.user_message(rows()[1])


def test_run_fills_schema_caches_and_logs(tmp_path):
    fake = Fake()
    out = L.run(rows(), fake, "SYSTEM", tmp_path / "cache", tmp_path / "log.jsonl", effort="medium")
    assert [list(r) for r in out] == [SHEET_COLUMNS] * 2 and out[0]["orientation"] == "I"
    assert len(fake.calls) == 2
    L.run(rows(), fake, "SYSTEM", tmp_path / "cache", tmp_path / "log.jsonl", effort="medium")
    assert len(fake.calls) == 2
    log = [json.loads(line) for line in open(tmp_path / "log.jsonl")]
    assert [x["cache_hit"] for x in log] == [False, False, True, True]
    assert {x["prompt_hash"] for x in log} == {L.sha("SYSTEM")} and all(x["date"] for x in log)
    assert "याद" not in (tmp_path / "log.jsonl").read_text()
    L.run(rows(), fake, "SYSTEM v2", tmp_path / "cache", tmp_path / "log.jsonl", effort="medium")
    assert len(fake.calls) == 4


def test_out_of_codebook_answer_is_rejected_and_not_cached(tmp_path):
    bad = Fake(dict(ANSWER, orientation="X"))
    with pytest.raises(ValueError):
        L.run(rows()[:1], bad, "S", tmp_path / "cache", tmp_path / "log.jsonl")
    assert not list((tmp_path / "cache").glob("*.json"))


def test_main_gold_sheets_are_refused(tmp_path):
    for name in ("gold_sheet_v1_coder1.csv", "gold_components_v1.csv"):
        with pytest.raises(SystemExit):
            L.main(["--in", str(tmp_path / name), "--out", str(tmp_path / "o.csv")])


class StubMessages:
    def __init__(self, response):
        self.kwargs, self.response = None, response

    def create(self, **kwargs):
        self.kwargs = kwargs
        return self.response


def response(stop="end_turn", text=None, fallback=False, model="model-a"):
    iterations = [SimpleNamespace(type="fallback_message")] if fallback else []
    return SimpleNamespace(model=model, stop_reason=stop, _request_id="req_1",
                           stop_details=SimpleNamespace(category="bio") if stop == "refusal" else None,
                           usage=SimpleNamespace(input_tokens=10, output_tokens=5, iterations=iterations),
                           content=[SimpleNamespace(type="text", text=text or json.dumps(ANSWER))])


def api_env(monkeypatch, messages):
    sdk = SimpleNamespace(__version__="0.0", Client=lambda api_key: SimpleNamespace(beta=SimpleNamespace(
        messages=messages)))
    monkeypatch.setitem(sys.modules, "fake_llm_sdk", sdk)
    for k, v in (("LLM_PROVIDER", "fake_llm_sdk"), ("LLM_MODEL", "model-a"), ("LLM_API_KEY", "test-key-not-real")):
        monkeypatch.setenv(k, v)


def provider(monkeypatch, resp, temperature=None):
    stub = StubMessages(resp)
    api_env(monkeypatch, stub)
    return L.ApiProvider(effort="medium", temperature=temperature), stub


def test_api_request_shape(monkeypatch):
    p, stub = provider(monkeypatch, response())
    answer, meta = p.code("SYS", "USER", L.output_schema())
    k = stub.kwargs
    assert k["model"] == "model-a" and "cache_control" not in k
    assert k["system"] == [{"type": "text", "text": "SYS", "cache_control": {"type": "ephemeral"}}]
    assert k["output_config"]["format"]["type"] == "json_schema" and k["output_config"]["effort"] == "medium"
    assert k["fallbacks"] == "default" and k["betas"] == ["server-side-fallback-2026-07-01"]
    assert "extra_body" not in k and not p.temperature_sent
    assert answer == ANSWER and meta["served_model"] == "model-a" and meta["fallback"] is False


def test_temperature_sent_only_when_given(monkeypatch):
    p, stub = provider(monkeypatch, response(), temperature=0.0)
    p.code("S", "U", L.output_schema())
    assert stub.kwargs["extra_body"] == {"temperature": 0.0} and p.temperature_sent


def test_refusal_and_fallback_are_recorded(monkeypatch, tmp_path):
    p, _ = provider(monkeypatch, response(stop="refusal"))
    answer, meta = p.code("S", "U", L.output_schema())
    assert answer is None and meta["refusal_category"] == "bio"
    p, _ = provider(monkeypatch, response(fallback=True, model="model-b"))
    out = L.run(rows()[:1], p, "S", tmp_path / "c", tmp_path / "log.jsonl")
    assert out[0]["notes"].startswith("[served by fallback model-b]")
    logged = (tmp_path / "log.jsonl").read_text() + "".join(x.read_text() for x in (tmp_path / "c").iterdir())
    assert "test-key-not-real" not in logged


@pytest.mark.parametrize("missing", ["LLM_PROVIDER", "LLM_MODEL", "LLM_API_KEY"])
def test_missing_setting_stops(monkeypatch, missing):
    api_env(monkeypatch, StubMessages(response()))
    monkeypatch.delenv(missing)
    with pytest.raises(SystemExit, match=missing):
        L.ApiProvider()


class NoAnswer(L.Provider):
    name, model = "fake", "fake-1"

    def code(self, system, user, schema):
        return None, dict(served_model="fake-1", stop_reason="refusal", usage={})


def test_unanswered_row_does_not_inherit_the_input_codes(tmp_path):
    filled = [dict(r, **{f: v[-1] for f, v in CODEBOOK.items()}) for r in rows()]
    out = L.run(filled, NoAnswer(), "S", tmp_path / "cache", tmp_path / "log.jsonl")
    assert all(r[f] == "" for r in out for f in CODEBOOK)
    assert out[0]["clause_text"] == filled[0]["clause_text"] and "no answer" in out[0]["notes"]


def test_plan_counts_cache_hits_and_sends_nothing(tmp_path):
    pl = L.plan(rows(), "SYSTEM", "fake", "fake-1", "medium", tmp_path / "cache")
    assert (pl["requests"], pl["cached"], pl["to_send"]) == (2, 0, 2) and pl["cost_estimate_usd"] is None
    L.run(rows()[:1], Fake(), "SYSTEM", tmp_path / "cache", tmp_path / "log.jsonl", effort="medium")
    pl = L.plan(rows(), "SYSTEM", "fake", "fake-1", "medium", tmp_path / "cache")
    assert (pl["cached"], pl["to_send"]) == (1, 1)
    priced = L.plan(rows(), "SYSTEM", "api", "model-a", "medium", tmp_path / "cache", price=(4.0, 20.0))
    assert priced["to_send"] == 2 and priced["cost_estimate_usd"] > 0


def _third_fixture(tmp_path):
    ctx_cols = ["gold_id", "lang", "context_before", "clause_text", "span_text", "context_after"]
    ctx = tmp_path / "ctx.csv"
    with open(ctx, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=ctx_cols + ["orientation", "target"])
        w.writeheader()
        w.writerow(dict(gold_id="GRF-a", lang="hi", context_before="पहले", clause_text="मुझे उनकी याद आती है",
                        span_text="", context_after="बाद", orientation="", target=""))
    dis = tmp_path / "dis.csv"
    with open(dis, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["gold_id", "lang", "field", "coder1", "coder2", "clause_text"])
        w.writeheader()
        w.writerow(dict(gold_id="GRF-a", lang="hi", field="orientation", coder1="CODERONE", coder2="CODERTWO"))
        w.writerow(dict(gold_id="GRF-a", lang="hi", field="target", coder1="CODERONE", coder2="CODERTWO"))
    return {"codebook": (dis, ctx)}


def test_third_coder_is_blind_and_asks_only_disagreeing_fields(tmp_path):
    items = L.third_items(_third_fixture(tmp_path))
    assert len(items) == 1 and items[0]["fields"] == ["orientation", "target"]
    assert "CODERONE" not in json.dumps(items) and "CODERTWO" not in json.dumps(items)
    s = L.third_schema(items[0])
    assert set(s["required"]) == {"orientation", "target", "notes"} and s["properties"]["target"]["enum"] == \
        CODEBOOK["target"]
    fake = Fake({"orientation": "F", "target": "kin", "notes": ""})
    out = L.run_third(items, fake, {"codebook": "S"}, tmp_path / "c", tmp_path / "log.jsonl", effort="medium")
    assert [(r["field"], r["third"]) for r in out] == [("orientation", "F"), ("target", "kin")]
    assert "CODER" not in fake.calls[0] and "orientation, target" in fake.calls[0]
    assert "याद" not in (tmp_path / "log.jsonl").read_text()
    L.run_third(items, fake, {"codebook": "S"}, tmp_path / "c", tmp_path / "log.jsonl", effort="medium")
    assert len(fake.calls) == 1


def test_components_system_lists_every_gloss():
    s = L.components_system()
    assert "FEEL_BAD" in s and "this someone feels something bad" in s and "EVERYONE" in s
