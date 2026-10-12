import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_annotate as B

HTML = ROOT / "tools" / "annotate.html"
ANN = ROOT / "data" / "annotation"
SHEETS = ["gold_pilot_r1.csv", "gold_sheet_v1_coder1.csv", "gold_components_v1_coder1.csv", "audit_rating_sheet_r1.csv",
          "audit_calibration_brighter_r1.csv", "meta_review.csv"]
osa = pytest.mark.skipif(shutil.which("osascript") is None, reason="needs macOS osascript (JavaScriptCore)")


def core():
    m = re.search(r"// CORE-BEGIN.*?\n(.*)// CORE-END", HTML.read_text(encoding="utf-8"), flags=re.S)
    return m.group(1)


def run_js(body):
    import tempfile
    js = core() + "\n" + body
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "run.js"
        f.write_text(js, encoding="utf-8")
        r = subprocess.run(["osascript", "-l", "JavaScript", str(f)], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout)


def test_page_is_current_and_carries_the_code_values():
    assert HTML.read_text(encoding="utf-8") == B.build(), "tools/annotate.html is stale: run tools/build_annotate.py"
    cfg = B.config()
    gold = next(s for s in cfg["sheets"] if s["type"] == "gold")
    import gold as G
    assert {e["col"]: e["values"] for e in gold["edit"] if "values" in e} == {k: list(v) for k, v in G.CODEBOOK.items()}
    review = next(s for s in cfg["sheets"] if s["type"] == "review")
    assert review["edit"][0]["values"] == ["maybe", "no", "yes"]
    assert "<script src" not in HTML.read_text() and "http" not in core()


@osa
def test_round_trip_and_edits_on_tricky_csv():
    samples = ["a,b\r\n1,2\r\n", "a,b\n\"x, y\",\"he said \"\"hi\"\"\"\n", "﻿a,b\r\n\"line1\r\nline2\",\r\n",
               "a,b\r\n,\r\n", "a,b\r\n\"q\",bare", "h\r\nमाँ, \"बेटा\"\r\n"]
    out = run_js(f"""
var S = {json.dumps(samples, ensure_ascii=False)}, res = [];
S.forEach(function (t) {{ res.push(serializeCSV(parseCSV(t)) === t); }});
var d = parseCSV("a,b,c\\r\\n1,,3\\r\\n");
setCell(d, 1, 1, "x, y");
JSON.stringify({{rt: res, edited: serializeCSV(d)}});""")
    assert out["rt"] == [True] * len(samples)
    assert out["edited"] == 'a,b,c\r\n1,"x, y",3\r\n'


@osa
def test_key_files_and_unknown_files_are_refused():
    cfg = json.dumps(B.config())
    out = run_js(f"""
var C = {cfg};
JSON.stringify(["gold_key_v1.csv", "audit_key.csv", "annotation_key.csv", "audit_passages.csv", "gold_sheet_v1_coder2.csv",
  "audit_rating_sheet_r2.csv", "meta_review.csv", "review_master_2026-10.csv", "gold_components_v1_coder1.csv"].map(function (n) {{
  var t = sheetType(C, n); return t.refused ? "refused" : t.type; }}));""")
    assert out == ["refused", "refused", "refused", "refused", "gold", "rating", "meta", "review", "components"]


@osa
@pytest.mark.skipif(not (ANN / "gold_pilot_r1.csv").exists(), reason="data/annotation is local")
def test_every_real_sheet_round_trips_byte_for_byte():
    files = [ANN / n for n in SHEETS if (ANN / n).exists()] + [p for p in [ROOT / "docs/review_master_2026-10.csv"]
                                                               if p.exists()]
    texts = [f.read_bytes().decode("utf-8") for f in files]
    out = run_js(f"var T = {json.dumps(texts, ensure_ascii=False)};"
                 "JSON.stringify(T.map(function (t) { return serializeCSV(parseCSV(t)) === t; }));")
    assert out == [True] * len(files), [f.name for f, ok in zip(files, out) if not ok]
