"""Stage 5 -- dictionary channel: match lexicon v0.2 entries to clauses, combine with Stage 4 flags."""
import argparse
import csv
import json
import re
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
NUKTA = "़"
TAGS = {"orientation": {"I": "orient_I", "F": "orient_F", "C": "orient_C", "R": "orient_R"},
        "process": {"L": "proc_loss", "Rs": "proc_restoration"},
        "function": {"Sk": "func_seek", "Of": "func_offer"}}
TAG_COLUMNS = [c for m in TAGS.values() for c in m.values()]
PLACEHOLDER = re.compile(r"(?:^|\s)X(?:\s|$)|\.\.\.|…|,|~|\+")
STAGE4_EXTRA = {"dative_parse": "F1"}


def norm_word(w, lang):
    w = unicodedata.normalize("NFC", w or "").replace(NUKTA, "").strip("\"'“”‘’()[].,;:!?।")
    return w.lower() if lang == "en" else w


SURFACE_ONLY = {"L-EN-16"}


def headword_variants(entry, include_surface_only=False):
    if entry["pos"].startswith("construction") or (entry["entry_id"] in SURFACE_ONLY and not include_surface_only):
        return []
    hw = entry["headword_deva"] if entry["lang"] == "hi" else entry["headword_en"]
    out = []
    for v in hw.split("/"):
        v = re.sub(r"\([^)]*\)", " ", v).strip()
        if not v or PLACEHOLDER.search(v):
            continue
        words = [norm_word(x, entry["lang"]) for x in v.split()]
        if all(words):
            out.append(words)
    return out


def load_lexicon(lex_path):
    lex_dir = Path(lex_path).parent
    entries = list(csv.DictReader(open(lex_path, encoding="utf-8")))
    for e in entries:
        e["rx"] = re.compile(e["pattern"], re.I if e["lang"] == "en" else 0)
        e["variants"] = headword_variants(e)
    with open(lex_dir / "entry_vectors.csv", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    components = [c for c in rows[0] if c not in ("entry_id", "lang", "names_emotion")]
    vectors = {r["entry_id"]: {c for c in components if r[c] == "1"} for r in rows}
    names_emotion = {r["entry_id"] for r in rows if r["names_emotion"] == "1"}
    flags = {}
    with open(lex_dir / "flag_components.csv", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            comps = [c.strip() for c in r["components"].split(";") if c.strip() in components]
            members = set(r["entry_ids"].split()) if not r["entry_ids"].startswith("(") else set()
            flags[r["flag_id"]] = dict(name=r["flag_name"], members=members, components=comps,
                                       forced=r["grammar_forced"] == "Y")
    y = yaml.safe_load((lex_dir / "constructions.yaml").read_text(encoding="utf-8"))
    kin = {}
    for f in y["flags"]:
        if f["id"] == "F9":
            for p in f["patterns"]:
                kin[p["lang"]] = re.compile(p["regex"], re.I if p["lang"] == "en" else 0)
    stage4 = {f["column"]: f["extends"] for f in y.get("stage4_flags", [])}
    stage4.update(STAGE4_EXTRA)
    flags.pop("F12", None)
    return dict(entries=entries, components=components, vectors=vectors, names_emotion=names_emotion,
                flags=flags, kin=kin, stage4=stage4)


def lemma_match(variants, toks):
    for words in variants:
        n = len(words)
        for i in range(len(toks) - n + 1):
            if all(words[k] in toks[i + k] for k in range(n)):
                return True
    return False


def match_clause(clause, toks, lex, channels=("surface", "lemma")):
    out = {}
    for e in lex["entries"]:
        if e["lang"] != clause["lang"]:
            continue
        s = "surface" in channels and bool(e["rx"].search(clause["clause_text"]))
        m = "lemma" in channels and bool(e["variants"]) and lemma_match(e["variants"], toks)
        if s or m:
            out[e["entry_id"]] = "both" if s and m else ("surface" if s else "lemma")
    return out


def feature_columns(lex):
    entry_cols = [e["entry_id"] for e in lex["entries"]]
    flag_cols = [f"flag_{k}" for k in lex["flags"]]
    gf = sorted({c for f in lex["flags"].values() if f["forced"] for c in f["components"]})
    return (entry_cols + TAG_COLUMNS + flag_cols + [f"comp_{c}" for c in lex["components"]]
            + [f"gf_{c}" for c in gf] + ["names_emotion"])


def clause_features(clause, matches, stage4_row, lex):
    by_id = {e["entry_id"]: e for e in lex["entries"]}
    f = {c: 0 for c in feature_columns(lex)}
    for eid in matches:
        e = by_id[eid]
        f[eid] = 1
        for field, cols in TAGS.items():
            if e[field] in cols:
                f[cols[e[field]]] = 1
        for c in lex["vectors"].get(eid, ()):
            f[f"comp_{c}"] = 1
        if eid in lex["names_emotion"]:
            f["names_emotion"] = 1
    active = {fid for fid, fl in lex["flags"].items() if fl["members"] & set(matches)}
    for col, fid in lex["stage4"].items():
        if stage4_row.get(col) == "True" and fid in lex["flags"]:
            active.add(fid)
    if "F9" in lex["flags"] and clause["lang"] in lex["kin"] and lex["kin"][clause["lang"]].search(clause["clause_text"]):
        active.add("F9")
    for fid in active:
        fl = lex["flags"][fid]
        f[f"flag_{fid}"] = 1
        for c in fl["components"]:
            f[(f"gf_{c}" if fl["forced"] else f"comp_{c}")] = 1
    return f


def load_tokens(path):
    toks = defaultdict(list)
    with open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["upos"] != "PUNCT":
                toks[r["clause_id"]].append((r["token"], r["lemma"]))
    return toks


def text_rates(clauses, feats, cols):
    agg = defaultdict(lambda: dict(n_clauses=0, n_tokens=0, counts=Counter(), lang=None))
    for c in clauses:
        a = agg[c["record_id"]]
        a["lang"] = c["lang"]
        a["n_clauses"] += 1
        a["n_tokens"] += c["n_tokens"]
        for k in cols:
            a["counts"][k] += feats[c["clause_id"]][k]
    rows = []
    for rid, a in agg.items():
        row = dict(record_id=rid, lang=a["lang"], n_clauses=a["n_clauses"], n_tokens=a["n_tokens"])
        for k in cols:
            row[k] = round(1000 * a["counts"][k] / a["n_tokens"], 3) if a["n_tokens"] else 0.0
        rows.append(row)
    return rows


def write_text_features(path, rows, extra=None):
    extra = extra or {}
    extra_cols = sorted({k for v in extra.values() for k in v})
    base = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=base + extra_cols)
        w.writeheader()
        for r in rows:
            w.writerow({**r, **{k: extra.get(r["record_id"], {}).get(k, "") for k in extra_cols}})


def write_summary(path, args, lex, clauses, matches, elapsed):
    n = Counter(c["lang"] for c in clauses)
    n_fin = Counter(c["lang"] for c in clauses if c["is_finite"])
    hit = Counter(c["lang"] for c in clauses if matches[c["clause_id"]])
    hit_fin = Counter(c["lang"] for c in clauses if c["is_finite"] and matches[c["clause_id"]])
    per = defaultdict(Counter)
    for c in clauses:
        for eid, ch in matches[c["clause_id"]].items():
            per[eid][ch] += 1
    L = ["# Lexmatch summary (Stage 5)", "",
         f"- Input: `{args.inp}`, `{args.flags}`; lexicon `{args.lexicon}` (v0.2, all entries status = proposed)",
         f"- Run: {time.strftime('%Y-%m-%d %H:%M')} ({elapsed:.0f} s); channels: {args.channels}",
         "- Matches are unreviewed. 'lemma only' = found by the headword lemma channel but not by the entry's "
         "pattern; those are where the two definitions of an entry disagree.", "",
         "## Coverage (clauses with at least one entry match)", "",
         "| lang | clause units | with match | share | finite clauses | with match | share |",
         "|---|---|---|---|---|---|---|"]
    for lg in ("hi", "en"):
        L.append(f"| {lg} | {n[lg]:,} | {hit[lg]:,} | {hit[lg] / n[lg]:.1%} | {n_fin[lg]:,} | {hit_fin[lg]:,} | "
                 f"{hit_fin[lg] / n_fin[lg]:.1%} |")
    by_lang = defaultdict(list)
    for e in lex["entries"]:
        by_lang[e["lang"]].append(e)
    hw = lambda e: e["headword_deva"] if e["lang"] == "hi" else e["headword_en"]
    for lg in ("hi", "en"):
        zero = [e for e in by_lang[lg] if not per[e["entry_id"]]]
        L += ["", f"## Entries with zero matches, {lg} ({len(zero)} of {len(by_lang[lg])}) — revision list for v0.3", "",
              "| entry_id | headword | pos |", "|---|---|---|"]
        L += [f"| {e['entry_id']} | {hw(e)} | {e['pos']} |" for e in zero]
    for lg in ("hi", "en"):
        top = sorted(by_lang[lg], key=lambda e: -sum(per[e["entry_id"]].values()))[:20]
        L += ["", f"## 20 most frequent entries, {lg}", "",
              "| entry_id | headword | clauses | per 1,000 clause units | surface | lemma only |", "|---|---|---|---|---|---|"]
        for e in top:
            p = per[e["entry_id"]]
            tot = sum(p.values())
            L.append(f"| {e['entry_id']} | {hw(e)} | {tot:,} | {1000 * tot / n[lg]:.1f} | {p['surface'] + p['both']:,} | "
                     f"{p['lemma']:,} |")
    lemma_only = sorted((e for e in lex["entries"] if per[e["entry_id"]]["lemma"]),
                        key=lambda e: -per[e["entry_id"]]["lemma"])[:20]
    L += ["", "## Largest lemma-only additions (headword variant matched, pattern did not)", "",
          "| entry_id | lang | headword | lemma only | surface |", "|---|---|---|---|---|"]
    L += [f"| {e['entry_id']} | {e['lang']} | {hw(e)} | {per[e['entry_id']]['lemma']:,} | "
          f"{per[e['entry_id']]['surface'] + per[e['entry_id']]['both']:,} |" for e in lemma_only]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--lexicon", default=str(ROOT / "lexicon" / "lexicon.csv"))
    ap.add_argument("--in", dest="inp", default="data/processed/clauses.jsonl")
    ap.add_argument("--tokens", default=None, help="default: tokens.csv next to --in")
    ap.add_argument("--flags", default="data/processed/flags.csv")
    ap.add_argument("--out", default="data/processed/clause_features.csv")
    ap.add_argument("--channels", default="surface,lemma", help="surface, lemma or surface,lemma")
    args = ap.parse_args()
    channels = tuple(x.strip() for x in args.channels.split(","))
    args.tokens = args.tokens or str(Path(args.inp).with_name("tokens.csv"))
    t0 = time.time()
    lex = load_lexicon(args.lexicon)
    clauses = [json.loads(line) for line in open(args.inp, encoding="utf-8")]
    raw_toks = load_tokens(args.tokens)
    with open(args.flags, encoding="utf-8", newline="") as fh:
        stage4 = {r["clause_id"]: r for r in csv.DictReader(fh)}
    cols = feature_columns(lex)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    matches, feats = {}, {}
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["clause_id", "record_id", "lang", "is_finite"] + cols)
        w.writeheader()
        for c in clauses:
            toks = [{norm_word(f, c["lang"]), norm_word(l, c["lang"])} for f, l in raw_toks[c["clause_id"]]]
            matches[c["clause_id"]] = match_clause(c, toks, lex, channels)
            feats[c["clause_id"]] = clause_features(c, matches[c["clause_id"]], stage4.get(c["clause_id"], {}), lex)
            w.writerow(dict(clause_id=c["clause_id"], record_id=c["record_id"], lang=c["lang"],
                            is_finite=int(c["is_finite"]), **feats[c["clause_id"]]))
    rows = text_rates(clauses, feats, cols)
    extra = None
    ref_path = out.parent / "referents.csv"
    if ref_path.exists():
        from referents import referent_text_columns
        extra = referent_text_columns(ref_path, clauses)
    write_text_features(out.parent / "text_features.csv", rows, extra)
    write_summary(out.parent / "lexmatch_summary.md", args, lex, clauses, matches, time.time() - t0)
    for lg in ("hi", "en"):
        cl = [c for c in clauses if c["lang"] == lg]
        print(f"{lg}: {len(cl)} clause units, {sum(1 for c in cl if matches[c['clause_id']])} with >=1 entry match")
    print(f"wrote {out}, text_features.csv, lexmatch_summary.md")


if __name__ == "__main__":
    main()
