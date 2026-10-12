import csv, re, sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from lexutil_v02 import COLS
from components import COMPONENTS, K_IDS
from entries_hi import HI
from entries_en import EN

OUT = pathlib.Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)
ALL = HI + EN
IDS = {e["entry_id"] for e in ALL}

PRIMES = """i me my mine you your someone someone's something thing things people person person's body kind kinds part parts
this these the same other else another one two some all much many little few good bad big small
think thinks thought thinking know knows knew want wants wanted feel feels felt feeling see sees saw hear hears heard
say says said saying words word true do does did done doing happen happens happened happening move moves moved
be is are was were being been am there mine live lives lived living die dies died dying
when time times now before after long short moment moments where place places here above below far near side inside touch
not no maybe can cannot can't because if very more like as way""".split()
FUNCTION = """a an of to in at on from with for about it its it's that those than then there's isn't don't didn't doesn't
could couldn't have has had having would will not nothing anything no-one noone none nobody anyone everything each other otherwise
anymore again once somewhere anywhere nowhere everywhere elsewhere so such too also only even still yet ever never always
who whom whose what which how why any every both either neither less least most much-more very-much
into onto out up down off over under between among through without within during until till while
himself herself myself yourself themselves itself oneself them they he she him her his hers their theirs we us our ours
or and but nor if-not lot lots ago later earlier same-time""".split()
TOLERATED = {
 "towards": "NSM love explications use 'feel something good towards someone'",
 "have": "'have to' = 'can't not' (conventional abbreviation)",
 "has": "'has to'", "had": "'had to'",
 "respect": "v0.1 §3.7 verbatim line",
 "parent": "v0.1 §3.10 verbatim gloss in parentheses", "elder": "v0.1 §3.10 verbatim gloss",
 "slowly": "v0.1 §3.17 verbatim", "finished": "v0.1 §3.17 verbatim",
 "thirteen": "number", "forty": "number", "first": "ordinal",
}
MOLECULES = {"mother","father","child","family","god","eyes","home","body","tree","son","cry","cries","day","days","year","years",
             "water","heavy","sleep","sleeping","eat","shoulders","broken"}

def words(line): return re.findall(r"[a-z][a-z'’-]*", line.lower())

def check_primes(e):
    bad = []
    for raw in e["nsm_explication"].split("\n"):
        line = re.sub(r"\[m\]", " ", raw)
        for w in words(line):
            w2 = w.strip("'’")
            if w2 in PRIMES or w2 in FUNCTION or w2 in TOLERATED or w2 in MOLECULES: continue
            bad.append(w2)
    return sorted(set(bad))

def cplist(e):
    if e["counterpart"] == "none":
        return [], []
    return [c.strip() for c in e["counterpart"].split(";")], [o.strip() for o in e["overlap"].split(";")]

def check_tags(e):
    v = set(e["component_vector"].replace(" ", "").split(";")) - {""}
    x = e["nsm_explication"].lower(); errs = []
    unknown = v - set(K_IDS)
    if unknown: errs.append(f"unknown components {unknown}")
    if e["orientation"] == "R" and "RITUAL_WORDS" not in v: errs.append("R without RITUAL_WORDS")
    if "RITUAL_WORDS" in v and e["orientation"] != "R" and e["register"] != "ritual": errs.append("RITUAL_WORDS but not R/ritual")
    if e["orientation"] == "F" and not (v & {"KIN","BOND"}): errs.append("F without KIN/BOND")
    if e["orientation"] == "C" and not (v & {"WITH_OTHERS","EVERYONE","HONOUR"}): errs.append("C without WITH_OTHERS/EVERYONE/HONOUR")
    if "FEEL_BAD" in v and not re.search(r"\bfe(?:el|lt)", x): errs.append("FEEL_BAD without a feel line")
    if "AVOID_DIE" in v and "die" not in x: errs.append("AVOID_DIE without the die line")
    if "ABOVE" in v and "above" not in x: errs.append("ABOVE without an above line")
    if "SPEAK_TO_DEAD" in v and "say" not in x: errs.append("SPEAK_TO_DEAD without a say line")
    n = len(e["nsm_explication"].split("\n"))
    if not 2 <= n <= 8: errs.append(f"{n} explication lines")
    return errs

problems = collections.OrderedDict()
seen = collections.Counter(e["entry_id"] for e in ALL)
for k, c in seen.items():
    if c > 1: problems[k] = [f"duplicate id ×{c}"]
for e in ALL:
    errs = check_tags(e)
    cp = e["counterpart"]
    cps, ovs = cplist(e)
    if cp != "none":
        errs += [f"counterpart {c} missing" for c in cps if c not in IDS]
        if len(cps) != len(ovs): errs.append("overlap list does not align with the counterpart list")
    if cp == "none" and e["overlap"] != "none": errs.append("counterpart none but overlap != none")
    try:
        rx = re.compile(e["pattern"], re.IGNORECASE)
        ex = e["example_hi"] if e["lang"] == "hi" else e["example_en"]
        if e["pattern"] and ex and not rx.search(ex): errs.append("pattern misses own example")
        if "\\b" in e["pattern"]: errs.append("pattern uses \\b")
    except re.error as ex_:
        errs.append(f"regex error {ex_}")
    np_ = check_primes(e)
    if np_: errs.append("non-prime: " + ", ".join(np_))
    if errs: problems[e["entry_id"]] = errs
by = {e["entry_id"]: e for e in ALL}
for e in ALL:
    for cp, ov in zip(*cplist(e)):
        if cp in by:
            back = dict(zip(*cplist(by[cp])))
            if e["entry_id"] in back and back[e["entry_id"]] != ov:
                problems.setdefault(e["entry_id"], []).append(f"overlap asymmetry with {cp}: {ov} vs {back[e['entry_id']]}")
sig = collections.defaultdict(list)
for e in ALL: sig[(e["lang"], e["nsm_explication"].strip())].append(e["entry_id"])
for k, ids in sig.items():
    if len(ids) > 1: problems[ids[0]] = problems.get(ids[0], []) + [f"identical explication: {ids}"]

if "--check" in sys.argv:
    for k, v in problems.items(): print(k, "|", "; ".join(v))
    print(f"\n{len(HI)} hi + {len(EN)} en = {len(ALL)} entries; {len(problems)} entries with issues")
    sys.exit(0)

with open(OUT / "lexicon.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(ALL)
with open(OUT / "components.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["component_id", "gloss_primes", "example_hi", "example_en", "status", "n_entries_hi", "n_entries_en", "carriers", "note"])
    for cid, g, ehi, een, st, note in COMPONENTS:
        car = [e["entry_id"] for e in ALL if cid in e["component_vector"].split("; ")]
        w.writerow([cid, g, ehi, een, st, sum(c.startswith(("L-HI","P-HI")) for c in car), sum(c.startswith(("L-EN","P-EN")) for c in car), " ".join(car), note])
with open(OUT / "entry_vectors.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["entry_id", "lang"] + K_IDS + ["names_emotion"])
    for e in ALL:
        v = set(e["component_vector"].split("; "))
        names = "1" if e["pos"].startswith("noun") and "FEEL_BAD" in v and "(" not in e["pos"] else "0"
        w.writerow([e["entry_id"], e["lang"]] + [int(c in v) for c in K_IDS] + [names])
with open(OUT / "molecules.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["molecule", "used_in", "why_unavoidable"])
    why = {"mother":"kin term; NSM molecule", "father":"kin term", "child":"kin term", "family":"kin group", "son":"kin term (mukhagni)",
           "god":"divine referent; NSM molecule", "eyes":"body part for tears", "body":"prime BODY, marked only when it is the corpse",
           "home":"place where the family lives", "tree":"banyan-shade image", "cry":"weeping", "day":"time unit", "days":"time unit",
           "year":"time unit", "years":"time unit", "water":"tears", "heavy":"burden image", "sleep":"somatic symptom", "eat":"somatic symptom",
           "shoulders":"body part (कंधा देना)", "hospital":"circumstances move"}
    for m in sorted(MOLECULES):
        used = [e["entry_id"] for e in ALL if re.search(rf"\b{m}\[m\]", e["nsm_explication"])]
        if used: w.writerow([m, " ".join(used), why.get(m, "")])
    for t, r in TOLERATED.items():
        used = [e["entry_id"] for e in ALL if re.search(rf"\b{t}\b", e["nsm_explication"].lower())]
        if used: w.writerow([f"(tolerated) {t}", " ".join(used), r])
src = pathlib.Path(__file__).resolve().parents[1] / "tables" / "primes_hi.csv"
rows = list(csv.DictReader(open(src, encoding="utf-8")))
with open(OUT / "primes.csv", "w", newline="", encoding="utf-8") as f:
    cols = ["prime_en", "hindi_exponent", "status", "group", "hindi_roman", "allolexes", "polysemy_notes",
            "test_sentence_1_hi", "test_sentence_2_hi", "confidence", "confidence_reason", "v01_exponent"]
    v01 = {r[0]: r[1] for r in csv.reader(open(pathlib.Path(__file__).resolve().parent / "v01_primes.csv", encoding="utf-8"))}
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
    for r in rows:
        w.writerow({"prime_en": r["prime_en"], "hindi_exponent": r["exponent_hi_deva"], "status": "proposed", "group": r["group"],
                    "hindi_roman": r["exponent_hi_roman"], "allolexes": r["allolexes"], "polysemy_notes": r["polysemy_notes"],
                    "test_sentence_1_hi": r["test_sentence_1_hi"], "test_sentence_2_hi": r["test_sentence_2_hi"],
                    "confidence": r["confidence"], "confidence_reason": r["confidence_reason"], "v01_exponent": v01.get(r["prime_en"], "")})
print(f"wrote lexicon.csv ({len(ALL)} rows: {len(HI)} hi, {len(EN)} en), components.csv, entry_vectors.csv, molecules.csv, primes.csv")
print("counterpart=none:", sum(e['counterpart']=='none' for e in ALL), "| overlap none/partial/full:",
      collections.Counter(e['overlap'] for e in ALL))
