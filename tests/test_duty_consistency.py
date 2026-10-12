import csv
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DUTY = ("DUTY_DONE", "DUTY_UNDONE")
TRACE = {"DUTY_DONE": re.compile(r"\bi (do|did) (good )?things for|things i have to do"),
         "DUTY_UNDONE": re.compile(r"cannot do|could have done|did not do|wanted to do|cannot be")}
KNOWN_UNTRACED = set()
KNOWN_ONE_WAY = set()


def load():
    ev = {r["entry_id"]: r for r in csv.DictReader(open(ROOT / "lexicon/entry_vectors.csv", encoding="utf-8"))}
    lex = {r["entry_id"]: r for r in csv.DictReader(open(ROOT / "lexicon/lexicon.csv", encoding="utf-8"))}
    return ev, lex


def duty_entries(ev):
    return [(e, c) for e in ev for c in DUTY if ev[e][c] == "1"]


def test_every_tag_traces_to_a_line():
    ev, lex = load()
    untraced = {(e, c) for e, c in duty_entries(ev) if not TRACE[c].search(lex[e]["nsm_explication"].lower())}
    assert untraced == KNOWN_UNTRACED


def cps(entry):
    return [c.strip() for c in entry["counterpart"].split(";") if c.strip() != "none"]


def test_counterparts_agree_on_the_component():
    ev, lex = load()
    for e, c in duty_entries(ev):
        for cp in cps(lex[e]):
            assert ev[cp][c] == "1", (e, cp, c)


def test_counterpart_links_are_two_way():
    ev, lex = load()
    one_way = {(e, cp) for e, _ in duty_entries(ev) for cp in cps(lex[e]) if e not in cps(lex[cp])}
    assert one_way == KNOWN_ONE_WAY


@pytest.mark.skipif(not (ROOT / "data/processed/clause_features.csv").exists(), reason="data/processed is local")
def test_clause_components_follow_the_matched_entries():
    ev, lex = load()
    with open(ROOT / "data/processed/clause_features.csv", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        entries = [c for c in reader.fieldnames if c in ev]
        bad = 0
        for r in reader:
            for c in DUTY:
                from_entries = any(r[e] == "1" and ev[e][c] == "1" and lex[e]["grammar_forced"] == "N" for e in entries)
                bad += (r[f"comp_{c}"] == "1") != from_entries
    assert bad == 0
