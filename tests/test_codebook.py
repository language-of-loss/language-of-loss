import json
import re
from pathlib import Path

import pytest

import codebook_examples as C
from gold import CODEBOOK

ROOT = Path(__file__).resolve().parents[1]
CLAUSES = ROOT / "data/processed/clauses.jsonl"


def test_every_value_has_two_examples_per_language_or_a_reason():
    for field, values in CODEBOOK.items():
        for value in values:
            for lang in ("hi", "en"):
                n = sum(1 for e in C.EXAMPLES if e[:3] == (field, value, lang))
                assert n == 2 or (field, value, lang) in C.NOT_APPLICABLE, (field, value, lang, n)


def test_committed_codebook_cites_every_example_and_has_no_markers_left_empty():
    md = (ROOT / "docs/codebook_v1.md").read_text(encoding="utf-8")
    cited = set(re.findall(r"`(blogs:[^`]+#\d{4})`", md))
    assert cited == C.example_ids()
    assert not re.search(r"<!-- EXAMPLES \w+ -->\n<!-- /EXAMPLES -->", md)


@pytest.mark.skipif(not CLAUSES.exists(), reason="needs the local parse (data/processed is git-ignored)")
def test_examples_are_dev_finite_and_their_text_stays_out_of_the_committed_file():
    clauses = C.load_clauses(CLAUSES)
    assert C.check(clauses) == []
    md = (ROOT / "docs/codebook_v1.md").read_text(encoding="utf-8")
    for cid in C.example_ids():
        text = clauses[cid]["clause_text"]
        assert text not in md, cid
