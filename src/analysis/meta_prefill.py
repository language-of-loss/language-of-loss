import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from griefcorpus.textutil import word_count

FIELDS = {
    "genre": ("narrative", "reflective"),
    "home_language_statement": ("en", "hi", "both", "none"),
    "diaspora": ("yes", "no", "unknown"),
    "script_mix": ("devanagari", "latin", "mixed"),
}
CONF = ("high", "medium", "low")
REVIEW_COLUMNS = ["record_id", "lang", "split", "source_url", "field", "prefill_value", "confidence", "rule",
                  "evidence_clause_ids", "prefill_changed", "confirmed_value", "reviewer", "notes"]
HUMAN = ("confirmed_value", "reviewer", "notes")
MAX_EVIDENCE = 5

DEVA = re.compile(r"[ऀ-ॿ]")
LATIN = re.compile(r"[A-Za-z]")
HOME_RX = {
    "en": re.compile(r"mother[- ]?tongue|first language|native language|home language|language of (my|our) home|"
                     r"(we|i) (spoke|speak|talked|talk) (only |mostly |in )?\w+ at home|at home,? (we|i) (spoke|speak)|"
                     r"(grew up|growing up) speaking", re.I),
    "hi": re.compile(r"मातृ ?भाषा|मादरी ज़?ब़?ान|पहली भाषा|घर (में|पर) (हम|मैं)?\s*(हिंदी|हिन्दी|अंग्रेज़ी|अंग्रेजी|इंग्लिश)"),
}
REMARK_RX = {
    "en": re.compile(r"\bmy (hindi|english)\b|\b(can't|cannot|couldn't|could not) (read|write|speak) (in )?(hindi|english)\b|"
                     r"\b(think|dream|wrote|write|writing) in (hindi|english)\b|\b(in|into) (hindi|english)\b", re.I),
    "hi": re.compile(r"(मेरी|मेरा) (हिंदी|हिन्दी|अंग्रेज़ी|अंग्रेजी)|(हिंदी|हिन्दी|अंग्रेज़ी|अंग्रेजी|इंग्लिश) में (लिख|बोल|सोच|पढ़)"),
}
LANG_RX = {
    "hi": re.compile(r"\bhindi\b|हिंदी|हिन्दी", re.I),
    "en": re.compile(r"\benglish\b|अंग्रेज़ी|अंग्रेजी|इंग्लिश", re.I),
    "other": re.compile(r"\b(tamil|telugu|kannada|malayalam|bengali|bangla|marathi|gujarati|punjabi|urdu|odia|oriya|"
                        r"assamese|konkani|sindhi|kashmiri|bhojpuri|maithili|nepali)\b|तमिल|तेलुगु|कन्नड़|मलयालम|"
                        r"बंगाली|बांग्ला|मराठी|गुजराती|पंजाबी|उर्दू|ओड़िया|असमिया|भोजपुरी|मैथिली|नेपाली", re.I),
}
ABROAD = (r"the us|usa|u\.s\.|united states|america|the uk|u\.k\.|united kingdom|england|britain|london|canada|toronto|"
          r"vancouver|australia|sydney|melbourne|new zealand|dubai|uae|abu dhabi|singapore|germany|france|ireland|"
          r"netherlands|new york|new jersey|california|texas|chicago|boston|seattle|abroad|overseas")
INDIA = (r"india|delhi|mumbai|bombay|bangalore|bengaluru|chennai|madras|kolkata|calcutta|hyderabad|pune|lucknow|"
         r"jaipur|bhopal|indore|patna|kanpur|chandigarh|ahmedabad|noida|gurgaon|gurugram|dehradun|varanasi|banaras|"
         r"nagpur|kochi|goa|shimla|ranchi|allahabad|prayagraj|agra|meerut|nainital|almora")
RESIDENCE_RX = {
    "en": re.compile(r"\b(i|we)\s+(?:had\s+|have\s+)?(?:live|lived|living|moved|settled|relocated|emigrated|migrated|"
                     r"stay|stayed|staying|was living|were living|am living|are living)\s+(?:back\s+)?(?:in|to)\s+"
                     r"(?:the\s+)?(?P<place>[a-z.\s]{2,30})", re.I),
    "hi": re.compile(r"(?:मैं|हम)\s+(?:\S+\s+){0,3}?(?P<place>अमेरिका|लंदन|कनाडा|विदेश|ऑस्ट्रेलिया|दुबई|सिंगापुर|इंग्लैंड|"
                     r"जर्मनी|दिल्ली|मुंबई|बंबई|लखनऊ|भोपाल|पटना|जयपुर|कोलकाता|बेंगलुरु|चेन्नई|पुणे|भारत|देहरादून|"
                     r"इंदौर|कानपुर|नैनीताल|अल्मोड़ा|वाराणसी|बनारस|इलाहाबाद|प्रयागराज)\s+(?:में|को|आ|जा|चल|ही)\s*"
                     r"(?:\S+\s+){0,2}?(?:रह|बस|शिफ़्ट|शिफ्ट|आ गए|आ गई|चले गए|चली गई|जा बसे)"),
}
ABROAD_HI = {"अमेरिका", "लंदन", "कनाडा", "विदेश", "ऑस्ट्रेलिया", "दुबई", "सिंगापुर", "इंग्लैंड", "जर्मनी"}


def load_clauses(path):
    out = defaultdict(list)
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            c = json.loads(line)
            out[c["record_id"]].append((c["clause_id"], c["clause_text"], bool(c["is_finite"])))
    return out


def load_verb_feats(path, finite_ids):
    out = defaultdict(list)
    with open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["upos"] in ("VERB", "AUX") and r["clause_id"] in finite_ids:
                feats = dict(kv.split("=", 1) for kv in (r["feats"] or "").split("|") if "=" in kv)
                out[r["clause_id"]].append((r["upos"], (r["lemma"] or "").lower(), feats))
    return out


def tense(chain, lang):
    tenses = {f.get("Tense") for _, _, f in chain}
    if "Fut" in tenses or (lang == "en" and any(u == "AUX" and l in ("will", "shall") for u, l, _ in chain)):
        return "future"
    if "Pres" in tenses:
        return "present"
    if "Past" in tenses:
        return "past"
    if lang == "hi" and any(u == "VERB" and f.get("Aspect") == "Perf" for u, _, f in chain):
        return "past"
    return None


def genre(clauses, feats, lang):
    seen = [(cid, tense(feats.get(cid, []), lang)) for cid, _, fin in clauses if fin]
    known = [(cid, t) for cid, t in seen if t]
    if not known:
        return "reflective", "low", "no finite clause with a tense reading", []
    past = [cid for cid, t in known if t == "past"]
    share = len(past) / len(known)
    dist = abs(share - 0.5)
    conf = "high" if dist >= 0.2 else "medium" if dist >= 0.1 else "low"
    other = [cid for cid, t in known if t != "past"]
    ev = past[:3] + other[:2]
    return ("narrative" if share >= 0.5 else "reflective"), conf, \
        f"past share {share:.2f} of {len(known)} finite clauses with a tense", ev[:MAX_EVIDENCE]


def home_language(clauses):
    hits = []
    for cid, text, _ in clauses:
        if any(rx.search(text) for rx in HOME_RX.values()):
            langs = {k for k, rx in LANG_RX.items() if rx.search(text)}
            hits.append((cid, langs))
    if not hits:
        remarks = [cid for cid, text, _ in clauses if any(rx.search(text) for rx in REMARK_RX.values())]
        if remarks:
            return "none", "low", "no home-language statement; language remark(s) for the reviewer to read", \
                remarks[:MAX_EVIDENCE]
        return "none", "low", "no home-language statement matched", []
    named = set().union(*(l for _, l in hits))
    ev = [cid for cid, _ in hits][:MAX_EVIDENCE]
    if {"hi", "en"} <= named:
        return "both", "medium", "statement names Hindi and English", ev
    if "hi" in named:
        return "hi", "medium", "statement names Hindi", ev
    if "en" in named:
        return "en", "medium", "statement names English", ev
    if "other" in named:
        return "none", "low", "statement names another language (field has no 'other' value)", ev
    return "none", "low", "statement matched but names no language", ev


def diaspora(clauses, lang):
    abroad, india = [], []
    for cid, text, _ in clauses:
        for m in RESIDENCE_RX[lang].finditer(text):
            place = m.group("place").lower()
            if lang == "hi":
                (abroad if m.group("place") in ABROAD_HI else india).append(cid)
            elif re.match(rf"\s*({ABROAD})\b", place):
                abroad.append(cid)
            elif re.match(rf"\s*({INDIA})\b", place):
                india.append(cid)
    if abroad:
        return "yes", ("medium" if not india else "low"), \
            "first-person residence abroad" + (" (and in India)" if india else ""), (abroad + india)[:MAX_EVIDENCE]
    if india:
        return "no", "medium", "first-person residence in India only", india[:MAX_EVIDENCE]
    return "unknown", "low", "no first-person residence statement matched", []


def script_mix(text, clauses):
    d, l = len(DEVA.findall(text or "")), len(LATIN.findall(text or ""))
    share = l / (d + l) if d + l else 0.0
    value = "devanagari" if share < 0.05 else "latin" if share > 0.95 else "mixed"
    minority = DEVA if value == "latin" else LATIN
    ev = [cid for cid, t, _ in clauses if minority.search(t)][:MAX_EVIDENCE] if value != "mixed" else \
        [cid for cid, t, _ in clauses if DEVA.search(t) and LATIN.search(t)][:MAX_EVIDENCE]
    return value, "high", f"Latin share {share:.3f} of Devanagari + Latin letters", ev


def prefill(record, clauses, feats, lang):
    text = record.get("text_clean") or ""
    out = {"genre": genre(clauses, feats, lang), "home_language_statement": home_language(clauses),
           "diaspora": diaspora(clauses, lang), "script_mix": script_mix(text, clauses)}
    return out, word_count(text)


def read_review(path):
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, encoding="utf-8", newline="") as fh:
        return {(r["record_id"], r["field"]): r for r in csv.DictReader(fh)}


def confirmed(row):
    v = (row.get("confirmed_value") or "").strip()
    if not v or not (row.get("reviewer") or "").strip():
        return None
    if v not in FIELDS[row["field"]]:
        raise ValueError(f"meta_review.csv {row['record_id']} {row['field']}: '{v}' not in {FIELDS[row['field']]}")
    return v


def review_rows(texts, old):
    rows = []
    for t in texts:
        for f in FIELDS:
            value, conf, rule, ev = t["prefill"][f]
            prev = old.get((t["record_id"], f), {})
            has_human = any((prev.get(h) or "").strip() for h in HUMAN)
            changed = int(has_human and (prev.get("prefill_value") != value or str(prev.get("prefill_changed")) == "1"))
            rows.append(dict(record_id=t["record_id"], lang=t["lang"], split=t["split"], source_url=t["source_url"],
                             field=f, prefill_value=value, confidence=conf, rule=rule,
                             evidence_clause_ids=" ".join(ev), prefill_changed=changed,
                             **{h: prev.get(h, "") for h in HUMAN}))
    return rows


def write_review(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=REVIEW_COLUMNS)
        w.writeheader()
        w.writerows(rows)


def apply(texts, review):
    out = {}
    for t in texts:
        cols, n_human = {}, 0
        for f in FIELDS:
            value, conf = t["prefill"][f][:2]
            row = review.get((t["record_id"], f))
            human = confirmed(row) if row else None
            if human is not None:
                value, conf, n_human = human, "human", n_human + 1
            cols[f], cols[f"{f}_conf"] = value, conf
        cols["word_count"] = t["word_count"]
        cols["meta_review_status"] = "human_confirmed" if n_human == len(FIELDS) else \
            ("partly_confirmed" if n_human else "prefilled")
        out[t["record_id"]] = cols
    return out


def build(records, clauses_path, tokens_path, review_path, split_of):
    by_rec = load_clauses(clauses_path)
    finite = {cid for cl in by_rec.values() for cid, _, fin in cl if fin}
    feats = load_verb_feats(tokens_path, finite)
    texts = []
    for r, lang in records:
        cl = by_rec.get(r["record_id"], [])
        pre, wc = prefill(r, cl, feats, lang)
        texts.append(dict(record_id=r["record_id"], lang=lang, split=split_of(r["record_id"]),
                          source_url=r.get("source_url", ""), prefill=pre, word_count=wc))
    old = read_review(review_path)
    rows = review_rows(texts, old)
    write_review(review_path, rows)
    review = {(r["record_id"], r["field"]): r for r in rows}
    cols = apply(texts, review)
    summary = {f: Counter(c[f] for c in cols.values()) for f in FIELDS}
    return cols, summary
