import math

import numpy as np

import decompose as D

HI = dict(n=100, forced=8, chosen=22, nominative_alt=18)
EN = dict(n=100, forced=2, chosen=10, nominative_alt=15)


def r(c):
    return D.rates(c["n"], c["forced"], c["chosen"], c["nominative_alt"])


def test_toy_example():
    hi, en = r(HI), r(EN)
    assert math.isclose(hi["r"], 30) and math.isclose(en["r"], 12)
    assert math.isclose(hi["q"], 40) and math.isclose(hi["p"], 0.55)
    assert math.isclose(en["q"], 25) and math.isclose(en["p"], 0.40)
    assert math.isclose(hi["r"], hi["f"] + hi["q"] * hi["p"])
    out = D.decompose(hi, en)
    assert math.isclose(out["forced_share"], 6)
    assert math.isclose(out["opportunity_share"], 7.125)
    assert math.isclose(out["choice_share"], 4.875)
    assert math.isclose(out["delta"], 18)
    assert D.COMPONENTS == ("forced_share", "opportunity_share", "choice_share")


def test_identity_holds_for_random_counts():
    rng = np.random.default_rng(0)
    for _ in range(200):
        a, b = (rng.integers(1, 50, size=4) for _ in range(2))
        a[0] += 200
        b[0] += 200
        out = D.decompose(D.rates(*a), D.rates(*b))
        assert math.isclose(out["delta"], sum(out[k] for k in D.COMPONENTS), abs_tol=1e-9)


def test_bootstrap_point_matches_toy_and_interval_brackets_it():
    hi = {"a": dict(n=25, forced=2, chosen=5, nominative_alt=5, review=0),
          "b": dict(n=25, forced=2, chosen=6, nominative_alt=4, review=0),
          "c": dict(n=25, forced=2, chosen=5, nominative_alt=5, review=0),
          "d": dict(n=25, forced=2, chosen=6, nominative_alt=4, review=0)}
    en = {"e": dict(n=50, forced=1, chosen=5, nominative_alt=8, review=0),
          "f": dict(n=50, forced=1, chosen=5, nominative_alt=7, review=0)}
    rows, info = D.bootstrap(dict(hi=hi, en=en), B=500, seed=1)
    got = {x["quantity"]: x for x in rows}
    assert math.isclose(got["delta"]["estimate"], 18) and math.isclose(got["opportunity_share"]["estimate"], 7.125)
    assert math.isclose(got["choice_share"]["estimate"], 4.875) and math.isclose(got["q_hi"]["estimate"], 40)
    for k in ("delta",) + D.COMPONENTS:
        assert got[k]["lo"] <= got[k]["estimate"] <= got[k]["hi"]
    assert got["f_en"]["lo"] == got["f_en"]["hi"] == 2
    assert info["hi_nominative_alt_detected"] and info["replicates_dropped"] == 0


def test_builder_maps_decisions_and_uses_finite_clause_denominator(monkeypatch):
    monkeypatch.setattr(D, "split_of", lambda rid: "dev")
    elig = [dict(clause_id="h:1#1", lang="hi", decision="forced_dative"),
            dict(clause_id="h:1#1", lang="hi", decision="chosen_dative"),
            dict(clause_id="h:1#2", lang="hi", decision="review"), dict(clause_id="h:1#3", lang="hi", decision="NA"),
            dict(clause_id="h:1#4", lang="hi", decision="chosen_nominative"),
            dict(clause_id="h:1#5", lang="hi", decision="forced_nominative"),
            dict(clause_id="e:1#1", lang="en", decision="chosen_impersonal"),
            dict(clause_id="e:1#2", lang="en", decision="chosen_nominative"), dict(clause_id="e:1#3", lang="en", decision="NA")]
    refs = [dict(clause_id=c, referent_class="self") for c in ("h:1#1", "h:1#2", "h:1#3", "e:1#1", "e:1#2", "e:1#3", "h:1#4", "h:1#5")]
    refs[2]["referent_class"] = "impersonal"
    t = D.text_counts(refs, D.clause_flags(elig))
    assert t["hi"]["h:1"] == dict(n=5, forced=1, chosen=1, nominative_alt=1, review=1)
    assert t["en"]["e:1"] == dict(n=3, forced=0, chosen=1, nominative_alt=1, review=0)
    t = D.text_counts(refs, D.clause_flags(elig), experiencer={"self"})
    assert t["hi"]["h:1"]["n"] == 4


def test_relational_marker_counts_sites():
    import decompose as D
    rows = [dict(clause_id="a#1", lang="hi", marker_type="relational", decision="chosen_relational"),
            dict(clause_id="a#1", lang="hi", marker_type="relational", decision="chosen_individual"),
            dict(clause_id="a#1", lang="hi", marker_type="relational", decision="chosen_relational"),
            dict(clause_id="a#1", lang="hi", marker_type="dative", decision="forced_dative"),
            dict(clause_id="a#2", lang="hi", marker_type="relational", decision="forced_relational")]
    site = D.clause_flags(rows, "relational", "site")
    assert (site["a#1"]["chosen"], site["a#1"]["nominative_alt"], site["a#1"]["forced"]) == (2, 1, 0)
    assert site["a#2"]["forced"] == 1
    clause = D.clause_flags(rows, "relational", "clause")
    assert clause["a#1"]["chosen"] == 1
    assert D.clause_flags(rows, "dative")["a#1"]["forced"] == 1


def test_r_is_defined_without_eligible_clauses():
    r = D.rates(100, 5, 0, 0)
    assert r["r"] == 5 and r["f"] == 5 and r["q"] == 0 and math.isnan(float(r["p"]))
    r = D.rates(100, 4, 3, 7)
    assert math.isclose(float(r["r"]), float(r["f"] + r["q"] * r["p"]))


def test_finite_clause_without_eligibility_row_stays_in_denominator(monkeypatch):
    monkeypatch.setattr(D, "split_of", lambda rid: "dev")
    elig = [dict(clause_id="h:1#1", lang="hi", marker_type="dative", decision="forced_dative")]
    refs = [dict(clause_id="h:1#1", referent_class="self"), dict(clause_id="h:1#2", referent_class="self")]
    t = D.text_counts(refs, D.clause_flags(elig))
    assert t["hi"]["h:1"]["n"] == 2 and t["hi"]["h:1"]["forced"] == 1


def test_drop_largest_text_sensitivity():
    hi = {"big": dict(n=60, forced=6, chosen=6, nominative_alt=6, review=0),
          "a": dict(n=20, forced=1, chosen=1, nominative_alt=3, review=0),
          "b": dict(n=20, forced=1, chosen=2, nominative_alt=2, review=0)}
    en = {"x": dict(n=30, forced=0, chosen=2, nominative_alt=6, review=0),
          "y": dict(n=25, forced=0, chosen=1, nominative_alt=5, review=0)}
    rows, summary = D.drop_largest(dict(hi=hi, en=en), B=50)
    assert summary["largest_hi"] == dict(record_id="big", finite_clauses=60, share_of_clauses=0.6, n_texts=3)
    assert {r["variant"] for r in rows} == {"all", "drop_largest_hi", "drop_largest_en", "drop_largest_both"}
    f_all = next(r for r in rows if r["variant"] == "all" and r["quantity"] == "f_hi")["estimate"]
    f_drop = next(r for r in rows if r["variant"] == "drop_largest_hi" and r["quantity"] == "f_hi")["estimate"]
    assert math.isclose(f_all, 100 * 8 / 100) and math.isclose(f_drop, 100 * 2 / 40)
