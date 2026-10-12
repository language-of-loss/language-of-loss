import dict_channel as D
from gold import CODEBOOK, SHEET_COLUMNS


def e(eid, orient="I", proc="L", func="NA"):
    return dict(entry_id=eid, orientation=orient, process=proc, function=func)


def test_orientation_r_wins_then_majority_then_tie_rule():
    assert D.orientation([e("a", "F"), e("b", "R")]) == "R"
    assert D.orientation([e("a", "F"), e("b", "F"), e("c", "I")]) == "F"
    assert D.orientation([e("a", "F"), e("b", "C")]) == "F"
    assert D.orientation([e("a", "C"), e("b", "I")]) == "I"
    assert D.orientation([]) == "NA"


def test_process_and_function():
    assert D.process([e("a", proc="Rs"), e("b", proc="L")]) == "L"
    assert D.process([e("a", proc="Rs"), e("b", proc="NA")]) == "Rs"
    assert D.process([]) == "NA"
    assert D.function([e("a", func="Of"), e("b", func="Sk")]) == "Sk"
    assert D.function([e("a", func="Of")]) == "Of" and D.function([]) == "NA"


def test_predicate_type_rule_order():
    t = "True"
    assert D.predicate_type({"closing_formula": t, "no_more": t}, set(), "कह", "VERB")[0] == "other"
    assert D.predicate_type({"motion_euphemism": t}, {"chosen_nominative"}, "जा", "VERB")[0] == "event_befalling"
    assert D.predicate_type({}, {"forced_dative"}, "आ", "VERB")[0] == "event_befalling"
    assert D.predicate_type({}, {"chosen_nominative"}, "दुखी", "ADJ")[0] == "state"
    assert D.predicate_type({}, set(), "die", "VERB")[0] == "event_befalling"
    assert D.predicate_type({}, set(), "say", "VERB")[0] == "speech"
    assert D.predicate_type({}, set(), "होना", "VERB")[0] == "state"
    assert D.predicate_type({}, set(), "take", "VERB")[0] == "action"
    assert D.predicate_type({}, set(), "teacher", "NOUN")[0] == "state"
    assert D.predicate_type({}, set(), None, None)[0] == "other"


def test_grammar_forced_and_dative_alternative():
    assert D.grammar_forced({"forced_dative"}, set()) == "Y"
    assert D.grammar_forced(set(), {"REL-HON-F"}) == "Y"
    assert D.grammar_forced(set(), {"REL-HON-C"}) == "context"
    assert D.grammar_forced({"chosen_dative"}, {"REL-HON-SG"}) == "N"
    assert D.dative_alternative({"chosen_nominative", "forced_dative"}) == "Y"
    assert D.dative_alternative({"forced_nominative"}) == "N"
    assert D.dative_alternative({"review"}) == "NA" and D.dative_alternative(set()) == "NA"


def test_code_clause_values_are_in_codebook_and_sheet_fill():
    ref = dict(referent_class="self", target_class="")
    v = D.code_clause(dict(head_lemma="miss"), [e("L-EN-08")], {}, ref, {"forced_nominative"}, set(), "VERB")
    assert v["experiencer"] == "self" and v["target"] == "none" and v["grammar_forced"] == "Y"
    assert all(v[f] in CODEBOOK[f] for f in CODEBOOK) and "L-EN-08" in v["evidence"]
    sheet = [dict.fromkeys(SHEET_COLUMNS, "") | dict(gold_id="G1", clause_text="x"),
             dict.fromkeys(SHEET_COLUMNS, "") | dict(gold_id="G2")]
    rows = D.fill_sheet(sheet, [dict(gold_id="G1", clause_id="c#1")], {"c#1": v})
    assert list(rows[0]) == SHEET_COLUMNS and rows[0]["orientation"] == "I" and rows[0]["clause_text"] == "x"
    assert rows[1]["orientation"] == "" and "not found" in rows[1]["notes"]
