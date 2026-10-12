import math

import pytest

import translation_extra as X


def test_wordnet_expansion_with_fake_iwn():
    class Syn:
        def __init__(self, names):
            self.names = names

        def lemma_names(self):
            return self.names

    class Fake:
        def synsets(self, w):
            return [Syn(["दुख", "कष्ट", "दुख_दर्द"])] if w == "दुख" else []
    assert X.wordnet_expansion(["दुख", "अज्ञात"], Fake()) == {"दुख", "कष्ट", "दुख दर्द", "अज्ञात"}


def test_component_recall_and_mt_only():
    items = [dict(native={"KIN"}, mt={"KIN"}), dict(native={"KIN"}, mt=set()), dict(native=set(), mt={"KIN", "BOND"})]
    rows = {r["component"]: r for r in X.component_recall(items, B=100)}
    assert rows["KIN"]["reference_items"] == 2 and rows["KIN"]["mt_recall"] == 0.5 and rows["KIN"]["mt_only_items"] == 1
    assert rows["BOND"]["reference_items"] == 0 and math.isnan(rows["BOND"]["mt_recall"])


def test_stripped_table_counts():
    orig = [{"entry:A", "construction:dative_pronoun"}, {"entry:A"}, set()]
    back = [{"entry:A"}, set(), {"entry:B"}]
    rows = {r["feature"]: r for r in X.stripped_table(orig, back)}
    assert (rows["entry:A"]["original"], rows["entry:A"]["kept"], rows["entry:A"]["stripped"]) == (2, 1, 1)
    assert rows["construction:dative_pronoun"]["strip_rate"] == 1.0 and rows["entry:B"]["added"] == 1


def test_topic_agreement_identical_and_relabelled():
    a = [0, 0, 1, 1, -1]
    assert X.topic_agreement(a, [5, 5, 7, 7, 9])["ari"] == pytest.approx(1.0)
    out = X.topic_agreement(a, [0, 1, 0, 1, 0])
    assert out["ari"] < 0.5 and out["outliers_native"] == 1 and out["n_docs"] == 5


def test_construction_features():
    f = X.construction_features("मुझे उनकी बहुत याद आती है")
    assert f["dative_pronoun"] and set(f) >= {"dative_regex", "motion_euphemism", "closing_formula"}
