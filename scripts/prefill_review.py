"""Rule-based suggestions for the human corpus review."""
import argparse
import csv
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "docs" / "review_master_2026-10.csv"
HUMAN = ("decision", "relation", "reason", "reviewer")
NEW = ["suggested_decision", "suggested_relation", "suggested_reason", "suggestion_confidence"]
MIN_WORDS = 150

FLAGS = re.IGNORECASE
LISTICLE = re.compile(r"condolence (messages|quotes|wishes)|sympathy (messages|quotes)|rip (messages|quotes|status)|"
                      r"शोक संदेश|श्रद्धांजलि संदेश|शोक सन्देश|quotes on|messages for", FLAGS)
EXCLUDE = [
    ("verse", re.compile(r"\bpoem\b|\bpoetry\b|\bverse\b|कविता|ग़?ज़ल|गजल|शायरी|नज़्म|नज्म|\bghazal\b|\bshayari\b", FLAGS)),
    ("fiction", re.compile(r"\bshort story\b|\bfiction\b|लघुकथा|लघु कथा|उपन्यास|\bnovel\b|कहानी\s*[:।-]", FLAGS)),
    ("advice", re.compile(r"\btips\b|how to (cope|deal|handle|overcome)|ways to (cope|deal)|\badvice\b|\bsteps to\b|"
                          r"कैसे (उबरें|करें|निपटें)|उपाय|सुझाव", FLAGS)),
    ("religious instruction", re.compile(r"garud(a)? puran|गरुड़? ?पुराण|श्राद्ध विधि|पिंडदान विधि|pind ?daan vidhi|"
                                         r"rituals? to (perform|follow)|क्या करें और क्या न करें", FLAGS)),
    ("news / obituary report", re.compile(r"\bpasses away\b|\bdies at\b|\bdied at the age\b|\bobituary\b|"
                                          r"\bcondolences pour\b|का निधन|ने दुख जताया|शोक व्यक्त किया|"
                                          r"अंतिम संस्कार में शामिल", FLAGS)),
    ("translation", re.compile(r"\btranslated (from|by)\b|\btranslation\b|अनुवाद|अनूदित", FLAGS)),
]
AS_TOLD = re.compile(r"as told to|जैसा कि .{0,30} ने बताया|की ज़?ुबानी", FLAGS)
FIRST_PERSON = re.compile(r"(?<![A-Za-z])(i|i'm|i've|my|me|we|our|us)(?![A-Za-z])|मैं|मैंने|मुझे|मेरा|मेरी|मेरे|हम|हमारा|"
                          r"हमारी|हमारे|हमें|\b(main|mera|meri|mere|mujhe|hum|humne|hamare)\b", FLAGS)
DEATH = re.compile(r"\bdie(d|s)?\b|\bdeath\b|\bpassed (away|on)\b|\bpassing\b|\bloss\b|\bfuneral\b|\bcremat|\bgrief\b|"
                   r"\bgrieving\b|\bmourn|निधन|मृत्यु|मौत|देहांत|देहावसान|स्वर्गवास|गुज़?र (गए|गई|गये|गयीं)|"
                   r"नहीं रहे|नहीं रहीं|चल बसे|चल बसीं|अंतिम संस्कार|श्रद्धांजलि|शोक|\bguzar\b|\bnahi rahe\b", FLAGS)
KIN = [
    ("grandmother", r"grand ?mother|grandma|\bnani\b|\bdadi\b|\bpaati\b|\bnaani\b|\bdaadi\b|दादी|नानी"),
    ("grandfather", r"grand ?father|grandpa|\bnana\b|\bdada\b|\bdadaji\b|\bthatha\b|दादा|नाना|दादाजी|नानाजी"),
    ("mother-in-law", r"mother[- ]in[- ]law|सास"),
    ("father-in-law", r"father[- ]in[- ]law|ससुर"),
    ("mother", r"\bmother\b|\bmom\b|\bmum\b|\bmummy\b|\bmaa\b|\bamma\b|\bammi\b|\baai\b|माँ|मां|मम्मी|माता|अम्मा|अम्मी"),
    ("father", r"\bfather\b|\bdad\b|\bdaddy\b|\bpapa\b|\bappa\b|\babbu\b|\bbaba\b|पिता|पापा|पिताजी|बाबूजी|अब्बू|बाबा"),
    ("husband", r"\bhusband\b|पति"), ("wife", r"\bwife\b|पत्नी"),
    ("son", r"\bson\b|बेटा|बेटे"), ("daughter", r"\bdaughter\b|बेटी"),
    ("brother", r"\bbrother\b|\bbhai\b|\bbhaiya\b|भाई|भैया"), ("sister", r"\bsister\b|\bdidi\b|बहन|दीदी"),
    ("friend", r"\bfriend\b|दोस्त|मित्र|सहेली"),
    ("uncle / aunt", r"\buncle\b|\baunt\b|चाचा|चाची|मामा|मामी|ताऊ|बुआ|मौसी"),
]
KIN = [(k, re.compile(p, FLAGS)) for k, p in KIN]


def suggest(row):
    text = f"{row.get('title', '')} {row.get('first_300_chars', '')}"
    reasons = []
    try:
        n = int(float(row.get("n_words") or 0))
    except ValueError:
        n = 0
    relation = next((k for k, rx in KIN if rx.search(row.get("title", ""))), None) or \
        next((k for k, rx in KIN if rx.search(row.get("first_300_chars", ""))), "not stated")
    if AS_TOLD.search(text):
        reasons.append("as-told-to marker: admissible only if flagged")
    if n < MIN_WORDS:
        return "exclude", relation, f"under {MIN_WORDS} words ({n})", "high"
    if LISTICLE.search(text):
        return "exclude", relation, "condolence-message / quote listicle", "high"
    hits = [name for name, rx in EXCLUDE if rx.search(text)]
    if hits:
        return "exclude", relation, "; ".join([f"{h} marker" for h in hits] + reasons), "medium"
    cap = (row.get("over_cap") or "").strip()
    if cap in ("domain_cap", "author_cap"):
        return "exclude", relation, "; ".join([f"over the sampling cap ({cap})"] + reasons), "medium"
    fp, death, kin = bool(FIRST_PERSON.search(text)), bool(DEATH.search(text)), relation != "not stated"
    if cap == "same_author_dev":
        reasons.append("same author as a corpus text (development split)")
    if not fp and not death:
        return "exclude", relation, "; ".join(["no first-person form and no death word in the first 300 characters"]
                                              + reasons), "low"
    found = [x for x, ok in (("first person", fp), ("death word", death), ("kin / friend term", kin)) if ok]
    reason = "; ".join([" + ".join(found) + " in title / first 300 characters"] + reasons)
    if fp and death and kin:
        return "include", relation, reason, "high"
    if fp and (death or kin):
        return "include", relation, reason, "medium"
    return "include", relation, reason, "low"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--master", default=str(MASTER))
    args = ap.parse_args(argv)
    path = Path(args.master)
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fields, rows = list(reader.fieldnames), list(reader)
    before = [{h: r[h] for h in HUMAN} for r in rows]
    for r in rows:
        r.update(zip(NEW, suggest(r)))
    assert before == [{h: r[h] for h in HUMAN} for r in rows], "human columns must not change"
    out_fields = fields + [c for c in NEW if c not in fields]
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=out_fields)
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)
    c = Counter((r["lang"], r["suggested_decision"], r["suggestion_confidence"]) for r in rows)
    print(f"{len(rows)} rows -> {path}")
    for k, v in sorted(c.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
