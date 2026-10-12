from pathlib import Path

import pytest

import appendix as A

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not (ROOT / "data/processed/predicate_inventory.csv").exists(),
                                reason="table C reads data/processed (local)")


def rows(text):
    return [l for l in text.splitlines() if l.startswith("| ")][1:]


def test_appendix_is_current_and_complete():
    built = A.build()
    for name, text in built.items():
        assert (A.OUT / name).read_text(encoding="utf-8") == text, f"{name} is stale: run src/analysis/appendix.py"
    counts = {name: len(rows(t)) for name, t in built.items()}
    assert counts == {"A_component_inventory.md": 24, "B_lexicon.md": 205, "C_rule_table.md": 570,
                      "D_exponent_table.md": 65, "E_flag_test_set.md": 22}


def test_lexicon_table_carries_no_example_sentences():
    b = A.build()["B_lexicon.md"]
    assert "Example" not in b.splitlines()[next(i for i, l in enumerate(b.splitlines()) if l.startswith("| Entry"))]
    assert "(hi_0" not in b


def test_cells_escape_pipes_and_line_breaks():
    assert A.cell("a|b\nc") == "a\\|b / c" and A.cell("") == "—"
