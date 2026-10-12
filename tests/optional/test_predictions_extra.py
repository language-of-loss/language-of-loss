import math

from test_predictions import ENTRIES, argv, fixture, read

import predictions as P
import predictions_extra as X


def run(tmp_path, paths, agreement="missing.csv"):
    X.main(argv(tmp_path, paths, agreement))
    return tmp_path / "out"


def test_all_optional_outputs_written_with_provenance(fixture):
    tmp_path, paths = fixture
    out = run(tmp_path, paths)
    names = ["p1_pos_profile", "p1_pos_logodds", "p1_we_i", "p2_naming_texts", "p2_naming_share", "p2_beta",
             "p2_component_profile", "p2_component_logodds", "p2_residue"]
    sha = P.sha256(paths["eligibility"])
    for n in names:
        rows = read(out / f"{n}.csv")
        assert rows, n
        assert all(r["eligibility_sha256"] == sha and r["split"] == "all" for r in rows), n


def test_beta_guarded(fixture, tmp_path):
    tmp, paths = fixture
    out = run(tmp, paths)
    assert read(out / "p2_beta.csv")[0]["note"].startswith("refused")
    (tmp / "agreement_summary.csv").write_text("field,n_both_coded,alpha_nominal\norientation,40,0.71\n",
                                               encoding="utf-8")
    out = run(tmp, paths, "agreement_summary.csv")
    beta = read(out / "p2_beta.csv")
    assert {r["term"] for r in beta} >= {"const", "hindi"} and all(r["p"] for r in beta)


def test_pos_categories_and_agentive_self(fixture):
    tmp_path, paths = fixture
    X.main(argv(tmp_path, paths))
    prof = {(r["lang"], r["category"]): r for r in read(tmp_path / "out" / "p1_pos_profile.csv")}
    assert int(prof[("hi", "emotion_noun")]["count"]) == 7
    assert int(prof[("hi", "emotion_adjective")]["count"]) == 2
    assert int(prof[("hi", "emotion_verb")]["count"]) == 4
    assert int(prof[("hi", "emotion_noun")]["n_tokens"]) == 240
    assert math.isclose(float(prof[("hi", "emotion_noun")]["per_1000"]), 1000 * 7 / 240, rel_tol=1e-5)
    assert int(prof[("hi", "agentive_self")]["count"]) == 4
    assert int(prof[("en", "emotion_adjective")]["count"]) == 2
    assert int(prof[("hi", "unclassified")]["count"]) == 0


def test_unfound_hindi_predicate_is_unclassified_not_noun():
    site = dict(lang="hi", predicate="दुख+हो")
    assert X.predicate_category(site, [dict(token="बात", lemma="बात", upos="NOUN")]) is None
    assert X.predicate_category(dict(lang="hi", predicate="रो"), [dict(token="रोया", lemma="रोना", upos="VERB")]) \
        == "emotion_verb"
    assert X.predicate_category(dict(lang="hi", predicate="रो"), [dict(token="घर", lemma="घर", upos="NOUN")]) is None


def test_structural_zero_category_has_no_log_odds(fixture):
    tmp_path, paths = fixture
    X.main(argv(tmp_path, paths))
    lo = {r["category"]: r for r in read(tmp_path / "out" / "p1_pos_logodds.csv")}
    assert lo["emotion_noun"]["z"] == "" and lo["emotion_noun"]["note"].startswith("n/a")
    assert lo["emotion_verb"]["z"] != ""


def test_monroe_log_odds_matches_formula():
    out = X.monroe_log_odds({"a": 10}, {"a": 2}, 100, 100, alpha0=10)
    aw = 10 * 12 / 200
    d = math.log((10 + aw) / (100 + 10 - 10 - aw)) - math.log((2 + aw) / (100 + 10 - 2 - aw))
    assert math.isclose(out["a"]["delta"], d) and out["a"]["z"] > 0
    assert math.isclose(out["a"]["sd"], math.sqrt(1 / (10 + aw) + 1 / (2 + aw)))


def test_we_i_and_naming_and_residue(fixture):
    tmp_path, paths = fixture
    X.main(argv(tmp_path, paths))
    wi = {r["lang"]: r for r in read(tmp_path / "out" / "p1_we_i.csv")}
    assert (int(wi["hi"]["I"]), int(wi["hi"]["we"])) == (4, 3)
    texts = read(tmp_path / "out" / "p2_naming_texts.csv")
    for r in texts:
        assert math.isclose(float(r["naming_share"]), int(r["naming"]) / int(r["matches"]), rel_tol=1e-5)
    res = {(r["lang"], r["residue"]): r for r in read(tmp_path / "out" / "p2_residue.csv")}
    assert int(res[("hi", "grammar_forced_component_clauses")]["count"]) == 4
