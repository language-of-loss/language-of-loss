import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
import gold
import meta_prefill

OUT = ROOT / "tools" / "annotate.html"
TEMPLATE = ROOT / "tools" / "annotate_template.html"


def review_decisions():
    src = (ROOT / "scripts" / "apply_review.py").read_text(encoding="utf-8")
    line = next(l for l in src.splitlines() if l.startswith("DECISIONS = "))
    return sorted(eval(line.split("=", 1)[1].strip()))


def config():
    comps = gold.components_list(ROOT / "lexicon")
    text = ["context_before", "clause_text", "span_text", "context_after"]
    codebook = {k: list(v) for k, v in gold.CODEBOOK.items()}
    return {
        "sheets": [
            {"type": "gold", "label": "Gold / pilot clause sheet",
             "pattern": r"^(gold_sheet_v\d+_(coder\d|adjudicated)|gold_pilot_r\d)\.csv$",
             "show": text, "main": "clause_text",
             "edit": [{"col": c, "values": v} for c, v in codebook.items()] + [{"col": "notes", "text": True}]},
            {"type": "components", "label": "Component sheet (0 / 1 per component)",
             "pattern": r"^gold_components_v\d+_(coder\d|adjudicated)\.csv$",
             "show": text, "main": "clause_text",
             "edit": [{"col": c, "values": ["0", "1"]} for c in comps] + [{"col": "notes", "text": True}]},
            {"type": "rating", "label": "Intensity rating sheet (1-7)",
             "pattern": r"^(audit_rating_sheet_r\d|audit_calibration_brighter_r\d)\.csv$",
             "show": ["passage_text"], "main": "passage_text",
             "edit": [{"col": "intensity_1to7", "values": [str(k) for k in range(1, 8)]},
                      {"col": "notes", "text": True}]},
            {"type": "meta", "label": "Text metadata confirmation",
             "pattern": r"^meta_review\.csv$",
             "show": ["record_id", "lang", "field", "prefill_value", "confidence", "rule", "evidence_clause_ids",
                      "prefill_changed", "source_url"], "main": "field",
             "edit": [{"col": "confirmed_value", "valuesByField": {k: list(v) for k, v in meta_prefill.FIELDS.items()}},
                      {"col": "reviewer", "text": True}, {"col": "notes", "text": True}]},
            {"type": "review", "label": "Corpus review master",
             "pattern": r"^review_master.*\.csv$",
             "show": ["review_id", "lang", "title", "url", "n_words", "over_cap", "first_300_chars",
                      "suggested_decision", "suggested_relation", "suggested_reason", "suggestion_confidence"],
             "main": "first_300_chars",
             "edit": [{"col": "decision", "values": review_decisions()}, {"col": "relation", "text": True},
                      {"col": "reason", "text": True}, {"col": "reviewer", "text": True}]},
        ],
        "refuse": r"key",
    }


def build():
    html = TEMPLATE.read_text(encoding="utf-8")
    return html.replace("/*__CONFIG__*/null", json.dumps(config(), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT}")
