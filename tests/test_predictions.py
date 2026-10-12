import csv
import math
from pathlib import Path

import numpy as np
import pytest

import predictions as P

HI_SITES = {
    "h1": [("chosen_dative", "दुख+हो", "HI-C01", "dative"), ("chosen_nominative", "रो", "HI-N14", "nominative"),
           ("forced_dative", "याद+आ", "HI-F01", "dative"), ("forced_dative", "लग", "HI-F02", "dative")],
    "h2": [("chosen_dative", "डर+लग", "HI-C02", "dative"), ("chosen_nominative", "दुखी+हो", "HI-N01", "nominative"),
           ("chosen_nominative", "रो", "HI-N14", "nominative"), ("forced_dative", "याद+आ", "HI-F01", "dative"),
           ("forced_dative", "मिल", "HI-F03", "dative")],
    "h3": [("chosen_dative", "दुख+हो", "HI-C01", "dative"), ("chosen_nominative", "डर", "HI-N13", "nominative"),
           ("forced_dative", "चाहिए", "HI-F04", "dative"), ("forced_dative", "याद+आ", "HI-F01", "dative"),
           ("forced_nominative", "तडप", "HI-N19", "nominative")],
    "h4": [("chosen_nominative", "खुश+हो", "HI-N05", "nominative"), ("forced_dative", "याद+आ", "HI-F01", "dative"),
           ("forced_dative", "लग", "HI-F02", "dative"), ("forced_dative", "INF+पड", "HI-F08", "dative")],
}
EN_SITES = {
    "e1": [("chosen_nominative", "miss", "EN-NOM", "nominative"), ("chosen_impersonal", "hurt", "EN-IMP-IT", "impersonal")],
    "e2": [("chosen_nominative", "sad", "EN-NOM", "nominative"), ("chosen_nominative", "grieve", "EN-NOM", "nominative")],
    "e3": [("chosen_nominative", "cry", "EN-NOM", "nominative"), ("chosen_impersonal", "devastate", "EN-STIM", "stimulus")],
    "e4": [("chosen_nominative", "afraid", "EN-NOM", "nominative"), ("review", "hit", "EN-R02", "")],
}
UPOS = {"याद": "NOUN", "दुख": "NOUN", "डर": "NOUN", "दुखी": "ADJ", "खुश": "ADJ", "sad": "ADJ", "afraid": "ADJ"}
ENTRIES = ["L-HI-01", "L-HI-02", "L-EN-01", "L-EN-02"]
COMPS = ["FEEL_BAD", "NOT_HERE", "KIN"]


def write(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return str(path)


@pytest.fixture()
def fixture(tmp_path):
    elig, refs, toks, cf = [], [], [], []
    rng = np.random.default_rng(1)
    for lang, sites in (("hi", HI_SITES), ("en", EN_SITES)):
        for t, ss in sites.items():
            rid = f"blogs:{t}"
            for k in range(6):
                cid = f"{rid}#{k + 1:04d}"
                s = ss[k] if k < len(ss) else None
                if s:
                    dec, pred, rule, cons = s
                    elig.append(dict(clause_id=cid, lang=lang, marker_type="dative", site="x", predicate=pred,
                                     decision=dec, rule_id=rule, subject_source="", construction=cons, twin_rule=""))
                    word = pred.split("+")[0]
                    toks.append(dict(clause_id=cid, token_index=1, token=word, lemma=word,
                                     upos=UPOS.get(word, "VERB") if (lang == "en" or "+" in pred) else "VERB", feats="", head=0,
                                     deprel="root"))
                else:
                    toks.append(dict(clause_id=cid, token_index=1, token="x", lemma="x", upos="NOUN", feats="",
                                     head=0, deprel="root"))
                    elig.append(dict(clause_id=cid, lang=lang, marker_type="dative", site="", predicate="",
                                     decision="NA", rule_id="HI-NA", subject_source="", construction="", twin_rule=""))
                elig.append(dict(clause_id=cid, lang=lang, marker_type="relational", site="", predicate="",
                                 decision="chosen_individual", rule_id="REL", subject_source="", construction="",
                                 twin_rule=""))
                for j in range(9):
                    toks.append(dict(clause_id=cid, token_index=j + 2, token="w", lemma="w", upos="NOUN", feats="",
                                     head=1, deprel="dep"))
                toks.append(dict(clause_id=cid, token_index=11, token="।", lemma="।", upos="PUNCT", feats="", head=1,
                                 deprel="punct"))
                first = k in (0, 1)
                refs.append(dict(clause_id=cid, referent_class="self" if first else "other",
                                 pronoun_person="1" if first else "", pronoun_number=("pl" if k == 1 else "sg") if first
                                 else ""))
                row = dict(clause_id=cid, record_id=rid, lang=lang, is_finite="1")
                for e in ENTRIES:
                    row[e] = int(e.startswith(f"L-{lang.upper()}") and rng.random() < 0.8)
                for c in COMPS:
                    row[f"comp_{c}"] = int(rng.random() < (0.6 if (c == "KIN") == (lang == "hi") else 0.2))
                row["gf_HAPPEN_TO"] = int(lang == "hi" and k == 5)
                cf.append(row)
    ev = [dict(entry_id=e, lang="hi" if "HI" in e else "en", FEEL_BAD=0, NOT_HERE=int(e == "L-HI-02"), KIN=0,
               names_emotion=int(e in ("L-HI-01", "L-EN-01"))) for e in ENTRIES]
    paths = dict(eligibility=write(tmp_path / "eligibility.csv", elig), referents=write(tmp_path / "referents.csv", refs),
                 tokens=write(tmp_path / "tokens.csv", toks), clause_features=write(tmp_path / "cf.csv", cf),
                 entry_vectors=write(tmp_path / "ev.csv", ev))
    return tmp_path, paths


def argv(tmp_path, paths, agreement="missing.csv"):
    return ["--eligibility", paths["eligibility"], "--referents", paths["referents"], "--tokens", paths["tokens"],
            "--clause-features", paths["clause_features"], "--entry-vectors", paths["entry_vectors"],
            "--lexicon", str(tmp_path / "no_lexicon.csv"), "--agreement", str(tmp_path / agreement), "--split", "all", "--B", "200", "--out-dir", str(tmp_path / "out")]


def read(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_all_outputs_written_with_provenance(fixture):
    tmp_path, paths = fixture
    P.main(argv(tmp_path, paths))
    names = ["p1_choice", "p2_jsd"]
    assert sorted(p.stem for p in (tmp_path / "out").iterdir()) == names
    sha = P.sha256(paths["eligibility"])
    for n in names:
        rows = read(tmp_path / "out" / f"{n}.csv")
        assert rows, n
        assert all(r["eligibility_sha256"] == sha and r["split"] == "all" for r in rows), n


def test_dev_split_rows_are_labelled_smoke(fixture, monkeypatch):
    tmp_path, paths = fixture
    monkeypatch.setattr(P, "split_of", lambda rid: "dev")
    a = argv(tmp_path, paths)
    a[a.index("--split") + 1] = "dev"
    P.main(a)
    assert {r["status"] for r in read(tmp_path / "out" / "p1_choice.csv")} == {"dev smoke, not a result"}


def test_choice_rate_baseline_and_guard(fixture):
    tmp_path, paths = fixture
    P.main(argv(tmp_path, paths))
    rows = {r["quantity"]: r for r in read(tmp_path / "out" / "p1_choice.csv")}
    assert math.isclose(float(rows["dative_choice_rate"]["estimate"]), 3 / 8)
    assert math.isclose(float(rows["forced_baseline_dative_share"]["estimate"]), 9 / 10)
    t = rows["binomial_test_vs_forced_baseline"]
    assert t["p"] == "" and t["test"].startswith("refused")


def test_tests_run_only_with_agreement_statistics(fixture):
    from scipy.stats import binomtest
    tmp_path, paths = fixture
    (tmp_path / "agreement_summary.csv").write_text("field,n_both_coded,alpha_nominal\norientation,40,0.71\n",
                                                    encoding="utf-8")
    P.main(argv(tmp_path, paths, agreement="agreement_summary.csv"))
    t = {r["quantity"]: r for r in read(tmp_path / "out" / "p1_choice.csv")}["binomial_test_vs_forced_baseline"]
    assert math.isclose(float(t["p"]), binomtest(3, 8, 0.9).pvalue, rel_tol=1e-5)


def test_jsd_on_fixture(fixture):
    tmp_path, paths = fixture
    P.main(argv(tmp_path, paths))
    j = read(tmp_path / "out" / "p2_jsd.csv")[0]
    assert 0 < float(j["estimate"]) <= 1 and float(j["lo"]) <= float(j["hi"])


def test_jsd_bounds():
    assert P.jsd([1, 2, 3], [2, 4, 6]) == 0
    assert math.isclose(P.jsd([1, 0], [0, 1]), 1.0)
    assert 0 < P.jsd([3, 1], [1, 3]) < 1


def test_guard_refuses_blank_sheet_summary(tmp_path):
    blank = tmp_path / "blank.csv"
    blank.write_text("field,n_both_coded,pct_agree,alpha_nominal\norientation,0,,\nprocess,0,,\n", encoding="utf-8")
    assert not P.tests_allowed(blank)
    assert not P.tests_allowed(tmp_path / "missing.csv")
    nan = tmp_path / "nan.csv"
    nan.write_text("field,n_both_coded,alpha_nominal\norientation,12,nan\n", encoding="utf-8")
    assert not P.tests_allowed(nan)
    ok = tmp_path / "ok.csv"
    ok.write_text("field,n_both_coded,alpha_nominal\norientation,0,\nprocess,30,0.64\n", encoding="utf-8")
    assert P.tests_allowed(ok)


def test_holm_matches_step_down_definition():
    import predictions as P
    assert P.holm([0.01, 0.04]) == [0.02, 0.04]
    assert P.holm([0.04, 0.01]) == [0.04, 0.02]
    assert P.holm([0.03, 0.02, 0.5]) == pytest.approx([0.06, 0.06, 0.5])


def test_jsd_permutation_p_small_when_profiles_differ_large_when_same():
    import numpy as np
    import predictions as P
    rng = np.random.default_rng(1)
    hi = rng.poisson([8, 1, 1], size=(20, 3)).astype(float)
    en = rng.poisson([1, 1, 8], size=(20, 3)).astype(float)
    mat = {"hi": hi, "en": en}
    p = P.jsd_permutation_p(mat, P.jsd(hi.sum(0), en.sum(0)), B=199)
    assert p == pytest.approx(1 / 200)
    same = {"hi": hi[:10], "en": hi[10:]}
    assert P.jsd_permutation_p(same, P.jsd(hi[:10].sum(0), hi[10:].sum(0)), B=199) > 0.05
