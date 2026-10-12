import argparse
import csv
import datetime
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from build_review_master import load_candidates, norm_url
from griefcorpus.textutil import dedup_key

MASTER = ROOT / "docs" / "review_master_2026-10.csv"
MERGED = ROOT / "data" / "clean" / "blogs_merged.jsonl"
LEDGER = ROOT / "data" / "clean" / "blogs_review_accepted.jsonl"
REPORT = ROOT / "docs" / "merge_report.md"
DECISIONS = {"yes", "no", "maybe"}
REVIEW_STATUS = "human_inclusion_review"


def validate(rows):
    errs = []
    blank = [r["review_id"] for r in rows if not (r.get("decision") or "").strip()]
    if blank:
        errs.append(f"{len(blank)} blank decision cell(s), e.g. {', '.join(blank[:10])}")
    bad = [f"{r['review_id']}={r['decision']!r}" for r in rows
           if (r.get("decision") or "").strip() and r["decision"].strip().lower() not in DECISIONS]
    if bad:
        errs.append(f"{len(bad)} decision(s) not yes/no/maybe: {', '.join(bad[:10])}")
    noreviewer = [r["review_id"] for r in rows
                  if (r.get("decision") or "").strip().lower() == "yes" and not (r.get("reviewer") or "").strip()]
    if noreviewer:
        errs.append(f"{len(noreviewer)} yes row(s) without reviewer: {', '.join(noreviewer[:10])}")
    dup = [k for k, n in Counter(r["review_id"] for r in rows).items() if n > 1]
    if dup:
        errs.append(f"repeated review_id: {', '.join(dup[:10])}")
    return errs


def make_record(row, c, review_date, template_keys):
    d, cand_meta = c["doc"], c["doc"].get("candidate") or {}
    flags = []
    if c["boilerplate_removed"]:
        flags.append(f"boilerplate_lines_removed:{c['boilerplate_removed']}")
    if c["n_words"] > 5000:
        flags.append("length_outlier_gt5000w")
    if row["over_cap"]:
        flags.append("over_cap")
        flags += [f"over_cap:{f}" for f in row["over_cap"].split(";")]
    if c["route"] == "same_author_dev":
        flags.append("proposed_split:development")
    rid = row["record_id"]
    rec = {k: None for k in template_keys}
    rec.update(record_id=rid, platform="web", genre="blog_or_personal_essay", source_url=d["url"],
               source_record_id=rid.split(":", 1)[1], collected_at=d["collected_at"],
               published_at=d.get("publication_date"), thread_id=d["domain"], author_group=d.get("author_group"),
               text_original=d["text"], text_clean=c["text"], lang_provisional=c["lang_provisional"],
               n_words=c["n_words"], message_type_provisional="personal_disclosure",
               message_type_source="human inclusion review (decision = yes)",
               eligibility_status="provisionally_eligible", exclusion_reason=None,
               retrieval_route=f"expansion {c['pass_']} ({c['route']}): {cand_meta.get('query_that_found_it', '')}",
               duplicate_group=rid, reuse_notes="copyright of author/site; local analysis copy; do not redistribute text",
               flags=flags, review_status=REVIEW_STATUS, dedup_key=dedup_key(c["text"]),
               extra={"title": d.get("title"),
                      "deceased_relation_as_stated": (row.get("relation") or "").strip()
                      or cand_meta.get("deceased_relation_as_stated"),
                      "indian_context_evidence": cand_meta.get("indian_context_evidence", "not recorded"),
                      "searcher_notes": cand_meta.get("notes"), "domain_covariate": row["domain_covariate"],
                      "review": {"review_id": row["review_id"], "pass": row["pass"], "route": row["route"],
                                 "review_date": review_date, "reviewer": row["reviewer"].strip(),
                                 "reason": (row.get("reason") or "").strip(),
                                 **({"provenance": row["provenance"], "corrections": row.get("corrections", "")}
                                    if (row.get("provenance") or "").strip() else {})}})
    return rec


def update_ledger(rows, review_date, dry_run):
    ledger = {}
    if LEDGER.exists():
        for l in LEDGER.open(encoding="utf-8"):
            r = json.loads(l)
            ledger[r["record_id"]] = r
    cands = load_candidates()
    template = list(json.loads(MERGED.open(encoding="utf-8").readline()).keys())
    stats = Counter(r["decision"].strip().lower() for r in rows)
    missing = []
    for row in rows:
        rid = row["record_id"]
        ledger.pop(rid, None)
        if row["decision"].strip().lower() != "yes":
            continue
        c = cands.get(rid.split(":", 1)[1])
        if c is None:
            missing.append(row["review_id"])
            continue
        ledger[rid] = make_record(row, c, review_date, template)
    if missing:
        sys.exit(f"REFUSED: {len(missing)} accepted text(s) not found locally (nothing is fetched): {missing[:10]}")
    recs = sorted(ledger.values(), key=lambda r: r["record_id"])
    if not dry_run:
        with LEDGER.open("w", encoding="utf-8") as fh:
            fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in recs)
    return recs, stats


def eligible_counts(recs):
    el = [r for r in recs if r["eligibility_status"] == "provisionally_eligible"]
    return (Counter(r["lang_provisional"] for r in el),
            Counter(r["lang_provisional"] for r in el if "over_cap" not in r["flags"]))


def rebuild(ledger_recs, stats, dry_run):
    if dry_run:
        base = [json.loads(l) for l in MERGED.open(encoding="utf-8") if json.loads(l)["review_status"] != REVIEW_STATUS]
    else:
        subprocess.run([sys.executable, str(ROOT / "scripts" / "merge_seed_v2.py")], check=True)
        base = [json.loads(l) for l in MERGED.open(encoding="utf-8")]
    have_id, have_url = {r["record_id"] for r in base}, {norm_url(r["source_url"]) for r in base}
    added, skipped = [], []
    for r in ledger_recs:
        (skipped if r["record_id"] in have_id or norm_url(r["source_url"]) in have_url else added).append(r)
    allrecs = base + added
    before, before_nc = eligible_counts(base)
    after, after_nc = eligible_counts(allrecs)
    if not dry_run and ledger_recs:
        with MERGED.open("w", encoding="utf-8") as fh:
            fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in allrecs)
        with REPORT.open("a", encoding="utf-8") as fh:
            fh.write("\n## Review additions (scripts/apply_review.py)\n\n")
            fh.write(f"Ledger `data/clean/blogs_review_accepted.jsonl`: {len(ledger_recs)} accepted texts; "
                     f"added {len(added)}, skipped {len(skipped)} (already in the base). review_status "
                     f"`{REVIEW_STATUS}`: a person decided inclusion only.\n\n")
            fh.write("| language | eligible before | eligible after | after, without over_cap |\n|---|---:|---:|---:|\n")
            for k in sorted(set(after) | set(before)):
                fh.write(f"| {k} | {before[k]} | {after[k]} | {after_nc[k]} |\n")
            fh.write("\n| review_id | pass | lang | words | flags | reviewer | review date | url |\n"
                     "|---|---|---|---:|---|---|---|---|\n")
            for r in added:
                rv = r["extra"]["review"]
                fh.write(f"| {rv['review_id']} | {rv['pass']} | {r['lang_provisional']} | {r['n_words']} | "
                         f"{';'.join(f for f in r['flags'] if f.startswith(('over_cap', 'proposed')))} | "
                         f"{rv['reviewer']} | {rv['review_date']} | {r['source_url']} |\n")
    if stats:
        print("decisions:", dict(stats))
    print(f"{'DRY RUN: would add' if dry_run else 'added'} {len(added)} texts, skipped {len(skipped)}")
    for k in sorted(set(after) | set(before)):
        print(f"eligible {k}: {before[k]} -> {after[k]} (without over_cap: {after_nc[k]})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", default=str(MASTER))
    ap.add_argument("--review-date", default=datetime.date.today().isoformat())
    ap.add_argument("--from-ledger", action="store_true", help="rebuild blogs_merged from base + ledger only")
    ap.add_argument("--dry-run", action="store_true", help="validate and count; write nothing")
    a = ap.parse_args()
    if a.from_ledger:
        recs = [json.loads(l) for l in LEDGER.open(encoding="utf-8")] if LEDGER.exists() else []
        return rebuild(recs, Counter(), a.dry_run)
    datetime.date.fromisoformat(a.review_date)
    rows = list(csv.DictReader(open(a.master, encoding="utf-8")))
    errs = validate(rows)
    if errs:
        sys.exit("REFUSED (nothing written):\n  " + "\n  ".join(errs))
    recs, stats = update_ledger(rows, a.review_date, a.dry_run)
    rebuild(recs, stats, a.dry_run)


if __name__ == "__main__":
    main()
