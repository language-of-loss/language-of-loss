"""`make all`: run the analysis pipeline in order and check every output against the previous run."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = str(ROOT / ".venv" / "bin" / "python")
PROC = "data/processed"
STEPS = [
    ("preprocess", [PY, "src/analysis/preprocess.py", "--in", "data/clean/blogs_merged.jsonl",
                    "--out", f"{PROC}/clauses.jsonl"],
     [f"{PROC}/clauses.jsonl", f"{PROC}/tokens.csv"]),
    ("flags", [PY, "src/analysis/flags.py", "--in", f"{PROC}/clauses.jsonl", "--out", f"{PROC}/flags.csv"],
     [f"{PROC}/flags.csv"]),
    ("lexmatch", [PY, "src/analysis/lexmatch.py", "--lexicon", "lexicon/lexicon.csv", "--in", f"{PROC}/clauses.jsonl",
                  "--flags", f"{PROC}/flags.csv", "--out", f"{PROC}/clause_features.csv"],
     [f"{PROC}/clause_features.csv"]),
    ("referents", [PY, "src/analysis/referents.py", "--in", f"{PROC}/clauses.jsonl", "--out", f"{PROC}/referents.csv"],
     [f"{PROC}/referents.csv", f"{PROC}/text_features.csv"]),
    ("eligibility", [PY, "src/analysis/eligibility.py", "--in", f"{PROC}/clauses.jsonl",
                     "--out", f"{PROC}/eligibility.csv", "--flags", f"{PROC}/flags.csv"],
     [f"{PROC}/eligibility.csv", f"{PROC}/predicate_inventory.csv", f"{PROC}/relational_sites.csv",
      f"{PROC}/flags.csv"]),
    ("decompose_relational", [PY, "src/analysis/decompose.py", "--marker", "relational",
                              "--out", "results/decompose_relational_dev.csv"],
     ["results/decompose_relational_dev.csv", "results/decompose_relational_dev.json",
      "results/decompose_relational_dev_drop_largest.csv"]),
    ("text_meta", [PY, "src/analysis/text_meta.py"], [f"{PROC}/text_meta.csv"]),
]
STEP_NAMES = [s[0] for s in STEPS]
LAST_WRITER = {o: name for name, _, outs in STEPS for o in outs}
MANIFEST = ROOT / PROC / "repro_manifest.json"


def file_stats(path):
    p = ROOT / path
    if not p.exists():
        return None
    h = hashlib.sha256()
    lines = 0
    with open(p, "rb") as fh:
        for line in fh:
            h.update(line)
            if line.strip():
                lines += 1
    rows = lines - 1 if p.suffix == ".csv" and lines else lines
    return dict(rows=rows, sha256=h.hexdigest())


def compare(prev, now):
    if now is None:
        return "missing"
    if prev is None:
        return "new"
    return "same" if prev["sha256"] == now["sha256"] else "changed"


def git_head():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def run(steps, snapshot=False):
    records, failed = [], None
    for name, cmd, outputs in steps:
        t0 = time.time()
        rc, tail = 0, ""
        if not snapshot:
            print(f"== {name}: {' '.join(c.replace(str(ROOT) + '/', '') for c in cmd)}", flush=True)
            p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            rc = p.returncode
            tail = (p.stdout + p.stderr).strip().splitlines()[-3:] if (p.stdout or p.stderr) else []
            print("\n".join(tail), flush=True)
        records.append(dict(step=name, returncode=rc, seconds=round(time.time() - t0, 1), log_tail=tail,
                            outputs={o: file_stats(o) for o in outputs if LAST_WRITER[o] == name}))
        if rc != 0:
            failed = name
            break
    return records, failed


def write_report(path, records, prev, failed, args, started):
    prev_out = {}
    for r in (prev or {}).get("steps", []):
        for o, st in r["outputs"].items():
            prev_out[(r["step"], o)] = st
    n = {"same": 0, "changed": 0, "new": 0, "missing": 0}
    rows = []
    for r in records:
        for o, st in r["outputs"].items():
            p = prev_out.get((r["step"], o))
            s = compare(p, st)
            n[s] += 1
            rows.append(f"| {r['step']} | `{o}` | {p['rows'] if p else '–'} | {st['rows'] if st else '–'} | "
                        f"{p['sha256'][:12] if p else '–'} | {st['sha256'][:12] if st else '–'} | **{s}** |")
    L = ["# Reproducibility check (`make all`)", "",
         f"- Run: {started} → {time.strftime('%Y-%m-%d %H:%M')}; commit {git_head()}; mode: "
         f"{'snapshot (nothing executed)' if args.snapshot else 'pipeline run'}"
         + (f", from step `{args.start}`" if args.start else ""),
         f"- Baseline: {prev['finished'] + ' (commit ' + prev['commit'] + ')' if prev else 'none (first run): every output is new'}",
         f"- Result: {n['same']} same, {n['changed']} changed, {n['new']} new, {n['missing']} missing"
         + (f"; **stopped: step `{failed}` failed**" if failed else ""),
         "- Rows = data lines (CSV header excluded); sha256 over the raw bytes. Markdown summaries are not compared "
         "(they contain run timestamps). `changed` is not an error by itself: it is expected after a code or input "
         "change and must be explained in docs/session_notes.md; with no change in code or input it means the step "
         "is not deterministic.", "",
         "| step | output | rows before | rows now | sha256 before | sha256 now | status |",
         "|---|---|---|---|---|---|---|"] + rows + ["", "## Steps", "",
                                                    "| step | exit | seconds |", "|---|---|---|"]
    L += [f"| {r['step']} | {r['returncode']} | {r['seconds']} |" for r in records]
    if failed:
        L += ["", f"## Failure in `{failed}`", "", "```"] + records[-1]["log_tail"] + ["```"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return n


def summary(report_path, manifest_path=MANIFEST):
    import csv
    rep = Path(report_path)
    if not rep.exists() or not manifest_path.exists():
        print("no run recorded yet: run `make all`")
        return 1
    lines = rep.read_text(encoding="utf-8").splitlines()
    print("\n".join(l for l in lines[:6] if l.startswith("- ")))
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(f"\nmanifest: {m['finished']} (commit {m['commit']}); steps: "
          + ", ".join(f"{r['step']}={'ok' if r['returncode'] == 0 else 'FAILED'}" for r in m["steps"]))
    for name in ("decompose_dev.csv", "decompose_relational_dev.csv"):
        f = ROOT / "results" / name
        if f.exists():
            rows = {r["quantity"]: r for r in csv.DictReader(open(f, encoding="utf-8"))}
            print(f"\n{name} (dev smoke, per 100 finite clauses):")
            for q in ("delta", "forced_share", "opportunity_share", "choice_share"):
                if q in rows:
                    r = rows[q]
                    print(f"  {q:18} {float(r['estimate']):8.3f}  [{float(r['lo']):8.3f}, {float(r['hi']):8.3f}]")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--from", dest="start", choices=STEP_NAMES, default=None, help="start at this step")
    ap.add_argument("--snapshot", action="store_true", help="hash current outputs, run nothing")
    ap.add_argument("--report", default=str(ROOT / "docs" / "repro_check.md"))
    ap.add_argument("--summary", action="store_true", help="print the last run's result and exit")
    args = ap.parse_args(argv)
    if args.summary:
        sys.exit(summary(args.report))
    started = time.strftime("%Y-%m-%d %H:%M")
    steps = STEPS[STEP_NAMES.index(args.start):] if args.start else STEPS
    prev = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else None
    records, failed = run(steps, args.snapshot)
    n = write_report(Path(args.report), records, prev, failed, args, started)
    if not failed:
        if MANIFEST.exists():
            shutil.copy(MANIFEST, MANIFEST.with_name("repro_manifest.prev.json"))
        if args.start and prev:
            kept = [r for r in prev["steps"] if r["step"] not in {s[0] for s in steps}]
            records = kept + records
        MANIFEST.write_text(json.dumps(dict(started=started, finished=time.strftime("%Y-%m-%d %H:%M"),
                                            commit=git_head(), snapshot=args.snapshot, steps=records), indent=1),
                            encoding="utf-8")
    print(f"repro: {n}; report {args.report}" + (f"; FAILED at {failed}" if failed else ""))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
