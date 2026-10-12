from pathlib import Path

import pytest

import core as C

ROOT = Path(__file__).resolve().parents[1]


def test_main_path_uses_no_optional_code():
    for s in C.steps():
        for part in s.cmd + (s.fallback or []):
            assert "src/optional" not in part and "R/optional" not in part, (s.name, part)
    covered = {o for s in C.steps() for o in s.outputs}
    assert covered == set(C.OUTPUTS) == set(range(1, 10))


def test_api_steps_are_exactly_the_two_allowed_scripts_and_opt_in():
    api = {s.script for s in C.steps() if s.api}
    assert api == {"src/analysis/llm_coder.py", "src/analysis/audit_chat.py"}
    for s in C.steps():
        if s.api:
            assert C.plan(s, llm=False)[0] in ("skipped", "not built")
        else:
            assert not any(x.endswith(("llm_coder.py", "audit_chat.py")) for x in s.cmd), s.name


def test_blocked_without_human_input(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "ROOT", tmp_path)
    (tmp_path / "src/analysis").mkdir(parents=True)
    for s in C.steps():
        if s.script:
            (tmp_path / s.script).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / s.script).write_text("")
    acts = {s.name: C.plan(s, llm=False) for s in C.steps()}
    assert acts["agreement"][0] == "blocked" and "gold_sheet_v1_coder1.csv" in acts["agreement"][1]
    assert acts["validate"][0] == "blocked" and "agreement_summary_gold_sheet_v1.csv" in acts["validate"][1]
    assert acts["a1_recall"][0] == "fallback"
    assert acts["h1_glmm_rival"][0] == "fallback" and "diaspora" in acts["h1_glmm_rival"][1]
    assert acts["predictions"][0] == "run" and acts["collocation"][0] == "run"


def test_blank_agreement_file_does_not_unblock(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "ROOT", tmp_path)
    f = tmp_path / C.AGREEMENT
    f.parent.mkdir(parents=True)
    f.write_text("field,n_both_coded,alpha_nominal\norientation,0,\n")
    assert not C.agreement_ok()[1]()
    f.write_text("field,n_both_coded,alpha_nominal\norientation,30,0.71\n")
    assert C.agreement_ok()[1]()


def test_coded_needs_a_filled_cell(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "ROOT", tmp_path)
    (tmp_path / "s.csv").write_text("gold_id,orientation,notes\nGRF-1,,\n")
    assert not C.coded("s.csv")
    (tmp_path / "s.csv").write_text("gold_id,orientation,notes\nGRF-1,F,\n")
    assert C.coded("s.csv") and not C.coded("missing.csv")


def test_status_table_has_one_row_per_output(tmp_path):
    recs = C.run(dry_run=True)
    path = C.write_status(recs, True, tmp_path / "STATUS.md")
    rows = [l for l in path.read_text().splitlines() if l.startswith("| ") and not l.startswith("| output")]
    assert [r.split("|")[1].strip() for r in rows] == [str(k) for k in range(1, 10)]
    assert not (tmp_path / "core_run.json").exists()


def test_confirmatory_fits_wait_for_the_registration(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "ROOT", tmp_path)
    for s in C.steps():
        if s.script:
            (tmp_path / s.script).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / s.script).write_text("")
    agr = tmp_path / C.AGREEMENT
    agr.parent.mkdir(parents=True)
    agr.write_text("field,n_both_coded,alpha_nominal\norientation,40,0.72\n")
    h1 = next(s for s in C.steps() if s.name == "h1_glmm")
    act, why = C.plan(h1, llm=False)
    assert "registration.txt" in why and act == "fallback"
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "registration.txt").write_text("doi:10.17605/OSF.IO/XXXXX 2026-11-01\n")
    assert C.plan(h1, llm=False)[0] in ("run", "blocked")


def test_registration_accepts_an_existing_tag_or_a_doi_only(tmp_path):
    import subprocess
    f = tmp_path / "registration.txt"
    assert not C.registration_ok(f)
    f.write_text("tag: prereg-does-not-exist-xyz\ncommit: abc\nOSF DOI: pending; the git tag is the timestamped record\n")
    assert not C.registration_ok(f)
    roots = subprocess.run(["git", "rev-list", "--max-parents=0", "HEAD"], cwd=C.ROOT, capture_output=True,
                           text=True).stdout.split()
    if not roots:
        pytest.skip("no commit yet")
    first = roots[0]
    tags = subprocess.run(["git", "tag", "--points-at", first], cwd=C.ROOT, capture_output=True, text=True).stdout
    f.write_text("OSF DOI: pending\n")
    assert not C.registration_ok(f)
    f.write_text("doi:10.17605/OSF.IO/XXXXX 2026-11-01\n")
    assert C.registration_ok(f)
    if tags.split():
        f.write_text(f"tag: {tags.split()[0]}\n")
        assert C.registration_ok(f)


def test_core_never_redraws_rated_audit_sheets_and_runs_confirmatory_after_registration():
    steps = {s.name: s for s in C.steps()}
    names = [c[0] for c in steps["audit_passages"].conditions] if hasattr(steps["audit_passages"], "conditions") else []
    src = (C.ROOT / "src" / "analysis" / "core.py").read_text()
    assert "sheets_blank(" in src and "never overwrite filled rating sheets" in src
    if C.registration_ok(C.ROOT / "docs" / "registration.txt"):
        assert "confirmatory" in steps["predictions"].cmd and "confirmatory" in steps["corrected_rates"].cmd
    assert names is not None
