import pytest

import preregistration as PR


@pytest.mark.skipif(not PR.OUT.exists(), reason="docs/preregistration.md is not in the public release")
def test_preregistration_matches_the_code():
    assert PR.OUT.read_text(encoding="utf-8") == PR.build(), \
        "docs/preregistration.md is stale: run .venv/bin/python src/analysis/preregistration.py"


def test_every_core_output_and_direction_is_registered():
    text = PR.build()
    for k in range(1, 10):
        assert f"### Output {k}:" in text
    for eid in ("H-1", "H-2", "P1", "A1", "A2"):
        assert f"| {eid} |" in text
    assert "?" not in text.split("## 4.")[0].replace("? ", "")
