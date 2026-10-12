"""Freeze the lexicon: write lexicon/FREEZE.md (sha256 and size of every file that defines the instrument) or check"""
import argparse
import hashlib
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FREEZE = ROOT / "lexicon" / "FREEZE.md"
FROZEN = ["lexicon/lexicon.csv", "lexicon/entry_vectors.csv", "lexicon/components.csv", "lexicon/flag_components.csv",
          "lexicon/molecules.csv", "lexicon/primes.csv", "lexicon/constructions.yaml",
          "lexicon/src/build_v02.py", "lexicon/src/components.py", "lexicon/src/entries_hi.py",
          "lexicon/src/entries_en.py", "lexicon/src/lexutil_v02.py", "lexicon/src/write_support_files.py"]
ROW = re.compile(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \| (\d+) \|$")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def current(root=ROOT):
    return {f: (sha256(root / f), (root / f).stat().st_size) for f in FROZEN}


def recorded(path=FREEZE):
    if not Path(path).exists():
        return {}
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = ROW.match(line)
        if m:
            out[m.group(1)] = (m.group(2), int(m.group(3)))
    return out


def diff(rec, cur):
    out = []
    for f in sorted(set(rec) | set(cur)):
        if f not in rec:
            out.append(f"{f}: not recorded in FREEZE.md")
        elif f not in cur:
            out.append(f"{f}: recorded but no longer in the frozen set")
        elif rec[f][0] != cur[f][0]:
            out.append(f"{f}: sha256 {rec[f][0][:12]} -> {cur[f][0][:12]}")
    return out


def write(version, reason, open_items, path=FREEZE):
    cur = current()
    L = [f"# Lexicon freeze: {version}", "",
         f"Frozen {time.strftime('%Y-%m-%d %H:%M')} by `src/analysis/freeze.py --write`. Reason: {reason}", "",
         "Every stage reads the lexicon through these files. `tests/test_lexicon_freeze.py` recomputes the hashes and "
         "fails on any difference: a change to the instrument must be a new freeze (new version, reason, RESULTS_LOG "
         "row), never a silent edit. Rule (draft v4 §3.3): the lexicon is revised on the development split only and "
         "frozen before the confirmatory split is opened; after that it does not change.", "",
         "| file | sha256 | bytes |", "|---|---|---|"]
    L += [f"| `{f}` | `{h}` | {n} |" for f, (h, n) in cur.items()]
    L += ["", "## Resolved before this freeze (investigators' decisions, 2026-10-10)", ""] + [f"- {x}" for x in RESOLVED]
    L += ["", "## Still open (not blocking the freeze)", ""]
    L += [f"- {x}" for x in open_items] or ["- none"]
    Path(path).write_text("\n".join(L) + "\n", encoding="utf-8")
    return path


OPEN_ITEMS = [
    "21 one-way counterpart links outside the DUTY entries (e.g. L-HI-22 -> L-EN-21 -> L-HI-24); the 2026-10-10 "
    "decision covered the four DUTY links only. build_v02.py --check still does not require symmetry.",
]
RESOLVED = [
    "DUTY_UNDONE dropped from P-HI-44 and P-EN-44.",
    "The four one-way DUTY counterpart links made two-way (list-valued counterpart / overlap).",
    "Lexicon stays v0.2 (no v0.3 revision before the confirmatory split).",
]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--version", default="v0.2")
    ap.add_argument("--reason", default="")
    args = ap.parse_args(argv)
    if args.write:
        if not args.reason:
            ap.error("--write needs --reason")
        print(f"wrote {write(args.version, args.reason, OPEN_ITEMS)}")
        return
    d = diff(recorded(), current())
    print("lexicon matches FREEZE.md" if not d else "LEXICON CHANGED SINCE THE FREEZE:\n  " + "\n  ".join(d))
    sys.exit(1 if d else 0)


if __name__ == "__main__":
    main()
