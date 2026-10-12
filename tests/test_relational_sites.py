import eligibility as E


def W(i, token, upos, head, deprel, feats=""):
    return dict(token_index=i, token=token, lemma=token, upos=upos, head=head, deprel=deprel, feats=feats)


def REF(**kw):
    base = dict(referent_class="other", honorific="False", overt_pronoun="", pronoun_person="", pronoun_number="",
                subject_text="", subject_source="overt", target_class="", target_text="")
    base.update(kw)
    return base


def rules(lang, ref=None, cf=None, words=(), category="parent", deceased=frozenset()):
    return [(r["rule_id"], r["decision"]) for r in E.classify_relational(lang, ref, cf, list(words), category,
                                                                          set(deceased))]


PITA_GAYE = [W(1, "पिताजी", "NOUN", 2, "nsubj"), W(2, "चले", "VERB", 0, "root"), W(3, "गए", "AUX", 2, "aux")]


def test_honorific_forced_for_parent_chosen_for_sibling_na_when_unknown():
    ref = REF(referent_class="deceased", honorific="True", subject_text="पिताजी")
    assert ("REL-HON-F", "forced_relational") in rules("hi", ref, words=PITA_GAYE, category="parent")
    assert ("REL-HON-F", "forced_relational") in rules("hi", ref, words=PITA_GAYE, category="teacher")
    assert ("REL-HON-C", "chosen_relational") in rules("hi", ref, words=PITA_GAYE, category="sibling")
    assert not [r for r in rules("hi", ref, words=PITA_GAYE, category="unknown") if r[0].startswith("REL-HON")]
    assert ("REL-KIN-TERM", "chosen_relational") in rules("hi", ref, words=PITA_GAYE)


def test_singular_pronoun_needs_non_plural_agreement():
    words = [W(1, "वह", "PRON", 2, "nsubj"), W(2, "चला", "VERB", 0, "root", "Number=Sing"),
             W(3, "गया", "AUX", 2, "aux", "Number=Sing")]
    ref = REF(referent_class="deceased", overt_pronoun="वह", pronoun_person="3", pronoun_number="sg",
              subject_text="वह", subject_source="overt+antecedent")
    assert ("REL-HON-SG", "chosen_individual") in rules("hi", ref, words=words, category="sibling")
    assert ("REL-HON-SG-ELDER", "review") in rules("hi", ref, words=words, category="parent")
    words_pl = [W(1, "वह", "PRON", 2, "nsubj"), W(2, "पूछते", "VERB", 0, "root"), W(3, "थे", "AUX", 2, "aux")]
    assert ("REL-HON-F", "forced_relational") in rules("hi", ref, words=words_pl, category="parent")
    erg = REF(referent_class="deceased", overt_pronoun="उसने", pronoun_person="3", pronoun_number="sg",
              subject_text="उसने", subject_source="overt+antecedent")
    assert not [r for r in rules("hi", erg, words=[W(1, "उसने", "PRON", 2, "nsubj"), W(2, "कहा", "VERB", 0, "root")],
                                 category="sibling") if r[0].startswith("REL-HON")]


def test_honorific_site_is_hindi_only():
    ref = REF(referent_class="deceased", honorific="", subject_text="Papa")
    assert not [r for r in rules("en", ref, category="parent") if r[0].startswith("REL-HON")]


def test_self_reference_plural_is_relational_singular_individual():
    assert ("REL-SELF-PL", "chosen_relational") in rules("hi", REF(referent_class="community", overt_pronoun="हम",
                                                                   pronoun_person="1", pronoun_number="pl"))
    assert ("REL-SELF-PL", "chosen_relational") in rules("en", REF(referent_class="community", overt_pronoun="we",
                                                                   pronoun_person="1", pronoun_number="pl"))
    assert ("REL-SELF-SG", "chosen_individual") in rules("en", REF(referent_class="self", overt_pronoun="I",
                                                                   pronoun_person="1", pronoun_number="sg"))
    assert rules("hi", REF(referent_class="self", subject_source="agreement")) == [("REL-NA", "NA")]


def test_deceased_by_kin_term_vs_pronoun_subject_and_target():
    assert ("REL-KIN-PRON", "chosen_individual") in rules("en", REF(referent_class="deceased", subject_text="she",
                                                                    subject_source="overt+antecedent"))
    papa = rules("en", REF(referent_class="self", overt_pronoun="I", pronoun_person="1", pronoun_number="sg",
                           target_class="deceased", target_text="Papa"))
    assert ("REL-KIN-TERM", "chosen_relational") in papa and ("REL-SELF-SG", "chosen_individual") in papa
    assert ("REL-KIN-PRON", "chosen_individual") in rules("en", REF(referent_class="self", target_class="deceased",
                                                                    target_text="him"))
    assert rules("hi", REF(referent_class="deceased", subject_source="antecedent")) == [("REL-NA", "NA")]


def test_vocative_community_ritual_always_chosen():
    words = [W(1, "माँ", "NOUN", 4, "vocative"), W(2, "तुम", "PRON", 4, "nsubj"), W(4, "चली", "VERB", 0, "root")]
    got = rules("hi", REF(target_class="deceased", target_text="माँ"), words=words, deceased={"माँ"})
    assert ("REL-VOC", "chosen_relational") in got and not [r for r in got if r[0].startswith("REL-KIN")]
    assert ("REL-VOC", "chosen_relational") in rules("en", cf={"flag_F7": "1"})
    assert ("REL-VOC", "chosen_relational") not in rules("en", words=[W(1, "Sir", "PROPN", 2, "vocative"),
                                                                      W(2, "listen", "VERB", 0, "root")])
    assert rules("hi", cf={"orient_C": "1", "comp_RITUAL_WORDS": "1"}) == [("REL-COMM", "chosen_relational"),
                                                                           ("REL-RITUAL", "chosen_relational")]


def test_rule_table_is_documented():
    ids = [r[0] for r in E.REL_RULES]
    assert len(ids) == len(set(ids)) and all(len(r) == 6 and r[5] for r in E.REL_RULES)
    assert {"forced_relational", "chosen_relational", "chosen_individual", "review"} <= {r[3] for r in E.REL_RULES}


def test_address_to_the_dead_by_pronoun_is_rel_voc():
    ref = dict(referent_class="self", overt_pronoun="मैं", pronoun_person="1", pronoun_number="sg",
               target_class="deceased", target_text="तुम्हे", address_to_dead="True", subject_source="overt")
    rows = E.classify_relational("hi", ref, {}, [], "spouse", set())
    rules = {r["rule_id"]: r["decision"] for r in rows}
    assert rules.get("REL-VOC") == "chosen_relational" and "REL-KIN-PRON" not in rules
    ref2 = dict(ref, address_to_dead="False")
    assert "REL-KIN-PRON" in {r["rule_id"] for r in E.classify_relational("hi", ref2, {}, [], "spouse", set())}
