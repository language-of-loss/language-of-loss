import datetime
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "registration.txt"
PREREG = ROOT / "docs" / "preregistration.md"
FROZEN = ["docs/preregistration.md", "R/", "src/analysis/agreement.py", "src/analysis/validate.py",
          "src/analysis/corrected_rates.py", "src/analysis/rae.py", "src/analysis/decompose.py",
          "src/analysis/predictions.py", "src/analysis/eligibility.py", "src/analysis/referents.py",
          "src/analysis/text_meta.py", "src/analysis/audit_match.py", "src/analysis/mcnemar.py",
          "src/analysis/translation_bias.py", "src/analysis/gold.py", "src/analysis/core.py", "lexicon/"]


def git(*args, check=True):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=check).stdout.strip()


def main():
    stale = subprocess.run([sys.executable, str(ROOT / "src/analysis/preregistration.py"), "--check"], cwd=ROOT,
                           capture_output=True, text=True)
    if stale.returncode:
        raise SystemExit("refusing: docs/preregistration.md is stale; regenerate and commit it first")
    dirty = git("status", "--porcelain", "--", *FROZEN)
    if dirty:
        raise SystemExit(f"refusing: uncommitted changes on the confirmatory path:\n{dirty}")
    now = datetime.datetime.now(datetime.timezone.utc)
    tag = f"prereg-v1-{now:%Y%m%d}"
    if git("tag", "-l", tag):
        raise SystemExit(f"refusing: tag {tag} already exists")
    commit = git("rev-parse", "HEAD")
    sha = hashlib.sha256(PREREG.read_bytes()).hexdigest()
    signed = bool(git("config", "--get", "user.signingkey", check=False))
    msg = (f"Pre-registration v1, {now:%Y-%m-%d %H:%M:%S} UTC\n\ndocs/preregistration.md sha256 {sha}\n"
           "OSF DOI: pending; the git tag is the timestamped record")
    git("tag", "-s" if signed else "-a", tag, "-m", msg)
    porcelain = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout
    others = [l[3:] for l in porcelain.splitlines() if l[3:] != "docs/registration.txt"]
    OUT.write_text("\n".join([
        f"tag: {tag}", f"commit: {commit}", f"date: {now:%Y-%m-%dT%H:%M:%SZ}",
        f"signed: {'yes' if signed else 'no (no git signing key configured; annotated tag)'}",
        f"preregistration_sha256: {sha}",
        "OSF DOI: pending; the git tag is the timestamped record",
        "not_frozen (uncommitted at tagging, outside the confirmatory path): " + (", ".join(others) or "none"),
    ]) + "\n", encoding="utf-8")
    print(f"tagged {tag} at {commit[:10]} ({'signed' if signed else 'unsigned, annotated'}); wrote {OUT}")


if __name__ == "__main__":
    main()
