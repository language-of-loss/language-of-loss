"""Short-form pipeline: Reddit / YouTube-style posts -> the clauses.jsonl / tokens.csv schema, register = short."""
import argparse
import csv
import json
import pickle
import random
import re
import subprocess
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preprocess as P

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "processed" / "shortform"
LONG = ROOT / "data" / "processed"
XLIT_PY = ROOT / ".venv_xlit" / "bin" / "python"
XLIT_WORKER = ROOT / "src" / "analysis" / "xlit_worker.py"
SOURCES = {
    "reddit_sample": ROOT / "docs" / "reddit_india_bereavement_sample.csv",
    "hinemo9": ROOT / "data" / "clean" / "hinemo9.jsonl",
    "ytcv_nonenglish": ROOT / "data" / "clean" / "ytcv.jsonl",
}
N_HI, N_EN, XLIT_TOPK, SEED = 4000, 4000, 3, 20261010
LANGID_FORMAT = 2
SHARED_RATIO = 4
MIN_RUN = 3
SHORT_TOKEN = 3
CONTEXT_WINDOW = 3
SHORT_WEIGHT = 0.5
HINDI_SHARE, ENGLISH_SHARE = 0.8, 0.2

TOKEN_RE = re.compile(r"(?P<deva>[ऀ-ॣॱ-ॿ]+)|(?P<latin>[A-Za-z]+(?:['’][A-Za-z]+)?)|(?P<num>\d+(?:[.,:]\d+)*)|"
                      r"(?P<other>\S)")
ROMAN_LEXICON = {
    "h": "है", "hai": "है", "hain": "हैं", "hn": "हाँ", "haan": "हाँ", "nhi": "नहीं", "nahi": "नहीं", "nahin": "नहीं",
    "na": "ना", "me": "में", "mein": "में", "main": "मैं", "mai": "मैं", "ab": "अब", "is": "इस", "us": "उस",
    "to": "तो", "ki": "की", "ke": "के", "ka": "का", "ko": "को", "se": "से", "ho": "हो", "or": "और", "aur": "और",
    "bhi": "भी", "kr": "कर", "kar": "कर", "rha": "रहा", "raha": "रहा", "rhi": "रही", "rahi": "रही", "rhe": "रहे",
    "rahe": "रहे", "tha": "था", "thi": "थी", "the": "थे", "hu": "हूँ", "hoo": "हूँ", "hun": "हूँ", "hum": "हम",
    "tum": "तुम", "ap": "आप", "aap": "आप", "bhut": "बहुत", "bht": "बहुत", "bahut": "बहुत", "kya": "क्या",
    "ye": "ये", "yeh": "यह", "wo": "वो", "woh": "वो", "vo": "वो", "ji": "जी", "maa": "माँ", "yad": "याद",
    "yaad": "याद", "aisa": "ऐसा", "aisi": "ऐसी", "aise": "ऐसे", "kuch": "कुछ", "kuchh": "कुछ", "mtlb": "मतलब",
    "matlab": "मतलब", "chahiye": "चाहिए", "chahye": "चाहिए", "chahie": "चाहिए", "abhi": "अभी", "aj": "आज",
    "aaj": "आज", "tk": "तक", "tak": "तक", "gyi": "गई", "gayi": "गई", "gya": "गया", "gaya": "गया", "ek": "एक",
}
ELONGATION_RE = re.compile(r"([a-z])\1{2,}")


def roman_key(w):
    return ELONGATION_RE.sub(r"\1", w.lower())


def parse_field(v, default):
    from text_meta import parse_field as pf
    return pf(v, default)


def load_source(name):
    path = SOURCES.get(name, Path(name))
    if not path.exists():
        raise SystemExit(f"source {name}: {path} not found")
    rows = []
    if path.suffix == ".csv":
        with open(path, encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                if (r.get("eligibility_status") or "provisionally_eligible") != "provisionally_eligible":
                    continue
                rows.append(dict(record_id=r["record_id"], source=name, platform=r.get("platform") or "reddit",
                                 text=r.get("text_clean") or r.get("text") or "", lang_hint=r.get("lang_provisional", ""),
                                 extra={}))
    else:
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            if name == "ytcv_nonenglish" and r.get("lang_provisional") == "english":
                continue
            if r.get("eligibility_status", "provisionally_eligible") != "provisionally_eligible":
                continue
            rows.append(dict(record_id=r["record_id"], source=name, platform=r.get("platform") or "",
                             text=r.get("text_clean") or r.get("text") or "", lang_hint=r.get("lang_provisional", ""),
                             extra=parse_field(r.get("extra"), {})))
    return rows


def tokenize(text):
    return [(m.group(0), m.lastgroup, m.start(), m.end()) for m in TOKEN_RE.finditer(text)]


class Xlit:

    def __init__(self, cache_path):
        self.path = Path(cache_path)
        self.cache = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}

    def available(self):
        return XLIT_PY.exists()

    def run(self, direction, words, topk=1):
        c = self.cache.setdefault(f"{direction}:{topk}", {})
        todo = sorted({w for w in words if w not in c})
        if todo:
            if not self.available():
                raise SystemExit("IndicXlit is not set up: run `bash scripts/setup_xlit.sh` (make setup-xlit)")
            p = subprocess.run([str(XLIT_PY), "-I", str(XLIT_WORKER)], input=json.dumps(
                dict(direction=direction, words=todo, topk=topk)), capture_output=True, text=True)
            if p.returncode:
                raise SystemExit(f"xlit worker failed: {p.stderr[-800:]}")
            c.update(json.loads(p.stdout))
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.cache, ensure_ascii=False), encoding="utf-8")
        return {w: c[w] for w in words}


def rom2deva(words, xlit):
    keys = {w: roman_key(w) for w in words}
    need = sorted({k for k in keys.values() if k not in ROMAN_LEXICON})
    got = xlit.run("rom2deva", need, 1) if need else {}
    return {w: ROMAN_LEXICON.get(k) or (got.get(k) or [w])[0] for w, k in keys.items()}


def informal_variants(rom):
    v = {rom}
    s = rom
    for a, b in (("aa", "a"), ("ee", "i"), ("ii", "i"), ("oo", "u"), ("uu", "u")):
        s = s.replace(a, b)
    v.add(s)
    if s.endswith("ey"):
        v.add(s[:-1])
    if s.endswith("y") and len(s) > 3:
        v.add(s[:-1])
    return {x for x in v if x.isalpha()}


def corpus_words(long_dir=LONG):
    lang = {}
    for line in open(long_dir / "clauses.jsonl", encoding="utf-8"):
        c = json.loads(line)
        lang[c["clause_id"]] = c["lang"]
    hi, en = Counter(), Counter()
    with open(long_dir / "tokens.csv", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            t = unicodedata.normalize("NFC", r["token"].strip())
            if lang.get(r["clause_id"]) == "hi" and re.fullmatch(r"[ऀ-ॣॱ-ॿ]+", t):
                hi[t] += 1
            elif lang.get(r["clause_id"]) == "en" and re.fullmatch(r"[A-Za-z]+", t):
                en[t.lower()] += 1
    return hi, en


def train_langid(xlit, out_dir, seed=SEED):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    hi, en = corpus_words()
    hi_types = [w for w, _ in hi.most_common(N_HI)]
    en_types = [w for w, _ in en.most_common(N_EN)]
    roman = xlit.run("deva2rom", hi_types, XLIT_TOPK)
    rng = random.Random(seed)
    split = {}
    for w in hi_types + en_types:
        split[w] = "test" if rng.random() < 0.15 else "train"
    n_hi, n_en = sum(hi.values()), sum(en.values())
    hi_rel = Counter()
    for w in hi_types:
        for r in roman.get(w, []):
            for v in informal_variants(r.lower()):
                hi_rel[v] = max(hi_rel[v], hi[w] / n_hi)
    english_side, hindi_side, ambiguous = set(), set(), set()
    for v in hi_rel:
        if en[v] < 2:
            continue
        e = en[v] / n_en
        if e >= SHARED_RATIO * hi_rel[v]:
            english_side.add(v)
        elif hi_rel[v] >= SHARED_RATIO * e:
            hindi_side.add(v)
        else:
            ambiguous.add(v)

    def training_set(types_ok):
        X, y, wts = [], [], []
        for w in hi_types:
            if not types_ok(w):
                continue
            for r in roman.get(w, []):
                for v in informal_variants(r.lower()):
                    if v not in ambiguous and v not in english_side:
                        X.append(v), y.append(1), wts.append(1 + (hi[w] ** 0.5) / len(roman[w]))
        for w in en_types:
            if types_ok(w) and w not in ambiguous and w not in hindi_side:
                X.append(w), y.append(0), wts.append(1 + en[w] ** 0.5)
        return X, y, wts
    X, y, wts = training_set(lambda w: split[w] == "train")
    model = make_pipeline(TfidfVectorizer(analyzer="char_wb", ngram_range=(1, 4), lowercase=True, sublinear_tf=True),
                          LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced"))
    model.fit(X, y, logisticregression__sample_weight=wts)
    hi_test = [w for w in hi_types if split[w] == "test" and roman.get(w)]
    en_test = [w for w in en_types if split[w] == "test" and w not in ambiguous and w not in hindi_side]
    en_draw = rng.choices(en_test, weights=[en[w] for w in en_test], k=100)
    def hi_form(w):
        forms = sorted(v for r in roman[w] for v in informal_variants(r.lower())
                       if v not in ambiguous and v not in english_side)
        return rng.choice(forms) if forms else None
    hi_test = [w for w in hi_test if any(v not in ambiguous and v not in english_side
                                         for r in roman[w] for v in informal_variants(r.lower()))]
    hi_draw = rng.choices(hi_test, weights=[hi[w] for w in hi_test], k=100)
    toks = [hi_form(w) for w in hi_draw] + en_draw
    gold = [1] * 100 + [0] * 100
    pred = [int(p >= 0.5) for p in model.predict_proba(toks)[:, 1]]
    acc = sum(int(a == b) for a, b in zip(pred, gold)) / len(gold)
    ev = dict(n_train=len(X), n_train_hi=sum(y), n_train_en=len(y) - sum(y), n_shared_english=len(english_side), n_shared_hindi=len(hindi_side), n_ambiguous_forms=len(ambiguous),
              shared_hindi_examples=sorted(hindi_side, key=lambda v: -hi_rel[v])[:30],
              ambiguous_examples=sorted(ambiguous, key=lambda v: -en[v])[:30],
              heldout_tokens=len(gold),
              heldout_accuracy=round(acc, 4),
              heldout_hi_recall=round(sum(p for p, g in zip(pred, gold) if g) / 100, 4),
              heldout_en_recall=round(sum(1 - p for p, g in zip(pred, gold) if not g) / 100, 4),
              errors=[(t, g) for t, p, g in zip(toks, pred, gold) if p != g][:40],
              note="held-out tokens follow the training distribution (IndicXlit romanisations + informal variants "
                   "vs English corpus words) and exclude the ambiguous shared forms, which are tagged from context; "
                   "real chat Hinglish is scored on tests/shortform_sentences.csv")
    X, y, wts = training_set(lambda w: True)
    model.fit(X, y, logisticregression__sample_weight=wts)
    ev["n_final_fit"] = len(X)
    out_dir.mkdir(parents=True, exist_ok=True)
    model = dict(format=LANGID_FORMAT, clf=model, ambiguous=ambiguous)
    with open(out_dir / "langid.pkl", "wb") as fh:
        pickle.dump(model, fh)
    (out_dir / "langid_eval.json").write_text(json.dumps(ev, ensure_ascii=False, indent=1), encoding="utf-8")
    return model, ev


def load_langid(out_dir=OUT):
    p = Path(out_dir) / "langid.pkl"
    if not p.exists():
        return None
    with open(p, "rb") as fh:
        m = pickle.load(fh)
    if not isinstance(m, dict) or m.get("format") != LANGID_FORMAT:
        print(f"note: {p} is an older classifier format; retrain with --retrain", file=sys.stderr)
        return None
    return m


def tag_tokens(tokens, model):
    amb = model["ambiguous"]
    latin = [i for i, t in enumerate(tokens) if t[1] == "latin"]
    probs = dict(zip(latin, model["clf"].predict_proba([tokens[i][0] for i in latin])[:, 1])) if latin else {}
    anchors = [i for i, t in enumerate(tokens)
               if t[1] == "deva" or (t[1] == "latin" and t[0].lower() not in amb)]
    if not anchors:
        anchors = [i for i, t in enumerate(tokens) if t[1] in ("latin", "deva")]
    pa = {i: probs.get(i, 1.0) for i in anchors}
    wt = {i: SHORT_WEIGHT if tokens[i][1] == "latin" and len(tokens[i][0]) <= SHORT_TOKEN else 1.0 for i in anchors}

    def wmean(idx):
        return sum(pa[j] * wt[j] for j in idx) / sum(wt[j] for j in idx) if idx else 0.5
    line_mean = wmean(anchors)

    def context(i):
        near = [j for j in anchors if j < i and j != i][-CONTEXT_WINDOW:] + [j for j in anchors if j > i][:CONTEXT_WINDOW]
        return wmean(near) if near else line_mean
    out = []
    for i, (tok, kind, _, _) in enumerate(tokens):
        if kind == "deva":
            out.append(("hi", 1.0))
        elif kind == "latin":
            p = probs[i]
            if tok.lower() in amb:
                p = context(i)
            elif len(tok) <= SHORT_TOKEN:
                p = SHORT_WEIGHT / 2 * p + (1 - SHORT_WEIGHT / 2) * context(i)
            out.append(("hi" if p >= 0.5 else "en", round(float(p), 4)))
        else:
            out.append(("x", None))
    return out


def text_label(tokens, tags):
    lex = [(t[1], g) for t, (g, _) in zip(tokens, tags) if g in ("hi", "en")]
    if not lex:
        return "unknown", None
    share = sum(1 for _, g in lex if g == "hi") / len(lex)
    if share >= HINDI_SHARE:
        deva = sum(1 for k, g in lex if g == "hi" and k == "deva")
        return ("devanagari_hindi" if deva >= sum(1 for _, g in lex if g == "hi") / 2 else "romanized_hindi"), share
    if share <= ENGLISH_SHARE:
        return "english", share
    return "code_mixed", share


def language_runs(tags, min_run=MIN_RUN):
    words = [g for g, _ in tags if g != "x"]
    if not tags:
        return []
    if len(words) < 2 * min_run:
        c = Counter(words)
        lang = (c.most_common(1)[0][0] if len(c) == 1 or c["hi"] != c["en"] else words[0]) if words else "en"
        return [(lang, list(range(len(tags))))]
    runs = []
    for i, (g, _) in enumerate(tags):
        if g == "x" or (runs and runs[-1][0] == g):
            if runs:
                runs[-1][1].append(i)
            else:
                runs.append([None, [i]])
        elif runs and runs[-1][0] is None:
            runs[-1][0] = g
            runs[-1][1].append(i)
        else:
            runs.append([g, [i]])

    def nwords(r):
        return sum(1 for i in r[1] if tags[i][0] != "x")
    while True:
        short = [k for k, r in enumerate(runs) if nwords(r) < min_run]
        if len(runs) < 2 or not short:
            break
        k = short[0]
        cands = [j for j in (k - 1, k + 1) if 0 <= j < len(runs)]
        j = max(cands, key=lambda j: (nwords(runs[j]), -j))
        lo, hi = sorted((j, k))
        runs[lo:hi + 1] = [[runs[j][0], runs[lo][1] + runs[hi][1]]]
        merged = []
        for r in runs:
            if merged and merged[-1][0] == r[0]:
                merged[-1][1] += r[1]
            else:
                merged.append(r)
        runs = merged
    return [(g, idx) for g, idx in runs]


def build_run_text(tokens, idxs, lang, tags, deva_of):
    parts, spans, pos = [], [], 0
    for i in idxs:
        tok, kind = tokens[i][0], tokens[i][1]
        piece = deva_of.get(tok, tok) if lang == "hi" and kind == "latin" else tok
        spans.append((pos, pos + len(piece), i))
        parts.append(piece)
        pos += len(piece) + 1
    return " ".join(parts), spans


def renumber(clauses, tokens, rid, offset_pos, offset_sent):
    mapping = {}
    for c in clauses:
        new = f"{rid}#{c['position'] + offset_pos:04d}"
        mapping[c["clause_id"]] = new
    for c in clauses:
        c["clause_id"] = mapping[c["clause_id"]]
        c["record_id"] = rid
        c["position"] += offset_pos
        c["sent_index"] += offset_sent
        if c["subject_inherited_from"]:
            c["subject_inherited_from"] = mapping[c["subject_inherited_from"]]
    for t in tokens:
        t[0] = mapping[t[0]]
    return clauses, tokens


def process_record(rec, model, xlit, nlps, cache_dir):
    text = P.prepare_text(rec["text"], None)
    lines = [ln for ln in text.split("\n\n") if ln.strip()]
    toks_all, tags_all, line_runs = [], [], []
    for ln in lines:
        toks = tokenize(ln)
        tags = tag_tokens(toks, model) if toks else []
        base = len(toks_all)
        toks_all += toks
        tags_all += tags
        line_runs += [(g, [base + i for i in idx]) for g, idx in language_runs(tags)] if toks else []
    label, share = text_label(toks_all, tags_all)
    need = sorted({toks_all[i][0] for g, idx in line_runs if g == "hi" for i in idx if toks_all[i][1] == "latin"})
    deva_of = rom2deva(need, xlit) if need else {}
    clauses, tokens = [], []
    pos = sent = 0
    for k, (g, idx) in enumerate(line_runs):
        run_text, spans = build_run_text(toks_all, idx, g, tags_all, deva_of)
        if not run_text.strip():
            continue
        prepared = run_text
        pseudo = dict(record_id=f"{rec['record_id']}~r{k}")
        sents, _ = P.parse_cached(pseudo, g, prepared, nlps[g], cache_dir, nlps["_version"])
        cl, tk, _, _ = P.segment(pseudo, g, sents, prepared)
        word_tok = {}
        for si, words in enumerate(sents):
            for w in words:
                orig = next((i for s, e, i in spans if s <= w["start"] < e), None)
                word_tok[(si, w["id"])] = orig
        by_clause = defaultdict(list)
        for row in tk:
            by_clause[row[0]].append(row)
        for c in cl:
            origs = [word_tok.get((c["sent_index"], row[1])) for row in by_clause[c["clause_id"]]]
            origs = sorted({o for o in origs if o is not None})
            votes = Counter(tags_all[o][0] for o in origs if tags_all[o][0] in ("hi", "en"))
            c["parse_lang"] = g
            c["lang"] = (votes.most_common(1)[0][0] if votes and (len(votes) == 1 or votes["hi"] != votes["en"])
                         else g)
            c["share_hi"] = round(votes["hi"] / sum(votes.values()), 3) if votes else None
            c["translit"] = any(toks_all[o][1] == "latin" for o in origs) and g == "hi"
            c["orig_text"] = " ".join(toks_all[o][0] for o in origs)
            c["register"], c["source"] = "short", rec["source"]
        renumber(cl, tk, rec["record_id"], pos, sent)
        pos += len(cl)
        sent += len(sents)
        clauses += cl
        tokens += tk
    lang_rows = [[rec["record_id"], i, t[0], t[1], g, p if p is not None else "",
                  deva_of.get(t[0], "") if t[1] == "latin" else ""] for i, (t, (g, p)) in enumerate(zip(toks_all, tags_all))]
    record = dict(record_id=rec["record_id"], source=rec["source"], platform=rec["platform"], register="short",
                  lang_provisional=label, share_hi=share, lang_hint=rec["lang_hint"], text_clean=rec["text"],
                  eligibility_status="provisionally_eligible", review_status="no_human_review",
                  extra=dict(deceased_relation_as_stated=str(rec["extra"].get("deceased_relation_as_stated") or "")))
    return record, clauses, tokens, lang_rows


def rates(dir_):
    lang = {}
    for line in open(dir_ / "clauses.jsonl", encoding="utf-8"):
        c = json.loads(line)
        lang[c["clause_id"]] = c["lang"]
    out = {lg: Counter() for lg in ("hi", "en")}
    with open(dir_ / "flags.csv", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            o = out[r["lang"]]
            o["units"] += 1
            o["dative_regex"] += r.get("dative_regex") == "True"
            o["dative_parse"] += r.get("dative_parse") == "True"
    entry_cols = None
    with open(dir_ / "clause_features.csv", encoding="utf-8", newline="") as fh:
        rd = csv.DictReader(fh)
        entry_cols = [c for c in rd.fieldnames if re.match(r"^[LP]-(HI|EN)-", c)]
        for r in rd:
            out[r["lang"]]["covered"] += any(r[c] not in ("0", "", "False") for c in entry_cols)
    with open(dir_ / "referents.csv", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            o = out[lang[r["clause_id"]]]
            o["finite"] += 1
            o["honorific"] += r["honorific"] == "True"
            o["relational"] += r.get("relational") == "True"
    return out


def report(path):
    s, l = rates(OUT), rates(LONG)
    recs = [json.loads(x) for x in open(OUT / "records.jsonl", encoding="utf-8")]
    ev = json.loads((OUT / "langid_eval.json").read_text(encoding="utf-8"))

    def pct(c, k, d):
        return f"{100 * c[k] / c[d]:.1f}% ({c[k]:,}/{c[d]:,})" if c[d] else "n/a (0)"

    def per1000(c, k):
        return f"{1000 * c[k] / c['units']:.1f} ({c[k]:,})" if c["units"] else "n/a (0)"
    L = ["# Short-form pipeline: dev smoke", "",
         f"_Generated {time.strftime('%Y-%m-%d %H:%M')} by `src/analysis/shortform.py --report`. DEV SMOKE: machine "
         "language tags and transliteration, unreviewed parses and matches, tiny samples. The numbers check the "
         "pipeline. They are not findings._", "",
         "## Input", "", "| source | posts | devanagari_hindi | romanized_hindi | code_mixed | english | unknown |",
         "|---|---|---|---|---|---|---|"]
    for src in sorted({r["source"] for r in recs}):
        c = Counter(r["lang_provisional"] for r in recs if r["source"] == src)
        L.append(f"| {src} | {sum(c.values())} | " + " | ".join(str(c[k]) for k in
                 ("devanagari_hindi", "romanized_hindi", "code_mixed", "english", "unknown")) + " |")
    L += ["", "## Language classifier", "",
          f"- Held-out accuracy {ev['heldout_accuracy']:.3f} on {ev['heldout_tokens']} tokens "
          f"(romanised-Hindi recall {ev['heldout_hi_recall']:.2f}, English recall {ev['heldout_en_recall']:.2f}); "
          f"trained on {ev['n_train']:,} word forms.", f"- {ev['note']}.", "",
          "## Rates: short vs long form", "",
          "| measure | short hi | long hi | short en | long en |", "|---|---|---|---|---|",
          f"| clause units | {s['hi']['units']:,} | {l['hi']['units']:,} | {s['en']['units']:,} | {l['en']['units']:,} |",
          f"| lexicon coverage (≥1 entry) | {pct(s['hi'], 'covered', 'units')} | {pct(l['hi'], 'covered', 'units')} | "
          f"{pct(s['en'], 'covered', 'units')} | {pct(l['en'], 'covered', 'units')} |",
          f"| dative_regex per 1,000 units | {per1000(s['hi'], 'dative_regex')} | {per1000(l['hi'], 'dative_regex')} "
          "| n/a | n/a |",
          f"| dative_parse per 1,000 units | {per1000(s['hi'], 'dative_parse')} | {per1000(l['hi'], 'dative_parse')} "
          "| n/a | n/a |",
          f"| honorific (% of finite clauses) | {pct(s['hi'], 'honorific', 'finite')} | "
          f"{pct(l['hi'], 'honorific', 'finite')} | n/a | n/a |",
          f"| relational (% of finite clauses) | {pct(s['hi'], 'relational', 'finite')} | "
          f"{pct(l['hi'], 'relational', 'finite')} | {pct(s['en'], 'relational', 'finite')} | "
          f"{pct(l['en'], 'relational', 'finite')} |", "",
          "Short-form Hindi clauses come almost entirely from romanised YouTube comments that were transliterated "
          "by machine; every Hindi rate above depends on that transliteration and on Stanza parsing chat text "
          "it was not trained on."]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return s, l


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sources", default="reddit_sample,hinemo9,ytcv_nonenglish")
    ap.add_argument("--out-dir", default=str(OUT))
    ap.add_argument("--retrain", action="store_true", help="retrain the language classifier")
    ap.add_argument("--report", action="store_true", help="only write docs/shortform_report.md from existing outputs")
    args = ap.parse_args(argv)
    out = Path(args.out_dir)
    if args.report:
        report(ROOT / "docs" / "shortform_report.md")
        print("wrote docs/shortform_report.md")
        return
    t0 = time.time()
    out.mkdir(parents=True, exist_ok=True)
    xlit = Xlit(out / "xlit_cache.json")
    model = None if args.retrain else load_langid(out)
    ev = json.loads((out / "langid_eval.json").read_text()) if model else None
    if model is None:
        model, ev = train_langid(xlit, out)
    print(f"langid: held-out accuracy {ev['heldout_accuracy']} on {ev['heldout_tokens']} tokens")
    recs = [r for name in args.sources.split(",") if name for r in load_source(name)]
    import stanza
    nlps = P.make_pipelines(["hi", "en"])
    nlps["_version"] = stanza.__version__
    need = set()
    for rec in recs:
        for ln in (x for x in P.prepare_text(rec["text"], None).split("\n\n") if x.strip()):
            toks = tokenize(ln)
            if toks:
                for g, idx in language_runs(tag_tokens(toks, model)):
                    need |= {toks[i][0] for i in idx if g == "hi" and toks[i][1] == "latin"}
    rom2deva(sorted(need), xlit)
    all_rec, all_cl, all_tok, all_lang = [], [], [], []
    for n, rec in enumerate(recs, 1):
        r, cl, tk, lg = process_record(rec, model, xlit, nlps, out / "stanza_cache")
        all_rec.append(r), all_cl.extend(cl), all_tok.extend(tk), all_lang.extend(lg)
        print(f"[{n}/{len(recs)}] {rec['record_id']} {r['lang_provisional']} {len(cl)} units", file=sys.stderr)
    with open(out / "records.jsonl", "w", encoding="utf-8") as fh:
        for r in all_rec:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(out / "clauses.jsonl", "w", encoding="utf-8") as fh:
        for c in all_cl:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    with open(out / "tokens.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["clause_id", "token_index", "token", "lemma", "upos", "feats", "head", "deprel"])
        w.writerows(all_tok)
    with open(out / "token_lang.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["record_id", "token_index", "token", "kind", "tag", "p_hi", "translit"])
        w.writerows(all_lang)
    by_src = Counter((r["source"], r["lang_provisional"]) for r in all_rec)
    mism = sum(1 for c in all_cl if c["lang"] != c["parse_lang"])
    summary = ["# Short-form preprocess summary", "",
               f"- Run {time.strftime('%Y-%m-%d %H:%M')} ({time.time() - t0:.0f} s); sources {args.sources}",
               f"- Posts {len(all_rec)}; clause units {len(all_cl)} (hi {sum(c['lang'] == 'hi' for c in all_cl)}, "
               f"en {sum(c['lang'] == 'en' for c in all_cl)}); clauses whose majority language differs from the "
               f"parsing pipeline: {mism}; transliterated Hindi clauses {sum(bool(c['translit']) for c in all_cl)}",
               f"- Language classifier: held-out accuracy {ev['heldout_accuracy']} on {ev['heldout_tokens']} tokens",
               "", "| source | label | posts |", "|---|---|---|"]
    summary += [f"| {s} | {lab} | {k} |" for (s, lab), k in sorted(by_src.items())]
    (out / "shortform_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary[2:6]))


if __name__ == "__main__":
    main()
