import json
import re
from collections import Counter

import pytest

import reader_kit as K

LOSS = ["parent", "parent", "parent", "grandparent", "spouse", "sibling", "child", "other"]


def synthetic_passages(per_lang=150, texts=37):
    out, loss = [], {}
    for lang in ("hi", "en"):
        for i in range(per_lang):
            rec = f"blogs:{lang}{i % texts:02d}"
            loss[rec] = LOSS[(i % texts) % len(LOSS)]
            out.append(dict(passage_id=f"AP-{lang}{i:03d}", lang=lang, record_id=rec, register="long",
                            passage_text=f"(synthetic {lang} {i})"))
    return out, loss


def test_ten_blocks_of_fifteen_plus_fifteen_each_passage_once():
    passages, loss = synthetic_passages()
    rows = K.assign_blocks(passages, loss)
    assert len(rows) == 300 and len({r["passage_id"] for r in rows}) == 300
    for b in range(1, 11):
        blk = [r for r in rows if r["block"] == b]
        assert Counter(r["lang"] for r in blk) == {"hi": 15, "en": 15}
        assert sorted(r["position"] for r in blk) == list(range(1, 31))


def test_relationship_balanced_across_blocks():
    passages, loss = synthetic_passages()
    rows = K.assign_blocks(passages, loss)
    for lang in ("hi", "en"):
        for lt in set(loss.values()):
            per_block = [sum(1 for r in rows if r["block"] == b and r["lang"] == lang and r["loss_type"] == lt)
                         for b in range(1, 11)]
            assert max(per_block) - min(per_block) <= 1, (lang, lt, per_block)


def test_texts_spread_over_blocks():
    passages, loss = synthetic_passages()
    rows = K.assign_blocks(passages, loss)
    worst = max(Counter((r["block"], r["record_id"]) for r in rows).values())
    assert worst <= 2


def test_seed_fixes_assignment_and_order_is_shuffled():
    passages, loss = synthetic_passages()
    a, b = K.assign_blocks(passages, loss, seed=7), K.assign_blocks(passages, loss, seed=7)
    assert [(r["block"], r["position"], r["passage_id"]) for r in a] == \
           [(r["block"], r["position"], r["passage_id"]) for r in b]
    c = K.assign_blocks(passages, loss, seed=8)
    assert [r["passage_id"] for r in a] != [r["passage_id"] for r in c]
    first = [r for r in a if r["block"] == 1]
    langs = "".join(r["lang"][0] for r in sorted(first, key=lambda r: r["position"]))
    assert langs not in ("h" * 15 + "e" * 15, "e" * 15 + "h" * 15)


def test_wrong_passage_count_refuses():
    passages, loss = synthetic_passages(per_lang=140)
    with pytest.raises(SystemExit):
        K.assign_blocks(passages, loss)


def cache(dir_, passages, ratings, model, cues=("none", "india"), kinds=("reply", "rating")):
    dir_.mkdir(parents=True, exist_ok=True)
    for p, rating in zip(passages, ratings):
        for cue in cues:
            for kind in kinds:
                text = json.dumps({"rating": rating if cue == "none" else 1}) if kind == "rating" \
                    else f"reply to {p['passage_id']} ({cue})"
                key = dict(provider="x", model=model, passage_id=p["passage_id"], kind=kind, cue=cue, sample=0)
                (dir_ / f"{p['passage_id']}-{cue}-{kind}.json").write_text(json.dumps(dict(key=key, text=text,
                                                                     meta={"served_model": model + "@served"})))


def test_replies_span_rating_range_no_cue_only(tmp_path):
    passages, _ = synthetic_passages(per_lang=20)
    hi = [p for p in passages if p["lang"] == "hi"]
    en = [p for p in passages if p["lang"] == "en"]
    local = tmp_path / "local"
    cache(local, hi, [1 + i % 7 for i in range(20)], "llama@sha")
    cache(local, en, [2 + i % 5 for i in range(20)], "llama@sha")
    rows, shortfall, sources = K.select_replies(passages, [("api", tmp_path / "none"), ("ollama", local)])
    assert not shortfall and sources == {"hi": "ollama", "en": "ollama"}
    assert [r["exchange_id"] for r in rows] == [f"R{i:02d}" for i in range(1, 11)]
    for lang, lo, hi_ in (("hi", 1, 7), ("en", 2, 6)):
        rr = [r for r in rows if r["lang"] == lang]
        assert len(rr) == 5 and len({r["passage_id"] for r in rr}) == 5
        got = [r["model_rating"] for r in rr]
        assert min(got) == lo and max(got) == hi_ and len(set(got)) >= 4
    assert all(r["cue"] == "none" and "(none)" in r["reply"] for r in rows)
    assert all(r["system"] == "ollama:llama" and r["served_model"] == "llama@sha@served" for r in rows)


def test_api_cache_preferred_and_shortfall_reported(tmp_path):
    passages, _ = synthetic_passages(per_lang=20)
    hi = [p for p in passages if p["lang"] == "hi"]
    api, local = tmp_path / "api", tmp_path / "local"
    cache(api, hi[:6], [2, 3, 4, 5, 6, 7], "model-a")
    cache(local, hi, [4] * 20, "llama@sha")
    rows, shortfall, sources = K.select_replies(passages, [("api", api), ("ollama", local)])
    assert sources["hi"] == "api" and all(r["system"] == "api:model-a" for r in rows)
    assert shortfall == {"en": 5} and sources["en"] is None


def test_india_cue_or_unrated_passages_never_chosen(tmp_path):
    passages, _ = synthetic_passages(per_lang=10)
    hi = [p for p in passages if p["lang"] == "hi"]
    local = tmp_path / "local"
    cache(local, hi[:5], [3] * 5, "m", cues=("india",))
    cache(local, hi[5:], [3] * 5, "m", kinds=("reply",))
    rows, shortfall, _ = K.select_replies(passages, [("ollama", local)])
    assert rows == [] and shortfall == {"hi": 5, "en": 5}


def test_forms_script_embeds_valid_json_and_template_is_empty(tmp_path):
    passages, loss = synthetic_passages()
    blocks = K.assign_blocks(passages, loss)
    replies = [dict(exchange_id="R01", passage_id="AP-hi000", passage_text="(p)", reply="(r)")]
    text = "# I\n\n## Part 1: passages\n\nrate 1-7\n\n## Part 2: replies\n\nrate 1-5\n"
    gs = K.forms_script(blocks, replies, "consent", text)
    data = json.loads(re.search(r"var KIT = (.*?);\n\nvar CONSENT_ITEM", gs, re.S).group(1))
    assert len(data["blocks"]) == 10 and all(len(v) == 30 for v in data["blocks"].values())
    assert data["blocks"]["3"][6]["code"] == "B03-07"
    assert data["instructions"] == {"passages": "rate 1-7", "replies": "rate 1-5"}
    assert K.DATA_MARK in K.TEMPLATE.read_text(encoding="utf-8")
    bad = tmp_path / "t.gs"
    bad.write_text("var KIT = null;")
    with pytest.raises(SystemExit):
        K.forms_script(blocks, replies, "", text, template=bad)


def test_kit_files_with_text_are_ignored_and_pages_tracked():
    import subprocess
    root = K.ROOT
    for f in ("blocks.csv", "block_assignment.csv", "replies.csv", "make_reader_forms.gs", "kit_manifest.json"):
        assert subprocess.run(["git", "check-ignore", "-q", f"docs/reader_study/{f}"], cwd=root).returncode == 0, f
    for f in ("consent.md", "instructions.md", "recruitment.md"):
        assert subprocess.run(["git", "check-ignore", "-q", f"docs/reader_study/{f}"], cwd=root).returncode == 1, f
    for f in ("readers/x.csv", "reader_ratings.csv", "reader_reply_ratings.csv", "a1_gold.csv"):
        assert subprocess.run(["git", "check-ignore", "-q", f"data/annotation/{f}"], cwd=root).returncode == 0, f
