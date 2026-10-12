"""Draw a random sample of finite clause units for a manual segmentation check."""
import argparse
import json
import random
import time
from pathlib import Path


def cell(s):
    return (s or "").replace("|", "\\|").replace("\n", " ")


def draw(clauses, lang, n, rng):
    pool = [c for c in clauses if c["lang"] == lang and c["is_finite"]]
    picked = rng.sample(range(len(pool)), min(n, len(pool)))
    return [pool[i] for i in sorted(picked)]


def table(rows):
    out = ["| # | clause_id | clause_text | span_text (if discontinuous) | subject from | split | ok? |",
           "|---|---|---|---|---|---|---|"]
    for k, c in enumerate(rows, 1):
        span = c["span_text"] if c["discontinuous"] else ""
        out.append(f"| {k} | `{c['clause_id']}` | {cell(c['clause_text'])} | {cell(span)} | "
                   f"{'`' + c['subject_inherited_from'] + '`' if c['subject_inherited_from'] else ''} | "
                   f"{c['split']} |  |")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--in", dest="inp", default="data/processed/clauses.jsonl")
    ap.add_argument("--out", default="data/processed/clause_sample_stage3.md")
    ap.add_argument("--hi", type=int, default=30)
    ap.add_argument("--en", type=int, default=15)
    ap.add_argument("--seed", type=int, default=20261010)
    args = ap.parse_args()
    clauses = [json.loads(line) for line in open(args.inp, encoding="utf-8")]
    rng = random.Random(args.seed)
    hi, en = draw(clauses, "hi", args.hi, rng), draw(clauses, "en", args.en, rng)
    lines = ["# Stage 3 clause sample (manual check)", "",
             f"Random finite clause units from `{args.inp}`, seed {args.seed}, drawn {time.strftime('%Y-%m-%d')}. "
             "Project-internal: contains short excerpts of third-party blog text, do not share.", "",
             "Check each row: is `clause_text` one clause (finite predicate + its own dependents)? Mark `ok?` "
             "with y / n + note. `span_text` is the original text from the first to the last token where the "
             "unit is discontinuous; `subject from` is the clause whose subject a subject-less conj shares.", "",
             f"## Hindi ({len(hi)})", ""] + table(hi) + ["", f"## English ({len(en)})", ""] + table(en)
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.out}: {len(hi)} hi, {len(en)} en")


if __name__ == "__main__":
    main()
