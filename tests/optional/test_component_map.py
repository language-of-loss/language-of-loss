import math

import numpy as np

import component_map as M


def test_component_map_jaccard_and_layout():
    x = np.array([[1, 1, 0], [1, 1, 0], [0, 0, 1], [1, 0, 0]], dtype=bool)
    d = M.jaccard(x)
    assert d[0, 1] == 0 and d[0, 2] == 1 and math.isclose(d[0, 3], 0.5)
    assert M.layout(x).shape == (4, 2)


def test_visible_points_hides_markers_under_an_earlier_one():
    pts = np.array([[0.0, 0.0], [1.0, 0.0], [10.0, 0.0], [10.5, 0.2]])
    keep, cover = M.visible_points(pts, radius=3.0)
    assert keep.tolist() == [True, False, True, False] and cover.tolist() == [-1, 0, -1, 2]


def test_counterpart_pairs_are_symmetric_and_deduplicated(tmp_path):
    import csv
    with open(tmp_path / "lexicon.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["entry_id", "counterpart"])
        w.writerows([["L-HI-01", "L-EN-01; L-EN-02"], ["L-EN-01", "L-HI-01"], ["L-EN-02", ""], ["L-HI-02", "L-EN-99"]])
    ids = ["L-HI-01", "L-HI-02", "L-EN-01", "L-EN-02"]
    assert M.counterpart_pairs(tmp_path, ids) == [(0, 2), (0, 3)]
