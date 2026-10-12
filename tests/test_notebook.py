import json
from pathlib import Path

import pytest

from gold import CODEBOOK, SHEET_COLUMNS

NB = Path(__file__).resolve().parents[1] / "notebooks" / "train_muril.ipynb"
pytestmark = pytest.mark.skipif(not NB.exists(), reason="notebooks/ is not in the public release")


def cells():
    nb = json.loads(NB.read_text(encoding="utf-8"))
    assert nb["nbformat"] == 4
    return nb["cells"]


def test_parameters_cell_and_dry_run_default():
    params = [c for c in cells() if "parameters" in c["metadata"].get("tags", [])]
    assert len(params) == 1
    g = {}
    exec("".join(params[0]["source"]), g)
    assert g["DRY_RUN"] is True and g["N_FOLDS"] == 5 and g["MODEL_NAME"] == "google/muril-base-cased"


def test_codebook_and_schema_match_gold():
    src = next("".join(c["source"]) for c in cells() if "CODEBOOK = " in "".join(c["source"]))
    g = {}
    exec(src, g)
    assert g["CODEBOOK"] == CODEBOOK and g["SHEET_COLUMNS"] == SHEET_COLUMNS


def test_folds_are_grouped_by_text_and_outputs_are_clean():
    body = "".join("".join(c["source"]) for c in cells() if c["cell_type"] == "code")
    assert "GroupKFold" in body and 'groups=data["record_id"]' in body
    assert all(not c.get("outputs") for c in cells() if c["cell_type"] == "code")
