import pytest

import text_meta as T


@pytest.mark.parametrize("relation,expected", [
    ("father", "parent"), ("mother (Amma)", "parent"), ("father (Appa)", "parent"), ("mother (बीजी)", "parent"),
    ("estranged father (died suddenly)", "parent"), ("mother; father (earlier)", "parent"),
    ("grandmother (दादी)", "grandparent"), ("maternal grandmother (paati)", "grandparent"),
    ("grandfather (बाबा)", "grandparent"), ("wife", "spouse"), ("son", "child"), ("elder brother", "sibling"),
    ("sister", "sibling"), ("best friend", "other"), ("uncle (father figure; काका)", "other"),
    ("mentor / elder family friend (addressed as भाभी)", "other"), ("uncle; pet dog; several relatives", "other"),
    ("not stated (family member addressed)", "unstated"), ("", "unstated"), ("None", "unstated"),
])
def test_loss_type(relation, expected):
    assert T.loss_type(relation) == expected


def row(rid, lang, n, loss="parent", split="confirmatory", same=False):
    return dict(record_id=rid, lang=lang, split=split, n_clauses=n, loss_type=loss, same_author_pair=same, pair_id="")


def test_pairs_match_within_cell_by_length():
    rows = [row("h1", "hi", 100), row("h2", "hi", 10), row("e1", "en", 12), row("e2", "en", 90),
            row("e3", "en", 50, loss="spouse"), row("h3", "hi", 50, split="dev")]
    T.match_pairs(rows)
    pid = {r["record_id"]: r["pair_id"] for r in rows}
    assert pid["h1"] == pid["e2"] and pid["h2"] == pid["e1"] and pid["h1"] != pid["h2"]
    assert pid["e3"] == "" and pid["h3"] == ""


def test_same_author_pair_first():
    rows = [row("ha", "hi", 100, same=True), row("ea", "en", 5, same=True), row("eb", "en", 100)]
    T.match_pairs(rows)
    pid = {r["record_id"]: r["pair_id"] for r in rows}
    assert pid["ha"] == pid["ea"] != "" and pid["eb"] == ""


@pytest.mark.parametrize("relation,expected", [
    ("father (Appa)", "parent"), ("grandmother (दादी)", "grandparent"), ("mother-in-law", "parent_in_law"),
    ("uncle (father's elder brother, called बाबूजी)", "elder"), ("mentor / elder family friend (addressed as भाभी)", "elder"),
    ("elder friend / mentor from blogging circle (called दादा भाई)", "elder"), ("my teacher", "teacher"),
    ("father (Prof. S. N. Manwani)", "parent"), ("elder brother", "sibling"), ("wife", "spouse"), ("son", "child"),
    ("best friend", "friend"), ("not stated (family member)", "unknown"),
    ("paternal grandfather (dada), cause not stated", "grandparent"),
])
def test_relation_category(relation, expected):
    assert T.relation_category(relation) == expected


def test_cause_not_stated_is_not_unstated():
    assert T.loss_type("father (cause not stated)") == "parent"


def test_review_category_words_map_to_their_loss_type():
    import text_meta as T
    for word, lt in (("parent", "parent"), ("parents", "parent"), ("grandparent", "grandparent"),
                     ("sibling", "sibling"), ("spouse", "spouse"), ("child", "child"), ("friend", "other"),
                     ("parent-in-law", "parent")):
        assert T.loss_type(word) == lt, word
    assert T.relation_category("parent-in-law") == "parent_in_law" and not T.elder_relation("parent")
