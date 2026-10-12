import numpy as np

import audit_models as A

SPEC = dict(key="fake", repo="org/fake", revision="0" * 40, window=8)
TEXTS = [("r:1", "hi", "x"), ("r:2", "en", "y"), ("r:3", "en", "z")]


def fetch(spec):
    return "/nowhere", {"model.bin": "abc"}


def scores(fail_at=None):
    def gen(local, spec, texts, dev):
        for k, (rid, lang, _) in enumerate(texts):
            if k == fail_at:
                raise RuntimeError("out of memory")
            yield rid, lang, ["A", "B"], np.array([0.7, 0.3]), np.array([1.0, 0.0]), 1, 5
    return gen


def test_complete_model_keeps_all_rows():
    entry, rows = A.run_model(SPEC, TEXTS, "cpu", fetch, scores())
    assert entry["status"] == "ok" and len(rows) == 3 and rows[0]["top_label"] == "A"


def test_failure_part_way_discards_the_model_rows():
    entry, rows = A.run_model(SPEC, TEXTS, "cpu", fetch, scores(fail_at=2))
    assert entry["status"] == "failed" and rows == [] and entry["n_scored_before_failure"] == 2


def test_audit_mode_caches_by_text_and_model_hash(tmp_path):
    calls = []

    def scorer(local, spec, texts, dev):
        calls.append([t[0] for t in texts])
        for rid, lang, _ in texts:
            yield rid, lang, ["A", "B"], np.array([0.6, 0.4]), np.array([1.0, 0.0]), 1, 3
    texts = [("p1", "hi", "पहला"), ("p2", "en", "second")]
    spec = dict(SPEC, model_sha256="a" * 64)
    fn = A.cached(tmp_path, scorer)
    assert [r[0] for r in fn(None, spec, texts, "cpu")] == ["p1", "p2"] and fn.n_scored == 2
    fn = A.cached(tmp_path, scorer)
    list(fn(None, spec, texts, "cpu"))
    assert fn.n_cached == 2 and fn.n_scored == 0 and len(calls) == 1
    list(A.cached(tmp_path, scorer)(None, dict(spec, model_sha256="b" * 64), texts, "cpu"))
    list(A.cached(tmp_path, scorer)(None, spec, texts + [("p3", "en", "third")], "cpu"))
    assert calls[1:] == [["p1", "p2"], ["p3"]]
    stored = list(tmp_path.rglob("*.json"))
    assert stored and all("पहला" not in p.read_text(encoding="utf-8") for p in stored)
    assert A.model_hash({"b": "2", "a": "1"}) == A.model_hash({"a": "1", "b": "2"})
