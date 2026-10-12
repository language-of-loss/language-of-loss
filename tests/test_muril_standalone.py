import csv
from pathlib import Path

import pytest

import train_muril_pair as P
import train_muril_standalone as S

TINY = dict(repo="hf-internal-testing/tiny-random-BertForSequenceClassification", revision=None)


def test_pools_match_size_and_share_and_reuse_the_translation_cache(tmp_path, monkeypatch):
    native = [dict(id=f"b{i}", text=f"हिंदी {i}", label=int(i < 3), split="train") for i in range(10)]
    english = [dict(id=f"g{i}", text=f"sentence {i}", label=int(i % 5 == 0)) for i in range(100)]
    monkeypatch.setattr(P, "load_brighter", lambda d: native)
    monkeypatch.setattr(P, "load_goemotions", lambda d: english)
    args = type("A", (), dict(brighter="", goemotions="", seed=1, only="both",
                              translation_cache=str(tmp_path / "cache.jsonl")))()
    monkeypatch.setattr(P, "NllbTranslator", lambda *a, **k: (lambda texts: [f"hi:{t}" for t in texts]))
    nat, tr, info = S.pools(args)
    assert len(tr) == len(nat) == 10 and sum(r["label"] for r in tr) == 3
    assert info["n_translated"] == 10 and all(r["text"].startswith("hi:") for r in tr)
    _, _, info2 = S.pools(args)
    assert info2["n_translated"] == 0 and info2["n_cached"] == 10


def test_fit_saves_checkpoint_and_log(tmp_path):
    try:
        from transformers import AutoTokenizer
        AutoTokenizer.from_pretrained(TINY["repo"], local_files_only=True)
    except Exception:
        pytest.skip("tiny test model not cached")
    rows = [dict(id=f"x{i}", text=f"word {i}", label=i % 2) for i in range(8)]
    cfg = dict(P.CONFIG, epochs=1, batch=4)
    res = S.fit(rows, cfg, 1, "cpu", tmp_path / "m", model_spec=TINY)
    log = list(csv.DictReader(open(tmp_path / "m" / "training_log.csv")))
    assert res["steps"] == 2 and len(log) == 2 and (tmp_path / "m" / "config.json").exists()
    ids = list(csv.DictReader(open(tmp_path / "m" / "train_ids.csv")))
    assert [r["id"] for r in ids] == [r["id"] for r in rows] and "text" not in ids[0]


def test_same_configuration_as_the_pair():
    src = Path(S.__file__).read_text()
    assert "P.CONFIG" in src and "P.MURIL" in src and "api_client" not in src
