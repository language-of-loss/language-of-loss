import math
import re

import numpy as np

import collocation as C


def entry(eid, lang, head, pattern):
    e = dict(entry_id=eid, lang=lang, pos="noun", headword_en=head if lang == "en" else "",
             headword_deva=head if lang == "hi" else "", rx=re.compile(pattern, re.I if lang == "en" else 0))
    e["variants"] = [[w.lower() for w in head.split()]] if lang == "en" else [head.split()]
    return e


LEX = dict(entries=[entry("E1", "en", "grief", r"grie(f|ving)"), entry("E2", "en", "passed away", r"passed away")])


def sentence(rid, s, toks, lang="en"):
    cid = f"{rid}#{s:04d}"
    clause = dict(clause_id=cid, record_id=rid, lang=lang, sent_index=s,
                  clause_text=" ".join(t[0] for t in toks))
    words = [dict(i=i + 1, form=f, lemma=l, upos=u, lang=lang) for i, (f, l, u) in enumerate(toks)]
    return clause, words


def corpus(sents):
    clauses, words = {}, {}
    for rid, s, toks in sents:
        c, w = sentence(rid, s, toks)
        clauses[c["clause_id"]], words[c["clause_id"]] = c, w
    return clauses, words


GRIEF_ROW = [("my", "my", "PRON"), ("grief", "grief", "NOUN"), ("was", "be", "AUX"), ("heavy", "heavy", "ADJ"),
             ("and", "and", "CCONJ"), ("Ravi", "Ravi", "PROPN"), ("cried", "cry", "VERB")]


def test_anchor_by_regex_and_by_lemma_run():
    c, w = sentence("t:1", 1, [("She", "she", "PRON"), ("passed", "pass", "VERB"), ("away", "away", "ADP")])
    assert C.anchors(LEX["entries"][1], c, w) == [{1, 2}]
    c, w = sentence("t:1", 2, [("grieving", "grieve", "VERB"), ("hard", "hard", "ADV")])
    assert C.anchors(LEX["entries"][0], c, w) == [{0}]


def test_window_drops_function_words_names_and_anchor():
    clauses, words = corpus([("t:1", 1, GRIEF_ROW)])
    es = C.cooccurrences(clauses, words, LEX, window=5)["en"]["entries"]["E1"]
    assert set(es["pairs"]) == {"heavy", "cry"}
    clauses, words = corpus([("t:1", 1, GRIEF_ROW)])
    es = C.cooccurrences(clauses, words, LEX, window=1)["en"]["entries"]["E1"]
    assert set(es["pairs"]) == set()


def test_overlapping_windows_count_a_word_once():
    toks = [("grief", "grief", "NOUN"), ("heavy", "heavy", "ADJ"), ("grief", "grief", "NOUN")]
    clauses, words = corpus([("t:1", 1, toks)])
    st = C.cooccurrences(clauses, words, LEX, window=5)["en"]
    assert st["entries"]["E1"]["occ"] == 2 and st["entries"]["E1"]["pairs"]["heavy"] == 1


def test_pmi_formula_min_count_and_texts():
    sents = [(f"t:{i % 2}", i, GRIEF_ROW) for i in range(10)] + \
            [("t:9", 100 + i, [("tree", "tree", "NOUN"), ("heavy", "heavy", "ADJ")]) for i in range(5)]
    clauses, words = corpus(sents)
    stats = C.cooccurrences(clauses, words, LEX, window=5)
    rows = {r["collocate"]: r for r in C.pmi_table(stats, LEX, min_matches=10, min_count=3, window=5)}
    st = stats["en"]
    expect = math.log2(10 * st["N"] / (10 * 15 * 10))
    assert math.isclose(rows["heavy"]["pmi"], round(expect, 3)) and rows["heavy"]["n_texts"] == 2
    assert C.pmi_table(stats, LEX, min_matches=11, min_count=3, window=5) == []


def test_candidates_skip_lexicon_words_and_single_text_pairs():
    rows = [dict(lang="en", entry_id="E1", headword="grief", collocate=w, pmi=4.0, cooc=5, collocate_freq=9,
                 n_texts=n) for w, n in (("grieving", 3), ("heavy", 3), ("ravine", 1))]
    cands = C.candidates(rows, LEX, min_pmi=3.0, min_texts=2)
    assert [c["candidate"] for c in cands] == ["heavy"]


def test_devanagari_font_is_available():
    assert C.font_family()[0] != "DejaVu Sans"


def test_no_self_collocation():
    toks = [("grief", "grief", "NOUN"), ("heavy", "heavy", "ADJ"), ("grieving", "grieve", "VERB")]
    clauses, words = corpus([("t:1", 1, toks)])
    es = C.cooccurrences(clauses, words, LEX, window=5)["en"]["entries"]["E1"]
    assert es["occ"] == 2 and set(es["pairs"]) == {"heavy"}


def _toy_graph():
    import networkx as nx
    g = nx.Graph()
    for a, b, pmi in [("E1", "w:a", 4.0), ("E1", "w:b", 5.0), ("w:b", "E2", 3.0), ("E3", "w:c", 6.0),
                      ("E4", "w:d", 2.5), ("E4", "w:e", 7.0), ("E4", "w:f", 3.5)]:
        for n in (a, b):
            g.add_node(n, kind="entry" if n.startswith("E") else "collocate", label=n)
        g.add_edge(a, b, pmi=pmi, length=1 / pmi)
    return g


def test_packed_layout_places_components_in_disjoint_boxes():
    import networkx as nx
    g = _toy_graph()
    pos = C.packed_layout(g)
    assert set(pos) == set(g)
    boxes = []
    for comp in nx.connected_components(g):
        xy = np.array([pos[n] for n in comp])
        boxes.append((*xy.min(0), *xy.max(0)))
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            assert a[2] < b[0] or b[2] < a[0] or a[3] < b[1] or b[3] < a[1]
    assert C.packed_layout(g) == pos


def test_spread_enforces_minimum_distance_and_leaves_far_points():
    xy = np.array([[0.0, 0.0], [0.01, 0.0], [5.0, 5.0]])
    out = C.spread(xy, 0.5)
    assert np.hypot(*(out[0] - out[1])) >= 0.5 - 1e-6 and np.allclose(out[2], xy[2])


def test_write_caption_replaces_only_its_own_block(tmp_path):
    p = tmp_path / "captions.md"
    C.write_caption("Figure1", "one", p)
    C.write_caption("Figure2", "two", p)
    C.write_caption("Figure1", "uno", p)
    text = p.read_text(encoding="utf-8")
    assert "uno" in text and "one" not in text and text.count("<!-- Figure1:begin -->") == 1 and "two" in text


def test_draw_only_reads_the_pmi_table_and_writes_figures_only(tmp_path):
    rows = [dict(lang=l, entry_id=e, headword=h, entry_clauses=12, entry_occurrences=15, collocate=w, cooc=4,
                 collocate_freq=f, pmi=p, n_texts=2)
            for l, e, h, w, f, p in [("hi", "L-HI-01", "शोक", "दुख", 40, 4.2), ("hi", "L-HI-01", "शोक", "X-रे", 9, 3.1),
                                     ("en", "L-EN-01", "grief", "heavy", 30, 5.0)]]
    pmi = tmp_path / "pmi.csv"
    C.write_csv(pmi, rows, list(rows[0]))
    before = pmi.read_bytes()
    C.main(["--draw-only", "--pmi-out", str(pmi), "--in", str(tmp_path / "none.jsonl"), "--fig-dir", str(tmp_path / "legacy"),
            "--final-dir", str(tmp_path / "final"), "--captions", str(tmp_path / "captions.md"),
            "--candidates-out", str(tmp_path / "never.csv")])
    names = sorted(p.name for p in (tmp_path / "final").iterdir())
    assert names == sorted(f"Figure2_collocation{s}.{x}" for s in ("", "_hi", "_en") for x in ("pdf", "png"))
    assert pmi.read_bytes() == before and not (tmp_path / "never.csv").exists()
    assert "development set" in (tmp_path / "captions.md").read_text(encoding="utf-8")
