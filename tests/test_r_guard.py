import shutil
import subprocess
from pathlib import Path

import pytest

import predictions as P

ROOT = Path(__file__).resolve().parents[1]
CASES = {"blank": "field,n_both_coded,pct_agree,alpha_nominal\norientation,0,,\n",
         "nan": "field,n_both_coded,alpha_nominal\norientation,12,NaN\n",
         "ok": "field,n_both_coded,alpha_nominal\norientation,0,\nprocess,30,0.64\n"}


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="R not installed")
def test_r_guard_matches_python_guard(tmp_path):
    for name, text in CASES.items():
        f = tmp_path / f"{name}.csv"
        f.write_text(text, encoding="utf-8")
        code = (f'agreement_ok <- NULL; src <- readLines("{ROOT / "R" / "common.R"}"); '
                f'start <- grep("^agreement_ok <- function", src); end <- start + which(src[start:length(src)] == "}}")[1] - 1; '
                f'eval(parse(text = src[start:end])); cat(agreement_ok("{f}"))')
        r = subprocess.run(["Rscript", "-e", code], capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr
        assert (r.stdout.strip() == "TRUE") == P.tests_allowed(f), name
    assert P.tests_allowed(tmp_path / "ok.csv") and not P.tests_allowed(tmp_path / "blank.csv")
