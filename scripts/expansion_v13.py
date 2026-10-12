import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from griefcorpus.clean import clean_doc_text
from rank_screen import score

ROUTES = {"blog_candidates_v13_hi_webzines.jsonl": "v1.3_hi_webzines",
          "blog_candidates_v13_hi_blogs.jsonl": "v1.3_hi_personal_blogs",
          "blog_candidates_v13_pratilipi.jsonl": "v1.3_hi_pratilipi_listing",
          "blog_candidates_v13_en.jsonl": "v1.3_en_essays"}
LANG2 = {"devanagari_hindi": "hi", "english": "en", "romanized_hindi": "hi-Latn", "mixed_hi_en": "mixed"}
OUT = ROOT / "docs" / "expansion_candidates_v13.csv"
V12 = ROOT / "docs" / "expansion_candidates_v12.csv"
CUTOFF = 2.5
TARGET = {"hi": 40, "en": 30}
DOM_CAP = 3


def dom(d):
    d = d.replace("www.", "").replace("hindi.pratilipi.com", "pratilipi.com")
    return d[2:] if d.startswith("m.") else d


def ranked_rows():
    known = {json.loads(l)["source_url"].rstrip("/")
             for l in (ROOT / "data" / "clean" / "blogs_merged.jsonl").open(encoding="utf-8")}
    log, earlier = {}, set()
    for l in (ROOT / "data" / "raw" / "blogs" / "fetch_log.jsonl").open(encoding="utf-8"):
        r = json.loads(l)
        if r.get("candidate_file") in ROUTES:
            log[r["doc_id"]] = r
        else:
            earlier.add(r["url"].rstrip("/"))
    stats = Counter(f"fetch_{ROUTES[r['candidate_file']]}_{r['status']}" for r in log.values())
    rows, seen = [], set()
    for l in (ROOT / "data" / "interim" / "blogs_extracted.jsonl").open(encoding="utf-8"):
        d = json.loads(l)
        if d["doc_id"] not in log or d["doc_id"] in seen:
            continue
        seen.add(d["doc_id"])
        route = ROUTES[log[d["doc_id"]]["candidate_file"]]
        text, _ = clean_doc_text(d["text"])
        lang = LANG2.get(d["lang_provisional"], d["lang_provisional"])
        url = d["url"].rstrip("/")
        checks = [c for c, bad in (("short_lt80w", d["n_words"] < 80), (f"lang_{lang}", lang not in ("hi", "en")),
                                   ("already_in_corpus", url in known), ("fetched_before_v13", url in earlier))
                  if bad]
        s = score(text, lang) if lang in ("hi", "en") else dict(score=0, first_person=0, kin=0, death_near_kin=0, past=0)
        cand = d.get("candidate") or {}
        rows.append(dict(record_id=f"blogs:{d['doc_id']}", lang=lang, route=route, source=d["domain"], url=d["url"],
                         query_family=cand.get("query_family", ""), n_words=d["n_words"], rank_score=s["score"],
                         first_person=s["first_person"], kin=s["kin"], death_near_kin=s["death_near_kin"],
                         past=s["past"], automatic_checks="pass" if not checks else ";".join(checks), flags="",
                         first_300_chars=text[:300].replace("\n", " "),
                         reviewer_eligible="", reviewer_type="", reviewer_note=""))
    per_dom = defaultdict(list)
    for r in rows:
        if r["route"] == "v1.3_hi_webzines" and r["automatic_checks"] == "pass":
            per_dom[dom(r["source"])].append(r)
    v12 = Counter(dom(r["source"]) for r in csv.DictReader(V12.open(encoding="utf-8"))
                  if r["route"] == "v1.2_hi_webzines" and r["automatic_checks"] == "pass")
    for d, rs in per_dom.items():
        rs.sort(key=lambda x: (-x["rank_score"], x["record_id"]))
        for r in rs[DOM_CAP:]:
            r["automatic_checks"] = "over_domain_cap"
        for r in rs[:DOM_CAP][max(DOM_CAP - v12[d], 0):]:
            r["flags"] = "over_cumulative_domain_cap"
    return rows, stats, v12


def main():
    rows, stats, v12 = ranked_rows()
    for r in rows:
        stats[f"{r['lang']}_{r['route']}_{r['automatic_checks']}"] += 1
    keep = []
    for lang in ("hi", "en"):
        ok = sorted((r for r in rows if r["lang"] == lang and r["automatic_checks"] == "pass"),
                    key=lambda r: (-r["rank_score"], r["record_id"]))
        keep += ok
        ge = [r for r in ok if r["rank_score"] >= CUTOFF]
        stats[f"{lang}_passing_total"] = len(ok)
        stats[f"{lang}_score_ge_3"] = sum(1 for r in ok if r["rank_score"] >= 3)
        stats[f"{lang}_score_ge_2.5"] = len(ge)
        stats[f"{lang}_score_ge_2.5_cumulative_cap"] = sum(1 for r in ge if r["flags"] != "over_cumulative_domain_cap")
        stats[f"{lang}_target_ge_2.5"] = TARGET[lang]
        for r in ge:
            stats[f"{lang}_ge_2.5_by_route_{r['route']}"] += 1
            if r["query_family"]:
                stats[f"{lang}_ge_2.5_by_family_{r['query_family']}"] += 1
        for r in ge:
            if r["route"] == "v1.3_hi_webzines":
                stats[f"hi_ge_2.5_webzine_{dom(r['source'])}"] += 1
    stats.update({f"v12_webzine_kept_{d}": n for d, n in v12.items()})
    fields = list(rows[0].keys()) if rows else []
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(keep)
    (ROOT / "data" / "interim" / "expansion_v13_counts.json").write_text(json.dumps(dict(sorted(stats.items())), indent=1,
                                                                               ensure_ascii=False))
    for k, v in sorted(stats.items()):
        print(f"{k}: {v}")
    print(f"{len(keep)} rows -> {OUT}")


if __name__ == "__main__":
    main()
