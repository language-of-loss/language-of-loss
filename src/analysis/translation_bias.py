"""Output 8 (part 1): does a translated resource miss native Hindi grief? NRC-Hindi against our native lexicon, recall"""
import argparse
import csv
import hashlib
import json
import math
import random
import re
import sys
import time
import unicodedata
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lexmatch as LM

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"
EXT = ROOT / "data" / "external"
DRY = "dry run (50 dev clauses; reference = our lexicon's matches): pipeline check, not a result"
NRC_PATH = EXT / "nrc_emolex" / "NRC-Emotion-Lexicon" / "OneFilePerLanguage" / "Hindi-NRC-EmoLex.txt"
HSL_DIR = EXT / "hindi_subjective_lexicon"
NRC_EMOTIONS = ("anger", "anticipation", "disgust", "fear", "joy", "sadness", "surprise", "trust", "negative")
NUKTA = "़"
DEVA = "ऀ-ॿ"
IWN_HINDI = Path.home() / "iwn_data" / "synsets" / "all.hindi"
CHANNELS = PROC / "channels"
SHORT = PROC / "shortform"
AGREEMENT = ROOT / "results" / "agreement" / "agreement_summary_gold_sheet_v1.csv"
NLLB = dict(repo="facebook/nllb-200-distilled-600M", revision="f8d333a098d19b4fd9a8b18f94170487ad3f821d",
            licence="CC-BY-NC-4.0")
REFUSED = (f"recall against gold refused: {AGREEMENT.relative_to(ROOT)} does not hold real agreement statistics yet "
           "(study protocol: no resource comparison against gold before human agreement)")


def norm(w):
    return unicodedata.normalize("NFC", w or "").replace(NUKTA, "").strip("\"'“”‘’()[].,;:!?।-")


def words_of(text):
    return [x for x in (norm(t) for t in re.split(r"[\s,;:!?।\"'“”‘’()\[\]]+", text or "")) if x]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path, rows, status):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [dict(r, status=status) for r in rows] or [dict(status=status)]
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: (float(f"{v:.6g}") if isinstance(v, float) and math.isfinite(v) else v)
                        for k, v in r.items()})
    return path

def is_tolerated(molecule_row):
    return molecule_row["molecule"].strip().startswith("(tolerated)")


def native_only_entries(molecule_rows, lexicon_rows, include_tolerated=False):
    lang = {r["entry_id"]: r["lang"] for r in lexicon_rows}
    out = set()
    for r in molecule_rows:
        if is_tolerated(r) and not include_tolerated:
            continue
        users = r["used_in"].split()
        if users and not any(lang.get(u) == "en" for u in users):
            out |= {u for u in users if lang.get(u) == "hi"}
    return out


def item_class(matched_hi_entries, native):
    if not matched_hi_entries:
        return "unmatched"
    return "native_only" if set(matched_hi_entries) & native else "translatable"

def load_nrc(path=NRC_PATH):
    path = Path(path)
    if not path.exists():
        return None
    out = {}
    with open(path, encoding="utf-8") as fh:
        rows = csv.DictReader(fh, delimiter="\t")
        for r in rows:
            emo = {e for e in NRC_EMOTIONS if r.get(e) == "1"}
            hw = norm(r.get("Hindi Word", ""))
            if emo and hw and re.search(f"[{DEVA}]", hw):
                out.setdefault(hw, set()).update(emo)
    return out


def load_hsl(directory=HSL_DIR):
    directory = Path(directory)
    files = sorted(directory.glob("*.txt")) if directory.exists() else []
    if not files:
        return None
    out = {}
    for f in files:
        for line in f.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) >= 3 and parts[2].strip().lower() not in ("", "neutral", "0", "n"):
                out[norm(parts[0])] = parts[2].strip()
    return out


def phrase_detector(phrases):
    singles = {p for p in phrases if " " not in p}
    multi = [tuple(p.split()) for p in phrases if " " in p]

    def detect(text):
        ws = words_of(text)
        if singles & set(ws):
            return True
        return any(tuple(ws[i:i + len(m)]) == m for m in multi for i in range(len(ws) - len(m) + 1))
    return detect


def load_iwn(path=IWN_HINDI):
    path = Path(path)
    if not path.exists():
        return None
    by_lemma, lemmas = defaultdict(set), {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) < 2 or not parts[0].strip().isdigit():
            continue
        words = [norm(w.replace("_", " ")) for w in parts[1].split(",")]
        lemmas[parts[0]] = [w for w in words if w]
        for w in lemmas[parts[0]]:
            by_lemma[w].add(parts[0])
    return dict(by_lemma=dict(by_lemma), lemmas=lemmas)


def english_headwords(lexicon_rows):
    out = set()
    for r in lexicon_rows:
        if r["lang"] != "en":
            continue
        for v in r["headword_en"].split("/"):
            v = re.sub(r"\([^)]*\)", " ", v).strip().lower()
            if v and not LM.PLACEHOLDER.search(v) and len(v.split()) <= 3:
                out.add(v)
    return sorted(out)


def nllb_en_hi(texts, batch=16):
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    kw = dict(revision=NLLB["revision"], local_files_only=True)
    tok = AutoTokenizer.from_pretrained(NLLB["repo"], src_lang="eng_Latn", **kw)
    model = AutoModelForSeq2SeqLM.from_pretrained(NLLB["repo"], **kw).eval()
    out = []
    for i in range(0, len(texts), batch):
        enc = tok(texts[i:i + batch], return_tensors="pt", padding=True)
        with torch.no_grad():
            gen = model.generate(**enc, num_beams=4, max_new_tokens=24,
                                 forced_bos_token_id=tok.convert_tokens_to_ids("hin_Deva"))
        out += tok.batch_decode(gen, skip_special_tokens=True)
    return out


def bridge(heads, cache_path, translate=None):
    cache_path = Path(cache_path)
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    todo = [h for h in heads if h not in cache]
    if todo:
        cache.update(zip(todo, (translate or nllb_en_hi)(todo)))
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=0, sort_keys=True) + "\n", encoding="utf-8")
    return {h: cache[h] for h in heads}


def wordnet_route(translations, iwn):
    out = set()
    for hi in translations:
        t = norm(hi.strip().rstrip("।"))
        if not t:
            continue
        out.add(t)
        for sid in iwn["by_lemma"].get(t, ()):
            out |= set(iwn["lemmas"][sid])
    return out


class TermList:

    def __init__(self, terms):
        self.first = defaultdict(list)
        for t in terms:
            words = [LM.norm_word(w, "hi") for w in str(t).split()]
            if words and all(words):
                self.first[words[0]].append(words)
        self.n_terms = sum(len(v) for v in self.first.values())

    def hits(self, toks):
        for i, tok in enumerate(toks):
            for w in tok:
                for words in self.first.get(w, ()):
                    if len(words) == 1 or (i + len(words) <= len(toks)
                                           and all(words[k] in toks[i + k] for k in range(1, len(words)))):
                        return True
        return False

class LexScorer:

    def __init__(self, lex, nlp=None):
        self.lex, self.nlp = lex, nlp or {}

    def tokens(self, text, lang):
        if lang not in self.nlp:
            return [(w, w) for w in words_of(text)]
        from preprocess import prepare_text
        doc = self.nlp[lang](prepare_text(text, lang))
        return [(w.text, w.lemma or w.text) for s in doc.sentences for w in s.words if w.upos != "PUNCT"]

    def score(self, text, lang):
        clause = dict(clause_text=text, lang=lang)
        m = LM.match_clause(clause, self.tokens(text, lang), self.lex)
        f = LM.clause_features(clause, m, {}, self.lex)
        return dict(entries=set(m), comps={c[5:] for c, v in f.items() if c.startswith("comp_") and v},
                    features={k: v for k, v in f.items() if v})

def paired_recall_bootstrap(items, resources, B=2000, seed=20261010):
    pos = [it for it in items if it["ref"] and it["cls"] in ("native_only", "translatable")]
    rng = np.random.default_rng(seed)
    cls = np.array([it["cls"] == "native_only" for it in pos])
    det = {r: np.array([bool(it["detected"].get(r)) for it in pos]) for r in resources}

    def recalls(idx):
        out = {}
        for r in resources:
            d, c = det[r][idx], cls[idx]
            n_n, n_t = c.sum(), (~c).sum()
            out[r] = (d[c].mean() if n_n else math.nan, d[~c].mean() if n_t else math.nan)
        return out
    point = recalls(np.arange(len(pos)))
    reps = [recalls(rng.integers(0, len(pos), len(pos))) for _ in range(B)] if pos else []
    rows = []

    def ci(vals):
        v = np.array([x for x in vals if math.isfinite(x)])
        return (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) if len(v) else (math.nan, math.nan)
    for r in resources:
        n_native, n_trans = int(cls.sum()), int((~cls).sum())
        for j, name in ((0, "recall_native_only"), (1, "recall_translatable")):
            lo, hi = ci([x[r][j] for x in reps])
            rows.append(dict(resource=r, quantity=name, estimate=point[r][j], lo=lo, hi=hi,
                             n_items=n_native if j == 0 else n_trans))
        gap = point[r][1] - point[r][0]
        lo, hi = ci([x[r][1] - x[r][0] for x in reps])
        rows.append(dict(resource=r, quantity="gap_translatable_minus_native", estimate=gap, lo=lo, hi=hi,
                         n_items=len(pos)))
        if r != "lexicon" and "lexicon" in resources:
            d = gap - (point["lexicon"][1] - point["lexicon"][0])
            lo, hi = ci([(x[r][1] - x[r][0]) - (x["lexicon"][1] - x["lexicon"][0]) for x in reps])
            rows.append(dict(resource=r, quantity="gap_minus_lexicon_gap", estimate=d, lo=lo, hi=hi,
                             n_items=len(pos)))
    return rows

def item_record(clause_id, stage5_matched, detected, native, native_tol, gold=None):
    ref = bool(stage5_matched) if gold is None else gold[clause_id]
    return dict(clause_id=clause_id, cls=item_class(stage5_matched, native),
                cls_tolerated=item_class(stage5_matched, native_tol), ref=ref, detected=detected)


def gold_items(gold, clauses, cf):
    by_id = {c["clause_id"]: c for c in clauses}
    hi_entries = [e for e in next(iter(cf.values()), {}) if e.startswith(("L-HI", "P-HI"))]
    return [(by_id[k], [e for e in hi_entries if cf.get(k, {}).get(e) == "1"]) for k in gold
            if k in by_id and by_id[k]["lang"] == "hi"]


def sample_dry_run(clauses, cf, native, n=50, seed=20261010):
    from gold import split_of
    hi_entries = [c for c in (next(iter(cf.values()), {}) or {}) if c.startswith(("L-HI", "P-HI"))]
    pools = defaultdict(list)
    for c in clauses:
        if c["lang"] != "hi" or not c["is_finite"] or split_of(c["record_id"]) != "dev":
            continue
        row = cf.get(c["clause_id"], {})
        matched = [e for e in hi_entries if row.get(e) == "1"]
        pools[item_class(matched, native)].append((c, matched))
    rng = random.Random(seed)
    want = {"native_only": 15, "translatable": 25}
    picked = []
    for k in ("native_only", "translatable"):
        picked += rng.sample(pools[k], min(want[k], len(pools[k])))
    picked += rng.sample(pools["unmatched"], min(n - len(picked), len(pools["unmatched"])))
    return picked, {k: len(v) for k, v in pools.items()}


def frozen_lexicon_ok():
    import freeze
    d = freeze.diff(freeze.recorded(), freeze.current())
    if d:
        raise SystemExit("lexicon differs from lexicon/FREEZE.md, entry classes would not be the frozen ones:\n  "
                         + "\n  ".join(d))
    return {f: h for f, (h, _) in freeze.current().items()}


def entry_classes(lexicon_rows, molecule_rows):
    native, native_tol = native_only_entries(molecule_rows, lexicon_rows), native_only_entries(
        molecule_rows, lexicon_rows, include_tolerated=True)
    lang = {r["entry_id"]: r["lang"] for r in lexicon_rows}
    why = defaultdict(lambda: dict(strict=[], tolerated=[]))
    for m in molecule_rows:
        users = m["used_in"].split()
        if users and not any(lang.get(u) == "en" for u in users):
            for u in users:
                why[u]["tolerated" if is_tolerated(m) else "strict"].append(m["molecule"].replace("(tolerated)", "").strip())
    rows = []
    for r in lexicon_rows:
        if r["lang"] != "hi":
            continue
        e = r["entry_id"]
        rows.append(dict(entry_id=e, headword_deva=r["headword_deva"], pos=r["pos"],
                         entry_class="native_only" if e in native else "translatable",
                         entry_class_tolerated="native_only" if e in native_tol else "translatable",
                         native_molecules=" ".join(why[e]["strict"]), tolerated_molecules=" ".join(why[e]["tolerated"])))
    return rows


def entry_class_counts(rows):
    c = defaultdict(int)
    for r in rows:
        c[("strict", r["entry_class"])] += 1
        c[("tolerated", r["entry_class_tolerated"])] += 1
    return {f"{d}_{k}": c[(d, k)] for d in ("strict", "tolerated") for k in ("native_only", "translatable")}


def read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def scoring_units(clauses_path, tokens_path, short_dir):
    def units(clauses, toks, register):
        return [dict(clause=c, register=register, source=c.get("source", c["record_id"].split(":")[0]),
                     translit=int(bool(c.get("translit"))),
                     toks=[{LM.norm_word(f, "hi"), LM.norm_word(lm, "hi")} for f, lm in toks.get(c["clause_id"], [])])
                for c in clauses]
    out = units([c for c in read_jsonl(clauses_path) if c["lang"] == "hi"], LM.load_tokens(tokens_path), "long")
    short = Path(short_dir) / "clauses.jsonl"
    if short.exists():
        sc = [c for c in read_jsonl(short) if c["lang"] == "hi" and c.get("translit") and c.get("parse_lang", "hi") == "hi"]
        out += units(sc, LM.load_tokens(Path(short_dir) / "tokens.csv"), "short_romanised")
    return out


def score_units(units, lex, lists, native, native_tol):
    rows = []
    for u in units:
        m = sorted(e for e in LM.match_clause(u["clause"], u["toks"], lex) if e.startswith(("L-HI", "P-HI")))
        rows.append(dict(clause_id=u["clause"]["clause_id"], record_id=u["clause"]["record_id"], register=u["register"],
                         source=u["source"], translit=u["translit"], lexicon_entries=" ".join(m),
                         item_class=item_class(m, native), item_class_tolerated=item_class(m, native_tol),
                         det_lexicon=int(bool(m)), **{f"det_{k}": int(t.hits(u["toks"])) for k, t in lists.items()}))
    return rows


def scoring_summary(rows, resources):
    out = []
    for subset in ("long", "short_romanised", "all"):
        sub = [r for r in rows if subset == "all" or r["register"] == subset]
        for definition, col in (("strict", "item_class"), ("tolerated", "item_class_tolerated")):
            for cls in ("native_only", "translatable", "unmatched", "all"):
                part = [r for r in sub if cls == "all" or r[col] == cls]
                for res in resources:
                    out.append(dict(subset=subset, definition=definition, item_class=cls, resource=res,
                                    n_clauses=len(part), n_detected=sum(r[f"det_{res}"] for r in part)))
    return out


def stage5_agreement(rows, features_path):
    if not Path(features_path).exists():
        return None
    mine = {r["clause_id"]: set(r["lexicon_entries"].split()) for r in rows if r["register"] == "long"}
    same = n = 0
    with open(features_path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["clause_id"] in mine:
                n += 1
                same += mine[r["clause_id"]] == {k for k, v in r.items() if k.startswith(("L-HI", "P-HI")) and v == "1"}
    return dict(compared=n, identical=same)


def input_hashes(paths):
    return {str(Path(p).relative_to(ROOT) if str(p).startswith(str(ROOT)) else p): sha256(p)
            for p in paths if Path(p).exists()}


def run_score(args, translate=None):
    t0 = time.time()
    frozen = frozen_lexicon_ok()
    channels, results = Path(args.channels), Path(args.results)
    out_csv, out_man = channels / "a1_scores.csv", channels / "a1_scores_manifest.json"
    short = Path(args.shortform)
    nrc_path, iwn_path, hsl_dir = Path(args.nrc), Path(args.iwn), Path(args.hsl)
    inputs = input_hashes([args.clauses, Path(args.clauses).with_name("tokens.csv"), short / "clauses.jsonl",
                           short / "tokens.csv", nrc_path, iwn_path, *sorted(hsl_dir.glob("*.txt")),
                           Path(__file__)])
    key = hashlib.sha256(json.dumps(dict(inputs=inputs, lexicon=frozen), sort_keys=True).encode()).hexdigest()
    if not args.force and out_csv.exists() and out_man.exists():
        old = json.loads(out_man.read_text(encoding="utf-8"))
        if old.get("cache_key") == key:
            return dict(old, cached=True)

    lexicon_rows = list(csv.DictReader(open(ROOT / "lexicon" / "lexicon.csv", encoding="utf-8")))
    molecules = list(csv.DictReader(open(ROOT / "lexicon" / "molecules.csv", encoding="utf-8")))
    ec = entry_classes(lexicon_rows, molecules)
    write_csv(results / "a1_entry_classes.csv", ec, "frozen lexicon v0.2 (lexicon/FREEZE.md); classes from "
              "molecules.csv; machine-derived, unreviewed")
    native = {r["entry_id"] for r in ec if r["entry_class"] == "native_only"}
    native_tol = {r["entry_id"] for r in ec if r["entry_class_tolerated"] == "native_only"}

    resources, lists = {}, {}
    nrc = load_nrc(nrc_path)
    if nrc is not None:
        lists["nrc_hi"] = TermList(nrc)
        resources["nrc_hi"] = dict(path=str(nrc_path), sha256=sha256(nrc_path), terms=len(nrc))
    hsl = load_hsl(hsl_dir)
    if hsl is not None:
        lists["hsl"] = TermList(hsl)
        resources["hsl"] = dict(path=str(hsl_dir), terms=len(hsl))
    iwn = load_iwn(iwn_path)
    if iwn is not None:
        heads = english_headwords(lexicon_rows)
        tr = bridge(heads, channels / "a1_wordnet_bridge.json", translate)
        terms = wordnet_route(tr.values(), iwn)
        lists["wordnet"] = TermList(terms)
        resources["wordnet"] = dict(path=str(iwn_path), sha256=sha256(iwn_path), synsets=len(iwn["lemmas"]),
                                    english_headwords=len(heads),
                                    translations_in_wordnet=sum(norm(t) in iwn["by_lemma"] for t in tr.values()),
                                    terms=len(terms), bridge=dict(NLLB))
    unavailable = {k: v for k, v in (("nrc_hi", nrc), ("hsl", hsl), ("wordnet", iwn)) if v is None}

    units = scoring_units(args.clauses, Path(args.clauses).with_name("tokens.csv"), short)
    rows = score_units(units, LM.load_lexicon(ROOT / "lexicon" / "lexicon.csv"), lists, native, native_tol)
    status = "scoring only (no reference): detections, not recall; machine output, unreviewed"
    write_csv(out_csv, rows, status)
    names = ["lexicon"] + list(lists)
    write_csv(results / "a1_scoring_summary.csv", scoring_summary(rows, names)
              + [dict(subset="", definition="", item_class="", resource=r, n_clauses="", n_detected="unavailable")
                 for r in unavailable], status)
    count = defaultdict(int)
    for r in rows:
        count[r["register"]] += 1
    manifest = dict(status=status, run=time.strftime("%Y-%m-%d %H:%M"), seconds=round(time.time() - t0),
                    cache_key=key, inputs=inputs, lexicon_freeze=frozen, n_clauses=dict(count),
                    resources=resources, unavailable=sorted(unavailable), entry_classes=entry_class_counts(ec),
                    native_only_entries=sorted(native), native_only_entries_tolerated=sorted(native_tol),
                    preprocessing="Stanza tokens.csv; token = {norm_word(form), norm_word(lemma)}; term = contiguous "
                                  "run (lexmatch lemma channel); lexicon also uses its Stage 5 surface patterns",
                    stage5_agreement=stage5_agreement(rows, Path(args.clauses).with_name("clause_features.csv")),
                    detections={k: sum(r[f"det_{k}"] for r in rows) for k in names})
    out_man.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return dict(manifest, cached=False)


def items_from_scores(gold, score_rows, resources):
    return [dict(clause_id=r["clause_id"], cls=r["item_class"], cls_tolerated=r["item_class_tolerated"],
                 ref=gold[r["clause_id"]], detected={k: r[f"det_{k}"] == "1" for k in resources})
            for r in score_rows if r["clause_id"] in gold]


def agreement_ready(path=AGREEMENT):
    from predictions import tests_allowed
    return tests_allowed(path)


def run_gold(args):
    if not agreement_ready(args.agreement):
        raise SystemExit(REFUSED)
    cache = Path(args.channels) / "a1_scores.csv"
    if not cache.exists():
        raise SystemExit(f"{cache} not found: run translation_bias.py --score first")
    score_rows = list(csv.DictReader(open(cache, encoding="utf-8")))
    resources = [k[4:] for k in score_rows[0] if k.startswith("det_")]
    gold = {r["clause_id"]: r["emotional"] == "1" for r in csv.DictReader(open(args.gold, encoding="utf-8"))}
    items = items_from_scores(gold, score_rows, resources)
    status = "gold run, unreviewed resources"
    rows = recall_rows(items, ["lexicon"] + sorted(r for r in resources if r != "lexicon"), args.B, args.seed)
    write_csv(Path(args.results) / "a1_resource_recall.csv", rows, status)
    write_csv(Path(args.results) / "a1_items.csv", [dict(clause_id=it["clause_id"], item_class=it["cls"],
                                                         item_class_tolerated=it["cls_tolerated"],
                                                         reference=int(it["ref"]),
                                                         **{f"det_{k}": int(v) for k, v in it["detected"].items()})
                                                    for it in items], status)
    return dict(status=status, n_items=len(items), seconds=0, pools={})


def prepare(args):
    lexicon_rows = list(csv.DictReader(open(ROOT / "lexicon" / "lexicon.csv", encoding="utf-8")))
    molecules = list(csv.DictReader(open(ROOT / "lexicon" / "molecules.csv", encoding="utf-8")))
    native = native_only_entries(molecules, lexicon_rows)
    native_tol = native_only_entries(molecules, lexicon_rows, include_tolerated=True)
    clauses = [json.loads(l) for l in open(PROC / "clauses.jsonl", encoding="utf-8")]
    cf = {r["clause_id"]: r for r in csv.DictReader(open(PROC / "clause_features.csv", encoding="utf-8"))}
    if args.dry_run:
        picked, pools = sample_dry_run(clauses, cf, native, args.n, args.seed)
        ref = None
    else:
        gold = {r["clause_id"]: r["emotional"] == "1" for r in csv.DictReader(open(args.gold, encoding="utf-8"))}
        picked = gold_items(gold, clauses, cf)
        pools, ref = {}, gold
    import stanza
    nlp = {lg: stanza.Pipeline(lg, processors=p, download_method=None, verbose=False)
           for lg, p in (("hi", "tokenize,pos,lemma"), ("en", "tokenize,mwt,pos,lemma"))}
    scorer = LexScorer(LM.load_lexicon(ROOT / "lexicon" / "lexicon.csv"), nlp)
    return dict(lexicon_rows=lexicon_rows, native=native, native_tol=native_tol, picked=picked, pools=pools, ref=ref,
                texts=[c["clause_text"] for c, _ in picked], scorer=scorer,
                status=DRY if args.dry_run else "gold run, unreviewed resources")


def score_items(prep, detectors):
    items, native_scores = [], []
    for (c, matched), text in zip(prep["picked"], prep["texts"]):
        s = prep["scorer"].score(text, "hi")
        native_scores.append(s)
        det = {k: d(text) for k, d in detectors.items()}
        det["lexicon"] = bool(s["entries"])
        items.append(item_record(c["clause_id"], matched, det, prep["native"], prep["native_tol"], prep["ref"]))
    return items, native_scores


def recall_rows(items, resources, B, seed):
    rows = [dict(definition="strict", **r) for r in paired_recall_bootstrap(items, resources, B, seed)]
    rows += [dict(definition="tolerated", **r) for r in paired_recall_bootstrap(
        [dict(it, cls=it["cls_tolerated"]) for it in items], resources, B, seed)]
    return rows


def run(args):
    if not args.dry_run:
        return run_gold(args)
    out_res, out_priv = Path(args.results), Path(args.private)
    out_priv.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    prep = prepare(args)
    nrc, hsl = load_nrc(), load_hsl()
    detectors = {}
    if nrc is not None:
        detectors["nrc_hi"] = phrase_detector(set(nrc))
    if hsl is not None:
        detectors["hsl"] = phrase_detector(set(hsl))
    items, _ = score_items(prep, detectors)
    a_rows = recall_rows(items, ["lexicon"] + sorted(detectors), args.B, args.seed)
    unavailable = [r for r, v in (("nrc_hi", nrc), ("hsl", hsl)) if v is None]
    a_rows += [dict(definition="", resource=r, quantity="unavailable", estimate="", lo="", hi="", n_items=0)
               for r in unavailable]
    write_csv(out_res / "a1_resource_recall.csv", a_rows, prep["status"])
    write_csv(out_res / "a1_items.csv", [dict(clause_id=it["clause_id"], item_class=it["cls"],
                                              item_class_tolerated=it["cls_tolerated"], reference=int(it["ref"]),
                                              **{f"det_{k}": int(v) for k, v in it["detected"].items()})
                                         for it in items], prep["status"])
    manifest = dict(status=prep["status"], run=time.strftime("%Y-%m-%d %H:%M"), seconds=round(time.time() - t0),
                    n_items=len(items), pools=prep["pools"], native_only_entries=sorted(prep["native"]),
                    native_only_entries_tolerated=sorted(prep["native_tol"]),
                    resources=dict(nrc_hi=dict(path=str(NRC_PATH.relative_to(ROOT)), entries=len(nrc or {}),
                                               sha256=sha256(NRC_PATH) if NRC_PATH.exists() else None),
                                   hsl="unavailable" if hsl is None else len(hsl)))
    (out_priv / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def parser(doc=None):
    ap = argparse.ArgumentParser(description=(doc or __doc__).split("\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="50 dev clauses, reference = our lexicon's matches")
    ap.add_argument("--gold", help="CSV with clause_id, emotional (0/1): the reference for the real run")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--B", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=20261010)
    ap.add_argument("--results", default=str(ROOT / "results"))
    ap.add_argument("--private", default=str(PROC / "translation_bias"))
    ap.add_argument("--score", action="store_true", help="score every Hindi clause with every resource (cached)")
    ap.add_argument("--force", action="store_true", help="--score: ignore the cache")
    ap.add_argument("--clauses", default=str(PROC / "clauses.jsonl"), help="tokens.csv is read next to it")
    ap.add_argument("--shortform", default=str(SHORT))
    ap.add_argument("--channels", default=str(CHANNELS))
    ap.add_argument("--nrc", default=str(NRC_PATH))
    ap.add_argument("--hsl", default=str(HSL_DIR))
    ap.add_argument("--iwn", default=str(IWN_HINDI))
    ap.add_argument("--agreement", default=str(AGREEMENT))
    return ap


def main(argv=None):
    ap = parser()
    args = ap.parse_args(argv)
    if args.score:
        m = run_score(args)
        print(json.dumps({k: m[k] for k in ("status", "cached", "seconds", "n_clauses", "detections", "unavailable",
                                            "entry_classes", "stage5_agreement")}, ensure_ascii=False))
        return
    if not args.dry_run and not args.gold:
        ap.error("--gold is required unless --dry-run or --score (no human annotation exists yet)")
    m = run(args)
    print(json.dumps({k: m[k] for k in ("status", "seconds", "n_items", "pools")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
