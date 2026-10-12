"""Stage 3 -- preprocessing: text preparation, Stanza parse, clause segmentation, near-duplicate report."""
import argparse
import csv
import hashlib
import json
import random
import re
import statistics
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ELIGIBLE = "provisionally_eligible"
LANG_MAP = {"devanagari_hindi": "hi", "english": "en"}
SET_ASIDE = {"romanized_hindi"}
PROCESSORS = {"hi": "tokenize,pos,lemma,depparse", "en": "tokenize,mwt,pos,lemma,depparse"}
CACHE_FORMAT = 1

CONNECTIVES = {"hi": {"कि", "और", "लेकिन", "पर", "क्योंकि"}, "en": {"that", "and", "but", "because"}}
CONNECTIVE_UPOS = {"CCONJ", "SCONJ"}
CHAIN_DEPRELS = {"aux", "aux:pass", "cop", "compound"}
HI_CONVERB_MARKS = {"कर", "के", "करके"}
SUBJ_DEPRELS = {"nsubj", "nsubj:pass", "csubj", "csubj:pass", "expl"}
HI_NONAGREEING_CASE_MARKS = {"ने", "को", "से"}
HI_NONAGREEING_CASES = {"Erg", "Dat"}
HI_NONPREDICATE_DEPRELS = {"amod", "acl", "nmod", "compound", "obl", "nsubj", "nsubj:pass", "case", "fixed"}
HI_PRODROP_DEPRELS = {"root", "conj", "ccomp", "parataxis", "acl:relcl"}
HI_SUBORDINATORS = {"जब", "जहाँ", "जहां", "जैसे", "ज्यों", "अगर", "यदि", "कि", "जबकि", "ताकि", "चूँकि", "चूंकि",
                    "मानो", "मानों"}
HI_PARTICIPIAL_AUX = {"हुआ", "हुए", "हुई", "हुईं"}
SHINGLE_N = 5
DUP_THRESHOLD = 0.8

PLACEHOLDER_RE = re.compile(r"\[(?:URL|EMAIL|PHONE|HANDLE)\]")
URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.I)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_CANDIDATE_RE = re.compile(r"(?<![\d])\+?\d[\d \-().]{8,}\d(?![\d])")
DANDA_RE = re.compile(r"(?<=\S)([।॥])")
FUSED_SENTENCE_RE = re.compile(r"([.।?!])(?=[A-Za-zऀ-ॿ])")
HI_LATIN_STOP_RE = re.compile(r"([ऀ-ॣॱ-ॿ]+)[ \t]*((?:[.?!][ \t]*)+)(?=([ऀ-ॣॱ-ॿ])?)")
HI_ABBREVIATIONS = {"डॉ", "डा", "प्रो", "श्री", "स्व", "पं", "सं", "कु", "पृ", "क्र", "नं", "मो", "प्र", "ई", "उ",
                    "ए", "बी", "सी", "डी", "एफ", "जी", "एच", "आई", "जे", "के", "एल", "एम", "एन", "ओ", "पी", "क्यू",
                    "आर", "एस", "टी", "यू", "वी", "डब्ल्यू", "एक्स", "वाई", "जेड", "ज़ेड"}
SPACES_RE = re.compile(r"[ \t ]+")


def strip_phone(match):
    s = match.group(0)
    return "" if sum(c.isdigit() for c in s) >= 10 else s


def hi_stop(match):
    word, marks, nxt = match.group(1), match.group(2), match.group(3)
    if marks.strip() == "." and word in HI_ABBREVIATIONS:
        return match.group(0)
    return f"{word} {marks.strip()}" + ("\n" if nxt else " ")


def prepare_text(text, lang=None):
    t = unicodedata.normalize("NFC", text)
    t = PLACEHOLDER_RE.sub(" ", t)
    t = URL_RE.sub(" ", t)
    t = EMAIL_RE.sub(" ", t)
    t = PHONE_CANDIDATE_RE.sub(strip_phone, t)
    t = DANDA_RE.sub(r" \1", t)
    if lang == "hi":
        t = HI_LATIN_STOP_RE.sub(hi_stop, t)
    t = FUSED_SENTENCE_RE.sub(r"\1 ", t)
    lines = [SPACES_RE.sub(" ", ln).strip() for ln in t.split("\n")]
    return "\n\n".join(ln for ln in lines if ln)


def load_records(path):
    keep, aside, skipped = [], [], Counter()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r["eligibility_status"] != ELIGIBLE:
                skipped[r["eligibility_status"]] += 1
            elif r["lang_provisional"] in SET_ASIDE:
                aside.append(r)
            elif r["lang_provisional"] in LANG_MAP:
                keep.append(r)
            else:
                skipped["eligible_but_lang_" + r["lang_provisional"]] += 1
    return keep, aside, skipped


def make_pipelines(langs):
    import stanza
    return {lg: stanza.Pipeline(lg, processors=PROCESSORS[lg], download_method=None, verbose=False) for lg in langs}


def cache_key(lang, text, stanza_version):
    h = hashlib.sha256()
    for part in (str(CACHE_FORMAT), stanza_version, lang, PROCESSORS[lang], text):
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


def doc_to_sentences(doc):
    sents = []
    for s in doc.sentences:
        words = []
        for tok_i, tok in enumerate(s.tokens):
            for w in tok.words:
                words.append(dict(id=w.id, text=w.text, lemma=w.lemma, upos=w.upos, feats=w.feats or "",
                                  head=w.head, deprel=w.deprel, tok=tok_i,
                                  start=tok.start_char, end=tok.end_char))
        sents.append(words)
    return sents


def parse_cached(rec, lang, text, nlp, cache_dir, stanza_version):
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", rec["record_id"])
    path = cache_dir / lang / f"{safe}.json"
    key = cache_key(lang, text, stanza_version)
    if path.exists():
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
            if cached.get("key") == key:
                return cached["sentences"], True
        except (json.JSONDecodeError, KeyError):
            pass
    sents = doc_to_sentences(nlp(text))
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"key": key, "record_id": rec["record_id"], "sentences": sents}, ensure_ascii=False),
                   encoding="utf-8")
    tmp.replace(path)
    return sents, False


def feats_dict(w):
    return dict(kv.split("=", 1) for kv in w["feats"].split("|") if "=" in kv)


def has_finite_morph(w, lang):
    if w["upos"] not in ("VERB", "AUX"):
        return False
    f = feats_dict(w)
    if f.get("VerbForm") == "Fin" or "Mood" in f or ("Tense" in f and f.get("VerbForm") != "Part"):
        return True
    return lang == "hi" and f.get("Aspect") == "Perf" and f.get("VerbForm") in (None, "Part")


def subject_agrees(subj, subj_children, participles):
    cases = set(feats_dict(subj).get("Case", "").split(","))
    marks = {c["text"] for c in subj_children if c["deprel"] == "case"} & HI_NONAGREEING_CASE_MARKS
    if "Erg" in cases or "ने" in marks:
        return any(feats_dict(x).get("Aspect") == "Perf" for x in participles)
    if cases & HI_NONAGREEING_CASES or marks:
        return True
    g = feats_dict(subj).get("Gender")
    return g is None or any(feats_dict(x).get("Gender") in (None, g) for x in participles)


def is_finite(w, children, lang, subj=None, subj_children=()):
    is_pred = w["upos"] == "VERB" or (w["upos"] == "AUX" and w["deprel"] not in CHAIN_DEPRELS) \
        or any(c["deprel"] == "cop" for c in children)
    if not is_pred or w["deprel"] in CHAIN_DEPRELS:
        return False
    chain = [w] + [c for c in children if c["deprel"] in CHAIN_DEPRELS and c["upos"] in ("VERB", "AUX")]
    if lang == "en":
        return any(feats_dict(x).get("VerbForm") == "Fin" or "Mood" in feats_dict(x) for x in chain)
    if feats_dict(w).get("VerbForm") == "Conv" or any(c["deprel"] == "mark" and c["text"] in HI_CONVERB_MARKS
                                                      for c in children):
        return False
    if any(f.get("VerbForm") == "Fin" or "Mood" in f or "Tense" in f for f in map(feats_dict, chain)):
        return True
    participles = [x for x in chain if feats_dict(x).get("Aspect") in ("Perf", "Imp")]
    if w["deprel"] in HI_NONPREDICATE_DEPRELS or not participles:
        return False
    if any(x["text"] in HI_PARTICIPIAL_AUX for x in chain[1:]):
        return False
    if w["deprel"] != "root" and feats_dict(w).get("Aspect") == "Imp" and any(c["text"] == "ही" for c in children):
        return False
    if subj is not None and any(c["deprel"] == "case" and c["text"] in ("के", "की", "का") for c in subj_children):
        return False
    if w["deprel"] in HI_PRODROP_DEPRELS or any(
            c["text"] in HI_SUBORDINATORS or (c["deprel"] == "mark" and c["text"] not in HI_CONVERB_MARKS)
            for c in children):
        return True
    if subj is None:
        subj = next((c for c in children if c["deprel"] == "compound" and c["upos"] in ("NOUN", "PROPN")), None)
        subj_children = ()
    return subj is not None and subject_agrees(subj, subj_children, participles)


def subject_source(w, by_id, own_subj):
    if w["id"] in own_subj:
        return own_subj[w["id"]], w["id"]
    seen = set()
    while w["deprel"] == "conj" and w["head"] in by_id and w["head"] not in seen:
        seen.add(w["head"])
        w = by_id[w["head"]]
        if w["id"] in own_subj:
            return own_subj[w["id"]], w["id"]
    return None, None


def tree_units(words, lang):
    by_id = {w["id"]: w for w in words}
    kids = defaultdict(list)
    for w in words:
        kids[w["head"]].append(w)
    own_subj = {}
    for w in words:
        if w["deprel"] in SUBJ_DEPRELS and w["head"] in by_id:
            own_subj.setdefault(w["head"], w)
    finite, inherited = set(), {}
    for w in words:
        subj, src = subject_source(w, by_id, own_subj)
        if is_finite(w, kids[w["id"]], lang, subj, kids[subj["id"]] if subj else ()):
            finite.add(w["id"])
            if w["deprel"] == "conj" and w["id"] not in own_subj:
                inherited[w["id"]] = src
    units = defaultdict(list)
    for w in words:
        cur, seen = w, set()
        while cur is not None and cur["id"] not in finite and cur["id"] not in seen:
            seen.add(cur["id"])
            cur = by_id.get(cur["head"])
        units[cur["id"] if cur is not None and cur["id"] in finite else None].append(w["id"])
    return units, finite, inherited


def connective_split(ids, by_id, lang):
    finite_pos = [i for i, wid in enumerate(ids) if has_finite_morph(by_id[wid], lang)]
    cuts = []
    start = 0
    for i, wid in enumerate(ids):
        w = by_id[wid]
        token = w["text"] if lang == "hi" else w["text"].lower()
        if i <= start or token not in CONNECTIVES[lang] or w["upos"] not in CONNECTIVE_UPOS:
            continue
        nxt = [p for p in finite_pos if p > i]
        if any(start <= p < i for p in finite_pos) and nxt:
            cuts.append(i)
            start = i
    bounds = [0] + cuts + [len(ids)]
    return [(ids[a:b], by_id[ids[a]]["text"] if a in cuts else None) for a, b in zip(bounds, bounds[1:])]


def span_text(ids, by_id, text):
    out, prev_tok, prev_end = [], None, None
    for wid in ids:
        w = by_id[wid]
        if w["tok"] == prev_tok:
            continue
        if prev_tok is not None:
            out.append(text[prev_end:w["start"]] if w["tok"] == prev_tok + 1 else " ")
        out.append(text[w["start"]:w["end"]])
        prev_tok, prev_end = w["tok"], w["end"]
    return "".join(out).strip()


def strip_edges(s):
    a, b = 0, len(s)
    while a < b and (s[a].isspace() or unicodedata.category(s[a]).startswith("P")):
        a += 1
    while b > a and (s[b - 1].isspace() or unicodedata.category(s[b - 1]).startswith("P")):
        b -= 1
    return s[a:b]


def full_span(ids, by_id, text):
    return text[by_id[ids[0]]["start"]:by_id[ids[-1]]["end"]]


def is_discontinuous(ids, by_id):
    core = [i for i in ids if by_id[i]["upos"] != "PUNCT"] or ids
    span = [i for i in range(core[0], core[-1] + 1) if by_id[i]["upos"] != "PUNCT"]
    return core != span


def attach_stray_punct(units, by_id):
    loose = units.get(None)
    if not loose or len(units) == 1 or any(by_id[i]["upos"] != "PUNCT" for i in loose):
        return
    owner = {i: h for h, ids in units.items() if h is not None for i in ids}
    for i in loose:
        h = next((owner[j] for j in range(i - 1, 0, -1) if j in owner), None)
        if h is None:
            h = next(owner[j] for j in range(i + 1, max(by_id) + 1) if j in owner)
        units[h].append(i)
    del units[None]


def repair_copular_complement(units, by_id):
    owner = {i: h for h, ids in units.items() for i in ids}

    def ancestors(h):
        out, cur, seen = [], h, set()
        while cur is not None and cur not in seen:
            seen.add(cur)
            g = by_id[cur]["head"]
            cur = owner.get(g) if g in by_id else None
            out.append(cur)
        return out

    moved = 0
    for h in [k for k in units if k is not None]:
        cops = [w["id"] for w in by_id.values() if w["head"] == h and w["deprel"] == "cop"]
        if not cops:
            continue
        lo, hi = sorted((h, cops[0]))
        anc = set(ancestors(h))
        for i in range(lo + 1, hi):
            o = owner.get(i)
            if o != h and o in anc and i not in units:
                units[o].remove(i)
                units[h].append(i)
                owner[i] = h
                moved += 1
    for k in [k for k, ids in units.items() if not ids]:
        del units[k]
    return moved


def segment(rec, lang, sents, text):
    pieces = []
    n_conn_splits = n_punct_only = 0
    for si, words in enumerate(sents):
        if not any(strip_edges(w["text"]) for w in words):
            n_punct_only += 1
            continue
        by_id = {w["id"]: w for w in words}
        units, finite, inherited = tree_units(words, lang)
        repair_copular_complement(units, by_id)
        attach_stray_punct(units, by_id)
        for head, ids in units.items():
            ids = sorted(ids)
            parts = connective_split(ids, by_id, lang) if head is not None else [(ids, None)]
            n_conn_splits += len(parts) - 1
            owner = next((k for k, (pids, _) in enumerate(parts) if head in pids), 0)
            for k, (pids, conn) in enumerate(parts):
                pieces.append(dict(sent_index=si, ids=pids, by_id=by_id, head=head if k == owner else None,
                                   inherit_from=inherited.get(head) if k == owner else None,
                                   is_finite=head is not None, split=("connective:" + conn) if conn else "tree"))
    pieces.sort(key=lambda p: (p["sent_index"], p["ids"][0]))
    cid_of_word = {}
    for pos, p in enumerate(pieces, 1):
        p["cid"] = f"{rec['record_id']}#{pos:04d}"
        for i in p["ids"]:
            cid_of_word[(p["sent_index"], i)] = p["cid"]
    clauses, tokens = [], []
    for pos, p in enumerate(pieces, 1):
        cid, ids, by_id = p["cid"], p["ids"], p["by_id"]
        assert all(a < b for a, b in zip(ids, ids[1:])), f"{cid}: word order broken"
        head = by_id[p["head"]] if p["head"] is not None else None
        src = p["inherit_from"]
        clauses.append(dict(record_id=rec["record_id"], lang=lang, clause_id=cid, position=pos,
                            clause_text=strip_edges(span_text(ids, by_id, text)),
                            span_text=full_span(ids, by_id, text),
                            n_tokens=sum(1 for i in ids if by_id[i]["upos"] != "PUNCT"),
                            sent_index=p["sent_index"], is_finite=p["is_finite"],
                            head_lemma=head["lemma"] if head else None, split=p["split"],
                            discontinuous=is_discontinuous(ids, by_id),
                            subject_inherited_from=cid_of_word[(p["sent_index"], src)] if src else None,
                            conj_without_subject=bool(head and head["deprel"] == "conj" and src is None
                                                      and not has_own_subject(head, by_id))))
        for i in ids:
            w = by_id[i]
            tokens.append([cid, w["id"], w["text"], w["lemma"], w["upos"], w["feats"], w["head"], w["deprel"]])
    return clauses, tokens, n_conn_splits, n_punct_only


def has_own_subject(w, by_id):
    return any(x["head"] == w["id"] and x["deprel"] in SUBJ_DEPRELS for x in by_id.values())


def shingles(text, lang):
    toks = (text.lower() if lang == "en" else text).split()
    return {" ".join(toks[i:i + SHINGLE_N]) for i in range(max(1, len(toks) - SHINGLE_N + 1))}


def near_duplicates(texts):
    from datasketch import MinHash, MinHashLSH
    lsh = MinHashLSH(threshold=DUP_THRESHOLD, num_perm=256)
    sh, mh = {}, {}
    for rid, (lang, text) in texts.items():
        sh[rid] = shingles(text, lang)
        m = MinHash(num_perm=256)
        for s in sh[rid]:
            m.update(s.encode("utf-8"))
        mh[rid] = m
        lsh.insert(rid, m)
    pairs = set()
    for rid in texts:
        for other in lsh.query(mh[rid]):
            if other != rid:
                pairs.add(tuple(sorted((rid, other))))
    out = []
    for a, b in sorted(pairs):
        exact = len(sh[a] & sh[b]) / len(sh[a] | sh[b])
        est = mh[a].jaccard(mh[b])
        if max(exact, est) >= DUP_THRESHOLD:
            out.append(dict(a=a, b=b, lang_a=texts[a][0], lang_b=texts[b][0], minhash=round(est, 3),
                            exact=round(exact, 3)))
    return out


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_summary(path, args, input_hash, stats, dups, aside, skipped, stanza_version, elapsed):
    L = ["# Preprocess summary (Stage 3)", "",
         f"- Input: `{args.inp}` sha256 `{input_hash[:16]}…`; records with eligibility_status = `{ELIGIBLE}` only",
         f"- Stanza {stanza_version}; processors hi `{PROCESSORS['hi']}`, en `{PROCESSORS['en']}`",
         f"- Run: {time.strftime('%Y-%m-%d %H:%M')} ({elapsed:.0f} s; {stats['cache_hits']} of "
         f"{stats['n_texts']} parses from cache)",
         "- All language labels are `lang_provisional` (rule-based, not human-reviewed).", "",
         "## Counts", "",
         "| lang | texts | clause units | finite | non-finite units | connective splits | discontinuous "
         "| tokens (excl. punct) | words incl. punct | clauses/text mean | median | min | max |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for lg in ("hi", "en"):
        s = stats[lg]
        per = s["per_text"] or [0]
        L.append(f"| {lg} | {s['texts']} | {s['clauses']:,} | {s['finite']:,} | {s['nonfinite']:,} | "
                 f"{s['conn']:,} | {s['discont']:,} | {s['tokens']:,} | {s['words']:,} | "
                 f"{statistics.mean(per):.1f} | {statistics.median(per):g} | {min(per)} | {max(per)} |")
    L += ["", "Clause units = finite-head units plus non-finite units (words with no finite ancestor: headings, "
          "verbless lines), kept so no text is lost; filter on `is_finite` when only clauses are wanted. "
          "Token counts are not comparable across languages (Hindi postpositions and auxiliaries are separate words).",
          "", "## Coordinated predicates and edge cases", "",
          "| lang | conj units with inherited subject | conj units with no overt subject anywhere | "
          "punctuation-only sentences skipped |", "|---|---|---|---|"]
    L += [f"| {lg} | {stats[lg]['inherited']:,} | {stats[lg]['conj_nosubj']:,} | {stats[lg]['punct_only']:,} |"
          for lg in ("hi", "en")]
    L += ["", "`subject_inherited_from` points to the clause whose overt subject a subject-less conj predicate "
          "shares (units are not merged). Hindi finiteness: a tensed form in the verb chain (aux, copula, "
          "finite verb), or a bare participle in a main/coordinate/complement/relative slot or a subordinated "
          "advcl (subjects may be dropped), or elsewhere a participle agreeing with its subject. Adverbial "
          "participles (-ए/-ते हुए/-ते ही, converbs) are not finite. See `is_finite` for the exact rule.",
          "", f"## Near-duplicate texts (MinHash, word {SHINGLE_N}-gram shingles, Jaccard >= {DUP_THRESHOLD})", ""]
    if dups:
        L += ["| record a | record b | lang | MinHash est. | exact Jaccard |", "|---|---|---|---|---|"]
        L += [f"| {d['a']} | {d['b']} | {d['lang_a']}/{d['lang_b']} | {d['minhash']} | {d['exact']} |" for d in dups]
        L.append("\nReported only; both records are still in clauses.jsonl. Decide by hand.")
    else:
        L.append("None found.")
    L += ["", "## Set aside", ""]
    L += [f"- `{r['record_id']}` ({r['lang_provisional']}, {r['n_words']} words) -> `set_aside_romanized.jsonl`; "
          "to be transliterated before parsing." for r in aside] or ["None."]
    L += ["", "## Not processed (eligibility)", ""]
    L += [f"- {k}: {v}" for k, v in sorted(skipped.items())]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def show_samples(clauses, n_hi, n_en, seed):
    rng = random.Random(seed)
    for lg, n in (("hi", n_hi), ("en", n_en)):
        pool = [c for c in clauses if c["lang"] == lg]
        print(f"\n=== {n} random {lg} clause units (seed {seed}) ===")
        for c in rng.sample(pool, min(n, len(pool))):
            tag = "" if c["is_finite"] else " [non-finite]"
            print(f"{c['record_id']}  #{c['position']}{tag}  {c['clause_text']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--in", dest="inp", default="data/clean/blogs_merged.jsonl")
    ap.add_argument("--out", default="data/processed/clauses.jsonl")
    ap.add_argument("--show-hi", type=int, default=20)
    ap.add_argument("--show-en", type=int, default=10)
    ap.add_argument("--seed", type=int, default=20261009)
    args = ap.parse_args()

    import stanza
    out = Path(args.out)
    out_dir = out.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = out_dir / "stanza_cache"
    t0 = time.time()

    recs, aside, skipped = load_records(args.inp)
    with open(out_dir / "set_aside_romanized.jsonl", "w", encoding="utf-8") as fh:
        for r in aside:
            fh.write(json.dumps(dict(record_id=r["record_id"], lang_provisional=r["lang_provisional"],
                                     n_words=r["n_words"], note="romanized Hindi: not parsed; transliterate to "
                                     "Devanagari in a later step, then re-run preprocess"), ensure_ascii=False) + "\n")

    prepared = {r["record_id"]: (LANG_MAP[r["lang_provisional"]],
                                 prepare_text(r["text_clean"], LANG_MAP[r["lang_provisional"]])) for r in recs}
    nlps = make_pipelines(sorted({lg for lg, _ in prepared.values()}))

    stats = {lg: dict(texts=0, clauses=0, finite=0, nonfinite=0, conn=0, discont=0, tokens=0, words=0, per_text=[],
                      inherited=0, conj_nosubj=0, punct_only=0)
             for lg in ("hi", "en")}
    stats["cache_hits"], stats["n_texts"] = 0, len(recs)
    all_clauses = []
    with open(out, "w", encoding="utf-8") as fc, open(out_dir / "tokens.csv", "w", encoding="utf-8", newline="") as ft:
        tw = csv.writer(ft)
        tw.writerow(["clause_id", "token_index", "token", "lemma", "upos", "feats", "head", "deprel"])
        for n, r in enumerate(recs, 1):
            lang, text = prepared[r["record_id"]]
            sents, hit = parse_cached(r, lang, text, nlps[lang], cache_dir, stanza.__version__)
            stats["cache_hits"] += hit
            clauses, tokens, n_conn, n_punct = segment(r, lang, sents, text)
            for c in clauses:
                fc.write(json.dumps(c, ensure_ascii=False) + "\n")
            tw.writerows(tokens)
            s = stats[lang]
            s["texts"] += 1
            s["clauses"] += len(clauses)
            s["finite"] += sum(c["is_finite"] for c in clauses)
            s["nonfinite"] += sum(not c["is_finite"] for c in clauses)
            s["conn"] += n_conn
            s["discont"] += sum(c["discontinuous"] for c in clauses)
            s["inherited"] += sum(c["subject_inherited_from"] is not None for c in clauses)
            s["conj_nosubj"] += sum(c["conj_without_subject"] for c in clauses)
            s["punct_only"] += n_punct
            s["tokens"] += sum(c["n_tokens"] for c in clauses)
            s["words"] += len(tokens)
            s["per_text"].append(len(clauses))
            all_clauses.extend(clauses)
            print(f"[{n}/{len(recs)}] {r['record_id']} {lang} {'cache' if hit else 'parsed'} "
                  f"{len(clauses)} units", file=sys.stderr)

    dups = near_duplicates(prepared)
    write_summary(out_dir / "preprocess_summary.md", args, file_sha256(args.inp), stats, dups, aside, skipped,
                  stanza.__version__, time.time() - t0)
    for lg in ("hi", "en"):
        s = stats[lg]
        print(f"{lg}: {s['texts']} texts, {s['clauses']} units ({s['finite']} finite), {s['tokens']} tokens")
    print(f"near-duplicate pairs: {len(dups)}; set aside: {len(aside)}; summary: {out_dir / 'preprocess_summary.md'}")
    show_samples(all_clauses, args.show_hi, args.show_en, args.seed)


if __name__ == "__main__":
    main()
