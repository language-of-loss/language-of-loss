"""Dictionary / rule channel in the gold-sheet schema: one predicted value per codebook field per clause."""
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from gold import CODEBOOK, SHEET_COLUMNS, refuse_annotation_dir

ROOT = Path(__file__).resolve().parents[2]
SPEECH = {"कह", "कहना", "बोल", "बोलना", "बता", "बताना", "पूछ", "पूछना", "पुकार", "पुकारना",
          "say", "tell", "ask", "speak", "talk", "reply", "answer", "call", "write", "shout", "whisper"}
BE = {"हो", "होना", "है", "था", "रह", "रहना", "be", "remain", "seem", "become"}
DEATH = {"मर", "मरना", "गुजर", "गुज़र", "गुजरना", "गुज़रना", "die", "pass", "perish"}
FORCED = {"forced_dative", "forced_nominative", "forced_impersonal"}
CHOSEN = {"chosen_dative", "chosen_nominative", "chosen_impersonal"}
NON_NOMINATIVE = {"forced_dative", "chosen_dative", "forced_impersonal", "chosen_impersonal"}
NOMINATIVE = {"forced_nominative", "chosen_nominative"}
TIE_ORIENTATION = ["I", "F", "C"]


def majority(tags, order):
    if not tags:
        return None
    counts = Counter(tags)
    top = max(counts.values())
    return next(t for t in order if counts.get(t) == top)


def orientation(entries):
    tags = [e["orientation"] for e in entries]
    if "R" in tags:
        return "R"
    return majority([t for t in tags if t in TIE_ORIENTATION], TIE_ORIENTATION) or "NA"


def process(entries):
    return majority([e["process"] for e in entries if e["process"] in ("L", "Rs")], ["L", "Rs"]) or "NA"


def function(entries):
    tags = {e["function"] for e in entries}
    return "Sk" if "Sk" in tags else "Of" if "Of" in tags else "NA"


def predicate_type(flags, sites, head_lemma, head_upos):
    if flags.get("closing_formula") == "True":
        return "other", "closing_formula"
    if flags.get("motion_euphemism") == "True" or flags.get("no_more") == "True":
        return "event_befalling", "death flag"
    if sites & NON_NOMINATIVE:
        return "event_befalling", "non-nominative experiencer site"
    if sites & NOMINATIVE:
        return "state", "nominative experiencer site"
    lemma = (head_lemma or "").lower()
    if lemma in DEATH:
        return "event_befalling", "death verb head"
    if lemma in SPEECH:
        return "speech", "speech head"
    if lemma in BE:
        return "state", "be / remain head"
    if not head_lemma:
        return "other", "no head"
    return ("action", "verb head") if head_upos == "VERB" else ("state", f"{head_upos or '?'} head")


def grammar_forced(sites, rel_rules):
    if sites & FORCED or "REL-HON-F" in rel_rules:
        return "Y"
    return "context" if "REL-HON-C" in rel_rules else "N"


def dative_alternative(sites):
    if sites & CHOSEN:
        return "Y"
    return "N" if sites & FORCED else "NA"


def code_clause(clause, entries, flags, ref, sites, rel_rules, head_upos):
    pt, why = predicate_type(flags, sites, clause.get("head_lemma"), head_upos)
    out = dict(orientation=orientation(entries), process=process(entries), function=function(entries),
               experiencer=ref["referent_class"] if ref else "",
               target=(ref["target_class"] or "none") if ref else "",
               predicate_type=pt, grammar_forced=grammar_forced(sites, rel_rules),
               dative_alternative_available=dative_alternative(sites))
    for f, v in out.items():
        assert v == "" or v in CODEBOOK[f], (f, v)
    out["evidence"] = "; ".join(filter(None, [
        "entries " + " ".join(e["entry_id"] for e in entries) if entries else "",
        "sites " + " ".join(sorted(sites)) if sites else "",
        "rel " + " ".join(sorted(rel_rules)) if rel_rules else "", f"pred: {why}"]))
    return out


def load(proc, lexicon_path):
    lex = {r["entry_id"]: r for r in csv.DictReader(open(lexicon_path, encoding="utf-8"))}
    usable = {k for k, r in lex.items() if r["grammar_forced"] == "N"}
    clauses = [json.loads(line) for line in open(proc / "clauses.jsonl", encoding="utf-8")]
    entries = {}
    with open(proc / "clause_features.csv", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        head = next(reader)
        cols = [(i, h) for i, h in enumerate(head) if h in usable]
        for row in reader:
            entries[row[0]] = [lex[h] for i, h in cols if row[i] == "1"]
    flags = {r["clause_id"]: r for r in csv.DictReader(open(proc / "flags.csv", encoding="utf-8", newline=""))}
    refs = {r["clause_id"]: r for r in csv.DictReader(open(proc / "referents.csv", encoding="utf-8", newline=""))}
    sites, rel = defaultdict(set), defaultdict(set)
    for r in csv.DictReader(open(proc / "eligibility.csv", encoding="utf-8", newline="")):
        if r["marker_type"] == "dative" and r["decision"] != "NA":
            sites[r["clause_id"]].add(r["decision"])
        elif r["marker_type"] == "relational" and r["rule_id"].startswith("REL-HON"):
            rel[r["clause_id"]].add(r["rule_id"])
    heads = {c["clause_id"]: c.get("head_lemma") for c in clauses}
    upos = {}
    with open(proc / "tokens.csv", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            cid = r["clause_id"]
            if cid not in upos and heads.get(cid) and r["lemma"] == heads[cid]:
                upos[cid] = r["upos"]
    return clauses, entries, flags, refs, sites, rel, upos


def run(proc, lexicon_path):
    clauses, entries, flags, refs, sites, rel, upos = load(proc, lexicon_path)
    return {c["clause_id"]: code_clause(c, entries.get(c["clause_id"], []), flags.get(c["clause_id"], {}),
                                        refs.get(c["clause_id"]), sites.get(c["clause_id"], set()),
                                        rel.get(c["clause_id"], set()), upos.get(c["clause_id"]))
            for c in clauses}


def fill_sheet(sheet_rows, key_rows, coded):
    cid = {k["gold_id"]: k["clause_id"] for k in key_rows}
    out = []
    for r in sheet_rows:
        v = coded.get(cid.get(r["gold_id"], ""), {})
        row = {c: r.get(c, "") for c in SHEET_COLUMNS}
        row.update({f: v.get(f, "") for f in CODEBOOK})
        row["notes"] = ("dict: " + v["evidence"]) if v else "dict: clause not found (Stage 3 re-run?)"
        out.append(row)
    return out


def write_csv(path, rows, columns):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--processed", default=str(ROOT / "data/processed"))
    ap.add_argument("--lexicon", default=str(ROOT / "lexicon/lexicon.csv"))
    ap.add_argument("--out", default=str(ROOT / "data/processed/dict_channel.csv"))
    ap.add_argument("--sheet", help="gold-schema sheet whose rows to fill (e.g. gold_pilot_r1.csv)")
    ap.add_argument("--key", help="its key file (gold_id -> clause_id)")
    ap.add_argument("--sheet-out", help="where to write the filled sheet")
    args = ap.parse_args(argv)

    coded = run(Path(args.processed), args.lexicon)
    write_csv(refuse_annotation_dir(args.out), [dict(clause_id=k, **v) for k, v in coded.items()], ["clause_id"] + list(CODEBOOK) + ["evidence"])
    print(f"{len(coded)} clauses -> {args.out}")
    for f in CODEBOOK:
        print(f"  {f}: {dict(Counter(v[f] for v in coded.values()).most_common())}")
    if args.sheet:
        sheet = list(csv.DictReader(open(args.sheet, encoding="utf-8", newline="")))
        key = list(csv.DictReader(open(args.key, encoding="utf-8", newline="")))
        rows = fill_sheet(sheet, key, coded)
        write_csv(refuse_annotation_dir(args.sheet_out), rows, SHEET_COLUMNS)
        print(f"{len(rows)} sheet rows -> {args.sheet_out}")


if __name__ == "__main__":
    main()
