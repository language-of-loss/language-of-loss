import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prefill_review as P


def row(title, text, n=900, cap="", lang="en"):
    return dict(review_id="R1", record_id="x", lang=lang, title=title, first_300_chars=text, n_words=str(n),
                over_cap=cap, decision="", relation="", reason="", reviewer="")


def test_include_high_needs_first_person_death_and_kin():
    d, rel, why, conf = P.suggest(row("Remembering my father", "My father died last winter and I still"))
    assert (d, rel, conf) == ("include", "father", "high") and "first person" in why


def test_hindi_include_and_relation():
    d, rel, _, conf = P.suggest(row("माँ की याद", "मेरी माँ का देहांत पिछले साल हुआ और मैं", lang="hi"))
    assert (d, rel, conf) == ("include", "mother", "high")


def test_exclusions():
    assert P.suggest(row("x", "my mother died", n=120))[0::3] == ("exclude", "high")
    assert P.suggest(row("50 condolence messages for a friend", "messages"))[0::3] == ("exclude", "high")
    assert P.suggest(row("माँ पर कविता", "मेरी माँ", lang="hi"))[0] == "exclude"
    assert P.suggest(row("5 tips to cope with grief", "When you lose someone"))[2].startswith("advice")
    assert P.suggest(row("My father", "my father died", cap="domain_cap"))[0::3] == ("exclude", "medium")
    assert P.suggest(row("Monsoon", "The rain fell on the hills all evening"))[0::3] == ("exclude", "low")


def test_as_told_to_is_noted_not_decided():
    d, _, why, _ = P.suggest(row("My mother, as told to a journalist", "I lost my mother in May"))
    assert d == "include" and "as-told-to" in why


def test_human_columns_untouched(tmp_path):
    p = tmp_path / "m.csv"
    rows = [row("My father", "my father died"), dict(row("x", "y", n=10), decision="yes", reviewer="A")]
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    P.main(["--master", str(p)])
    out = list(csv.DictReader(open(p, encoding="utf-8")))
    assert out[1]["decision"] == "yes" and out[1]["reviewer"] == "A" and out[0]["decision"] == ""
    assert all(out[0][c] for c in P.NEW)
