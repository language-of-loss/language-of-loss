import csv
import hashlib
import importlib.util
import shutil
from pathlib import Path

import pytest

import assemble as A
import assemble_tables as T
import code_appendix as CA
import corrected_rates
import synthetic_results as S
import validate
from predictions import tests_allowed as allowed

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


F = _load("analysis_figures", ROOT / "src" / "analysis" / "figures.py")
TABLES = ["Output1_agreement", "Output2_validation", "Output3_hypothesis", "Output4_rival_check", "Output5_audit",
          "Output6_dative_choice", "Output7_jsd", "Output8_translation", "Output9_collocation"]


@pytest.fixture(scope="module")
def synth(tmp_path_factory):
    out = tmp_path_factory.mktemp("synthetic")
    S.build(out)
    return out


def header(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return next(csv.reader(fh))


def test_synthetic_schemas_match_the_writers(synth):
    assert header(synth / "validation_table.csv") == validate.COLUMNS
    assert header(synth / "corrected_rates.csv") == corrected_rates.COLUMNS
    assert header(synth / "corrected_rates_hi_minus_en.csv") == corrected_rates.DIFF_COLUMNS
    assert header(synth / "decompose_relational_dev.csv") == ["quantity", "estimate", "lo", "hi"]
    for run in ("run1", "run2", "run2b", "rF6"):
        for suffix in ("", "_rival"):
            assert header(synth / f"h1_glmm_{run}{suffix}.csv")[:9] == ["term", "estimate", "se", "stat", "df", "p",
                                                                       "estimator", "ci_lo", "ci_hi"]
    assert header(synth / "mcnemar_muril.csv") == ["quantity", "value", "status"]
    names = {r["quantity"] for r in csv.DictReader(open(synth / "decompose_relational_dev.csv", encoding="utf-8"))}
    assert {"r_hi", "p_en", "delta", "choice_share"} <= names


def test_every_synthetic_row_says_synthetic(synth):
    for p in synth.rglob("*.csv"):
        rows = list(csv.DictReader(open(p, encoding="utf-8")))
        if "status" in rows[0]:
            assert all(r["status"] == S.STATUS for r in rows), p.name


def test_synthetic_agreement_never_unlocks_a_test(synth):
    path = synth / "agreement" / "agreement_summary_gold_sheet_v1.csv"
    assert not allowed(path)
    real = path.read_text().replace(S.STATUS, "two investigators")
    (synth.parent / "agr_real.csv").write_text(real)
    assert allowed(synth.parent / "agr_real.csv")


def test_synthetic_files_refused_in_real_results(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "ROOT", tmp_path)
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "p2_jsd.csv").write_text(f"quantity,estimate,status\njsd,0.1,{S.STATUS}\n")
    with pytest.raises(SystemExit, match="synthetic"):
        S.refuse_synthetic_in_real(tmp_path / "results")
    with pytest.raises(SystemExit):
        S.main(["--out", str(tmp_path / "results")])


def test_every_figure_renders_as_pdf_and_300_dpi_png(synth, tmp_path):
    from PIL import Image
    written, pending, stamp = F.build(synth, tmp_path)
    assert not pending
    assert stamp == F.STAMP_SYNTHETIC
    assert sorted(written) == sorted(stem for stem, *_ in F.FIGURES)
    for stem, paths in written.items():
        assert sorted(p.suffix for p in paths) == [".pdf", ".png"]
        assert paths[0].read_bytes()[:4] == b"%PDF"
        dpi = Image.open(tmp_path / f"{stem}.png").info["dpi"]
        assert round(dpi[0]) == F.DPI
    captions = (tmp_path / "captions.md").read_text()
    assert captions.count(F.STAMP_SYNTHETIC) == len(F.FIGURES)


def test_figures_are_deterministic(synth, tmp_path):
    F.build(synth, tmp_path / "a")
    F.build(synth, tmp_path / "b")
    for p in (tmp_path / "a").glob("*.p*"):
        assert hashlib.sha256(p.read_bytes()).digest() == hashlib.sha256((tmp_path / "b" / p.name).read_bytes()).digest(), p.name


def test_missing_csvs_are_pending_not_errors(synth, tmp_path):
    part = tmp_path / "res"
    part.mkdir()
    shutil.copy(synth / "decompose_relational_dev.csv", part)
    shutil.copy(synth / "audit_lmer.csv", part)
    written, pending, stamp = F.build(part, tmp_path / "fig")
    assert set(written) == {"F3a_decomposition", "F5a_audit_underreading"}
    assert pending["F3b_odds_ratios"] == "h1_glmm_run1.csv"
    assert stamp == F.STAMP_SYNTHETIC


def test_real_results_without_agreement_are_dev_smoke(tmp_path):
    (tmp_path / "decompose_relational_dev.csv").write_text("quantity,estimate,lo,hi\ndelta,1,0,2\n")
    assert F.stamp_for(tmp_path) == F.STAMP_SMOKE


def test_style_is_serif_and_colour_blind_palette():
    F.setup_style()
    import matplotlib.pyplot as plt
    fam = plt.rcParams["font.family"]
    assert fam[0] in F.SERIF + ["DejaVu Serif"]
    assert (F.LANG["hi"]["colour"], F.LANG["en"]["colour"]) == ("#0072B2", "#E69F00")
    assert F.LANG["hi"]["marker"] != F.LANG["en"]["marker"]


def test_wilson_interval():
    p, lo, hi = F.wilson(8, 10)
    assert p == 0.8 and 0.49 < lo < 0.5 and 0.94 < hi < 0.95
    assert F.wilson(0, 0) == (None, None, None)


def test_nine_tables_all_labelled_synthetic(synth, tmp_path):
    out, docs, synthetic = T.build(synth, tmp_path / "tables")
    assert synthetic
    assert sorted(p.stem for p in out.iterdir()) == sorted(TABLES)
    for name, text in docs.items():
        assert "SYNTHETIC PLACEHOLDER, NOT DATA" in text, name
        assert A.SMOKE not in text, name
    t3 = docs["Output3_hypothesis.md"]
    assert "Figure: `figures/synthetic/F3a_decomposition.pdf`" in t3
    assert "R-F6 robustness" in t3 and "drop_largest_both" in t3
    assert "(synthetic)" in t3
    assert "Component profile and log-odds" in docs["Output7_jsd.md"]
    assert "| FEEL_BAD |" in docs["Output7_jsd.md"]
    assert "top 8 collocates" in docs["Output9_collocation.md"]
    assert "2c. Hindi − English" in docs["Output2_validation.md"]


def test_default_output_never_overwrites_assemble_tables(synth):
    out, _, _ = T.build(synth)
    assert out == synth / "tables_full" and not (synth / "tables").exists()


def test_table_numbers_come_from_the_csv(synth, tmp_path):
    _, docs, _ = T.build(synth, tmp_path / "t")
    row = next(r for r in csv.DictReader(open(synth / "h1_glmm_run1.csv", encoding="utf-8"))
               if r["term"] == "hindi" and "glmer" in r["estimator"])
    import math
    assert f"{math.exp(float(row['estimate'])):.2f}" in docs["Output3_hypothesis.md"]


def test_code_appendix_reproduces_the_four_files_verbatim(tmp_path):
    out = tmp_path / "appendix.md"
    CA.main(["--out", str(out)])
    text = out.read_text(encoding="utf-8")
    for path, *_ in CA.FILES:
        src = (ROOT / path).read_text(encoding="utf-8").rstrip("\n")
        assert f". {path}\n" in text
        assert src in text, path
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() in text
    assert [p for p, *_ in CA.FILES] == ["src/analysis/decompose.py", "R/h1_glmm.R", "src/analysis/corrected_rates.py",
                                         "R/audit.R"]
    CA.main(["--out", str(tmp_path / "again.md")])
    assert (tmp_path / "again.md").read_bytes() == out.read_bytes()


def test_fence_outgrows_backticks_in_the_source():
    assert CA.fence("a ```` b") == "`````"
    assert CA.fence("plain") == "```"
