import csv
import json
from argparse import Namespace
from pathlib import Path

import pandas as pd
import pytest

import train_muril_pair as M

SRC = Path(M.__file__).read_text(encoding="utf-8")


def test_goemotions_label_grief_or_sadness():
    assert M.goemotions_label("16") == 1 and M.goemotions_label("2,25") == 1
    assert M.goemotions_label([27]) == 0 and M.goemotions_label("9,24") == 0


def test_grouped_folds_never_split_a_text():
    rows = [dict(id=f"t{g}#{i}", group=f"t{g}") for g in range(12) for i in range(g % 4 + 1)]
    fold_of = M.grouped_folds(rows, 5, seed=1)
    by_group = {}
    for r in rows:
        by_group.setdefault(r["group"], set()).add(fold_of[r["id"]])
    assert all(len(f) == 1 for f in by_group.values())
    assert set(fold_of.values()) == set(range(5))
    assert fold_of == M.grouped_folds(rows, 5, seed=1)


def test_equal_size_and_matched_prevalence():
    native = [dict(id=f"n{i}", label=int(i < 30)) for i in range(100)]
    translated = [dict(id=f"t{i}", label=int(i < 400)) for i in range(1000)]
    nat, tr = M.equal_size_pair(native, translated, seed=3)
    assert len(nat) == len(tr) == 100
    assert sum(r["label"] for r in nat) == sum(r["label"] for r in tr) == 30


def test_equal_size_cuts_to_smaller_pool():
    native = [dict(id=f"n{i}", label=i % 2) for i in range(500)]
    translated = [dict(id=f"t{i}", label=i % 3 == 0) for i in range(120)]
    nat, tr = M.equal_size_pair(native, translated, seed=3)
    assert len(nat) == len(tr) == 80
    assert sum(r["label"] for r in nat) == sum(r["label"] for r in tr) == 40


def test_matched_sample_fills_shortfall_from_other_class():
    pool = [dict(id=i, label=int(i < 5)) for i in range(50)]
    s = M.matched_sample(pool, 20, 0.5, seed=0)
    assert len(s) == 20 and sum(r["label"] for r in s) == 5


def test_translation_cache_is_used_before_the_translator(tmp_path):
    cache = tmp_path / "tr.jsonl"
    cache.write_text(json.dumps(dict(id="a", en_sha256=M.sha("I miss her"), hi="मुझे उसकी याद आती है")) + "\n",
                     encoding="utf-8")
    calls = []

    def fake(texts):
        calls.append(list(texts))
        return [f"HI:{t}" for t in texts]

    rows = [dict(id="a", text="I miss her", label=1), dict(id="b", text="ok then", label=0)]
    out, n_cached, n_new = M.translate_pool(rows, cache, fake)
    assert (n_cached, n_new) == (1, 1) and calls == [["ok then"]]
    assert out[0]["text"] == "मुझे उसकी याद आती है" and out[1]["text"] == "HI:ok then"
    _, n_cached, n_new = M.translate_pool(rows, cache, fake)
    assert (n_cached, n_new) == (2, 0) and len(calls) == 1


def test_smoke_outputs_never_use_the_real_file_names(tmp_path):
    smoke, real = M.output_paths(True, tmp_path), M.output_paths(False, tmp_path)
    assert real["translated"].name == "muril_translated_predictions.csv"
    assert real["native"].name == "muril_native_predictions.csv"
    assert all(smoke[m] != real[m] and smoke[m].parent.name == "smoke" for m in M.OUTPUTS)


def test_no_external_service_in_the_script():
    for banned in ("api_client", "requests", "urllib", "httpx", "googletrans", "deep_translator"):
        assert f"import {banned}" not in SRC and f"from {banned}" not in SRC
    assert M.NLLB["revision"] and M.MURIL["revision"]


def test_same_configuration_for_both_models():
    assert SRC.count("train_fn(") == 1


def _fixture(tmp_path):
    bdir = tmp_path / "brighter"
    bdir.mkdir()
    for split, n in (("train", 40), ("dev", 20)):
        pd.DataFrame(dict(id=[f"{split}{i}" for i in range(n)], text=[f"वाक्य {i}" for i in range(n)],
                          sadness=[i % 3 == 0 for i in range(n)])).astype({"sadness": int}).to_parquet(
            bdir / f"{split}-00000-of-00001.parquet")
    gdir = tmp_path / "goemo"
    gdir.mkdir()
    (gdir / "train.tsv").write_text("".join(f"sentence {i}\t{25 if i % 2 == 0 else 27}\tg{i}\n" for i in range(60)),
                                    encoding="utf-8")
    clauses = tmp_path / "clauses.jsonl"
    gold = tmp_path / "a1_gold.csv"
    with open(clauses, "w", encoding="utf-8") as fh, open(gold, "w", encoding="utf-8", newline="") as gh:
        w = csv.writer(gh)
        w.writerow(["clause_id", "emotional"])
        for t in range(10):
            for i in range(3):
                cid = f"blogs:b{t}#{i:04d}"
                fh.write(json.dumps(dict(record_id=f"blogs:b{t}", clause_id=cid, lang="hi", clause_text="x")) + "\n")
                w.writerow([cid, (t + i) % 2])
        fh.write(json.dumps(dict(record_id="blogs:e", clause_id="blogs:e#0001", lang="en", clause_text="y")) + "\n")
        w.writerow(["blogs:e#0001", 1])
    return bdir, gdir, clauses, gold


def _args(tmp_path, **kw):
    bdir, gdir, clauses, gold = _fixture(tmp_path)
    base = dict(gold=str(gold), clauses=str(clauses), brighter=str(bdir), goemotions=str(gdir),
                translation_cache=str(tmp_path / "cache.jsonl"), channels=str(tmp_path / "ch"),
                manifest=str(tmp_path / "manifest.json"), only="both", folds=5, seed=1, device="cpu", model="",
                smoke=False)
    base.update(kw)
    return Namespace(**base)


def test_real_run_predicts_every_hindi_gold_clause_held_out(tmp_path):
    seen = []

    def fake_train(train_rows, eval_rows, cfg, seed, device, spec):
        train_ids = {r["id"] for r in train_rows}
        assert not train_ids & {r["id"] for r in eval_rows}
        assert {r.get("group") for r in train_rows if "group" in r}.isdisjoint({r["group"] for r in eval_rows})
        seen.append((len(train_rows), cfg["epochs"]))
        return {r["id"]: 1 for r in eval_rows}

    args = _args(tmp_path)
    man = M.run(args, train_fn=fake_train, translator=lambda ts: [f"HI {t}" for t in ts])
    for m, name in M.OUTPUTS.items():
        rows = list(csv.DictReader(open(Path(args.channels) / name, encoding="utf-8")))
        assert len(rows) == 30 and {r["pred"] for r in rows} == {"1"}
        assert list(rows[0]) == ["clause_id", "pred"]
    for f in man["folds"]:
        assert f["translated"]["n_train"] == f["native"]["n_train"]
        assert f["translated"]["positive_share"] == pytest.approx(f["native"]["positive_share"], abs=0.02)
    assert all(e == 3 for _, e in seen) and "DRY RUN" not in man["status"]


def test_real_run_refuses_without_gold(tmp_path):
    args = _args(tmp_path, gold=str(tmp_path / "missing.csv"))
    with pytest.raises(SystemExit, match="not found"):
        M.run(args, train_fn=lambda *a: {})


def test_smoke_without_gold_is_brighter_only_and_a_dry_run(tmp_path):
    args = _args(tmp_path, gold=str(tmp_path / "missing.csv"), smoke=True, only="native")
    man = M.run(args, train_fn=lambda tr, ev, cfg, *a: {r["id"]: 0 for r in ev})
    assert man["status"].startswith("DRY RUN") and man["config"]["epochs"] == 1
    assert man["folds"][0]["native"]["n_train"] == 40
    assert not (Path(args.channels) / "muril_native_predictions.csv").exists()
    assert (Path(args.channels) / "smoke" / "muril_native_predictions_smoke.csv").exists()


TINY = "hf-internal-testing/tiny-random-BertForSequenceClassification"


def test_train_predict_runs_end_to_end_on_cpu_with_a_tiny_model():
    from huggingface_hub import try_to_load_from_cache
    if not isinstance(try_to_load_from_cache(TINY, "config.json"), str):
        pytest.skip("tiny test model not in the local Hugging Face cache")
    rows = [dict(id=str(i), text=f"word {i}", label=i % 2) for i in range(8)]
    out = M.train_predict(rows, rows[:4], dict(M.CONFIG, epochs=1, batch=4), 0, "cpu", dict(repo=TINY, revision=None))
    assert set(out) == {"0", "1", "2", "3"} and set(out.values()) <= {0, 1}
