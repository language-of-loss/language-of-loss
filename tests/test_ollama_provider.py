import csv
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import audit_chat as A
from providers import ollama as O

TAG = "llama3.1:8b-instruct-q4_K_M"
PASSAGES = [dict(passage_id="AP-1", lang="hi", passage_text="माँ को गए पाँच बरस हो गए।"),
            dict(passage_id="AP-2", lang="en", passage_text="My father passed away last spring.")]


class FakeOllama:
    def __init__(self, digest="a" * 64, rating='{"rating": 6}'):
        self.digest, self.rating, self.bodies = digest, rating, []
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, obj):
                data = json.dumps(obj).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                if self.path == "/api/version":
                    self._send({"version": "0.40.2"})
                elif self.path == "/api/tags":
                    self._send({"models": [{"name": TAG, "digest": fake.digest, "details": {"family": "llama"}}]})

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                fake.bodies.append(body)
                text = fake.rating if "format" in body else "मुझे आपके नुकसान का बहुत दुख है।"
                self._send({"message": {"role": "assistant", "content": text}, "done": True, "done_reason": "stop",
                            "prompt_eval_count": 40, "eval_count": 12, "total_duration": 5, "eval_duration": 3})

        self.server = HTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()


@pytest.fixture
def fake():
    f = FakeOllama()
    yield f
    f.close()


def test_loopback_only():
    for ok in ("http://127.0.0.1:11434", "http://localhost:11434", "http://[::1]:11434", "http://127.8.8.8"):
        assert O.is_loopback(ok)
    for bad in ("http://10.0.0.5:11434", "http://example.com", "https://ollama.com", "http://0.0.0.0:11434", ""):
        assert not O.is_loopback(bad)
        with pytest.raises(SystemExit, match="loopback"):
            O.OllamaProvider(host=bad)


def test_interface_and_request_shape(fake):
    p = A.OllamaProvider(model=TAG, host=fake.url)
    assert p.name == "ollama" and p.version() == "ollama 0.40.2"
    assert p.model_id == f"{TAG}@sha256:{'a' * 64}"
    text, meta = p.complete("U", A.RATING_SCHEMA, "rating")
    assert A.parse_rating(text) == 6
    assert set(meta) >= {"served_model", "stop_reason", "request_id", "usage", "fallback"}
    assert meta["served_model"] == p.model_id and meta["usage"]["input_tokens"] == 40
    body = fake.bodies[-1]
    assert body["messages"] == [{"role": "user", "content": "U"}]
    assert body["format"] == A.RATING_SCHEMA and body["stream"] is False
    assert body["options"]["num_predict"] == O.MAX_TOKENS["rating"] and body["options"]["temperature"] == 0
    p.complete("U", None, "reply")
    assert "format" not in fake.bodies[-1] and fake.bodies[-1]["options"]["num_predict"] == O.MAX_TOKENS["reply"]
    assert O.MAX_TOKENS["reply"] < A.MAX_TOKENS["reply"]


def test_proxy_settings_are_ignored(fake, monkeypatch):
    for v in ("HTTP_PROXY", "http_proxy", "ALL_PROXY"):
        monkeypatch.setenv(v, "http://203.0.113.9:3128")
    monkeypatch.delenv("NO_PROXY", raising=False)
    monkeypatch.delenv("no_proxy", raising=False)
    p = A.OllamaProvider(model=TAG, host=fake.url)
    assert p.complete("U")[0]


def test_model_not_pulled(fake):
    with pytest.raises(SystemExit, match="not pulled"):
        A.OllamaProvider(model="gemma3:4b", host=fake.url)


def test_run_caches_by_digest_and_logs_like_api(fake, tmp_path):
    p = A.OllamaProvider(model=TAG, host=fake.url)
    scores, replies = A.run(PASSAGES, p, tmp_path / "c", tmp_path / "log.jsonl", effort="none")
    assert len(scores) == len(replies) == 4 and len(fake.bodies) == 8
    files = list((tmp_path / "c").glob("*.json"))
    assert len(files) == 8
    key = json.loads(files[0].read_text())["key"]
    assert key["model"] == p.cache_model and key["model"].startswith(p.model_id + "|gen:") and len(key["passage_sha256"]) == 64 and key["cue"] in A.CUES
    A.run(PASSAGES, p, tmp_path / "c", tmp_path / "log.jsonl", effort="none")
    assert len(fake.bodies) == 8
    new = FakeOllama(digest="b" * 64)
    try:
        A.run(PASSAGES, A.OllamaProvider(model=TAG, host=new.url), tmp_path / "c", tmp_path / "log.jsonl",
              effort="none")
        assert len(new.bodies) == 8
    finally:
        new.close()
    other = A.OllamaProvider(model=TAG, host=fake.url, max_tokens={"rating": 2000, "reply": 512})
    assert other.cache_model != p.cache_model
    A.run(PASSAGES[:1], other, tmp_path / "c", tmp_path / "log.jsonl", effort="none")
    assert len(fake.bodies) == 12
    lines = [json.loads(x) for x in (tmp_path / "log.jsonl").read_text().splitlines()]
    assert all("passage_text" not in x and "text" not in x for x in lines)

    class Mock(A.Provider):
        name, model = "mock", "m"

        def complete(self, user, schema=None, kind="reply"):
            return ('{"rating": 3}' if kind == "rating" else "ok"), dict(served_model="m", stop_reason="end_turn")
    A.run(PASSAGES[:1], Mock(), tmp_path / "m", tmp_path / "mlog.jsonl")
    mock_keys = set(json.loads((tmp_path / "mlog.jsonl").read_text().splitlines()[0]))
    assert set(lines[0]) == mock_keys


def test_scores_file_keeps_other_systems(tmp_path):
    path = tmp_path / "scores.csv"
    A.write_csv(path, [dict(passage_id="AP-1", system="commercial_llm_A", cue="none", rating=5)],
                A.SCORE_COLUMNS)
    A.write_csv(path, [dict(passage_id="AP-1", system=f"ollama:{TAG}", cue="none", rating=6)], A.SCORE_COLUMNS)
    A.write_csv(path, [dict(passage_id="AP-1", system=f"ollama:{TAG}", cue="none", rating=7)], A.SCORE_COLUMNS)
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    assert sorted((r["system"], r["rating"]) for r in rows) == [("commercial_llm_A", "5"),
                                                                (f"ollama:{TAG}", "7")]


def test_main_local_needs_no_cost_and_uses_audit_cache(fake, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(O, "DEFAULT_HOST", fake.url)
    pas = tmp_path / "p.csv"
    with open(pas, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["passage_id", "lang", "passage_text"])
        w.writeheader()
        w.writerows(PASSAGES)
    monkeypatch.setitem(A.DEFAULT_CACHE, "ollama", tmp_path / "audit" / "chat")
    orig = O.OllamaProvider.__init__

    def init(self, model=TAG, host=None, **kw):
        orig(self, model=model, host=fake.url, **kw)
    monkeypatch.setattr(O.OllamaProvider, "__init__", init)
    A.main(["--provider", "ollama", "--passages", str(pas), "--limit", "2", "--log", str(tmp_path / "l.jsonl"),
            "--scores-out", str(tmp_path / "s.csv"), "--replies-out", str(tmp_path / "proc" / "r.csv")])
    out = capsys.readouterr().out
    assert "cost: none (local model)" in out and "nothing leaves this machine" in out
    assert len(list((tmp_path / "audit" / "chat").glob("*.json"))) == 8
    assert all(json.loads(x)["effort"] == "none" for x in (tmp_path / "l.jsonl").read_text().splitlines())


@pytest.mark.skipif(os.environ.get("OLLAMA_LIVE") != "1", reason="live check: OLLAMA_LIVE=1 with the model pulled")
def test_live_local_server():
    p = A.OllamaProvider()
    text, meta = p.complete(A.build_prompt("rating", "en", "none", "My father died last year."), A.RATING_SCHEMA,
                            "rating")
    assert A.parse_rating(text) in range(1, 8) and meta["served_model"].startswith(O.DEFAULT_MODEL + "@sha256:")
