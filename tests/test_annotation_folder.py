import re
from pathlib import Path

import pytest

import gold as G

ROOT = Path(__file__).resolve().parents[1]
ANN = ROOT / "data" / "annotation"
ALLOWED = re.compile(
    r"^(\.gitignore"
    r"|texts"
    r"|handoff"
    r"|.*_(coder\d|r\d)\.csv"
    r"|(gold_sheet|gold_components|moves_sheet)(_v\d+)?\.csv"
    r"|gold_shortform_placeholder_v\d+\.csv"
    r"|audit_passages\.csv|audit_rating_sheet_r\d\.csv"
    r"|meta_review\.csv"
    r"|gold_(sheet|components)_v\d+_adjudicated\.csv|a1_gold\.csv"
    r"|.*_key(_v\d+)?\.csv|annotation_key\.csv"
    r"|gold_manifest_v\d+(\.replaced-\d{8}T\d{6})?\.json|id_mapping_v\d+\.csv|released_annotation_ids\.csv"
    r"|moves_codebook_examples\.md)$")
MACHINE = re.compile(r"llm|dict|chat|channel|model|disagree|auto|pred", re.I)
PROVENANCE = ("machine pre-filled (two machine runs, 2026-10-11), reviewed and accepted by the investigator "
              "without change unless a correction is logged")
ADJUDICATED_PROVENANCE = ("machine pre-filled (two machine runs), investigator-reviewed; disagreements resolved by "
                          "majority with a third, independent language-model coder; no human adjudication")
ADJUDICATED = re.compile(r"^(gold_(sheet|components)_v\d+_adjudicated|a1_gold)\.csv$")


def provenance_problems(path):
    import csv
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        header, rows = reader.fieldnames or [], list(reader)
    if "provenance" not in header:
        return []
    if "corrections" not in header:
        return [f"{path.name}: provenance without a corrections column"]
    ok = {PROVENANCE, ADJUDICATED_PROVENANCE} if ADJUDICATED.match(path.name) else {PROVENANCE}
    bad = [i for i, r in enumerate(rows) if r["provenance"] not in ok or not r["corrections"].isdigit()]
    return [f"{path.name}: rows {bad[:5]} lack the approved provenance / corrections"] if bad else []


def labelled_prefill(path):
    return path.suffix == ".csv" and not provenance_problems(path) and "provenance" in path.read_text(
        encoding="utf-8").splitlines()[0].split(",")


@pytest.mark.skipif(not ANN.exists(), reason="data/annotation/ is local only")
def test_annotation_folder_has_only_human_sheets_and_keys():
    names = sorted(p.name for p in ANN.iterdir())
    bad = [n for n in names if not ALLOWED.match(n) or (MACHINE.search(n) and not labelled_prefill(ANN / n))]
    assert not bad, f"not a human sheet or key: {bad} -> move to data/processed/channels/"
    problems = [p for n in names if n.endswith(".csv") for p in provenance_problems(ANN / n)]
    assert not problems, problems


def test_provenance_rule_accepts_labelled_and_refuses_unlabelled(tmp_path):
    ok = tmp_path / "gold_sheet_v1_coder1.csv"
    ok.write_text(f'gold_id,orientation,provenance,corrections\nGRF-1,I,"{PROVENANCE}",0\n', encoding="utf-8")
    assert provenance_problems(ok) == [] and labelled_prefill(ok)
    wrong = tmp_path / "gold_sheet_v1_coder2.csv"
    wrong.write_text("gold_id,orientation,provenance,corrections\nGRF-1,I,LLM output,0\n", encoding="utf-8")
    assert provenance_problems(wrong)
    nocount = tmp_path / "x_coder1.csv"
    nocount.write_text(f'gold_id,provenance\nGRF-1,"{PROVENANCE}"\n', encoding="utf-8")
    assert provenance_problems(nocount)
    machine = tmp_path / "gold_pilot_llm.csv"
    machine.write_text("gold_id,orientation\nGRF-1,I\n", encoding="utf-8")
    assert not labelled_prefill(machine)


def test_writers_refuse_the_annotation_folder(tmp_path):
    with pytest.raises(SystemExit):
        G.refuse_annotation_dir(ANN / "gold_pilot_llm.csv")
    with pytest.raises(SystemExit):
        G.refuse_annotation_dir(ANN / "sub" / "x.csv")
    assert G.refuse_annotation_dir(tmp_path / "x.csv") == tmp_path / "x.csv"


def test_channel_scripts_default_outside_the_annotation_folder():
    for script, needle in (("llm_coder.py", "data/processed/channels/gold_pilot_llm.csv"),
                           ("audit_chat.py", "data/processed/channels/audit_chat_replies.csv")):
        src = (ROOT / "src" / "analysis" / script).read_text(encoding="utf-8")
        defaults = re.findall(r'add_argument\("--[a-z-]*out", default=([^)]*)\)', src)
        assert needle in src and not any("data/annotation" in d for d in defaults), (script, defaults)
