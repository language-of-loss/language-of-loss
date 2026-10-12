"""Eligibility detector (Plan v3 P8b): is an experiencer framing forced by the grammar or chosen by the writer?"""
import argparse
import csv
import json
import os
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import flags as F
import referents as R

EN_NONNOM = {"impersonal", "stimulus", "body_part"}

HI_RULES = [
    ("HI-F01", ["याद+आ"], "forced", "none (याद करना = deliberate recall, not 'miss')",
     "involuntary remembering/missing has only the dative frame", "brief; F1"),
    ("HI-F02", ["लग"], "forced", "none for 'seem / feel that' (मैं सोचता हूँ = think)",
     "bare लगना with an experiencer, incl. अच्छा/बुरा लगना; noun+लग rows below override", "brief"),
    ("HI-F03", ["मिल"], "forced", "मैंने पाया (formal, rare)",
     "receive / come upon: recipient is dative; noun rows (सुकून+मिल) override", "brief"),
    ("HI-F04", ["चाहिए"], "forced", "none", "need/should: only dative", "brief"),
    ("HI-F05", ["पता+हो", "पता+चल", "मालूम+हो", "पता+लग"], "forced", "मैं जानता हूँ (जानना)",
     "know/come to know; brief marks it forced, but जानना is a nominative near-synonym: check", "brief"),
    ("HI-F06", ["नींद+आ"], "forced", "none (मैं सो नहीं पाया = could not sleep, different frame)",
     "sleep coming to someone", "F1"),
    ("HI-F07", ["कमी+खल", "खल", "अखर", "भा", "सूझ", "चुभ", "सता"], "forced", "none",
     "experiencer-object verbs with no nominative-experiencer counterpart", "F1; constructions.yaml feel_verb_stems"),
    ("HI-F08", ["INF+पड"], "forced", "none", "obligation (मुझे जाना पड़ा)", "standard Hindi grammar"),
    ("HI-F09", ["INF+हो"], "forced", "none", "obligation/plan (मुझे जाना है)", "standard Hindi grammar"),
    ("HI-F10", ["जरूरत+हो", "आवश्यकता+हो"], "forced", "none (चाहना = want)", "need", "standard Hindi grammar"),
    ("HI-F11", ["होश+आ"], "forced", "none", "regain consciousness", "standard Hindi grammar"),
    ("HI-F12", [f"{n}+हो" for n in ("कैंसर", "कोरोना", "कोविड", "टीबी", "अटैक", "दौरा", "लकवा", "निमोनिया",
                                       "पीलिया", "मधुमेह", "डायबिटीज", "संक्रमण", "हार्ट-अटैक")] + ["दौरा+पड"],
     "forced", "'X से पीड़ित था' is a different register, not the same predicate",
     "named illness befalling someone (उन्हें कैंसर हुआ)", "constructions.yaml body_state_words"),
    ("HI-C01", ["दुख+हो", "दुःख+हो"], "chosen", "मैं दुखी हूँ / हुआ", "", "brief; F1"),
    ("HI-C02", ["डर+लग", "डर+हो", "भय+लग", "भय+हो"], "chosen", "मैं डर गया / डरा / भयभीत हुआ", "", "brief"),
    ("HI-C03", ["रोना+आ", "रुलाई+आ"], "chosen", "मैं रोया / रो पड़ा", "chosen pair: मुझे रोना आया ~ मैं रोया",
     "F1 (मैं रोया); Methodology v3; decision E3 (2026-10-10)"),
    ("HI-C04", ["हँसी+आ", "हंसी+आ"], "chosen", "मैं हँसा", "chosen pair: मुझे हँसी आई ~ मैं हँसा",
     "standard Hindi grammar; decision E3 (2026-10-10)"),
    ("HI-C05", ["गुस्सा+आ", "गुस्सा+हो", "क्रोध+आ", "क्रोध+हो"], "chosen", "मैं गुस्सा / नाराज़ / क्रोधित हुआ",
     "", "standard Hindi grammar"),
    ("HI-C06", ["चिंता+हो", "फिक्र+हो"], "chosen", "मैं चिंतित था / चिंता करता था", "", "standard Hindi grammar"),
    ("HI-C07", ["खुशी+हो"], "chosen", "मैं खुश हुआ / हूँ", "chosen pair: मुझे खुशी हुई ~ मैं खुश हूँ",
     "standard Hindi grammar; same treatment as decision E3 (2026-10-10) (not in the investigators' list; the rule was applied)"),
    ("HI-C08", ["शर्म+आ", "शर्म+लग"], "chosen", "मैं शर्मिंदा हूँ / हुआ / शर्माया",
     "chosen pair: मुझे शर्म आई ~ मैं शर्मिंदा हूँ", "standard Hindi grammar; decision E3 (2026-10-10)"),
    ("HI-C09", ["परेशानी+हो"], "chosen", "मैं परेशान हुआ", "", "standard Hindi grammar"),
    ("HI-C10", ["हैरानी+हो", "आश्चर्य+हो"], "chosen", "मैं हैरान / चकित हुआ", "", "standard Hindi grammar"),
    ("HI-C11", ["उदासी+हो", "उदासी+छा"], "chosen", "मैं उदास था", "", "standard Hindi grammar"),
    ("HI-C12", ["बेचैनी+हो", "घबराहट+हो"], "chosen", "मैं बेचैन था / घबरा गया", "", "standard Hindi grammar"),
    ("HI-C13", ["पछतावा+हो"], "chosen", "मैं पछताता हूँ / पछताया",
     "chosen pair: मुझे पछतावा है / हुआ ~ मैं पछताता हूँ", "standard Hindi grammar; decision E3 (2026-10-10)"),
    ("HI-C17", ["अकेलापन+लग", "अकेलापन+हो"], "chosen", "मैं अकेला / अकेली हूँ",
     "chosen pair: मुझे अकेलापन लगा / महसूस हुआ ~ मैं अकेला हूँ", "decision E3 (2026-10-10) (was HI-R05 review)"),
    ("HI-C18", ["सदमा+लग", "सदमा+हो"], "chosen", "मैं सदमे में हूँ / था",
     "chosen pair: मुझे सदमा लगा ~ मैं सदमे में हूँ", "decision E3 (2026-10-10) (was HI-R03 review)"),
    ("HI-C14", ["संतोष+हो"], "chosen", "मैं संतुष्ट था", "", "standard Hindi grammar"),
    ("HI-C15", ["समझ+आ"], "chosen", "मैं समझा / समझ गया", "", "standard Hindi grammar"),
    ("HI-C16", [f"{w}+लग" for w in ("अच्छा", "बुरा", "अजीब", "खराब", "सूना", "अकेला", "उदास", "दुख", "दुःख", "खाली",
                                     "भारी", "ठीक")], "chosen",
     "मैंने अच्छा / बुरा / अजीब महसूस किया; मैं उदास / दुखी था",
     "feel + emotion complement: मुझे बुरा लगा ~ I felt bad, both chosen (decision E2, 2026-10-10)",
     "decision E2 (code review 2026-10)"),
    ("HI-R01", ["महसूस+हो", "एहसास+हो", "अहसास+हो"], "review", "मैंने महसूस किया (ergative, volitional)",
     "हो/कर alternation is regular; is the volitional frame 'the same meaning'?", ""),
    ("HI-R02", ["अफसोस+हो", "गम+हो", "ग्लानि+हो", "मोह+हो"], "review", "मैं अफ़सोस करता हूँ / ग़मगीन (rare)",
     "nominative alternative exists only marginally", ""),
    ("HI-R03", ["धक्का+लग", "झटका+लग"], "review", "मैं सदमे में था",
     "nominative + locative alternative; same meaning?", ""),
    ("HI-R04", ["पसंद+हो", "पसंद+आ", "प्यार+हो"], "review", "मैं पसंद / प्यार करता हूँ",
     "प्यार हो जाना = fall in love (inchoative) vs प्यार करना = love", ""),
    ("HI-R05", ["तकलीफ+हो", "दर्द+हो", "पीडा+हो", "कष्ट+हो"], "review",
     "मैं अकेला / दर्द में / तकलीफ़ में था", "physical vs emotional pain; locative alternative", ""),
    ("HI-R06", ["भूख+लग", "प्यास+लग", "बीमारी+हो", "बुखार+हो", "चोट+लग", "थकान+हो", "सर्दी+हो", "खांसी+हो",
                "खाँसी+हो", "जुकाम+हो"], "review", "मैं भूखा / बीमार / थका / घायल था",
     "bodily states with an adjectival nominative counterpart", ""),
    ("HI-R07", ["विश्वास+हो", "यकीन+हो", "भरोसा+हो", "उम्मीद+हो", "आशा+हो", "इंतजार+हो"], "review",
     "मैं विश्वास / उम्मीद / इंतज़ार करता हूँ", "cognitive states, karna alternative", ""),
    ("HI-R08", ["चैन+मिल", "सुकून+मिल", "तसल्ली+मिल", "तसल्ली+हो", "शांति+मिल"], "review",
     "मैं शांत / आश्वस्त हुआ", "relief: receive-frame vs adjective", ""),
    ("HI-R09", ["आ"], "review", "", "bare आना with a dative: know (हिंदी आती है, forced) vs motion; parse cannot tell", ""),
    ("HI-R10", ["दिख", "दिखाई+दे", "सुनाई+दे"], "review", "मैंने देखा / सुना (ergative, volitional)",
     "perception: non-volitional dative vs volitional ergative", ""),
    ("HI-R11", ["हो", "रह", "पड", "छा", "चल"], "review", "",
     "light verb with a dative but no recognised noun: inspect", ""),
    ("HI-R12", ["याद+हो"], "review", "मैं याद रखता हूँ / मुझे याद आता है (dative too)",
     "मुझे याद है = remember (state); compare याद आना (HI-F01, forced)", ""),
]
HI_PRED = {k: (rid, dec) for rid, keys, dec, *_ in HI_RULES for k in keys}
HI_NON_EMOTION_RULES = {"HI-F02", "HI-F03", "HI-F04", "HI-F05", "HI-F08", "HI-F09", "HI-F10", "HI-C15", "HI-R09",
                        "HI-R10"}
HI_NON_EMOTION = {k for rid, keys, *_ in HI_RULES if rid in HI_NON_EMOTION_RULES for k in keys} | {"सूझ"}

HI_NOM_RULES = [
    ("HI-N01", ["दुखी+हो", "दुःखी+हो"], "दुख+हो", "same root दुख"),
    ("HI-N02", ["उदास+हो"], "उदासी+हो", "same root उदास"),
    ("HI-N03", ["परेशान+हो"], "परेशानी+हो", "same root परेशान"),
    ("HI-N04", ["अकेला+हो", "अकेली+हो", "अकेले+हो"], "अकेलापन+लग", "same root अकेला; dative row HI-C17 (decision E3)"),
    ("HI-N05", ["खुश+हो"], "खुशी+हो", "same root खुश"),
    ("HI-N06", ["बेचैन+हो"], "बेचैनी+हो", "same root बेचैन"),
    ("HI-N07", ["चिंतित+हो"], "चिंता+हो", "same root चिंता"),
    ("HI-N08", ["हैरान+हो"], "हैरानी+हो", "same root हैरान"),
    ("HI-N09", ["शर्मिंदा+हो"], "शर्म+आ", "same root शर्म"),
    ("HI-N10", ["भयभीत+हो"], "भय+लग", "same root भय"),
    ("HI-N11", ["संतुष्ट+हो"], "संतोष+हो", "conventional pair named in HI-C14"),
    ("HI-N12", ["क्रोधित+हो"], "क्रोध+आ", "same root क्रोध"),
    ("HI-N13", ["डर"], "डर+लग", "X लगना ~ X-ना (डरा हुआ = participle of डरना)"),
    ("HI-N14", ["रो"], "रोना+आ", "conventional pair named in HI-C03 (मुझे रोना आया ~ मैं रोया)"),
    ("HI-N15", ["घबरा"], "घबराहट+हो", "same root घबरा"),
    ("HI-N16", ["हँस", "हंस"], "हँसी+आ", "conventional pair named in HI-C04"),
    ("HI-N17", ["पछता"], "पछतावा+हो", "same root पछता"),
    ("HI-N18", ["शर्मा"], "शर्म+आ", "same root शर्म"),
    ("HI-N19", ["तडप"], None, "no dative frame with the same meaning"),
    ("HI-N20", ["सह"], None, "endure: agentive only"),
    ("HI-N21", ["टूट"], None, "break down (टूट गया, टूटा हुआ): no dative frame; person subject only"),
    ("HI-N22", ["याद+कर"], "याद+आ", "twin is HI-F01 (forced: याद करना = deliberate recall, not 'miss'), so "
                                      "याद करना is forced_nominative; the generic याद होना twin (HI-R12) is not used"),
]
HI_KAR_TWIN_RULES = {f"HI-C{i:02d}" for i in range(1, 16)} | {"HI-R01", "HI-R02", "HI-R03", "HI-R04", "HI-R07"}
HI_KAR_NOT_IDIOM = {"दुख", "दुःख", "डर", "भय", "खुशी", "परेशानी", "हैरानी", "उदासी", "बेचैनी", "घबराहट", "ग्लानि",
                    "सदमा", "याद"}
HI_NOM_RULES += [(f"HI-NK-{HI_PRED[k][0][3:]}", [f"{k[:-3]}+कर"], k, "X करना ~ X होना (same root)")
                 for k in HI_PRED if k.endswith("+हो") and HI_PRED[k][0] in HI_KAR_TWIN_RULES
                 and k[:-3] not in HI_KAR_NOT_IDIOM]
NOM_DECISION = {"chosen": "chosen_nominative", "forced": "forced_nominative", "review": "review"}


def nom_decision(twin):
    return "forced_nominative" if twin is None else NOM_DECISION[HI_PRED[twin][1]]


HI_NOM = {k: (rid, twin, nom_decision(twin)) for rid, keys, twin, _ in HI_NOM_RULES for k in keys}
HI_DATIVE_TWIN = {}
for _rid, _keys, _twin, _ in HI_NOM_RULES:
    if _twin:
        HI_DATIVE_TWIN.setdefault(_twin, _rid)
DATIVE_DECISION = {"forced": "forced_dative", "chosen": "chosen_dative", "review": "review"}

HI_EXP_VERBS = {"हो", "आ", "लग", "मिल", "पड", "रह", "चाहिए", "खल", "अखर", "भा", "सूझ", "चुभ", "सता", "दिख", "छा",
                "चल", "दे"}
HI_COPULA = {"है", "था", "हो", "होना"}
HI_LEMMA_STEM = {"होना": "हो", "है": "हो", "था": "हो", "हो": "हो", "आना": "आ", "लगना": "लग", "मिलना": "मिल",
                 "पडना": "पड", "रहना": "रह", "चाहिए": "चाहिए", "चाहिये": "चाहिए", "खलना": "खल", "अखरना": "अखर",
                 "भाना": "भा", "सूझना": "सूझ", "चुभना": "चुभ", "सताना": "सता", "दिखना": "दिख", "छाना": "छा",
                 "चलना": "चल", "देना": "दे"}
LAGANA_TRANSITIVE = {"लगाया", "लगाई", "लगायी", "लगाए", "लगाये", "लगाता", "लगाती", "लगाते", "लगाना", "लगाकर", "लगाओ"}
NOUN_DEPRELS = ("compound", "nsubj", "obj", "xcomp", "amod", "obl")
SITE_DEPRELS_PRON = {"nsubj", "iobj", "obl"}
SITE_DEPRELS_NOUN = {"nsubj", "iobj"}

EN_RULES = [
    ("EN-V-SUBJ", "SUBJ", "rule", ["miss", "grieve", "mourn", "cry", "weep", "sob", "wail", "fear", "regret", "love",
                                   "adore", "worry", "suffer", "long", "yearn", "hate", "dread", "despair", "panic",
                                   "ache", "laugh", "rejoice", "resent", "pine", "cherish", "envy", "sorrow"]),
    ("EN-V-OBJ", "OBJ", "rule", ["devastate", "sadden", "haunt", "crush", "shatter", "overwhelm", "consume", "scare",
                                 "frighten", "terrify", "upset", "shock", "hurt", "comfort", "console", "trouble", "bother",
                                 "torment", "pain", "gut", "surprise", "anger", "depress", "wreck", "distress", "sting",
                                 "relieve", "traumatize", "traumatise"]),
    ("EN-FEEL", "FEEL", "rule", ["feel", "seem"]),
    ("EN-ADJ", "ADJ", "rule", ["sad", "unhappy", "angry", "afraid", "scared", "frightened", "terrified", "devastated",
                               "heartbroken", "numb", "lonely", "guilty", "happy", "glad", "grateful", "thankful",
                               "broken", "shattered", "shocked", "depressed", "anxious", "worried", "sorry",
                               "empty", "miserable", "hopeless", "helpless", "bitter", "ashamed", "relieved",
                               "overwhelmed", "distraught", "inconsolable", "proud", "jealous", "nervous", "restless",
                               "furious", "grief-stricken", "sorrowful", "joyful", "crushed", "gutted"]),
    ("EN-STIM-ADJ", "STIM_ADJ", "rule", ["painful", "heartbreaking", "devastating", "unbearable", "scary", "frightening", "depressing", "upsetting", "agonizing", "agonising",
                                         "excruciating", "traumatic", "traumatizing", "shocking", "terrifying",
                                         "overwhelming", "saddening", "shattering", "crushing"]),
    ("EN-R01", "ADJ", "review", ["hard", "difficult", "tough", "strange", "surreal", "weird", "lost", "fine", "okay",
                                 "raw", "alone", "calm", "peaceful"]),
    ("EN-R02", "OBJ", "review", ["kill", "hit", "strike", "destroy", "move", "touch", "break", "tear", "eat"]),
]
EN_PRED = {lem: (rid, cls, status) for rid, cls, status, lems in EN_RULES for lem in lems}
assert len(EN_PRED) == sum(len(r[3]) for r in EN_RULES), "an English predicate is in two rows"
EN_TWINS = [
    ("EN-T01", ["devastate", "devastated", "devastating"], "I was devastated", "it devastated me", ""),
    ("EN-T02", ["feel"], "I felt lost", "it felt like the end", "brief example; same verb"),
    ("EN-T03", ["seem"], "I seemed fine", "it seemed unreal", "same verb"),
    ("EN-T04", ["hurt"], "I hurt", "it hurt me", ""),
    ("EN-T05", ["sad", "sadden", "saddening"], "I was sad / saddened", "it saddened me", "same root sad"),
    ("EN-T06", ["scare", "scared", "scary"], "I was scared", "it scared me / it was scary", ""),
    ("EN-T07", ["frighten", "frightened", "frightening"], "I was frightened", "it frightened me", ""),
    ("EN-T08", ["terrify", "terrified", "terrifying"], "I was terrified", "it terrified me", ""),
    ("EN-T09", ["shock", "shocked", "shocking"], "I was shocked", "it shocked me", ""),
    ("EN-T10", ["upset", "upsetting"], "I was upset", "it upset me", ""),
    ("EN-T11", ["crush", "crushed", "crushing"], "I was crushed", "it crushed me", ""),
    ("EN-T12", ["shatter", "shattered", "shattering"], "I was shattered", "it shattered me", ""),
    ("EN-T13", ["overwhelm", "overwhelmed", "overwhelming"], "I was overwhelmed", "it overwhelmed me", ""),
    ("EN-T14", ["gut", "gutted"], "I was gutted", "it gutted me", ""),
    ("EN-T15", ["depress", "depressed", "depressing"], "I was depressed", "it depressed me", ""),
    ("EN-T16", ["pain", "painful"], "I was pained", "it pained me / it was painful", ""),
    ("EN-T17", ["haunt"], "I was haunted", "it haunted me", ""),
    ("EN-T18", ["trouble"], "I was troubled", "it troubled me", ""),
    ("EN-T19", ["bother"], "I was bothered", "it bothered me", ""),
    ("EN-T20", ["torment"], "I was tormented", "it tormented me", ""),
    ("EN-T21", ["surprise"], "I was surprised", "it surprised me", ""),
    ("EN-T22", ["angry", "anger"], "I was angry", "it angered me", "same root anger"),
    ("EN-T23", ["wreck"], "I was wrecked", "it wrecked me", ""),
    ("EN-T24", ["distress"], "I was distressed", "it distressed me", ""),
    ("EN-T25", ["comfort"], "I was comforted", "it comforted me", ""),
    ("EN-T26", ["console"], "I was consoled", "it consoled me", ""),
    ("EN-T27", ["consume"], "I was consumed (by grief)", "grief consumed me", ""),
    ("EN-T28", ["sting"], "I was stung", "it stung (me)", ""),
    ("EN-T29", ["heartbroken", "heartbreaking"], "I was heartbroken", "it was heartbreaking", "same root heartbreak"),
    ("EN-T30", ["worry", "worried"], "I worried / was worried", "it worried me", ""),
    ("EN-T31", ["grieve"], "I grieved", "it grieves me", "the object frame is formal/rare but grammatical"),
    ("EN-T32", ["relieve", "relieved"], "I was relieved", "it relieved me", ""),
    ("EN-T33", ["traumatize", "traumatise", "traumatic", "traumatizing"], "I was traumatized", "it was traumatic", ""),
    ("EN-T34", ["numb"], "I was numb", "it numbed me", ""),
    ("EN-T35", ["ache"], "I ache (for her)", "my heart aches", "nominative <-> body-part subject"),
    ("EN-T36", ["broken"], "I was broken", "it broke me", "the verb break itself stays review (EN-R02)"),
]
EN_TWIN = {k: rid for rid, keys, *_ in EN_TWINS for k in keys}
assert len(EN_TWIN) == sum(len(t[1]) for t in EN_TWINS), "an English predicate is in two twin rows"
assert set(EN_TWIN) <= set(EN_PRED), f"twin keys the detector never produces: {set(EN_TWIN) - set(EN_PRED)}"

ASYM = "asymmetric by construction"
CROSS_LANG_EQUIVALENTS = [
    ("अच्छा+लग", "feel", "consistent"), ("बुरा+लग", "feel", "consistent"), ("अजीब+लग", "feel", "consistent"),
    ("याद+आ", "miss", "consistent"), ("दुख+हो", "sad", "consistent"), ("डर+लग", "scared", "consistent"),
    ("गुस्सा+आ", "angry", "consistent"), ("चिंता+हो", "worry", "consistent"),
    ("सदमा+लग", "shocked", "consistent"),
    ("रोना+आ", "cry", ASYM), ("हँसी+आ", "laugh", ASYM), ("खुशी+हो", "happy", ASYM),
    ("पछतावा+हो", "regret", ASYM), ("शर्म+आ", "ashamed", ASYM), ("अकेलापन+लग", "lonely", ASYM),
]


def hi_decision_class(key):
    if key in HI_NON_EMOTION:
        return "NA"
    if key in HI_PRED:
        return HI_PRED[key][1]
    if key in HI_NOM:
        return HI_NOM[key][2].split("_")[0]
    return "review"


def en_decision_class(lemma):
    if lemma not in EN_PRED or EN_PRED[lemma][2] == "review":
        return "review"
    return "chosen" if lemma in EN_TWIN else "forced"


EN_IT = {"it", "this", "that", "there"}
EN_PERSON_PRON = {"i", "we", "you", "he", "she", "they", "me", "us", "him", "her", "them", "one", "everyone",
                  "everybody", "someone", "somebody", "nobody", "who"}
EN_BODY = {"heart", "chest", "soul", "stomach", "gut", "mind", "eye", "eyes", "throat", "body", "bone", "bones",
           "insides", "nerve", "nerves", "head", "hand", "hands", "spirit"}
EN_PERSON_NOUNS = set(F.load_spec()["filters"]["animate_subject"]["kin"]) | {
    "family", "people", "person", "child", "children", "kids", "man", "woman", "boy", "girl", "baby", "parents",
    "siblings", "relatives", "friends", "everyone", "nobody", "doctor", "nurse", "grandparents"}
EN_EXPERIENCER_OBJ = EN_PERSON_PRON | {"myself", "ourselves", "himself", "herself", "themselves"}


def inventory_rows():
    rows = []
    eq_hi = {h: f"en: {e} ({st})" for h, e, st in CROSS_LANG_EQUIVALENTS}
    eq_en = {}
    for h, e, st in CROSS_LANG_EQUIVALENTS:
        eq_en.setdefault(e, []).append(f"hi: {h} ({st})")
    for rid, keys, dec, alt, why, src in HI_RULES:
        for k in keys:
            d = "NA (non-emotion, decision E1)" if k in HI_NON_EMOTION else DATIVE_DECISION[dec]
            rows.append(dict(predicate=k, lang="hi", site="dative", decision=d, rule_id=rid,
                             twin="", alternative=alt, rule=why, source=src or "machine judgement (2026-10-09)",
                             equivalent=eq_hi.get(k, "")))
    for rid, keys, twin, why in HI_NOM_RULES:
        for k in keys:
            alt = f"{twin} ({HI_PRED[twin][0]}, {HI_PRED[twin][1]})" if twin else "none"
            rows.append(dict(predicate=k, lang="hi", site="nominative", decision=HI_NOM[k][2], rule_id=rid, twin=twin or "",
                             alternative=alt, rule=why, source="machine judgement (2026-10-10)",
                             equivalent=eq_hi.get(k, "")))
    notes = {"SUBJ": "nominative if a person is the subject; impersonal if it/this/that",
             "OBJ": "stimulus subject + experiencer object -> stimulus; passive (I was devastated) -> nominative; "
                    "it/this/that subject -> impersonal",
             "FEEL": "person subject -> nominative (I felt like); it/this/that or inanimate subject -> impersonal",
             "ADJ": "person subject -> nominative; it/this/that or inanimate subject -> impersonal",
             "STIM_ADJ": "the subject is the cause, never the experiencer -> impersonal"}
    twin_row = {k: t for t in EN_TWINS for k in t[1]}
    for rid, cls, status, lems in EN_RULES:
        for lem in lems:
            why = notes[cls] if status == "rule" else f"is this an emotion predicate here? ({notes[cls]})"
            t = twin_row.get(lem)
            if status == "review":
                dec, twin, alt, src = "review", t[0] if t else "", "", "machine judgement (2026-10-09)"
            elif t:
                dec, twin = "chosen_nominative / chosen_impersonal (by construction)", t[0]
                alt = f"{t[2]} <-> {t[3]}" + (f" ({t[4]})" if t[4] else "")
                src = ("machine judgement (2026-10-10): English twin pair, same lexical root, same rule as "
                       "HI_NOM_RULES (EN_TWINS)")
            else:
                dec, twin, alt = ("forced_nominative (nominative frame only)" if cls in ("SUBJ", "ADJ")
                                  else "forced_nominative / forced_impersonal (by construction)"), "", "none"
                src = "machine judgement (2026-10-10): no same-root twin in English (EN_TWINS)"
            rows.append(dict(predicate=lem, lang="en", site="clause", decision=dec, rule_id=rid, twin=twin,
                             alternative=alt, rule=why, source=src, equivalent="; ".join(eq_en.get(lem, []))))
    return rows


def load_sentences(tokens_path, clause_meta):
    sentences, clause_ids = defaultdict(dict), defaultdict(list)
    with open(tokens_path, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if row["clause_id"] not in clause_meta:
                continue
            rid, si = clause_meta[row["clause_id"]]
            ti = int(row["token_index"])
            sentences[(rid, si)][ti] = dict(token_index=ti, token=row["token"], lemma=row["lemma"], upos=row["upos"],
                                            feats=row["feats"], head=int(row["head"]), deprel=row["deprel"])
            clause_ids[row["clause_id"]].append(ti)
    return sentences, clause_ids


def sentence_meta(clauses):
    return {c["clause_id"]: (c["record_id"], c["sent_index"]) for c in clauses}


def load_recovered(referents_arg, inp):
    if referents_arg == "":
        print("note: running without referents.csv (--referents ''): no recovered subjects, no referent-based "
              "relational sites")
        return {}
    ref_path = Path(referents_arg or Path(inp).with_name("referents.csv"))
    if not ref_path.exists():
        sys.exit(f"{ref_path} not found: run referents.py first, or pass --referents '' to run without it")
    with open(ref_path, encoding="utf-8", newline="") as fh:
        return {r["clause_id"]: r for r in csv.DictReader(fh)}


def children(sentence):
    kids = defaultdict(list)
    for i in sorted(sentence):
        kids[sentence[i]["head"]].append(sentence[i])
    return kids


def norm(s):
    return F.denukta(F.bare(s or ""))


def hi_verb_stem(w, kids):
    form, lemma = norm(w["token"]), norm(w["lemma"])
    if lemma == "लगाना":
        transitive = form in LAGANA_TRANSITIVE or any(norm(c["lemma"]) in ("देना", "लेना") and c["deprel"] == "compound"
                                                      for c in kids[w["token_index"]])
        return None if transitive or not form.startswith("लग") else "लग"
    if form.startswith("चाहिए") or form.startswith("चाहिये"):
        return "चाहिए"
    if lemma in HI_LEMMA_STEM:
        return HI_LEMMA_STEM[lemma]
    if lemma.endswith("ना"):
        return lemma[:-2]
    return lemma or None


def hi_predicate(head, kids):
    hk = kids[head["token_index"]]
    if head["upos"] in ("NOUN", "ADJ", "PROPN") and any(c["deprel"] == "cop" for c in hk):
        noun = norm(head["lemma"]) or norm(head["token"])
        for key in (f"{noun}+हो", f"{norm(head['token'])}+हो"):
            if key in HI_PRED:
                return key, "हो"
        return f"{noun}+हो", "हो"
    if head["upos"] == "VERB" and "VerbForm=Inf" in head["feats"]:
        for c in hk:
            if c["deprel"].startswith("aux"):
                st = hi_verb_stem(c, kids)
                if st == "पड":
                    return "INF+पड", "पड"
                if st == "हो" and norm(c["token"]) in HI_COPULA | {"होगा", "होगी", "थे", "थी", "हैं"}:
                    return "INF+हो", "हो"
    if head["upos"] not in ("VERB", "AUX"):
        return None, None
    form = norm(head["token"])
    if form in ("दिखाई", "सुनाई") and any(norm(c["lemma"]) == "देना" for c in hk):
        return f"{form}+दे", "दे"
    stem = hi_verb_stem(head, kids)
    if stem == "लग":
        for c in hk:
            if c["upos"] == "VERB" and "VerbForm=Inf" in c["feats"] and norm(c["token"]).endswith("ने"):
                inner = hi_predicate(c, kids)
                if inner[0] is not None:
                    return inner
    if stem not in HI_EXP_VERBS:
        return None, None
    nouns = [c for c in hk if c["deprel"] in NOUN_DEPRELS and c["upos"] in ("NOUN", "ADJ", "VERB", "PROPN")]
    for c in nouns:
        for n in (norm(c["lemma"]), norm(c["token"])):
            if f"{n}+{stem}" in HI_PRED:
                return f"{n}+{stem}", stem
    if stem == "दे":
        return None, None
    nominals = sorted((c for c in nouns if c["upos"] in ("NOUN", "ADJ")), key=lambda c: c["deprel"] != "compound")
    if nominals and stem not in ("लग", "मिल", "चाहिए"):
        return f"{norm(nominals[0]['lemma']) or norm(nominals[0]['token'])}+{stem}", stem
    return stem, stem


def hi_site_word(w, kids):
    if F.bare(w["token"]) in HI_DATIVE_PRONOUNS:
        return F.bare(w["token"])
    if w["upos"] in ("NOUN", "PROPN", "PRON", "DET") and any(c["deprel"] == "case" and F.bare(c["token"]) == "को"
                                                             for c in kids[w["token_index"]]):
        return f"{F.bare(w['token'])} को"
    return None


HI_DATIVE_PRONOUNS = set(F.load_spec()["dative"]["pronouns"])


def has_ergative_subject(head, kids):
    for c in kids[head["token_index"]]:
        if c["deprel"].startswith("nsubj") and ("Case=Acc,Erg" in c["feats"] or "Erg" in c["feats"].split("|")[0]
                                                or F.bare(c["token"]).endswith("ने")
                                                or any(F.bare(g["token"]) == "ने" for g in kids[c["token_index"]])):
            return True
    return False


HI_NOM_PRONOUNS = ({w for w in R.PRONOUNS["hi"] if w not in HI_DATIVE_PRONOUNS and w != "मुझ"} | R.RELATIVE
                   | {"तूं"}) - {"यह", "इसने"}
HI_PERSON_NOUNS = {F.denukta(w) for w in R.KIN["hi"] | R.HUMAN | R.COMMUNITY | R.GOD}
HI_NOM_LEMMA_FIX = {"सहाना": "सह"}
RECOVERED_SOURCES = {"inherited", "agreement", "antecedent"}


def hi_nom_predicate(head, kids):
    hk = kids[head["token_index"]]
    lemma, form = norm(head["lemma"]), norm(head["token"])
    if head["upos"] in ("ADJ", "NOUN", "VERB") and any(c["deprel"] == "cop" for c in hk):
        for a in (lemma, form):
            if f"{a}+हो" in HI_NOM:
                return f"{a}+हो"
    if head["upos"] not in ("VERB", "AUX"):
        return None
    stem = HI_NOM_LEMMA_FIX.get(lemma) or hi_verb_stem(head, kids)
    if stem in ("हो", "रह"):
        for c in hk:
            if c["deprel"] in ("compound", "xcomp", "amod", "advmod") and c["upos"] in ("ADJ", "NOUN"):
                for a in (norm(c["lemma"]), norm(c["token"])):
                    if f"{a}+हो" in HI_NOM:
                        return f"{a}+हो"
        return None
    if stem == "लग":
        for c in hk:
            if c["upos"] == "VERB" and "VerbForm=Inf" in c["feats"] and norm(c["token"]).endswith("ने"):
                return hi_nom_predicate(c, kids)
        return None
    if stem == "कर":
        for c in hk:
            if c["deprel"] in ("compound", "obj") and c["upos"] in ("NOUN", "ADJ", "PROPN"):
                for a in (norm(c["lemma"]), norm(c["token"])):
                    if f"{a}+कर" in HI_NOM:
                        return f"{a}+कर"
        return None
    if stem == "टूट" and any(c["deprel"] in ("aux", "compound") and hi_verb_stem(c, kids) == "पड" for c in hk):
        return None
    return stem if stem in HI_NOM else None


def hi_nom_subject(head, kids):
    for c in kids[head["token_index"]]:
        if not c["deprel"].startswith("nsubj"):
            continue
        cases = {F.bare(g["token"]) for g in kids[c["token_index"]] if g["deprel"] == "case"}
        t = F.bare(c["token"])
        if t in HI_DATIVE_PRONOUNS or cases - {"ने"}:
            continue
        if t in HI_NOM_PRONOUNS or c["upos"] == "PROPN" or norm(c["lemma"]) in HI_PERSON_NOUNS \
                or norm(c["token"]) in HI_PERSON_NOUNS:
            return t, "overt"
        return None, "nonperson"
    for w in [head] + [c for c in kids[head["token_index"]] if c["deprel"] in ("aux", "cop", "aux:pass")]:
        if "VerbForm=Fin" in w["feats"] and ("Person=1" in w["feats"] or "Person=2" in w["feats"]):
            return "∅", "agreement"
    return None, None


def classify_hi_nominative(sentence, kids, own_heads, skip_heads, recovered=None):
    rows, na_rule = [], None
    for h in sorted(own_heads):
        if h in skip_heads:
            continue
        pred = hi_nom_predicate(sentence[h], kids)
        if pred is None:
            continue
        subj, source = hi_nom_subject(sentence[h], kids)
        if subj is None and source is None and recovered and recovered.get("subject_source") in RECOVERED_SOURCES \
                and recovered.get("referent_class") != "impersonal":
            subj, source = f"∅→{recovered.get('subject_text') or '?'}", recovered["subject_source"]
        if subj is None:
            na_rule = "HI-NA-NOM-NONPERSON" if source == "nonperson" else "HI-NA-NOM-NOSUBJ"
            continue
        rid, twin, dec = HI_NOM[pred]
        rows.append(dict(site=subj, predicate=pred, decision=dec, rule_id=rid, subject_source=source,
                         construction="nominative", twin_rule=HI_PRED[twin][0] if twin else ""))
    return rows, na_rule


def classify_hi(clause_ids, sentence, own_heads, recovered=None):
    kids = children(sentence)
    sites, objects, dative_heads, nonemo = [], 0, set(), []
    for i in sorted(clause_ids):
        w = sentence[i]
        site = hi_site_word(w, kids)
        if site is None:
            continue
        is_pron = F.bare(w["token"]) in HI_DATIVE_PRONOUNS
        head = sentence.get(w["head"])
        pred = None
        if head is not None and w["deprel"] in SITE_DEPRELS_PRON and not has_ergative_subject(head, kids):
            pred, _ = hi_predicate(head, kids)
            if not is_pron and w["deprel"] not in SITE_DEPRELS_NOUN and not (pred in HI_PRED and "+" in pred):
                pred = None
        if pred is None and is_pron and w["deprel"] in ("obl", "iobj") and head is not None \
                and head["deprel"] in ("advcl", "xcomp") and head["token_index"] not in own_heads:
            for h in sorted(own_heads):
                p, _ = hi_predicate(sentence[h], kids)
                if p in HI_PRED and HI_PRED[p][1] != "review" and not has_ergative_subject(sentence[h], kids):
                    pred, head = p, sentence[h]
                    break
        if pred is None:
            objects += 1
            continue
        if pred in HI_NON_EMOTION:
            nonemo.append(pred)
            continue
        if pred in HI_PRED:
            rid, dec = HI_PRED[pred]
        else:
            rid, dec = "HI-UNL", "review"
        dative_heads.add(head["token_index"])
        sites.append(dict(site=site, predicate=pred, decision=DATIVE_DECISION[dec], rule_id=rid, subject_source="",
                          construction="dative", twin_rule=HI_DATIVE_TWIN.get(pred, "")))
    nom, nom_na = classify_hi_nominative(sentence, kids, own_heads, dative_heads, recovered)
    sites += nom
    if not sites:
        if nonemo:
            sites.append(dict(site="", predicate=nonemo[0], decision="NA", rule_id="HI-NA-NONEMO",
                              subject_source="", construction="", twin_rule=""))
        else:
            sites.append(dict(site="", predicate="", decision="NA", rule_id="HI-NA-OBJ" if objects else nom_na or "HI-NA",
                              subject_source="", construction="", twin_rule=""))
    return sites


def en_lemma(w, kids):
    form, lemma = w["token"].lower(), (w["lemma"] or "").lower()
    if form in EN_PRED and EN_PRED[form][1] in ("ADJ", "STIM_ADJ") and (
            w["upos"] == "ADJ" or any(c["deprel"] in ("cop", "aux:pass", "nsubj:pass") for c in kids[w["token_index"]])):
        return form
    return lemma


def en_subject(w, sentence, kids):
    seen = set()
    while w is not None and w["token_index"] not in seen:
        seen.add(w["token_index"])
        for c in kids[w["token_index"]]:
            if c["deprel"] in ("nsubj", "nsubj:pass", "expl", "csubj"):
                return c
        if w["deprel"] in ("conj", "xcomp"):
            w = sentence.get(w["head"])
        else:
            return None
    return None


def en_person(word, kids):
    t = word["token"].lower()
    if t in EN_PERSON_PRON or word["upos"] == "PROPN" or t in EN_PERSON_NOUNS or word["lemma"].lower() in EN_PERSON_NOUNS:
        return True
    return word["upos"] in ("NUM", "PRON", "DET") and any(c["token"].lower() in EN_PERSON_PRON | EN_PERSON_NOUNS
                                                          for c in kids[word["token_index"]])


EN_EMOTION_NOUNS = {"grief", "pain", "sadness", "sorrow", "guilt", "joy", "fear", "anger", "emptiness", "relief",
                    "love", "loneliness", "peace", "regret", "despair", "shame", "numbness", "anxiety", "helplessness",
                    "hurt", "loss", "heartbreak", "happiness", "longing", "gratitude", "hopelessness"}
EN_EMOTION_COMPLEMENT = ({lem for lem, (_, cls, st) in EN_PRED.items() if st == "rule" and cls != "FEEL"}
                         | EN_EMOTION_NOUNS)
EN_REVIEW_COMPLEMENT = {lem for lem, (_, _, st) in EN_PRED.items() if st == "review"}


def feel_complement(w, kids):
    for c in kids[w["token_index"]]:
        if c["deprel"] not in ("xcomp", "acomp", "obj", "attr", "advmod"):
            continue
        keys = {c["token"].lower(), (c["lemma"] or "").lower()}
        if keys & EN_EMOTION_COMPLEMENT:
            return "emotion"
        if keys & EN_REVIEW_COMPLEMENT:
            return "review"
    return None


def classify_en(clause_ids, sentence, own_heads):
    kids = children(sentence)
    cand = []
    for h in sorted(own_heads):
        w = sentence[h]
        cand.append(w)
        cand += [c for c in kids[h] if c["deprel"] == "xcomp" and c["token_index"] in clause_ids]
    no_experiencer = nonemo = False
    for w in cand:
        lem = en_lemma(w, kids)
        if lem not in EN_PRED or w["upos"] not in ("VERB", "ADJ", "AUX"):
            continue
        rid, cls, status = EN_PRED[lem]
        if cls == "FEEL":
            comp = feel_complement(w, kids)
            if comp is None:
                nonemo = True
                continue
            if comp == "review":
                status, rid = "review", "EN-FEEL-R"
        if w["upos"] == "ADJ" and cls in ("SUBJ", "OBJ"):
            cls = "ADJ"
        subj = en_subject(w, sentence, kids)
        passive = any(c["deprel"] in ("aux:pass", "nsubj:pass") for c in kids[w["token_index"]])
        obj = next((c for c in kids[w["token_index"]] if c["deprel"] in ("obj", "iobj")), None)
        site = subj["token"] if subj is not None else ""
        if status == "review":
            dec, rule = "review", rid
        elif subj is None:
            dec, rule = "review", "EN-NOSUBJ"
        elif subj["deprel"] == "expl" or subj["token"].lower() in EN_IT:
            dec, rule = "impersonal", "EN-IMP-IT"
        elif cls == "STIM_ADJ":
            dec, rule = "impersonal", "EN-IMP-NOEXP"
        elif subj["token"].lower() in EN_BODY or subj["lemma"].lower() in EN_BODY:
            dec, rule = "body_part", "EN-BODY"
        elif cls == "OBJ" and passive:
            dec, rule = ("nominative", "EN-NOM-PASS") if en_person(subj, kids) else ("impersonal", "EN-IMP-NOEXP")
        elif cls == "OBJ" and obj is not None and obj["token"].lower() in EN_EXPERIENCER_OBJ:
            dec, rule, site = "stimulus", "EN-STIM", obj["token"]
        elif cls == "OBJ" and obj is not None and en_person(obj, kids):
            dec, rule, site = "stimulus", "EN-STIM", obj["token"]
        elif en_person(subj, kids):
            dec, rule = "nominative", "EN-NOM"
        elif obj is not None and cls == "OBJ":
            dec, rule = "stimulus", "EN-STIM"
        else:
            dec, rule = "impersonal", "EN-IMP-NOEXP"
        if dec in ("impersonal", "stimulus") and not en_experiencer_arg(w, kids):
            no_experiencer = True
            continue
        return [dict(site=site, predicate=lem, decision=en_decision(dec, lem), rule_id=rule, subject_source="",
                     construction=dec if dec != "review" else "", twin_rule=EN_TWIN.get(lem, ""))]
    return [dict(site="", predicate="", decision="NA",
                 rule_id="EN-NA-IMP-NOEXP" if no_experiencer else "EN-NA-NONEMO" if nonemo else "EN-NA",
                 subject_source="", construction="", twin_rule="")]


def en_experiencer_arg(w, kids):
    for c in kids[w["token_index"]]:
        if c["deprel"] in ("obj", "iobj") or c["deprel"].startswith("obl"):
            if c["token"].lower() in EN_EXPERIENCER_OBJ or en_person(c, kids):
                return True
    return False


def en_decision(construction, predicate):
    if construction not in EN_NONNOM | {"nominative"}:
        return construction
    side = "nominative" if construction == "nominative" else "impersonal"
    return f"{'chosen' if predicate in EN_TWIN else 'forced'}_{side}"


def classify(lang, clause_ids, sentence, recovered=None):
    words = [sentence[i] for i in sorted(clause_ids)]
    own = F.clause_heads(words, sentence)
    if lang == "hi":
        return classify_hi(clause_ids, sentence, own, recovered)
    if lang == "en":
        return classify_en(set(clause_ids), sentence, own)
    raise ValueError(f"no eligibility rules for language {lang!r}")


def classify_text(text, lang, nlp):
    from preprocess import prepare_text
    rows = []
    for s in nlp(prepare_text(text, lang)).sentences:
        sent = {w.id: dict(token_index=w.id, token=w.text, lemma=w.lemma or "", upos=w.upos, feats=w.feats or "",
                           head=w.head, deprel=w.deprel) for w in s.words}
        rows = classify(lang, list(sent), sent)
        if rows[0]["decision"] != "NA":
            return rows
    return rows


REL_RULES = [
    ("REL-HON-F", "honorific", "hi: honorific plural reference to the deceased (referents.py honorific = True, or "
     "plural verb agreement with a singular pronoun: वह ... पूछते थे); relation parent / grandparent / "
     "parent-in-law / teacher / elder", "forced_relational",
     "none: singular reference to an elder is not an available register",
     "lexicon/flag_components.csv F2 (forced for a parent/elder referent); design note 2026-10-10"),
    ("REL-HON-C", "honorific", "hi: as above; relation sibling / spouse / child / friend / peer", "chosen_relational",
     "singular agreement (वह गया) was available", "F2 (chosen for a younger deceased); design note 2026-10-10"),
    ("REL-HON-SG", "honorific", "hi: singular reference to the deceased by an overt singular 3rd-person pronoun "
     "(वह / उसने / उसे / यह ...; वो is unmarked and not used) with non-honorific agreement; relation sibling / "
     "spouse / child / friend / peer. honorific = False alone is not evidence (agreement is often not observable: "
     "माँ को आपत्ति न थी), and वह with an honorific verb (वह ... देती थीं) counts as honorific",
     "chosen_individual", "honorific plural (वे गए) was available", "F2; the alternative side of REL-HON-C"),
    ("REL-HON-SG-ELDER", "honorific", "hi: the same singular pronoun for a deceased parent / grandparent / elder",
     "review", "", "a genuine non-honorific or a pronoun the referent stage resolved wrongly: a human decides"),
    ("REL-HON-NA", "honorific", "hi: relation unknown / not stated", "NA (no row)", "", "design note 2026-10-10"),
    ("REL-SELF-PL", "self", "overt first-person subject in a plural form (हम / हमें / हमने / we / us) for one person "
     "or a genuinely shared we", "chosen_relational", "मैं / I", "F10 plural_self_reference; design note 2026-10-10"),
    ("REL-SELF-SG", "self", "overt first-person singular subject (मैं / मुझे / मैंने / I / me)", "chosen_individual",
     "हम / we", "F10; the alternative side of REL-SELF-PL"),
    ("REL-KIN-TERM", "deceased_mention", "the deceased named by a kin term, as subject or target (पापा चले गए, "
     "I miss Papa)", "chosen_relational", "a pronoun (वे / he)",
     "F9 kin_term_for_deceased (Plan v3 P8b): kin term = relational option; design note 2026-10-10"),
    ("REL-KIN-PRON", "deceased_mention", "the deceased referred to by a pronoun, as subject or target (वे चले गए, "
     "I miss him)", "chosen_individual", "a kin term", "F9; the alternative side of REL-KIN-TERM"),
    ("REL-VOC", "vocative", "address to the deceased (referents.py address_to_dead, incl. by pronoun: decision 2026-10-10), "
     "vocative address with a kin / deceased term (parse deprel vocative) or a vocative-to-"
     "the-deceased lexicon entry (flag_F7)", "chosen_relational", "none counted (always chosen)",
     "F7 vocative_address_deceased: always chosen; design note 2026-10-10"),
    ("REL-COMM", "community", "matched lexicon entry with orientation C", "chosen_relational",
     "none counted (always chosen)", "orientation C entries (lexicon.csv); design note 2026-10-10"),
    ("REL-RITUAL", "ritual", "matched lexicon entry carrying RITUAL_WORDS", "chosen_relational",
     "none counted (always chosen)", "F6 closing_formula / RITUAL_WORDS: always chosen; design note 2026-10-10"),
]
REL_DECISION = {r[0]: r[3] for r in REL_RULES}


def is_pronoun(text, lang):
    t = R.norm(text or "", lang)
    return t in R.PRONOUNS[lang] or t in (R.SECOND_HI_INFORMAL | R.SECOND_HI_FORMAL | R.SECOND_EN)


def classify_relational(lang, ref, cf, words, category, deceased):
    from text_meta import HONORIFIC_CHOSEN, HONORIFIC_FORCED
    rows = []

    def add(rule, site, what):
        rows.append(dict(site=site, predicate=what, decision=REL_DECISION[rule], rule_id=rule, subject_source="",
                         construction=what, twin_rule=""))
    ref = ref or {}
    cf = cf or {}
    if lang == "hi" and ref.get("referent_class") == "deceased":
        singular_pron = ref.get("overt_pronoun") and ref.get("pronoun_person") == "3" \
            and ref.get("pronoun_number") == "sg"
        plural_verb = False
        ergative = F.bare(ref.get("overt_pronoun") or "").endswith("ने")
        if singular_pron and not ergative:
            kids = defaultdict(list)
            for w in words:
                kids[w["head"]].append(w)
            head = R.clause_head(words, {w["token_index"] for w in words})
            plural_verb = bool(head and R.chain_feats(head, kids).get("AnyPlur"))
        if singular_pron and ergative:
            pass
        elif ref.get("honorific") == "True" or plural_verb:
            if category in HONORIFIC_FORCED:
                add("REL-HON-F", ref.get("subject_text", ""), "honorific")
            elif category in HONORIFIC_CHOSEN:
                add("REL-HON-C", ref.get("subject_text", ""), "honorific")
        elif singular_pron:
            if category in HONORIFIC_CHOSEN:
                add("REL-HON-SG", ref["overt_pronoun"], "honorific")
            elif category in HONORIFIC_FORCED:
                add("REL-HON-SG-ELDER", ref["overt_pronoun"], "honorific")
    if ref.get("overt_pronoun") and ref.get("pronoun_person") == "1":
        add("REL-SELF-PL" if ref.get("pronoun_number") == "pl" else "REL-SELF-SG", ref["overt_pronoun"], "self")
    vocatives = [w for w in words if w["deprel"] == "vocative"
                 and R.classify_noun(w, lang, deceased) in ("kin", "deceased")]
    voc_texts = {R.norm(w["token"], lang) for w in vocatives}
    address = ref.get("address_to_dead") in ("True", True)
    if address:
        voc_texts.add(R.norm(ref.get("target_text", ""), lang))
    if ref.get("referent_class") == "deceased" and ref.get("subject_source") in ("overt", "overt+antecedent"):
        txt = ref.get("subject_text", "")
        add("REL-KIN-PRON" if is_pronoun(txt, lang) else "REL-KIN-TERM", txt, "deceased_mention")
    if ref.get("target_class") == "deceased" and R.norm(ref.get("target_text", ""), lang) not in voc_texts:
        txt = ref.get("target_text", "")
        add("REL-KIN-PRON" if is_pronoun(txt, lang) else "REL-KIN-TERM", txt, "deceased_mention")
    if vocatives or cf.get("flag_F7") in ("1", "True") or address:
        add("REL-VOC", vocatives[0]["token"] if vocatives else ref.get("target_text") if address else "(entry F7)",
            "vocative")
    if cf.get("orient_C") in ("1", "True"):
        add("REL-COMM", "", "community")
    if cf.get("comp_RITUAL_WORDS") in ("1", "True"):
        add("REL-RITUAL", "", "ritual")
    if not rows:
        rows.append(dict(site="", predicate="", decision="NA", rule_id="REL-NA", subject_source="", construction="",
                         twin_rule=""))
    for r in rows:
        r["marker_type"] = "relational"
    return rows


def flag_values(rows):
    decs = {r["decision"] for r in rows}
    if not decs & {"forced_dative", "chosen_dative"}:
        return None, None
    return "forced_dative" in decs, "chosen_dative" in decs


def fill_flags(flags_path, by_clause):
    flags_path = Path(flags_path)
    with open(flags_path, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        fields, rows = reader.fieldnames, list(reader)
    n = Counter()
    for r in rows:
        if r["lang"] == "hi" and r["clause_id"] in by_clause:
            gf, alt = flag_values(by_clause[r["clause_id"]])
            r["grammar_forced"] = "" if gf is None else str(gf)
            r["dative_alternative_available"] = "" if alt is None else str(alt)
        n[("gf", r["grammar_forced"])] += 1
        n[("alt", r["dative_alternative_available"])] += 1
    tmp = flags_path.with_suffix(".csv.tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, flags_path)
    return n


def write_summary(path, args, out_rows, n_finite, unlisted, examples, flag_counts, elapsed, seed):
    by = Counter((r["lang"], r["decision"]) for r in out_rows)
    rules = Counter((r["lang"], r["rule_id"]) for r in out_rows)
    L = ["# Eligibility summary (P8b)", "",
         f"- Input: `{args.inp}` + tokens.csv; run {time.strftime('%Y-%m-%d %H:%M')} ({elapsed:.0f} s)",
         "- Rule-based, unreviewed (machine-provisional). Rows = sites (hi) / clauses (en); NA = one row per clause "
         "with no site.",
         f"- Finite clauses: hi {n_finite['hi']:,}, en {n_finite['en']:,}", "",
         "## Decisions", "", "| lang | decision | rows | clauses |", "|---|---|---|---|"]
    clauses_by = defaultdict(set)
    for r in out_rows:
        clauses_by[(r["lang"], r["decision"])].add(r["clause_id"])
    for (lg, dec), k in sorted(by.items()):
        L.append(f"| {lg} | {dec} | {k:,} | {len(clauses_by[(lg, dec)]):,} |")
    L += ["", "## Rules hit", "", "| lang | rule_id | rows |", "|---|---|---|"]
    L += [f"| {lg} | {rid} | {k:,} |" for (lg, rid), k in sorted(rules.items(), key=lambda x: (x[0][0], -x[1]))]
    L += ["", "## Review predicates by frequency (a human decides)", "", "| lang | predicate | rule_id | rows |",
          "|---|---|---|---|"]
    rev = Counter((r["lang"], r["predicate"], r["rule_id"]) for r in out_rows if r["decision"] == "review")
    L += [f"| {lg} | {p or '(no subject)'} | {rid} | {k} |" for (lg, p, rid), k in rev.most_common()]
    L += ["", f"Unlisted Hindi predicates (HI-UNL, also in predicate_inventory.csv): {len(unlisted)}", "",
          "## flags.csv", "",
          f"- grammar_forced: True {flag_counts[('gf', 'True')]:,}, False {flag_counts[('gf', 'False')]:,}, "
          f"empty {flag_counts[('gf', '')]:,}",
          f"- dative_alternative_available: True {flag_counts[('alt', 'True')]:,}, "
          f"False {flag_counts[('alt', 'False')]:,}, empty {flag_counts[('alt', '')]:,}", "",
          f"## Examples (up to 4 random per language and decision, seed {seed})", ""]
    rng = random.Random(seed)
    for key in sorted(examples):
        pool = examples[key]
        L.append(f"**{key[0]} / {key[1]}** ({len(pool)})")
        L += [f"- `{cid}` [{site} | {pred} | {rid}] {text}" for cid, site, pred, rid, text in
              rng.sample(pool, min(4, len(pool)))]
        L.append("")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--in", dest="inp", default="data/processed/clauses.jsonl")
    ap.add_argument("--tokens", default=None, help="default: tokens.csv next to --in")
    ap.add_argument("--out", default="data/processed/eligibility.csv")
    ap.add_argument("--flags", default="data/processed/flags.csv", help="'' = do not touch flags.csv")
    ap.add_argument("--referents", default=None,
                    help="referents.csv (subject of clauses without an overt subject); default: next to --in if present")
    ap.add_argument("--features", default=None, help="clause_features.csv (relational sites); default: next to --in")
    ap.add_argument("--records", default="data/clean/blogs_merged.jsonl", help="deceased relation per text")
    ap.add_argument("--seed", type=int, default=20261009)
    args = ap.parse_args()
    args.tokens = args.tokens or str(Path(args.inp).with_name("tokens.csv"))
    t0 = time.time()
    from text_meta import parse_field, relation_category
    feat_path = Path(args.features or Path(args.inp).with_name("clause_features.csv"))
    if not feat_path.exists():
        sys.exit(f"{feat_path} not found: run lexmatch.py first (relational sites need orient_C / RITUAL / F7)")
    with open(feat_path, encoding="utf-8", newline="") as fh:
        cfeat = {r["clause_id"]: {k: r.get(k, "") for k in ("orient_C", "comp_RITUAL_WORDS", "flag_F7")}
                 for r in csv.DictReader(fh)}
    category, dec_terms = {}, {}
    for line in open(args.records, encoding="utf-8"):
        rec = json.loads(line)
        rel = str(parse_field(rec.get("extra"), {}).get("deceased_relation_as_stated") or "")
        category[rec["record_id"]] = relation_category(rel)
        dec_terms[rec["record_id"]] = R.deceased_terms(rel)
    recovered = load_recovered(args.referents, args.inp)
    all_clauses = [json.loads(line) for line in open(args.inp, encoding="utf-8")]
    clauses = [c for c in all_clauses if c["is_finite"]]
    sentences, clause_ids = load_sentences(args.tokens, sentence_meta(all_clauses))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out_rows, by_clause, n_finite, examples, unlisted = [], {}, Counter(), defaultdict(list), Counter()
    for c in clauses:
        if not clause_ids.get(c["clause_id"]):
            continue
        sent = sentences[(c["record_id"], c["sent_index"])]
        rows = classify(c["lang"], clause_ids[c["clause_id"]], sent, recovered.get(c["clause_id"]))
        for r in rows:
            r["marker_type"] = "dative"
        by_clause[c["clause_id"]] = rows
        rows = rows + classify_relational(c["lang"], recovered.get(c["clause_id"]), cfeat.get(c["clause_id"]),
                                          [sent[i] for i in sorted(clause_ids[c["clause_id"]])],
                                          category.get(c["record_id"], "unknown"), dec_terms.get(c["record_id"], set()))
        n_finite[c["lang"]] += 1
        for r in rows:
            r = dict(clause_id=c["clause_id"], lang=c["lang"], **r)
            out_rows.append(r)
            if r["rule_id"] == "HI-UNL":
                unlisted[r["predicate"]] += 1
            if r["decision"] != "NA" and r["marker_type"] == "dative":
                examples[(c["lang"], r["decision"])].append((c["clause_id"], r["site"], r["predicate"], r["rule_id"],
                                                             c["clause_text"]))
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["clause_id", "lang", "marker_type", "site", "predicate", "decision",
                                           "rule_id", "subject_source", "construction", "twin_rule"], restval="")
        w.writeheader()
        w.writerows(out_rows)
    with open(out.with_name("relational_sites.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["rule_id", "site", "condition", "decision", "alternative", "source"])
        w.writerows(REL_RULES)
    inv = inventory_rows() + [dict(predicate=p, lang="hi", site="dative", decision="review", rule_id="HI-UNL",
                                   twin="", alternative="",
                                   rule=f"unlisted predicate on an experiencer head; {k} corpus rows",
                                   source="corpus (unlisted)", equivalent="") for p, k in unlisted.most_common()]
    with open(out.with_name("predicate_inventory.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["predicate", "lang", "site", "decision", "rule_id", "twin", "alternative",
                                           "rule", "source", "equivalent"])
        w.writeheader()
        w.writerows(inv)
    flag_counts = fill_flags(args.flags, by_clause) if args.flags else Counter()
    dative_rows = [r for r in out_rows if r["marker_type"] == "dative"]
    write_summary(out.with_name("eligibility_summary.md"), args, dative_rows, n_finite, unlisted, examples,
                  flag_counts, time.time() - t0, args.seed)
    for mt in ("dative", "relational"):
        for lg in ("hi", "en"):
            cnt = Counter(r["decision"] for r in out_rows if r["lang"] == lg and r["marker_type"] == mt)
            print(f"{mt} {lg}: {n_finite[lg]} finite clauses; " + ", ".join(f"{k} {v}" for k, v in sorted(cnt.items())))
    print(f"wrote {out}, predicate_inventory.csv, relational_sites.csv, eligibility_summary.md"
          + (f"; filled {args.flags}" if args.flags else ""))


if __name__ == "__main__":
    main()
