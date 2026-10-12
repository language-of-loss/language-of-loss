import csv
import json
from pathlib import Path

import pytest

import referents as R
from test_referents import PERF_PL, W

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
REG_TEXT = "blogs:blog_0861b4d96495"
PRES = "Mood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin"


def run_rules(sentences, lang="hi", relation="wife", rules=R.RULES_V2, known=True, texts=None):
    clauses, sents, ids = [], {}, {}
    for k, words in enumerate(sentences):
        cid = f"t:1#{k:04d}"
        clauses.append(dict(clause_id=cid, record_id="t:1", lang=lang, sent_index=k, is_finite=True,
                            clause_text=texts[k] if texts else " ".join(w["token"] for w in words),
                            subject_inherited_from=None))
        sents[("t:1", k)] = {w["token_index"]: w for w in words}
        ids[cid] = [w["token_index"] for w in words]
    return R.classify_text(clauses, sents, ids, R.deceased_terms(relation), rules=rules, known_relation=known)


def tum_obj():
    return [W(1, "मैं", "PRON", 4, "nsubj"), W(2, "तुम्हे", "PRON", 4, "obj", "Person=2"),
            W(3, "याद", "NOUN", 4, "compound"), W(4, "करता", "VERB", 0, "root", PRES)]


def test_informal_second_person_is_address_to_dead():
    r = run_rules([tum_obj()])[0]
    assert r["address_to_dead"] is True and (r["target_class"], r["target_text"]) == ("deceased", "तुम्हे")
    v1 = run_rules([tum_obj()], rules=())[0]
    assert v1["target_class"] != "deceased" and v1["address_to_dead"] == ""


def test_no_address_rule_without_a_known_relation_or_in_quoted_speech():
    assert run_rules([tum_obj()], known=False)[0]["address_to_dead"] == ""
    r = run_rules([tum_obj()], texts=['उसने कहा "मैं तुम्हे याद करता हूँ"'])[0]
    assert r["address_to_dead"] is False and r["target_class"] != "deceased"


def test_another_addressee_resolves_the_pronoun():
    readers = [W(1, "दोस्तों", "NOUN", 2, "vocative"), W(2, "सुनो", "VERB", 0, "root", "Mood=Imp")]
    rows = run_rules([readers, tum_obj()])
    assert rows[1]["address_to_dead"] is False


def test_vocative_kin_term_of_the_deceased_is_address():
    voc = [W(1, "माँ", "NOUN", 3, "vocative"), W(2, "बहुत", "ADV", 3, "advmod"), W(3, "याद", "NOUN", 0, "root")]
    r = run_rules([voc], relation="mother (Maa)")[0]
    assert r["address_to_dead"] is True and r["target_class"] == "deceased"


def test_formal_and_english_you_need_an_address_context():
    you = [W(1, "you", "PRON", 2, "nsubj"), W(2, "learn", "VERB", 0, "root", "Mood=Ind|Tense=Pres|VerbForm=Fin")]
    assert run_rules([you], lang="en", relation="father")[0]["address_to_dead"] is False
    dad = [W(1, "Dad", "PROPN", 3, "vocative"), W(2, "I", "PRON", 3, "nsubj"), W(3, "miss", "VERB", 0, "root")]
    rows = run_rules([dad, you], lang="en", relation="father (Dad)", texts=["Dad, I miss", "you learn"])
    assert [r["address_to_dead"] for r in rows] == [True, True] and rows[1]["target_class"] == "deceased"


def test_letter_opener_starts_the_address():
    you = [W(1, "you", "PRON", 2, "nsubj"), W(2, "were", "AUX", 0, "root", "Mood=Ind|Tense=Past|VerbForm=Fin")]
    rows = run_rules([you], lang="en", relation="father (Dad)", texts=["Dear Dad, you were"])
    assert rows[0]["address_to_dead"] is True


def test_plural_demonstrative_after_plural_thing_is_not_honorific():
    papa = [W(1, "पापा", "NOUN", 2, "nsubj", "Number=Sing"), W(2, "थे", "AUX", 0, "root", "Number=Plur|Tense=Past")]
    things = [W(1, "यादें", "NOUN", 2, "nsubj", "Number=Plur"), W(2, "हैं", "AUX", 0, "root", "Number=Plur")]
    ye = [W(1, "ये", "PRON", 2, "nsubj"), W(2, "रहेंगी", "VERB", 0, "root", "Number=Plur|Tense=Fut")]
    v1 = run_rules([papa, things, ye], relation="father (Papa)", rules=())[2]
    v2 = run_rules([papa, things, ye], relation="father (Papa)")[2]
    assert v1["honorific"] is True and v1["referent_class"] == "deceased"
    assert v2["honorific"] is False and v2["referent_class"] == "impersonal" and v2["subject_source"] == "overt+inanimate"


def test_plural_pronoun_for_a_person_stays_honorific():
    papa = [W(1, "पापा", "NOUN", 2, "nsubj", "Number=Sing"), W(2, "आए", "VERB", 0, "root", PERF_PL)]
    ve = [W(1, "वे", "PRON", 2, "nsubj"), W(2, "गए", "VERB", 0, "root", PERF_PL)]
    assert run_rules([papa, ve], relation="father (Papa)")[1]["honorific"] is True


@pytest.mark.skipif(not (PROC / "tokens.csv").exists(), reason="data/processed is local")
def test_regression_blog_0861b4d96495_0060_0063():
    every = [json.loads(l) for l in open(PROC / "clauses.jsonl", encoding="utf-8")]
    clauses = [c for c in every if c["record_id"] == REG_TEXT]
    assert clauses, "regression text missing from clauses.jsonl"
    meta = {c["clause_id"]: (c["record_id"], c["sent_index"]) for c in every}
    sentences, clause_ids = R.load_sentences(PROC / "tokens.csv", meta)
    with open(PROC / "tokens.csv", encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            if r["clause_id"] in meta:
                sentences[meta[r["clause_id"]]][int(r["token_index"])]["feats"] = r["feats"]
    dec = R.deceased_terms("wife")
    rows = {r["clause_id"]: r for r in R.classify_text(clauses, sentences, clause_ids, dec)}
    old = {r["clause_id"]: r for r in R.classify_text(clauses, sentences, clause_ids, dec, rules=())}
    got = {int(cid[-4:]): (r["address_to_dead"], r["target_class"], r["honorific"])
           for cid, r in rows.items() if 60 <= int(cid[-4:]) <= 63}
    assert got == {60: (False, "impersonal", False),
                   61: (False, "impersonal", False),
                   62: (True, "deceased", False),
                   63: (True, "deceased", False)}
    assert old[f"{REG_TEXT}#0062"]["target_class"] != "deceased"
    assert old[f"{REG_TEXT}#0063"]["target_class"] == "impersonal"
    assert old[f"{REG_TEXT}#0065"]["honorific"] is True and rows[f"{REG_TEXT}#0065"]["honorific"] is False


def test_second_person_subject_addressing_the_deceased_is_the_deceased():
    tum = [W(1, "तुम", "PRON", 2, "nsubj"), W(2, "गईं", "VERB", 0, "root", "Aspect=Perf|Number=Plur")]
    r = run_rules([tum], relation="wife")[0]
    assert r["address_to_dead"] is True and r["referent_class"] == "deceased" and r["subject_source"].endswith("+address")
    old = run_rules([tum], relation="wife", rules=("address_to_dead", "demonstrative_inanimate"))[0]
    assert old["referent_class"] == "other"


def test_honorific_elder_marks_father_not_mother():
    import text_meta as T
    row = dict(honorific=True, referent_class="deceased", subject_text="")
    assert R.honorific_elder(row, T.elder_relation("father (Papa)")) is True
    assert R.honorific_elder(row, T.elder_relation("mother (Maa)")) is False
    assert T.elder_relation("grandmother (दादी)") and T.elder_relation("my teacher") and T.elder_relation("mother-in-law")
    kin = dict(honorific=True, referent_class="kin", subject_text="दादाजी")
    assert R.honorific_elder(kin, False) is True
    assert R.honorific_elder(dict(kin, honorific=False), False) is False
