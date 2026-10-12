import math

import numpy as np

import power as P


def test_anova_icc_hand_cases():
    assert math.isclose(P.anova_icc([(5, 10), (5, 10), (5, 10)]), -1 / 9, abs_tol=0.02) or \
        P.anova_icc([(5, 10), (5, 10), (5, 10)]) <= 0
    assert P.anova_icc([(10, 10), (0, 10), (10, 10), (0, 10)]) > 0.9


def synthetic():
    rng = np.random.default_rng(0)
    km = [(int(m * 0.3), m) for m in rng.integers(50, 300, 30)]
    prof = [(int(n), int(n * 0.05), int(n * 0.1), int(n * 0.2)) for n in rng.integers(50, 300, 30)]
    return {"hi": dict(km=km, profiles=prof), "en": dict(km=km, profiles=prof)}


def test_run2_power_rises_with_the_odds_ratio_and_type_one_is_small():
    rng = np.random.default_rng(1)
    inp, n = synthetic(), dict(hi=40, en=40)
    t1 = P.sim_run2(inp, n, 1.0, 200, 0.05, 0.3, rng)
    lo, hi = P.sim_run2(inp, n, 1.25, 200, 0.05, 0.3, rng), P.sim_run2(inp, n, 2.0, 200, 0.05, 0.3, rng)
    assert t1 < 0.15 and lo < hi and hi > 0.8


def test_choice_share_power_rises_with_the_difference():
    rng = np.random.default_rng(2)
    inp, n = synthetic(), dict(hi=40, en=40)
    rho = dict(hi=0.05, en=0.05)
    p0 = P.sim_choice(inp, n, 0.0, 60, 0.3, rho, rng, boot=200)
    p2 = P.sim_choice(inp, n, 0.2, 60, 0.3, rho, rng, boot=200)
    assert p0 < 0.2 and p2 > 0.8
