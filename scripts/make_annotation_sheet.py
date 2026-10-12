import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from griefcorpus.ids import annotation_id
CLEAN = ROOT / "data" / "clean"
OUT_TXT = ROOT / "data" / "annotation" / "texts"
SEED = 20260919
HINDI_SIDE = {"devanagari_hindi", "romanized_hindi", "mixed_hi_en"}

REVIEW_FIELDS = ["language_script", "message_type", "eligible_primary", "deceased_relation", "time_since_death",
                 "addressee", "personal_distress", "collective_coping", "continuing_bonds",
                 "responsibility_to_survivors", "indirect_death_reference", "authors_own_prose_span", "notes"]


def load(name):
    p = CLEAN / f"{name}.jsonl"
    return [json.loads(l) for l in p.open(encoding="utf-8")] if p.exists() else []


def seed_ids():
    ids = set()
    for r in csv.DictReader((ROOT / "docs" / "seed_corpus.csv").open(encoding="utf-8")):
        sid = r["source_record_id"]
        ids.add("york_" + sid.split()[-1] if sid.startswith("Respondent") else sid)
    return ids


def capped(records, per_thread, per_author, k, rng):
    rng.shuffle(records)
    th, au, out = Counter(), Counter(), []
    for r in records:
        if len(out) >= k:
            break
        if r["thread_id"] and th[r["thread_id"]] >= per_thread:
            continue
        if r["author_group"] and au[r["author_group"]] >= per_author:
            continue
        th[r["thread_id"]] += 1
        au[r["author_group"]] += 1
        out.append(r)
    return out


def main():
    registry_p = ROOT / "data" / "annotation" / "released_annotation_ids.csv"
    released = {r["record_id"]: r["annotation_id"] for r in csv.DictReader(registry_p.open(encoding="utf-8"))} if registry_p.exists() else {}
    append = "--append" in sys.argv
    if released and not append:
        sys.exit(f"Sheet is frozen ({len(released)} released IDs). Use --append to add new records without renumbering.")
    rng = random.Random(SEED)
    seeds = seed_ids()
    picks = []

    def add(recs, stratum, note):
        for r in recs:
            picks.append((r, stratum, note))

    blogs = [r for r in load("blogs") if r["source_record_id"] not in seeds]
    el = [r for r in blogs if r["eligibility_status"] == "provisionally_eligible" and "over_cap" not in r["flags"]]
    add(el, "blogs_provisionally_eligible", "census of eligible, non-seed, within domain/author caps")
    add([r for r in blogs if r["eligibility_status"].startswith("secondary_")], "blogs_contrast_types",
        "all non-disclosure contrast pages (poetry, tribute, advice, templates, translation, obituary)")

    yt = [r for r in load("ytcv") if r["n_words"] >= 4]
    add(capped([r for r in yt if r["lang_provisional"] in HINDI_SIDE], 15, 2, 80, rng), "ytcv_hindi_side",
        "all Hindi-side screen hits up to caps (15/video, 2/commenter)")
    add(capped([r for r in yt if r["lang_provisional"] == "english"], 5, 2, 80, rng), "ytcv_english",
        "random 80 English screen hits (5/video, 2/commenter)")

    rd = [r for r in load("reddit_confessions") if "focus_early" in r["flags"] and r["n_words"] <= 1500]
    add(rng.sample(rd, 60), "reddit_en_focus_early", "random 60 of early-match posts <=1500 words")

    add([r for r in load("hinemo9") if r["source_record_id"] not in seeds], "hinemo9_all", "all non-seed screen hits")
    yk = [r for r in load("york_survey") if r["source_record_id"] not in seeds and r["n_words"] >= 100]
    add(rng.sample(yk, 20), "york_reference_en", "random 20 respondents with >=100 words")

    rng.shuffle(picks)
    OUT_TXT.mkdir(parents=True, exist_ok=True)
    sheet_fields = (["annotation_id", "source_genre", "thread_context", "n_words_machine", "text_or_excerpt", "full_text_path"]
                    + [f"r1_{f}" for f in REVIEW_FIELDS] + [f"r2_{f}" for f in REVIEW_FIELDS]
                    + [f"adjudicated_{f}" for f in ("language_script", "message_type", "eligible_primary")]
                    + ["r1_reviewer_id", "r2_reviewer_id", "review_date"])
    key_fields = ["annotation_id", "record_id", "source", "stratum", "sampling_note", "lang_provisional_machine",
                  "message_type_provisional", "message_type_source", "eligibility_status_machine", "thread_id",
                  "author_group", "duplicate_group", "flags", "source_url"]
    picks = [p for p in picks if p[0]["record_id"] not in released]
    taken = {v: k for k, v in released.items()}
    mode = "a" if released else "w"
    with (ROOT / "docs" / "annotation_sheet.csv").open(mode, newline="", encoding="utf-8") as fs, \
            (ROOT / "data" / "annotation" / "annotation_key.csv").open(mode, newline="", encoding="utf-8") as fk:
        ws, wk = csv.DictWriter(fs, fieldnames=sheet_fields), csv.DictWriter(fk, fieldnames=key_fields)
        if not released:
            ws.writeheader()
            wk.writeheader()
        for r, stratum, note in picks:
            aid = annotation_id(r["record_id"], taken)
            taken[aid] = r["record_id"]
            text = r["text_clean"]
            long_item = len(text) > 1500
            if long_item:
                (OUT_TXT / f"{aid}.txt").write_text(text, encoding="utf-8")
            source = r["record_id"].split(":")[0]
            ws.writerow({"annotation_id": aid, "source_genre": r["genre"],
                         "thread_context": {"blogs": "standalone page", "york_survey": "answers to 40 survey prompts"}.get(
                             source, "comment/post; parent and video context unavailable" if source != "reddit_confessions" else "top-level post (title + body)"),
                         "n_words_machine": r["n_words"],
                         "text_or_excerpt": text if not long_item else text[:1500] + " [...] (read full text file)",
                         "full_text_path": f"texts/{aid}.txt" if long_item else ""})
            wk.writerow({"annotation_id": aid, "record_id": r["record_id"], "source": source, "stratum": stratum,
                         "sampling_note": note, "lang_provisional_machine": r["lang_provisional"],
                         "message_type_provisional": r["message_type_provisional"], "message_type_source": r["message_type_source"],
                         "eligibility_status_machine": r["eligibility_status"], "thread_id": r["thread_id"],
                         "author_group": r["author_group"], "duplicate_group": r["duplicate_group"],
                         "flags": ";".join(r["flags"]), "source_url": r["source_url"]})
    with registry_p.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["annotation_id", "record_id", "first_release", "released_at"])
        if not released:
            w.writeheader()
        from griefcorpus.http import now_iso
        for r, _s, _n in picks:
            w.writerow({"annotation_id": annotation_id(r["record_id"]), "record_id": r["record_id"],
                        "first_release": "unreleased-addition", "released_at": now_iso()})
    c = Counter((s, r["lang_provisional"]) for r, s, _ in picks)
    print(len(picks), "records")
    for k, v in sorted(c.items()):
        print(" ", k, v)


if __name__ == "__main__":
    sys.exit(main())
