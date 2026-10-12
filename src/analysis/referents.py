"""Stage 5b -- experiencer/subject referent of every finite clause, with honorific detection."""
import argparse
import csv
import json
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flags import load_sentences

CLASSES = ["self", "kin", "community", "deceased", "God", "impersonal", "other"]
PERSON_CLASSES = {"kin", "deceased", "God", "other"}
SUBJ = ("nsubj", "nsubj:pass", "csubj", "csubj:pass", "expl")
TARGET_DEPRELS = ("obj", "iobj", "obl", "obl:arg", "nmod", "vocative")
RELATIONAL = {"kin", "community", "deceased"}
TARGET_PRIORITY = ("deceased", "kin", "community")
CHAIN = ("aux", "aux:pass", "cop", "compound")
PLURAL_VERB_ENDINGS = ("े", "ए", "ये", "ीं", "ईं", "यीं", "ैं")

PRONOUNS = {
    "hi": {**{w: ("1", "sg") for w in ["मैं", "मुझे", "मैंने", "मुझको", "मुझ"]},
           **{w: ("1", "pl") for w in ["हम", "हमें", "हमने", "हमको"]},
           **{w: ("2", "sg") for w in ["तू", "तुझे", "तूने", "तुझको"]},
           **{w: ("2", "pl") for w in ["तुम", "तुम्हें", "तुमने", "तुमको", "आप", "आपको", "आपने"]},
           **{w: ("3", "sg") for w in ["वह", "उसने", "उसे", "उसको", "यह", "इसने", "इसे", "इसको"]},
           **{w: ("3", "pl") for w in ["वे", "उन्होंने", "उन्हें", "उनको", "ये", "इन्होंने", "इन्हें", "इनको"]},
           **{w: ("3", "u") for w in ["वो"]}},
    "en": {**{w: ("1", "sg") for w in ["i", "me"]}, **{w: ("1", "pl") for w in ["we", "us"]},
           **{w: ("2", "u") for w in ["you"]},
           **{w: ("3", "sg") for w in ["he", "she", "him", "her", "it"]},
           **{w: ("3", "pl") for w in ["they", "them"]}},
}
HONORIFIC_FORMS = {"आप", "आपको", "आपने"}
RULES_V2 = ("address_to_dead", "demonstrative_inanimate", "address_subject")
V1_COLUMNS = ("referent_class", "honorific", "target_class", "target_text", "rel_target", "relational")
ELDER_TERMS = {"पापा", "पिता", "पिताजी", "बाबूजी", "अब्बू", "अब्बा", "दादा", "दादी", "दादाजी", "नाना", "नानी", "नानाजी",
               "ससुर", "सास", "ससुरजी", "सासुजी", "गुरु", "गुरुजी", "ताऊ", "ताई", "चाचा", "चाची", "मामा", "मामी", "बुआ",
               "मौसी", "काका", "काकी", "बब्बा"}
SECOND_HI_INFORMAL = {"तू", "तुझे", "तूने", "तुझको", "तुझसे", "तुझमें", "तुझ", "तेरा", "तेरी", "तेरे", "तुम", "तुम्हें",
                      "तुम्हे", "तुमने", "तुमको", "तुमसे", "तुममें", "तुम्हारा", "तुम्हारी", "तुम्हारे", "तुम्हीं", "तुम्ही"}
SECOND_HI_FORMAL = {"आप", "आपको", "आपने", "आपसे", "आपमें", "आपका", "आपकी", "आपके", "आपही"}
SECOND_EN = {"you", "your", "yours", "yourself", "you'd", "you're", "you've", "you'll"}
OTHER_ADDRESSEE = {"दोस्तों", "मित्रों", "पाठकों", "साथियों", "भाइयों", "बहनों", "friends", "readers", "reader", "folks",
                   "guys", "everyone"}
DEMONSTRATIVES = {"pl": {"ये", "वे", "इन्हें", "उन्हें", "इनको", "उनको"}, "u": {"वो"}, "sg": set()}
QUOTES = "\"“”«»"
ADDRESS_WINDOW = 2
IMPERSONAL_PRON = {"it", "this", "that", "there", "what", "which", "something", "nothing", "anything", "everything",
                   "यह", "इसने", "इसे", "इसको", "क्या", "कुछ"}
RELATIVE = {"जो", "जिसने", "जिन्होंने", "जिसे", "जिन्हें", "जिसको", "who", "whom", "that", "which"}
COMMUNITY = {"लोग", "लोगों", "परिवार", "समाज", "सब", "सभी", "सबने", "सबको", "रिश्तेदार", "रिश्तेदारों", "घरवाले",
             "घरवालों", "पड़ोसी", "मोहल्ला", "people", "family", "everyone", "everybody", "all", "relatives",
             "neighbours", "neighbors", "society", "community", "friends", "nobody", "none"}
GOD = {"भगवान", "ईश्वर", "प्रभु", "परमात्मा", "अल्लाह", "खुदा", "ऊपरवाला", "ऊपरवाले", "राम", "god", "lord", "allah"}
HUMAN = {"डॉक्टर", "डाक्टर", "नर्स", "आदमी", "औरत", "लड़का", "लड़की", "लड़के", "बच्चा", "बच्चे", "बच्ची", "व्यक्ति",
         "इंसान", "मित्र", "गुरु", "अधिकारी", "साहब", "जी", "शिक्षक", "मास्टर", "पंडित", "doctor", "doctors", "nurse", "man", "woman",
         "boy", "girl", "child", "children", "kid", "kids", "person", "teacher", "someone", "somebody"}
KIN = {"hi": {"माँ", "मां", "मम्मी", "माता", "माताजी", "अम्मा", "अम्मी", "पापा", "पिता", "पिताजी", "बाबूजी", "बाबा",
              "अब्बू", "अब्बा", "दादी", "दादा", "दादाजी", "नानी", "नाना", "नानाजी", "भाई", "भैया", "भाईसाहब", "बहन",
              "दीदी", "बेटा", "बेटी", "पति", "पत्नी", "चाचा", "चाची", "मामा", "मामी", "बुआ", "मौसी", "ताऊ", "ताई",
              "काका", "काकी", "बीजी", "बब्बा", "ईजा", "आमा", "दोस्त", "सहेली", "बच्चों"},
       "en": {"mother", "mom", "mum", "mummy", "ma", "maa", "amma", "ammi", "aai", "father", "dad", "daddy", "papa",
              "appa", "abbu", "grandmother", "grandma", "dadi", "nani", "paati", "grandfather", "grandpa", "dada",
              "nana", "daadu", "brother", "bhai", "bhaiya", "sister", "didi", "son", "daughter", "husband", "wife",
              "uncle", "aunt", "aunty", "chacha", "chachi", "mama", "mami", "bua", "mausi", "friend", "parents",
              "parent", "grandparents"}}
RELATION_TERMS = {
    "mother": {"माँ", "मां", "मम्मी", "माता", "माताजी", "अम्मा", "अम्मी", "बीजी", "ईजा", "mother", "mom", "mum",
               "mummy", "ma", "maa", "amma", "ammi", "aai"},
    "father": {"पापा", "पिता", "पिताजी", "बाबूजी", "बाबा", "अब्बू", "अब्बा", "father", "dad", "daddy", "papa",
               "appa", "abbu"},
    "grandmother": {"दादी", "नानी", "आमा", "grandmother", "grandma", "dadi", "nani", "paati"},
    "grandfather": {"दादा", "दादाजी", "नाना", "नानाजी", "बाबा", "बब्बा", "grandfather", "grandpa", "dada", "nana",
                    "daadu"},
    "wife": {"पत्नी", "wife"}, "husband": {"पति", "husband"}, "son": {"बेटा", "son"}, "daughter": {"बेटी", "daughter"},
    "brother": {"भाई", "भैया", "भाईसाहब", "brother", "bhai", "bhaiya"}, "sister": {"बहन", "दीदी", "sister", "didi"},
    "uncle": {"चाचा", "मामा", "ताऊ", "काका", "uncle", "chacha"}, "friend": {"दोस्त", "मित्र", "सहेली", "friend"},
}
RELATION_TERMS.update({
    "parents?": RELATION_TERMS["mother"] | RELATION_TERMS["father"],
    "grandparents?": RELATION_TERMS["grandmother"] | RELATION_TERMS["grandfather"],
    "siblings?": RELATION_TERMS["brother"] | RELATION_TERMS["sister"],
    "spouse": RELATION_TERMS["wife"] | RELATION_TERMS["husband"],
    "child(?:ren)?": RELATION_TERMS["son"] | RELATION_TERMS["daughter"],
})


def norm(w, lang):
    w = unicodedata.normalize("NFC", w or "").strip("\"'“”‘’()[].,;:!?।-")
    return w.lower() if lang == "en" else w


def deceased_terms(relation):
    rel = (relation or "").lower()
    terms = set()
    for key, words in RELATION_TERMS.items():
        if re.search(rf"(?<![a-z]){key}(?![a-z])", rel):
            terms |= words
    for inner in re.findall(r"\(([^)]*)\)", relation or ""):
        terms |= {norm(x, "en") for x in re.split(r"[;,/ ]+", inner) if x and len(x) > 1}
        terms |= {x for x in re.split(r"[;,/ ]+", inner) if re.search(r"[ऀ-ॿ]", x)}
    return terms


def feats(w):
    return dict(kv.split("=", 1) for kv in (w.get("feats") or "").split("|") if "=" in kv)


def clause_head(words, ids):
    heads = [w for w in words if w["upos"] != "PUNCT" and w["head"] not in ids]
    for w in heads:
        if w["upos"] in ("VERB", "AUX") or w["deprel"] in ("root", "conj", "ccomp", "advcl", "acl:relcl"):
            return w
    return heads[0] if heads else None


def chain_feats(head, kids):
    out = {}
    for x in [head] + [c for c in kids[head["token_index"]] if c["deprel"] in CHAIN]:
        f = feats(x)
        for k in ("Person", "Number", "Gender", "Polite"):
            if k in f and (k not in out or x is not head):
                out[k] = f[k]
    chain = [x for x in [head] + [c for c in kids[head["token_index"]] if c["deprel"] in CHAIN]
             if x["upos"] in ("VERB", "AUX")]
    if chain:
        last = max(chain, key=lambda x: x["token_index"])
        if feats(last).get("Number") == "Plur" or norm(last["token"], "hi").endswith(PLURAL_VERB_ENDINGS):
            out["AnyPlur"] = True
    return out


def noun_number(w, lang):
    f = feats(w).get("Number")
    t = norm(w["token"], lang)
    if noun_keys(w, lang) & (KIN[lang] | HUMAN) or w["upos"] == "PROPN":
        return "Plur" if f == "Plur" and t != norm(w["lemma"], lang) else "Sing"
    return f


def pick_subject(head, kids, lang):
    subs = [c for c in kids[head["token_index"]] if c["deprel"] in SUBJ]
    if not subs:
        return None

    def rank(c):
        t = norm(c["token"], lang)
        if t in PRONOUNS[lang] and t not in IMPERSONAL_PRON:
            return 0
        if noun_keys(c, lang) & (KIN[lang] | GOD | HUMAN) or c["upos"] == "PROPN":
            return 1
        return 2
    return sorted(subs, key=lambda c: (rank(c), c["token_index"]))[0]


def noun_keys(w, lang):
    keys = {norm(w["token"], lang), norm(w.get("lemma") or "", lang)}
    if lang == "hi":
        keys |= {k[:-2] for k in keys if k.endswith("जी") and len(k) > 3}
    return {k for k in keys if k}


def classify_noun(w, lang, deceased):
    t = norm(w["token"], lang)
    keys = noun_keys(w, lang)
    if w["deprel"].startswith("csubj") or w["deprel"] == "expl" or t in IMPERSONAL_PRON:
        return "impersonal"
    if keys & GOD:
        return "God"
    if keys & set(deceased):
        return "deceased"
    if keys & KIN[lang]:
        return "kin"
    if keys & COMMUNITY:
        return "community"
    if w["upos"] == "PROPN" or keys & HUMAN:
        return "other"
    return "impersonal"


def plural_controller(words, kids):
    for w in words:
        if w["upos"] in ("NOUN", "PROPN") and noun_number(w, "hi") == "Plur" and \
                not any(c["deprel"] == "case" for c in kids[w["token_index"]]):
            return True
    return False


def is_singular_person(ref):
    return ref is not None and ref["cls"] in PERSON_CLASSES and ref["number"] != "Plur"


def resolve_antecedent(history, verb_gender):
    for ref in reversed(history[-5:]):
        if ref["cls"] in PERSON_CLASSES and not (verb_gender and ref["gender"] and verb_gender != ref["gender"]):
            return ref
    return None


def classify_target(head, kids, lang, deceased, history):
    cands = [c for c in kids[head["token_index"]] if c["deprel"] in TARGET_DEPRELS]
    for c in kids[head["token_index"]]:
        if c["deprel"] in ("compound", "xcomp") and c["upos"] in ("NOUN", "ADJ"):
            cands += [g for g in kids[c["token_index"]] if g["deprel"] == "nmod"]
    found = []
    for c in cands:
        if c["upos"] == "PUNCT":
            continue
        t = norm(c["token"], lang)
        if t in PRONOUNS[lang] and t not in IMPERSONAL_PRON:
            person, number = PRONOUNS[lang][t]
            if person == "1":
                cls = "self" if number == "sg" else "community"
            elif person == "2":
                cls = "other"
            else:
                ante = resolve_antecedent(history, None)
                cls = ante["cls"] if ante else "other"
        else:
            cls = classify_noun(c, lang, deceased)
        found.append((cls, c["token"]))
    for want in TARGET_PRIORITY:
        for cls, text in found:
            if cls == want:
                return cls, text
    return found[0] if found else ("", "")


def opener_rx(deceased, lang):
    terms = sorted({t for t in deceased if t}, key=len, reverse=True)
    if not terms:
        return None
    alt = "|".join(re.escape(t) for t in terms)
    lead = r"(?:dear(?:est)?\s+|my\s+)?" if lang == "en" else r"(?:प्रिय\s+|मेरी\s+|मेरे\s+)?"
    return re.compile(rf"^\W*{lead}(?:{alt})\s*[,!]", re.I if lang == "en" else 0)


def address(clause, words, lang, deceased, ctx):
    for w in words:
        if w["deprel"] == "vocative" and noun_keys(w, lang) & set(deceased):
            return True, w["token"], "vocative"
    text = clause.get("clause_text", "")
    rx = opener_rx(deceased, lang)
    m = rx.match(text) if rx else None
    if m:
        return True, m.group(0).strip(" ,!"), "vocative"
    if any(q in text for q in QUOTES) or ctx.get("other_addressee"):
        return False, "", ""
    for w in words:
        t = norm(w["token"], lang)
        if lang == "hi" and t in SECOND_HI_INFORMAL:
            return True, w["token"], "second_person"
        if ((lang == "hi" and t in SECOND_HI_FORMAL) or (lang == "en" and t in SECOND_EN)) and ctx.get("address"):
            return True, w["token"], "second_person"
    return False, "", ""


def other_addressee(words, lang, deceased):
    for w in words:
        t = norm(w["token"], lang)
        if t in OTHER_ADDRESSEE and (w["deprel"] == "vocative" or w["token_index"] == min(x["token_index"] for x in words)):
            return True
        if w["deprel"] == "vocative" and not noun_keys(w, lang) & set(deceased):
            return True
    return False


def last_nominal(words, lang, deceased, before=None):
    cands = [w for w in words if (before is None or w["token_index"] < before)
             and (w["upos"] in ("NOUN", "PROPN") or norm(w["token"], lang) in PRONOUNS[lang])]
    if not cands:
        return None
    w = max(cands, key=lambda x: x["token_index"])
    if norm(w["token"], lang) in PRONOUNS[lang]:
        return dict(inanimate=False, number=None)
    return dict(inanimate=w["upos"] == "NOUN" and classify_noun(w, lang, deceased) == "impersonal",
                number=noun_number(w, lang))


def inanimate_antecedent(subj, words, lang, deceased, ctx, number):
    near = last_nominal(words, lang, deceased, before=subj["token_index"]) or ctx.get("prev_nominal")
    if not near or not near["inanimate"]:
        return False
    return near["number"] == "Plur"


def relational_entries(lexicon_path):
    with open(lexicon_path, encoding="utf-8", newline="") as fh:
        return {r["entry_id"] for r in csv.DictReader(fh)
                if r["orientation"] in ("F", "C") and r.get("grammar_forced", "N") == "N"}


def relational_columns(rows, features_path, lexicon_path=None):
    if not Path(features_path).exists():
        sys.exit(f"{features_path} not found: run lexmatch.py first (rel_entry needs the entry columns)")
    rel_ids = relational_entries(lexicon_path or Path(__file__).resolve().parents[2] / "lexicon" / "lexicon.csv")
    entry = {}
    with open(features_path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        cols = [c for c in reader.fieldnames if c in rel_ids]
        for r in reader:
            entry[r["clause_id"]] = (any(r[c] in ("1", "True") for c in cols), r.get("flag_F7") in ("1", "True"))
    missing = [r["clause_id"] for r in rows if r["clause_id"] not in entry]
    if missing:
        sys.exit(f"{len(missing)} clauses missing from {features_path} (e.g. {missing[0]}): re-run lexmatch.py")
    for r in rows:
        ent, voc = entry[r["clause_id"]]
        r["rel_subject"] = r["referent_class"] in RELATIONAL
        r["rel_target"] = r["target_class"] in RELATIONAL or voc
        r["rel_entry"] = ent
        r["relational"] = r["rel_subject"] or r["rel_target"] or r["rel_entry"]
    return rows


def classify_clause(clause, words, sentence, ids, history, inherited_ref, deceased, rules=RULES_V2, ctx=None):
    ctx = ctx or {}
    lang = clause["lang"]
    kids = defaultdict(list)
    for w in sentence.values():
        kids[w["head"]].append(w)
    head = clause_head(words, ids)
    row = dict(clause_id=clause["clause_id"], referent_class="impersonal", overt_pronoun="", pronoun_person="",
               pronoun_number="", honorific="" if lang == "en" else False, subject_text="", subject_source="none",
               stanza_polite="", target_class="", target_text="")
    row["address_to_dead"] = "" if "address_to_dead" not in rules or not deceased else False
    if head is None:
        return row, None
    row["target_class"], row["target_text"] = classify_target(head, kids, lang, deceased, history)
    if "address_to_dead" in rules and deceased:
        addr, txt, _ = address(clause, words, lang, deceased, ctx)
        if addr:
            row.update(address_to_dead=True, target_class="deceased", target_text=txt)
    cf = chain_feats(head, kids)
    row["stanza_polite"] = cf.get("Polite", "")
    plural_agreement = bool(cf.get("AnyPlur")) and not plural_controller(words, kids)
    subj = pick_subject(head, kids, lang)
    ref = None
    if subj is not None:
        t = norm(subj["token"], lang)
        row["subject_text"] = subj["token"]
        row["subject_source"] = "overt"
        if t in PRONOUNS[lang] and t not in IMPERSONAL_PRON:
            person, number = PRONOUNS[lang][t]
            row.update(overt_pronoun=subj["token"], pronoun_person=person, pronoun_number=number)
            if person == "1":
                ref = dict(cls="self" if number == "sg" else "community", number="Sing" if number == "sg" else "Plur",
                           gender=None, text=t)
            elif person == "2":
                ref = dict(cls="other", number=None, gender=None, text=t)
                if lang == "hi" and t in HONORIFIC_FORMS:
                    row["honorific"] = True
            elif "demonstrative_inanimate" in rules and lang == "hi" and t in DEMONSTRATIVES[number] \
                    and inanimate_antecedent(subj, words, lang, deceased, ctx, number):
                ref = dict(cls="impersonal", number=None, gender=None, text=t)
                row["subject_source"] = "overt+inanimate"
            else:
                ergative = t.endswith("ने") or any(c["deprel"] == "case" and c["token"] == "ने"
                                                   for c in kids[subj["token_index"]])
                ante = resolve_antecedent(history, None if ergative else cf.get("Gender"))
                ref = dict(ante) if ante else dict(cls="other", number=None, gender=None, text=t)
                row["subject_source"] = "overt+antecedent" if ante else "overt"
                if lang == "hi" and number in ("pl", "u") and is_singular_person(ante):
                    row["honorific"] = True
        elif t in RELATIVE and head["deprel"] == "acl:relcl" and head["head"] in sentence:
            gov = sentence[head["head"]]
            ref = dict(cls=classify_noun(gov, lang, deceased), number=noun_number(gov, lang),
                       gender=feats(gov).get("Gender"), text=gov["token"])
            row["subject_source"] = "relative"
        else:
            ref = dict(cls=classify_noun(subj, lang, deceased), number=noun_number(subj, lang),
                       gender=feats(subj).get("Gender"), text=t)
            ergative = any(c["deprel"] == "case" and c["token"] == "ने" for c in kids[subj["token_index"]])
            if lang == "hi" and ref["cls"] in PERSON_CLASSES and ref["number"] != "Plur" and plural_agreement \
                    and not ergative:
                row["honorific"] = True
    elif inherited_ref is not None:
        ref = dict(inherited_ref)
        row["subject_source"] = "inherited"
        row["subject_text"] = inherited_ref["text"]
        if lang == "hi" and is_singular_person(ref) and plural_agreement:
            row["honorific"] = True
    else:
        person = cf.get("Person")
        if feats(head).get("Mood") == "Imp":
            person = "2"
        if person == "1":
            ref = dict(cls="community" if cf.get("Number") == "Plur" else "self", number=cf.get("Number"),
                       gender=cf.get("Gender"), text="")
            row["subject_source"] = "agreement"
        elif person == "2":
            ref = dict(cls="other", number=None, gender=None, text="")
            row["subject_source"] = "agreement"
            row["_agreement_person"] = "2"
        else:
            ante = resolve_antecedent(history, cf.get("Gender"))
            if ante is not None:
                ref = dict(ante)
                row["subject_source"] = "antecedent"
                row["subject_text"] = ante["text"]
                if lang == "hi" and is_singular_person(ante) and plural_agreement:
                    row["honorific"] = True
    if "address_subject" in rules and row.get("address_to_dead") is True and second_person_subject(subj, row, lang):
        ref = dict(cls="deceased", number=None, gender=None, text=subj["token"] if subj is not None else "")
        row["subject_source"] += "+address"
    if ref is not None:
        row["referent_class"] = ref["cls"]
    return row, ref


def honorific_elder(row, elder_deceased):
    if row.get("honorific") is not True:
        return False
    if row["referent_class"] == "deceased":
        return elder_deceased
    t = norm(row.get("subject_text", ""), "hi")
    keys = {t, t[:-2] if t.endswith("जी") and len(t) > 3 else t}
    return row["referent_class"] == "kin" and bool(keys & ELDER_TERMS)


def second_person_subject(subj, row, lang):
    if subj is not None:
        t = norm(subj["token"], lang)
        return PRONOUNS[lang].get(t, ("",))[0] == "2" or t in SECOND_HI_INFORMAL | SECOND_HI_FORMAL | SECOND_EN
    return row.get("subject_source") == "agreement" and row.get("pronoun_person", "") == "" and \
        row.get("_agreement_person") == "2"


def classify_text(clauses, sentences, clause_ids, deceased, rules=RULES_V2, known_relation=True):
    if not known_relation:
        rules = tuple(r for r in rules if r != "address_to_dead")
    rows, history, ref_by_clause = [], [], {}
    recent = []
    prev_nominal = None
    for c in clauses:
        if not c["is_finite"]:
            continue
        ids = set(clause_ids[c["clause_id"]])
        sentence = sentences[(c["record_id"], c["sent_index"])]
        words = [sentence[i] for i in sorted(ids)]
        inherited = ref_by_clause.get(c.get("subject_inherited_from"))
        lang = c["lang"]
        other_here = other_addressee(words, lang, deceased)
        ctx = dict(address=any(a for a, _ in recent[-ADDRESS_WINDOW:]),
                   other_addressee=other_here or any(o for _, o in recent[-ADDRESS_WINDOW:]),
                   prev_nominal=prev_nominal)
        row, ref = classify_clause(c, words, sentence, ids, history, inherited, deceased, rules, ctx)
        recent.append((row.get("address_to_dead") is True, other_here))
        prev_nominal = last_nominal(words, lang, deceased)
        rows.append(row)
        if ref is not None:
            ref_by_clause[c["clause_id"]] = ref
            history.append(ref)
    return rows


def referent_text_columns(ref_path, clauses):
    lang_of = {c["clause_id"]: (c["record_id"], c["lang"]) for c in clauses}
    n_fin = Counter(c["record_id"] for c in clauses if c["is_finite"])
    counts = defaultdict(Counter)
    with open(ref_path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            rid, _ = lang_of.get(r["clause_id"], (None, None))
            if rid is None:
                continue
            counts[rid][f"ref_{r['referent_class']}"] += 1
            if r["honorific"] == "True":
                counts[rid]["ref_honorific"] += 1
            if r["overt_pronoun"]:
                counts[rid][f"pron_{r['pronoun_person']}{r['pronoun_number']}"] += 1
            if r.get("target_class"):
                counts[rid][f"tgt_{r['target_class']}"] += 1
            for k in ("rel_subject", "rel_target", "rel_entry"):
                counts[rid][k] += r.get(k) == "True"
            counts[rid]["rel_any"] += r.get("relational") == "True"
    cols = [f"ref_{c}" for c in CLASSES] + ["ref_honorific"] + \
        [f"pron_{p}{n}" for p in "123" for n in ("sg", "pl", "u")] + [f"tgt_{c}" for c in CLASSES] + \
        ["rel_any", "rel_subject", "rel_target", "rel_entry"]
    out = {}
    for rid, n in n_fin.items():
        out[rid] = {"n_finite": n, **{k: round(100 * counts[rid][k] / n, 3) for k in cols}}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--in", dest="inp", default="data/processed/clauses.jsonl")
    ap.add_argument("--tokens", default=None, help="default: tokens.csv next to --in")
    ap.add_argument("--records", default="data/clean/blogs_merged.jsonl")
    ap.add_argument("--out", default="data/processed/referents.csv")
    ap.add_argument("--seed", type=int, default=20261009)
    ap.add_argument("--features", default=None, help="clause_features.csv (default: next to --out)")
    ap.add_argument("--show-sample", action="store_true",
                    help="print 15 random clauses with their referents (prints corpus text: local inspection only)")
    args = ap.parse_args()
    args.tokens = args.tokens or str(Path(args.inp).with_name("tokens.csv"))
    clauses = [json.loads(line) for line in open(args.inp, encoding="utf-8")]
    sentences, clause_ids = load_sentences(args.tokens, {c["clause_id"]: (c["record_id"], c["sent_index"])
                                                         for c in clauses})
    with open(args.tokens, encoding="utf-8", newline="") as fh:
        meta = {c["clause_id"]: (c["record_id"], c["sent_index"]) for c in clauses}
        for r in csv.DictReader(fh):
            sentences[meta[r["clause_id"]]][int(r["token_index"])]["feats"] = r["feats"]
    relation = {}
    for line in open(args.records, encoding="utf-8"):
        r = json.loads(line)
        relation[r["record_id"]] = (r.get("extra") or {}).get("deceased_relation_as_stated", "")
    by_text = defaultdict(list)
    for c in clauses:
        by_text[c["record_id"]].append(c)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    from text_meta import elder_relation, loss_type
    rows, rows_v1 = [], []
    for rid, cl in by_text.items():
        dec = deceased_terms(relation.get(rid))
        text_rows = classify_text(cl, sentences, clause_ids, dec,
                                  known_relation=loss_type(relation.get(rid) or "") != "unstated")
        elder = elder_relation(relation.get(rid) or "")
        for r in text_rows:
            r["honorific_elder"] = honorific_elder(r, elder)
        rows += text_rows
        rows_v1 += classify_text(cl, sentences, clause_ids, dec, rules=())
    features = args.features or out.parent / "clause_features.csv"
    relational_columns(rows, features)
    relational_columns(rows_v1, features)
    v1 = {r["clause_id"]: r for r in rows_v1}
    for r in rows:
        old = v1[r["clause_id"]]
        for k in V1_COLUMNS:
            r[f"{k}_v1"] = old[k]
    fields = ["clause_id", "referent_class", "overt_pronoun", "pronoun_person", "pronoun_number", "honorific",
              "subject_text", "subject_source", "stanza_polite", "target_class", "target_text", "address_to_dead",
              "honorific_elder", "rel_subject", "rel_target", "rel_entry", "relational"] + [f"{k}_v1" for k in V1_COLUMNS]
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tf = out.parent / "text_features.csv"
    if tf.exists():
        with open(tf, encoding="utf-8", newline="") as fh:
            base = [{k: v for k, v in r.items() if not k.startswith(("ref_", "pron_", "tgt_", "rel_"))
                     and k != "n_finite"}
                    for r in csv.DictReader(fh)]
        from lexmatch import write_text_features
        write_text_features(tf, base, referent_text_columns(out, clauses))
    lang = {c["clause_id"]: c["lang"] for c in clauses}
    for lg in ("hi", "en"):
        rr = [r for r in rows if lang[r["clause_id"]] == lg]
        dist = Counter(r["referent_class"] for r in rr)
        hon = sum(1 for r in rr if r["honorific"] is True)
        print(f"{lg}: {len(rr)} finite clauses; " + ", ".join(f"{k} {dist[k]}" for k in CLASSES)
              + (f"; honorific {hon}" if lg == "hi" else ""))
    print(change_summary(rows, lang))
    if args.show_sample:
        show_sample(clauses, rows, out.parent / "clause_features.csv", args.seed)


def change_summary(rows, lang):
    out = []
    for lg in ("hi", "en"):
        rr = [r for r in rows if lang[r["clause_id"]] == lg]
        n = lambda f: sum(1 for r in rr if f(r))
        out.append(f"{lg} v1 -> v2: target deceased {n(lambda r: r['target_class_v1'] == 'deceased')} -> "
                   f"{n(lambda r: r['target_class'] == 'deceased')}; address_to_dead {n(lambda r: r['address_to_dead'] is True)} "
                   f"(texts with a known deceased relation: {n(lambda r: r['address_to_dead'] != '')} clauses); "
                   f"honorific {n(lambda r: r['honorific_v1'] is True)} -> {n(lambda r: r['honorific'] is True)}; "
                   f"referent class changed {n(lambda r: r['referent_class'] != r['referent_class_v1'])}; "
                   f"relational {n(lambda r: r['relational_v1'])} -> {n(lambda r: r['relational'])}")
    return "\n".join(out)


def show_sample(clauses, rows, features_path, seed):
    if not features_path.exists():
        return
    with open(features_path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        entry_cols = [c for c in reader.fieldnames if re.match(r"^[LP]-(HI|EN)-", c)]
        matched = {r["clause_id"]: [c for c in entry_cols if r[c] == "1"] for r in reader}
    ref = {r["clause_id"]: r for r in rows}
    rng = random.Random(seed)
    for lg, n in (("hi", 10), ("en", 5)):
        pool = [c for c in clauses if c["lang"] == lg and c["is_finite"] and matched.get(c["clause_id"])]
        print(f"\n=== {n} random {lg} finite clauses with an entry match (seed {seed}) ===")
        for c in rng.sample(pool, min(n, len(pool))):
            r = ref[c["clause_id"]]
            hon = " honorific" if r["honorific"] is True else ""
            print(f"{c['clause_id']}\n   {c['clause_text']}\n   entries: {', '.join(matched[c['clause_id']])}"
                  f" | referent: {r['referent_class']}{hon} (subject '{r['subject_text']}', {r['subject_source']})")


if __name__ == "__main__":
    main()
