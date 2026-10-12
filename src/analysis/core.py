"""`make core`: the lean main path. Runs only what outputs 1-9 need, in order, and writes docs/STATUS.md."""
import argparse
import csv
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from predictions import tests_allowed

ROOT = Path(__file__).resolve().parents[2]
PY = str(ROOT / ".venv" / "bin" / "python")
A = "src/analysis"
ANN = "data/annotation"
PROC = "data/processed"
AGREEMENT = "results/agreement/agreement_summary_gold_sheet_v1.csv"
OUTPUTS = {
    1: "gold-set alpha per field",
    2: "dictionary precision / recall per category per language; Rogan-Gladen corrected rates",
    3: "Run 1 / Run 2 / Run 2b odds ratios; decomposition with bootstrap choice-share interval",
    4: "second-language rival: not estimable from text-internal evidence; rival check with diaspora + platform "
       "covariates",
    5: "audit: under-reading per system, cue interaction, stable under-read components",
    6: "chosen-dative rate vs forced baseline (binomial)",
    7: "component-profile JSD",
    8: "NRC-Hindi vs native lexicon recall (native-only vs translatable); MuRIL pair with McNemar",
    9: "collocation network figures (hi, en), appendix exhibit",
}


def p(rel):
    return ROOT / rel


def exists(rel, why):
    return (f"`{rel}` exists", lambda: p(rel).exists(), why)


def coded(rel, fields=None):
    path = p(rel)
    if not path.exists():
        return False
    with open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if any((r.get(f) or "").strip() for f in (fields or _codebook_fields())):
                return True
    return False


def _codebook_fields():
    from gold import CODEBOOK
    return list(CODEBOOK)


def sheets_coded(a, b, fields=None, why=""):
    return (f"`{a}` and `{b}` filled by the two investigators", lambda: coded(a, fields) and coded(b, fields), why)


def sheets_blank(a, b, field):
    return (f"`{a}` and `{b}` still blank (a redraw after rating would overwrite the ratings)",
            lambda: not coded(a, [field]) and not coded(b, [field]), "never overwrite filled rating sheets")


def gold_label():
    path, adj = p(f"{ANN}/gold_sheet_v1_coder1.csv"), p(f"{ANN}/gold_sheet_v1_adjudicated.csv")
    if adj.exists() and "third, independent model coder" in adj.read_text(encoding="utf-8"):
        return ("reviewed machine-prefilled labels (adjudicated = agreed fields + majority with a third model coder, "
                "commercial_llm_A; no human adjudication)")
    if path.exists() and "provenance" in path.read_text(encoding="utf-8").splitlines()[0].split(","):
        return "reviewed machine-prefilled labels (adjudicated = agreed fields of the two reviewed sheets)"
    return "gold v1, adjudicated"


def agreement_ok():
    return (f"`{AGREEMENT}` holds real agreement statistics (written by agreement.py from the two coded sheets)",
            lambda: tests_allowed(p(AGREEMENT)), "guard: no hypothesis test before human agreement (study protocol)")


def diaspora_confirmed():
    def check():
        path = p(f"{PROC}/text_meta.csv")
        if not path.exists():
            return False
        rows = list(csv.DictReader(open(path, encoding="utf-8", newline="")))
        return bool(rows) and "diaspora_conf" in rows[0] and all(r["diaspora_conf"] == "human" for r in rows)
    return (f"`{ANN}/meta_review.csv` diaspora rows confirmed by a human for every text, then `make text_meta`", check,
            "pre-filled metadata is never used as a covariate")


def registration_ok(path):
    import re
    path = Path(path)
    if not path.exists() or not path.read_text().strip():
        return False
    lines = dict(l.split(":", 1) for l in path.read_text().splitlines() if ":" in l)
    tag = lines.get("tag", "").strip()
    if tag:
        r = subprocess.run(["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"], cwd=ROOT, capture_output=True)
        return r.returncode == 0
    return bool(re.search(r"10\.\d{4,}/\S+", path.read_text()))


def registered():
    return ("`docs/registration.txt` (OSF DOI, or the `make register` git tag) exists and its tag is in git",
            lambda: registration_ok(p("docs/registration.txt")),
            "R --run fits on the confirmatory split by default: never before the registration")


def rscript():
    return ("R installed (`Rscript` on PATH)", lambda: shutil.which("Rscript") is not None, "")


@dataclass
class Step:
    name: str
    outputs: tuple
    cmd: list
    needs: list = field(default_factory=list)
    fallback: list = None
    api: bool = False
    script: str = ""
    inside_guard: str = ""

    def missing(self):
        return [desc for desc, check, _ in self.needs if not check()]


MCNEMAR_NOTE = ("standalone checkpoints, model 2 PROVISIONAL (BRIGHTER only, no native gold), not retrained per fold "
                "(investigators' decision 2026-10-11: not retrained)")


def steps():
    R = ["Rscript"]
    conf = ["--split", "confirmatory"] if registration_ok(p("docs/registration.txt")) else []
    label = gold_label()
    return [
        Step("pipeline", (3,), [PY, f"{A}/make_all.py"], script=f"{A}/make_all.py"),
        Step("predictions", (6, 7), [PY, f"{A}/predictions.py"] + conf + (["--status", label] if conf else []),
             script=f"{A}/predictions.py",
             inside_guard="output 6's exact binomial test (predictions.py refuses it)"),
        Step("collocation", (9,), [PY, f"{A}/collocation.py"], script=f"{A}/collocation.py"),
        Step("agreement", (1,),
             [PY, f"{A}/agreement.py", "--a", f"{ANN}/gold_sheet_v1_coder1.csv", "--b", f"{ANN}/gold_sheet_v1_coder2.csv"],
             [sheets_coded(f"{ANN}/gold_sheet_v1_coder1.csv", f"{ANN}/gold_sheet_v1_coder2.csv")],
             script=f"{A}/agreement.py"),
        Step("agreement_components", (1,),
             [PY, f"{A}/agreement.py", "--a", f"{ANN}/gold_components_v1_coder1.csv",
              "--b", f"{ANN}/gold_components_v1_coder2.csv"],
             [sheets_coded(f"{ANN}/gold_components_v1_coder1.csv", f"{ANN}/gold_components_v1_coder2.csv",
                           fields=_component_fields())],
             script=f"{A}/agreement.py"),
        Step("llm_channel", (2,), [PY, f"{A}/llm_coder.py"], [exists(f"{ANN}/gold_pilot_r1.csv", "")], api=True,
             script=f"{A}/llm_coder.py"),
        Step("dict_channel", (2,),
             [PY, f"{A}/dict_channel.py", "--sheet", f"{ANN}/gold_sheet_v1_adjudicated.csv",
              "--key", f"{ANN}/gold_key_v1.csv", "--sheet-out", f"{PROC}/channels/gold_dict_v1.csv"],
             [exists(f"{ANN}/gold_sheet_v1_adjudicated.csv", "the investigators' resolved codes")],
             script=f"{A}/dict_channel.py"),
        Step("validate", (2,),
             [PY, f"{A}/validate.py", "--gold", f"{ANN}/gold_sheet_v1_adjudicated.csv",
              "--coders", f"{ANN}/gold_sheet_v1_coder1.csv", f"{ANN}/gold_sheet_v1_coder2.csv",
              "--channel", f"dict={PROC}/channels/gold_dict_v1.csv", "--status", label],
             [exists(f"{ANN}/gold_sheet_v1_adjudicated.csv", "the investigators' resolved codes"), agreement_ok()],
             script=f"{A}/validate.py"),
        Step("corrected_rates", (2,), [PY, f"{A}/corrected_rates.py"]
             + (conf + ["--out", "results/corrected_rates_confirmatory.csv"] if conf else []),
             [exists("results/validation_table.csv", "validate.py on the adjudicated gold set"), agreement_ok()],
             script=f"{A}/corrected_rates.py"),
        Step("h1_glmm", (3,), R + ["R/h1_glmm.R", "--run"], [rscript(), agreement_ok(), registered()],
             fallback=R + ["R/h1_glmm.R", "--dry-run"], script="R/h1_glmm.R"),
        Step("h1_glmm_rival", (4,), R + ["R/h1_glmm.R", "--run", "--covariates", "rival"],
             [rscript(), agreement_ok(), registered(), diaspora_confirmed()],
             fallback=R + ["R/h1_glmm.R", "--dry-run", "--covariates", "rival"], script="R/h1_glmm.R"),
        Step("a1_score", (8,), [PY, f"{A}/translation_bias.py", "--score"], script=f"{A}/translation_bias.py"),
        Step("a1_recall", (8,), [PY, f"{A}/translation_bias.py", "--gold", f"{ANN}/a1_gold.csv"],
             [exists(f"{ANN}/a1_gold.csv", "clause_id, emotional (0/1) for the Hindi gold clauses"),
              agreement_ok()],
             fallback=[PY, f"{A}/translation_bias.py", "--dry-run"], script=f"{A}/translation_bias.py"),
        Step("mcnemar", (8,), [PY, f"{A}/mcnemar.py", "--status", label + "; " + MCNEMAR_NOTE],
             [exists(f"{ANN}/a1_gold.csv", "clause_id, emotional (0/1) for the Hindi gold clauses"),
              exists(f"{PROC}/channels/muril_translated_predictions.csv", "train_muril_pair.py, model 1 (GPU)"),
              exists(f"{PROC}/channels/muril_native_predictions.csv", "train_muril_pair.py, model 2 (GPU)"),
              agreement_ok()], script=f"{A}/mcnemar.py"),
        Step("audit_passages", (5,), [PY, f"{A}/audit_passages.py"],
             [sheets_blank(f"{ANN}/audit_rating_sheet_r1.csv", f"{ANN}/audit_rating_sheet_r2.csv", "intensity_1to7")],
             script=f"{A}/audit_passages.py"),
        Step("audit_models", (5,), [PY, f"{A}/audit_models.py", "--audit"],
             [exists(f"{ANN}/audit_passages.csv", "audit_passages.py")], script=f"{A}/audit_models.py"),
        Step("audit_chat", (5,), [PY, f"{A}/audit_chat.py", "--confirm"],
             [exists(f"{ANN}/audit_passages.csv", "audit_passages.py")], api=True, script=f"{A}/audit_chat.py"),
        Step("audit_match", (5,), [PY, f"{A}/audit_match.py"],
             [sheets_coded(f"{ANN}/audit_rating_sheet_r1.csv", f"{ANN}/audit_rating_sheet_r2.csv",
                           fields=["intensity_1to7"])], script=f"{A}/audit_match.py"),
        Step("audit_model", (5,), R + ["R/audit.R", "--run"],
             [rscript(), exists(f"{PROC}/audit_pairs.csv", "audit_match.py on the two filled rating sheets"),
              agreement_ok()], fallback=None, script="R/audit.R"),
        Step("assemble", tuple(OUTPUTS), [PY, f"{A}/assemble.py"], script=f"{A}/assemble.py"),
    ]


def _component_fields():
    path = Path(__file__).resolve().parents[2] / "lexicon" / "entry_vectors.csv"
    with open(path, encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    return [c for c in header if c not in ("entry_id", "lang", "names_emotion")]


def plan(step, llm):
    if step.script and not p(step.script).exists():
        return "not built", f"{step.script} does not exist"
    if step.api and not llm:
        return "skipped", "API step: opt in with `make core LLM=1`"
    miss = step.missing()
    if miss:
        return ("fallback" if step.fallback else "blocked"), "; ".join(miss)
    return "run", ""


def execute(cmd):
    t0 = time.time()
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
    return r.returncode, round(time.time() - t0, 1), tail


def run(llm=False, dry_run=False, only=None):
    records = []
    for s in steps():
        if only and s.name not in only:
            continue
        action, reason = plan(s, llm)
        rec = dict(step=s.name, outputs=list(s.outputs), script=s.script, action=action, reason=reason,
                   returncode=None, seconds=0.0,
                   inside_guard=s.inside_guard if s.inside_guard and not agreement_ok()[1]() else "")
        cmd = s.cmd if action == "run" else s.fallback if action == "fallback" else None
        print(f"== {s.name} [{', '.join(map(str, s.outputs))}]: {action}" + (f" ({reason})" if reason else ""),
              flush=True)
        if cmd and not dry_run:
            rc, secs, tail = execute(cmd)
            rec.update(returncode=rc, seconds=secs, command=" ".join(cmd).replace(PY, "python"))
            print("   " + "\n   ".join(tail), flush=True)
            if rc != 0:
                rec["action"] = "failed" if action == "run" else "fallback failed"
        records.append(rec)
    return records


def output_status(recs, dry_run):
    out = {}
    for o in OUTPUTS:
        rs = [r for r in recs if o in r["outputs"] and r["step"] != "assemble"]
        scripts = sorted({r["script"] for r in rs})
        acts = [r["action"] for r in rs]
        unblock = [r["reason"] for r in rs if r["action"] in ("blocked", "fallback", "not built",
                                                                 "failed", "fallback failed") and r["reason"]]
        api_off = [Path(r["script"]).name for r in rs if r["action"] == "skipped"]
        if any(a in ("failed", "fallback failed") for a in acts):
            st = "FAILED: see results/core_run.json"
        elif any(a == "not built" for a in acts):
            st = "not built"
        elif acts and all(a == "run" for a in acts if a != "skipped"):
            st = ("ready (dry run: nothing executed)" if dry_run else "ran (dev smoke while no agreement statistics)")
        elif any(a == "run" for a in acts):
            st = "partly ran; rest blocked on human input"
        else:
            st = "blocked on human input" + (" (machinery checked by a dry run)" if "fallback" in acts else "")
        inside = [r["inside_guard"] for r in rs if r.get("inside_guard") and 6 in r["outputs"] and o == 6]
        if inside and st.startswith(("ran", "ready")):
            st = ("estimates ready (dry run)" if st.startswith("ready") else "estimates ran (dev smoke)") + \
                "; test refused until agreement statistics exist"
            unblock.append(agreement_ok()[0])
        if api_off:
            st += f" (API step not run: {', '.join(api_off)}; opt in with LLM=1)"
        out[o] = (scripts, st, "; ".join(dict.fromkeys("; ".join(unblock).split("; "))) if unblock else "nothing")
    return out


def write_status(recs, dry_run, path=ROOT / "docs" / "STATUS.md"):
    st = output_status(recs, dry_run)
    L = ["# STATUS: core outputs 1-9", "",
         f"Generated by `src/analysis/core.py` ({'`make core-dry`, plan only' if dry_run else '`make core`'}) on "
         f"{time.strftime('%Y-%m-%d %H:%M')}. Regenerate; do not edit by hand. No number appears here: numbers are in RESULTS_LOG.md.", "",
         "| output | what | scripts | status | what unblocks it |", "|---|---|---|---|---|"]
    for o, what in OUTPUTS.items():
        scripts, s, unblock = st[o]
        L.append(f"| {o} | {what} | {', '.join(f'`{x}`' for x in scripts)} | {s} | {unblock} |")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    return path


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="print the plan, run nothing")
    ap.add_argument("--llm", action="store_true", help="also run the two API steps (llm_coder.py, audit_chat.py)")
    ap.add_argument("--only", nargs="*", help="run only these steps")
    ap.add_argument("--status-out", default=str(ROOT / "docs" / "STATUS.md"))
    args = ap.parse_args(argv)
    recs = run(llm=args.llm, dry_run=args.dry_run, only=args.only)
    if not args.only:
        write_status(recs, args.dry_run, Path(args.status_out))
    if not args.dry_run:
        (ROOT / "results" / "core_run.json").write_text(json.dumps(dict(
            finished=time.strftime("%Y-%m-%d %H:%M"), llm=args.llm, steps=recs), indent=1) + "\n", encoding="utf-8")
    failed = [r["step"] for r in recs if r["action"] in ("failed", "fallback failed")]
    print(f"core: {len(recs)} steps; failed: {failed or 'none'}; status -> {args.status_out}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
