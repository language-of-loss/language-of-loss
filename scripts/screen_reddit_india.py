import csv
import json
import random
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "data" / "clean" / "reddit_confessions.jsonl"
OUT = ROOT / "docs" / "reddit_india_bereavement_sample.csv"
COUNTS = ROOT / "data" / "interim" / "reddit_india_counts.json"
SEED, N_SAMPLE = 20261009, 200

L, R = r"(?<![A-Za-z])", r"(?![A-Za-z])"
GROUPS = {
    "kin_strong": ["amma", "appa", "dadi", "bhai", "didi", "ammi", "abbu", "nanaji", "dadaji", "naniji", "dadiji",
                   "bhaiya", "papaji"],
    "kin_weak": ["papa", "mummy", "nani", "nana", "dada"],
    "place": ["india", "indian", "mumbai", "bombay", "delhi", "bangalore", "bengaluru", "chennai", "madras",
              "kolkata", "calcutta", "hyderabad", "pune", "ahmedabad", "jaipur", "lucknow", "kanpur", "patna",
              "bhopal", "indore", "chandigarh", "kochi", "cochin", "kerala", "coimbatore", "nagpur", "surat",
              "varanasi", "noida", "gurgaon", "gurugram", "mysore", "mysuru", "punjab", "gujarat", "tamil nadu",
              "rajasthan", "bihar", "uttar pradesh", "maharashtra", "karnataka", "andhra", "telangana", "odisha",
              "assam", "goa"],
    "ritual": ["shraddh", "shraddha ceremony", "shradh", "tehravi", "terahvi", "tehrvi", "terahvin", "antim sanskar",
               "chautha", "pind daan", "pinddaan", "asthi visarjan"],
    "hospital": ["aiims", "apollo hospital", "fortis", "medanta", "tata memorial", "cmc vellore", "pgimer",
                 "kem hospital", "manipal hospital", "narayana health", "max hospital", "lilavati"],
    "exam": ["jee", "neet", "upsc", "iit", "iits", "cbse", "icse", "board exams", "12th boards", "10th boards",
             "class 12", "class 10", "competitive exams"],
}
STRONG = [g for g in GROUPS if g != "kin_weak"]
RX = {g: re.compile(L + "(?:" + "|".join(re.escape(w).replace(r"\ ", r"\s+") for w in ws) + ")" + R, re.I)
      for g, ws in GROUPS.items()}


def markers(text):
    out = {}
    for g, rx in RX.items():
        found = {m.group(0).lower() for m in rx.finditer(text)}
        if found:
            out[g] = sorted(found)
    return out


def main():
    posts, counts = [], Counter()
    for line in IN.open(encoding="utf-8"):
        r = json.loads(line)
        m = markers(r["text_clean"])
        counts["posts_screened"] += 1
        strong = any(g in m for g in STRONG)
        for g in m:
            counts[f"posts_with_{g}"] += 1
        if strong:
            counts["posts_with_any_strong_marker"] += 1
            counts["strong_and_focus_early"] += r["eligibility_status"] == "provisionally_eligible"
            posts.append((r, m))
        elif "kin_weak" in m:
            counts["posts_with_weak_kin_only"] += 1
    rng = random.Random(SEED)
    sample = rng.sample(posts, min(N_SAMPLE, len(posts)))
    sample.sort(key=lambda x: x[0]["record_id"])
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["record_id", "permalink", "focus_early", "n_words", "markers", "n_strong_groups",
                    "text_clean", "reviewer_indian_context", "reviewer_bereavement_disclosure", "reviewer_note"])
        for r, m in sample:
            w.writerow([r["record_id"], r["source_url"], r["eligibility_status"] == "provisionally_eligible",
                        r["n_words"], "; ".join(f"{g}: {', '.join(v)}" for g, v in m.items()),
                        sum(1 for g in STRONG if g in m), r["text_clean"], "", "", ""])
    COUNTS.parent.mkdir(parents=True, exist_ok=True)
    COUNTS.write_text(json.dumps(dict(counts, sample_size=len(sample), seed=SEED), indent=1), encoding="utf-8")
    for k, v in sorted(counts.items()):
        print(f"{k}: {v}")
    print(f"sample: {len(sample)} -> {OUT}")


if __name__ == "__main__":
    main()
