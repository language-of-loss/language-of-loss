"""Stage 4 -- construction flags per clause: regex channel + dependency-parse channel for the dative."""
import argparse
import csv
import json
import random
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONSTRUCTIONS = ROOT / "lexicon" / "constructions.yaml"
NUKTA = "़"
PUNCT_CHARS = "\"'“”‘’«»()[]{}.,;:!?।॥-–—…*"


def load_spec(path=CONSTRUCTIONS):
    d = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    columns, regex, defined = [], defaultdict(list), defaultdict(set)
    for f in d["stage4_flags"]:
        if f["column"] not in columns:
            columns.append(f["column"])
        if f.get("filter") and f["filter"] not in FILTERS:
            raise ValueError(f"{f['id']}: unknown filter {f['filter']!r}")
        regex[f["lang"]].append((f["column"], re.compile(f["regex"]), f.get("filter") or None))
        defined[f["lang"]].add(f["column"])
    columns.insert(1, "dative_parse")
    defined["hi"].add("dative_parse")
    dp = d["stage4_dative_parse"]
    dative = dict(pronouns=set(dp["pronouns"]), deprels=set(dp["deprels"]),
                  stems=tuple(denukta(x) for x in dp["feel_verb_stems"]),
                  light=tuple(denukta(x) for x in dp["light_verbs"]),
                  feel={denukta(x) for x in dp["feel_words"]},
                  body={denukta(x) for x in dp["body_state_words"]})
    filters = {k: {p: list(v) for p, v in params.items()} for k, params in d["stage4_filters"].items()}
    return dict(columns=columns, regex=dict(regex), defined=dict(defined), dative=dative, filters=filters,
                placeholders=list(d["stage4_placeholders"]))


def bare(token):
    return token.strip(PUNCT_CHARS)


def denukta(s):
    return (s or "").replace(NUKTA, "")


def regex_flags(text, lang, spec, words=None, sentence=None):
    hits = {}
    for col, rx, flt in spec["regex"].get(lang, []):
        if col in hits:
            continue
        m = rx.search(text)
        if m and (flt is None or words is None or FILTERS[flt](words, sentence, spec["filters"][flt])):
            hits[col] = m.group(0)
    return hits


def clause_heads(words, sentence):
    ids = {w["token_index"] for w in words}
    return {w["token_index"] for w in words if w["upos"] != "PUNCT" and w["head"] not in ids}


PROGRESSIVE = {"रहा", "रही", "रहे"}
EXPERIENCER_LEMMAS = {"लगना", "लगाना", "होना", "आना", "है", "था", "मिलना", "पडना", "रहना"}


def finite_dative(words, sentence, p):
    heads = clause_heads(words, sentence)
    for k, w in enumerate(words):
        if bare(w["token"]) not in p["pronouns"]:
            continue
        for v in words[k + 1:]:
            if bare(v["token"]) not in p["verbs"]:
                continue
            prev = sentence.get(v["token_index"] - 1)
            after_participle = prev is not None and prev["upos"] in ("VERB", "AUX") and \
                prev["token"].endswith(tuple(p["participle_endings"]))
            structural = v["token_index"] in heads or (v["deprel"] in p["aux_deprels"] and v["head"] in heads)
            if bare(v["token"]) in PROGRESSIVE and v["deprel"].startswith("aux"):
                main = sentence.get(v["head"])
                structural = structural and main is not None and denukta(main["lemma"]) in EXPERIENCER_LEMMAS
            if structural and not after_participle:
                return True
    return False


def no_destination(words, sentence, p):
    max_dist = int(p["bare_noun_max_distance"][0])
    kids = defaultdict(list)
    for w in sentence.values():
        kids[w["head"]].append(w)
    found = False
    for k, w in enumerate(words[:-1]):
        if bare(w["token"]) not in p["motion_stems"] or not words[k + 1]["token"].startswith("ग"):
            continue
        found = True
        dest = False
        for c in kids[w["token_index"]]:
            if denukta(c["token"]) in p["destination_adverbs"]:
                dest = True
            elif c["deprel"].startswith("obl") and c["upos"] in ("NOUN", "PROPN"):
                noun = denukta(bare(c["token"]))
                if noun in p["time_nouns"] or noun in p["otherworld_nouns"]:
                    continue
                cases = [g["token"] for g in kids[c["token_index"]] if g["deprel"] == "case"]
                if not cases:
                    dest = dest or 0 < w["token_index"] - c["token_index"] <= max_dist
                elif all(x in p["destination_case_markers"] for x in cases):
                    dest = True
        if not dest:
            return True
    return not found


def animate_subject(words, sentence, p):
    kids = defaultdict(list)
    for w in sentence.values():
        kids[w["head"]].append(w)
    for w in words:
        if w["token"].lower() != "gone":
            continue
        for c in kids[w["token_index"]]:
            if c["deprel"] in ("nsubj", "nsubj:pass") and (c["upos"] == "PROPN" or c["token"].lower() in p["pronouns"]
                                                          or c["token"].lower() in p["kin"]):
                return True
    return False


FILTERS = {"finite_dative": finite_dative, "no_destination": no_destination, "animate_subject": animate_subject}


LAGANA_TRANSITIVE = {"लगाया", "लगाई", "लगायी", "लगाए", "लगाये", "लगाता", "लगाती", "लगाते", "लगाना", "लगाकर",
                     "लगाओ"}


def is_feeling_word(w, dative):
    return denukta(w["token"]) in dative["feel"] or denukta(w["lemma"]) in dative["feel"]


def is_psych_head(h, children, dative):
    form, lemma = denukta(h["token"]), denukta(h["lemma"])
    if h["upos"] in ("VERB", "AUX") and any(c["upos"] == "VERB" and "VerbForm=Inf" in c.get("feats", "")
                                            and denukta(c["token"]).endswith("ने") for c in children):
        return False
    stem_lemmas = {s + "ना" for s in dative["stems"]}
    if h["upos"] in ("VERB", "AUX") and (lemma in stem_lemmas or (lemma == "लगाना" and form.startswith("लग")
                                                                  and form not in LAGANA_TRANSITIVE)):
        return True
    if is_feeling_word(h, dative):
        return True
    light_lemmas = {s + "ना" for s in dative["light"]} | {"है", "था"}
    if h["upos"] in ("VERB", "AUX") and lemma in light_lemmas:
        return any(is_feeling_word(c, dative) or denukta(c["token"]) in dative["body"] for c in children)
    return False


def dative_parse(sentence, clause_ids, dative):
    kids = defaultdict(list)
    for w in sentence.values():
        kids[w["head"]].append(w)
    for i in sorted(clause_ids):
        w = sentence[i]
        if bare(w["token"]) not in dative["pronouns"] or w["deprel"] not in dative["deprels"]:
            continue
        h = sentence.get(w["head"])
        if h is not None and is_psych_head(h, kids[h["token_index"]], dative):
            return f"{w['token']} -{w['deprel']}-> {h['token']}"
    return None


def load_sentences(tokens_path, clause_meta):
    sentences, clause_ids = defaultdict(dict), defaultdict(list)
    with open(tokens_path, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            rid, si = clause_meta[row["clause_id"]]
            ti = int(row["token_index"])
            sentences[(rid, si)][ti] = dict(token_index=ti, token=row["token"], lemma=row["lemma"],
                                            upos=row["upos"], head=int(row["head"]), deprel=row["deprel"])
            clause_ids[row["clause_id"]].append(ti)
    return sentences, clause_ids


def flag_clause(clause, sentence, ids, spec):
    lang, defined = clause["lang"], spec["defined"].get(clause["lang"], set())
    words = [sentence[i] for i in sorted(ids)]
    hits = regex_flags(clause["clause_text"], lang, spec, words, sentence)
    if "dative_parse" in defined:
        ev = dative_parse(sentence, ids, spec["dative"])
        if ev:
            hits["dative_parse"] = ev
    row = {c: (c in hits) if c in defined else None for c in spec["columns"]}
    row.update({p: None for p in spec["placeholders"]})
    return row, hits


def flag_text(text, lang, nlp, spec):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from preprocess import prepare_text

    prepared = prepare_text(text, lang)
    defined = spec["defined"].get(lang, set())
    hits = set()
    for s in nlp(prepared).sentences:
        sent = {w.id: dict(token_index=w.id, token=w.text, lemma=w.lemma or "", upos=w.upos, head=w.head,
                           deprel=w.deprel) for w in s.words}
        words = [sent[i] for i in sorted(sent)]
        hits |= set(regex_flags(prepared, lang, spec, words, sent))
        if "dative_parse" in defined and dative_parse(sent, list(sent), spec["dative"]):
            hits.add("dative_parse")
    return hits & defined


def write_summary(path, args, rows, n_units, hits_by, spec, elapsed, seed):
    cols = spec["columns"]
    L = ["# Flags summary (Stage 4)", "",
         f"- Input: `{args.inp}` + `{args.tokens}`; patterns: `lexicon/constructions.yaml` (stage4_flags)",
         f"- Run: {time.strftime('%Y-%m-%d %H:%M')} ({elapsed:.0f} s)",
         "- Denominator: all clause units of the language (finite and non-finite); n/a = flag not defined "
         "for that language. Regex matches are unreviewed: rates are upper bounds on construction use.", "",
         "| flag | hi n | hi per 1,000 | en n | en per 1,000 |", "|---|---|---|---|---|"]
    for c in cols:
        cells = []
        for lg in ("hi", "en"):
            vals = [r[c] for r in rows if r["lang"] == lg]
            if all(v is None for v in vals):
                cells += ["n/a", "n/a"]
            else:
                n = sum(1 for v in vals if v)
                cells += [f"{n:,}", f"{1000 * n / n_units[lg]:.1f}"]
        L.append(f"| {c} | " + " | ".join(cells) + " |")
    L += ["", f"Clause units: hi {n_units['hi']:,}, en {n_units['en']:,}. "
          f"{', '.join(spec['placeholders'])}: null everywhere (filled by the eligibility detector).", "",
          "## Dative: regex vs parse (hi)", "",
          "| | dative_parse true | dative_parse false |", "|---|---|---|"]
    hi = [r for r in rows if r["lang"] == "hi"]
    for rv in (True, False):
        L.append(f"| dative_regex {str(rv).lower()} | "
                 f"{sum(1 for r in hi if r['dative_regex'] is rv and r['dative_parse']):,} | "
                 f"{sum(1 for r in hi if r['dative_regex'] is rv and not r['dative_parse']):,} |")
    L += ["", f"## Examples (up to 5 random hits per flag and language, seed {seed}; check for false positives)", ""]
    rng = random.Random(seed)
    for c in cols:
        for lg in ("hi", "en"):
            pool = hits_by[(c, lg)]
            if not pool:
                continue
            L.append(f"**{c} / {lg}** ({len(pool)})")
            L += [f"- `{cid}` [{ev}] {text}" for cid, ev, text in rng.sample(pool, min(5, len(pool)))]
            L.append("")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--in", dest="inp", default="data/processed/clauses.jsonl")
    ap.add_argument("--tokens", default=None, help="default: tokens.csv next to --in")
    ap.add_argument("--out", default="data/processed/flags.csv")
    ap.add_argument("--constructions", default=str(CONSTRUCTIONS))
    ap.add_argument("--seed", type=int, default=20261009)
    args = ap.parse_args()
    args.tokens = args.tokens or str(Path(args.inp).with_name("tokens.csv"))
    t0 = time.time()
    spec = load_spec(args.constructions)
    clauses = [json.loads(line) for line in open(args.inp, encoding="utf-8")]
    sentences, clause_ids = load_sentences(args.tokens, {c["clause_id"]: (c["record_id"], c["sent_index"])
                                                         for c in clauses})
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fields = ["clause_id", "record_id", "lang"] + spec["columns"] + spec["placeholders"] + ["evidence"]
    rows, n_units, hits_by = [], Counter(), defaultdict(list)
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for c in clauses:
            flags, hits = flag_clause(c, sentences[(c["record_id"], c["sent_index"])], clause_ids[c["clause_id"]],
                                      spec)
            n_units[c["lang"]] += 1
            for col, ev in hits.items():
                hits_by[(col, c["lang"])].append((c["clause_id"], ev, c["clause_text"]))
            row = dict(clause_id=c["clause_id"], record_id=c["record_id"], lang=c["lang"], **flags,
                       evidence="; ".join(f"{k}={v}" for k, v in hits.items()))
            w.writerow({k: ("" if v is None else v) for k, v in row.items()})
            rows.append(dict(lang=c["lang"], **flags))
    write_summary(out.parent / "flags_summary.md", args, rows, n_units, hits_by, spec, time.time() - t0, args.seed)
    for lg in ("hi", "en"):
        got = {c: sum(1 for r in rows if r["lang"] == lg and r[c]) for c in spec["columns"]
               if c in spec["defined"].get(lg, set())}
        print(f"{lg}: {n_units[lg]} clause units; " + ", ".join(f"{k} {v}" for k, v in got.items()))
    print(f"wrote {out} and {out.parent / 'flags_summary.md'}")


if __name__ == "__main__":
    main()
