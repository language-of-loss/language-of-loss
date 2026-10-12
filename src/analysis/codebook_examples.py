"""Gold-set codebook v1 examples: render them into docs/codebook_v1.md (ids only) and docs/codebook_v1_examples.md."""
import argparse
import json
import re
import sys
from pathlib import Path

from gold import CODEBOOK, split_of

ROOT = Path(__file__).resolve().parents[2]
NOT_APPLICABLE = {("grammar_forced", "context", "en"): "English has no honorific agreement; no context-dependent "
                                                        "forced form exists. Do not use `context` for English."}
EXAMPLES = [
    ("orientation", "I", "hi", "blogs:blog_5d9bd3572a70#0035", "the writer's own missing (याद आना)"),
    ("orientation", "I", "hi", "blogs:blog_0861b4d96495#0051", "the writer's own sorrow, poured out"),
    ("orientation", "I", "en", "blogs:blog_1d8075d67392#0011", "the writer's own missing"),
    ("orientation", "I", "en", "blogs:cw_f167359e745f#0127", "the writer crying alone"),
    ("orientation", "F", "hi", "blogs:cw_8d3d92bb074b#0002", "a father lives on in his children"),
    ("orientation", "F", "hi", "blogs:blog_e831d4df1dba#0178", "the family received the mother's love for decades"),
    ("orientation", "F", "en", "blogs:blog_923ba743055e#0002", "family occasions without her"),
    ("orientation", "F", "en", "blogs:blog_1d8075d67392#0031", "the mother as the family's friend"),
    ("orientation", "C", "hi", "blogs:blog_56eb08c9fd16#0357", "everyone was grief-stricken"),
    ("orientation", "C", "hi", "blogs:blog_56eb08c9fd16#0473", "peers conveying condolences"),
    ("orientation", "C", "en", "blogs:blog_0bf67028c93c#0080", "grief as a society"),
    ("orientation", "C", "en", "blogs:cw_c8ad3b363b51#0171", "loss as shared, not unique to us"),
    ("orientation", "R", "hi", "blogs:blog_1a2307a93e96#0101", "श्रद्धांजलि on the death anniversary"),
    ("orientation", "R", "hi", "blogs:cw_c649fdea8bf0#0045", "performing the last rites"),
    ("orientation", "R", "en", "blogs:cw_e3e3e1f5f47e#0216", "the formula 'rest in peace'"),
    ("orientation", "R", "en", "blogs:blog_441e919414e5#0035", "a self-made last rite"),
    ("orientation", "NA", "hi", "blogs:blog_56eb08c9fd16#0159", "background: an old hobby"),
    ("orientation", "NA", "hi", "blogs:blog_dddd37b0b32a#0017", "background: a travel plan"),
    ("orientation", "NA", "en", "blogs:blog_0bf67028c93c#0096", "background: taking a photo"),
    ("orientation", "NA", "en", "blogs:blog_c92dad266d06#0034", "background: news"),
    ("experiencer", "self", "hi", "blogs:cw_6a2c0609408b#0045", "मैं, nominative"),
    ("experiencer", "self", "hi", "blogs:blog_56eb08c9fd16#0533", "मुझे, dative experiencer"),
    ("experiencer", "self", "en", "blogs:blog_12cca32b4a59#0065", "I"),
    ("experiencer", "self", "en", "blogs:cw_2ca5cb44e79d#0025", "I"),
    ("experiencer", "kin", "hi", "blogs:cw_95e0259c53b1#0030", "the living mother after the father's death"),
    ("experiencer", "kin", "hi", "blogs:cw_f5baf36bd55e#0271", "the (living) mother"),
    ("experiencer", "kin", "en", "blogs:blog_33be34a730e8#0086", "the sister and her husband"),
    ("experiencer", "kin", "en", "blogs:cw_2ca5cb44e79d#0090", "the writer's son"),
    ("experiencer", "community", "hi", "blogs:cw_8d3d92bb074b#0063", "हम लोग"),
    ("experiencer", "community", "hi", "blogs:blog_5aa741918356#0613", "हम बच्चों को, dative group"),
    ("experiencer", "community", "en", "blogs:blog_20065bd3d877#0117", "we (the bereaved)"),
    ("experiencer", "community", "en", "blogs:blog_0bf67028c93c#0080", "we as a society"),
    ("experiencer", "deceased", "hi", "blogs:blog_e831d4df1dba#0134", "अम्मा"),
    ("experiencer", "deceased", "hi", "blogs:cw_f5baf36bd55e#0117", "पिताजी"),
    ("experiencer", "deceased", "en", "blogs:blog_6f65b35a5349#0006", "she = the mother who died"),
    ("experiencer", "deceased", "en", "blogs:blog_1d8075d67392#0061", "she = the mother who died"),
    ("experiencer", "God", "hi", "blogs:blog_0861b4d96495#0066", "ईश्वर as agent of a wish"),
    ("experiencer", "God", "hi", "blogs:blog_dddd37b0b32a#0046", "God gives such a life and death"),
    ("experiencer", "God", "en", "blogs:blog_9fcac969c59f#0091", "God grant us patience"),
    ("experiencer", "God", "en", "blogs:blog_0bf67028c93c#0070", "God as the one who needs"),
    ("experiencer", "impersonal", "hi", "blogs:cw_c649fdea8bf0#0047", "everything began to fall apart"),
    ("experiencer", "impersonal", "hi", "blogs:cw_95e0259c53b1#0007", "an emptiness arose"),
    ("experiencer", "impersonal", "en", "blogs:blog_1d8075d67392#0010", "relative 'that' = the sense of loss"),
    ("experiencer", "impersonal", "en", "blogs:blog_441e919414e5#0201", "relationships"),
    ("experiencer", "other", "hi", "blogs:blog_dddd37b0b32a#0012", "the doctor"),
    ("experiencer", "other", "hi", "blogs:blog_5aa741918356#0096", "a classmate (non-kin individual)"),
    ("experiencer", "other", "en", "blogs:blog_05e43a83d245#0110", "the doctor"),
    ("experiencer", "other", "en", "blogs:blog_05e43a83d245#0064", "a friend who is the employer"),
    ("predicate_type", "state", "hi", "blogs:blog_e831d4df1dba#0144", "copular: was the centre of my life"),
    ("predicate_type", "state", "hi", "blogs:blog_ff5322367bcf#0015", "copular: had no equal"),
    ("predicate_type", "state", "en", "blogs:blog_923ba743055e#0013", "it's exhausting"),
    ("predicate_type", "state", "en", "blogs:cw_2ca5cb44e79d#0025", "feel guilty"),
    ("predicate_type", "action", "hi", "blogs:blog_5aa741918356#0169", "carried me to the fields"),
    ("predicate_type", "action", "hi", "blogs:blog_5aa741918356#0541", "carried soil on his head"),
    ("predicate_type", "action", "en", "blogs:blog_441e919414e5#0047", "took the next flight"),
    ("predicate_type", "action", "en", "blogs:cw_b0f49d0805b5#0111", "went straight to the hospital"),
    ("predicate_type", "event_befalling", "hi", "blogs:cw_8d3d92bb074b#0094", "स्वर्गवास हो गया: death happened"),
    ("predicate_type", "event_befalling", "hi", "blogs:blog_e831d4df1dba#0159", "वज्रपात हुआ on अम्मा"),
    ("predicate_type", "event_befalling", "en", "blogs:blog_441e919414e5#0003", "passed away"),
    ("predicate_type", "event_befalling", "en", "blogs:blog_0bec8419b0f9#0090", "it pains me"),
    ("predicate_type", "speech", "hi", "blogs:cw_c649fdea8bf0#0019", "कहा"),
    ("predicate_type", "speech", "hi", "blogs:blog_dddd37b0b32a#0026", "कहा कि"),
    ("predicate_type", "speech", "en", "blogs:cw_e3e3e1f5f47e#0180", "said"),
    ("predicate_type", "speech", "en", "blogs:blog_1d8075d67392#0006", "people tell you"),
    ("predicate_type", "other", "hi", "blogs:blog_5d9bd3572a70#0080", "imperative wish to the dead"),
    ("predicate_type", "other", "hi", "blogs:blog_0861b4d96495#0066", "optative wish (subjunctive दे)"),
    ("predicate_type", "other", "en", "blogs:blog_33be34a730e8#0145", "thanks formula"),
    ("predicate_type", "other", "en", "blogs:blog_1d8075d67392#0080", "thanks formula"),
    ("target", "self", "hi", "blogs:blog_56eb08c9fd16#0049", "called out to me"),
    ("target", "self", "hi", "blogs:cw_c649fdea8bf0#0063", "मुझे as recipient"),
    ("target", "self", "en", "blogs:blog_a8cbdcd5970a#0063", "there for me"),
    ("target", "self", "en", "blogs:blog_441e919414e5#0260", "wronged me"),
    ("target", "kin", "hi", "blogs:cw_f5baf36bd55e#0281", "arrangements for your (living) mother"),
    ("target", "kin", "hi", "blogs:blog_5aa741918356#0307", "said to the (living) mother"),
    ("target", "kin", "en", "blogs:cw_71020181a93a#0053", "trusted his parents"),
    ("target", "kin", "en", "blogs:blog_a8cbdcd5970a#0047", "helped my (living) mother"),
    ("target", "community", "hi", "blogs:blog_e831d4df1dba#0196", "enrich us"),
    ("target", "community", "hi", "blogs:cw_6a2c0609408b#0057", "taught all of us"),
    ("target", "community", "en", "blogs:blog_1d8075d67392#0020", "faith in us"),
    ("target", "community", "en", "blogs:blog_0bec8419b0f9#0298", "allow us"),
    ("target", "deceased", "hi", "blogs:cw_f5baf36bd55e#0297", "sent my sons to (the late) father"),
    ("target", "deceased", "hi", "blogs:blog_56eb08c9fd16#0514", "seeing Baba's body"),
    ("target", "deceased", "en", "blogs:blog_441e919414e5#0174", "told my (late) father"),
    ("target", "deceased", "en", "blogs:blog_12cca32b4a59#0124", "vocative paati: addressed to the dead"),
    ("target", "God", "hi", "blogs:blog_56eb08c9fd16#0339", "faith in ईश्वर"),
    ("target", "God", "hi", "blogs:cw_95e0259c53b1#0055", "prayer to ईश्वर"),
    ("target", "God", "en", "blogs:cw_2ca5cb44e79d#0065", "believed in God"),
    ("target", "God", "en", "blogs:blog_0bec8419b0f9#0043", "a gift from Allah"),
    ("target", "impersonal", "hi", "blogs:blog_dddd37b0b32a#0017", "made a plan"),
    ("target", "impersonal", "hi", "blogs:cw_c649fdea8bf0#0135", "looking at life"),
    ("target", "impersonal", "en", "blogs:cw_71020181a93a#0122", "approach life"),
    ("target", "impersonal", "en", "blogs:blog_923ba743055e#0065", "add mustard seeds"),
    ("target", "other", "hi", "blogs:blog_dddd37b0b32a#0021", "called the doctor"),
    ("target", "other", "hi", "blogs:blog_dddd37b0b32a#0025", "saw the doctor to his car"),
    ("target", "other", "en", "blogs:blog_05e43a83d245#0131", "asked him (the employer)"),
    ("target", "other", "en", "blogs:blog_ddc209e9df4c#0102", "urge you (the reader)"),
    ("target", "none", "hi", "blogs:blog_8b666dd3f7e4#0063", "date statement"),
    ("target", "none", "hi", "blogs:blog_e831d4df1dba#0020", "the road is hard"),
    ("target", "none", "en", "blogs:cw_2ca5cb44e79d#0012", "she was fifty-six"),
    ("target", "none", "en", "blogs:blog_a8cbdcd5970a#0006", "life has been wonderful"),
    ("process", "L", "hi", "blogs:cw_95e0259c53b1#0007", "the emptiness left by the death"),
    ("process", "L", "hi", "blogs:blog_e831d4df1dba#0185", "where did she go"),
    ("process", "L", "en", "blogs:blog_9fcac969c59f#0044", "the sound of pain"),
    ("process", "L", "en", "blogs:cw_b0f49d0805b5#0220", "kept feeling an ache"),
    ("process", "Rs", "hi", "blogs:cw_c649fdea8bf0#0135", "began to look at life positively"),
    ("process", "Rs", "hi", "blogs:cw_95e0259c53b1#0053", "will keep your ideals alive in my life"),
    ("process", "Rs", "en", "blogs:blog_33be34a730e8#0124", "move on with life"),
    ("process", "Rs", "en", "blogs:cw_71020181a93a#0135", "stopped stressing"),
    ("process", "NA", "hi", "blogs:blog_5d9bd3572a70#0032", "played cards (background)"),
    ("process", "NA", "hi", "blogs:blog_8b666dd3f7e4#0070", "was on a plane (background)"),
    ("process", "NA", "en", "blogs:blog_12cca32b4a59#0089", "hair and attire (background)"),
    ("process", "NA", "en", "blogs:cw_e3e3e1f5f47e#0171", "she was around (background)"),
    ("function", "Sk", "hi", "blogs:blog_ff5322367bcf#0043", "asks readers to pray"),
    ("function", "Sk", "hi", "blogs:blog_0861b4d96495#0051", "asks to be allowed to pour out grief"),
    ("function", "Sk", "en", "blogs:cw_e3e3e1f5f47e#0101", "a remembered need for her support"),
    ("function", "Sk", "en", "blogs:cw_c8ad3b363b51#0219", "borderline: asks readers to respond"),
    ("function", "Of", "hi", "blogs:blog_0861b4d96495#0023", "others' 'keep courage' (reported offer)"),
    ("function", "Of", "hi", "blogs:blog_5d9bd3572a70#0080", "blessing to the dead"),
    ("function", "Of", "en", "blogs:blog_ddc209e9df4c#0102", "advice to the reader"),
    ("function", "Of", "en", "blogs:blog_6b79cbddbd46#0138", "advice to the reader"),
    ("function", "NA", "hi", "blogs:cw_086da0589970#0007", "packed suits"),
    ("function", "NA", "hi", "blogs:blog_e831d4df1dba#0167", "health declined"),
    ("function", "NA", "en", "blogs:cw_c8ad3b363b51#0114", "discourse aside, no support move"),
    ("function", "NA", "en", "blogs:blog_441e919414e5#0150", "question to someone, no support move"),
    ("grammar_forced", "Y", "hi", "blogs:blog_1a2307a93e96#0047", "forced dative: दिखाई देना"),
    ("grammar_forced", "Y", "hi", "blogs:cw_f5baf36bd55e#0013", "honorific plural for the late father"),
    ("grammar_forced", "Y", "en", "blogs:blog_a8cbdcd5970a#0064", "miss: no impersonal twin"),
    ("grammar_forced", "Y", "en", "blogs:blog_12cca32b4a59#0056", "cry: no impersonal twin"),
    ("grammar_forced", "N", "hi", "blogs:blog_8b666dd3f7e4#0034", "रोना chosen over रोना आना"),
    ("grammar_forced", "N", "hi", "blogs:cw_c649fdea8bf0#0127", "चिंता करना chosen over चिंता होना"),
    ("grammar_forced", "N", "en", "blogs:blog_441e919414e5#0006", "I felt (twin: it felt strange to me)"),
    ("grammar_forced", "N", "en", "blogs:blog_20065bd3d877#0095", "I grieve (twin listed)"),
    ("grammar_forced", "context", "hi", "blogs:blog_0861b4d96495#0072", "honorific plural for a wife"),
    ("grammar_forced", "context", "hi", "blogs:cw_c649fdea8bf0#0012", "honorific plural for a husband"),
    ("dative_alternative_available", "Y", "hi", "blogs:blog_5aa741918356#0208", "गुस्सा आना ~ गुस्सा होना"),
    ("dative_alternative_available", "Y", "hi", "blogs:cw_c649fdea8bf0#0087", "समझ में आना ~ समझना"),
    ("dative_alternative_available", "Y", "en", "blogs:cw_2ca5cb44e79d#0025", "I feel guilty ~ guilt weighs on me"),
    ("dative_alternative_available", "Y", "en", "blogs:blog_0bec8419b0f9#0282", "body part: chests feel heavy"),
    ("dative_alternative_available", "N", "hi", "blogs:cw_6a2c0609408b#0042", "INF + पड़ना obligation"),
    ("dative_alternative_available", "N", "hi", "blogs:blog_0861b4d96495#0030", "INF + पड़ना obligation"),
    ("dative_alternative_available", "N", "en", "blogs:blog_6f65b35a5349#0092", "glad: no twin"),
    ("dative_alternative_available", "N", "en", "blogs:cw_e3e3e1f5f47e#0073", "love: no twin"),
    ("dative_alternative_available", "NA", "hi", "blogs:blog_5aa741918356#0020", "no experiencer predicate"),
    ("dative_alternative_available", "NA", "hi", "blogs:blog_e831d4df1dba#0078", "no experiencer predicate"),
    ("dative_alternative_available", "NA", "en", "blogs:cw_71020181a93a#0023", "no experiencer predicate"),
    ("dative_alternative_available", "NA", "en", "blogs:blog_0bec8419b0f9#0086", "no experiencer predicate"),
]


def example_ids():
    return {cid for *_, cid, _ in EXAMPLES}


def load_clauses(path):
    out = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            c = json.loads(line)
            out[c["clause_id"]] = c
    return out


def table(rows, text=None):
    head = "| value | lang | clause_id | why |" if text is None else "| value | lang | clause_id | clause | why |"
    out = [head, "|---|---|---|---|" if text is None else "|---|---|---|---|---|"]
    for _, value, lang, cid, why in rows:
        if text is None:
            out.append(f"| `{value}` | {lang} | `{cid}` | {why} |")
        else:
            out.append(f"| `{value}` | {lang} | `{cid}` | {text[cid].replace('|', '/')} | {why} |")
    return "\n".join(out)


def render(md, field):
    rows = [e for e in EXAMPLES if e[0] == field]
    notes = [f"- `{v}` ({lang}): {msg}" for (f, v, lang), msg in NOT_APPLICABLE.items() if f == field]
    block = table(rows) + ("\n\n" + "\n".join(notes) if notes else "")
    pat = re.compile(rf"(<!-- EXAMPLES {field} -->\n)(?:(?:(?!<!-- ).)*?\n)?(<!-- /EXAMPLES -->)", re.S)
    if not pat.search(md):
        raise SystemExit(f"marker for {field} missing in codebook")
    return pat.sub(lambda m: m.group(1) + block + "\n" + m.group(2), md)


def check(clauses):
    probs = []
    for field, value, lang, cid, _ in EXAMPLES:
        if value not in CODEBOOK[field]:
            probs.append(f"{field}={value} not in codebook")
        c = clauses.get(cid)
        if c is None:
            probs.append(f"{cid} not in clauses.jsonl (Stage 3 re-run?)")
            continue
        if split_of(c["record_id"]) != "dev" or not c["is_finite"] or c["lang"] != lang:
            probs.append(f"{cid}: not a dev finite {lang} clause")
    for field, values in CODEBOOK.items():
        for value in values:
            for lang in ("hi", "en"):
                n = sum(1 for e in EXAMPLES if e[:3] == (field, value, lang))
                if n != 2 and (field, value, lang) not in NOT_APPLICABLE:
                    probs.append(f"{field}={value} {lang}: {n} examples")
    return probs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--in", dest="inp", default=str(ROOT / "data/processed/clauses.jsonl"))
    ap.add_argument("--codebook", default=str(ROOT / "docs/codebook_v1.md"))
    ap.add_argument("--examples-out", default=str(ROOT / "docs/codebook_v1_examples.md"))
    ap.add_argument("--check", action="store_true", help="only report problems")
    args = ap.parse_args(argv)
    clauses = load_clauses(args.inp)
    probs = check(clauses)
    for p in probs:
        print("PROBLEM", p)
    if args.check or probs:
        sys.exit(1 if probs else 0)
    md = Path(args.codebook).read_text(encoding="utf-8")
    for field in CODEBOOK:
        md = render(md, field)
    Path(args.codebook).write_text(md, encoding="utf-8")
    text = {cid: clauses[cid]["clause_text"] for cid in example_ids()}
    out = ["# Gold codebook v1: example clauses (LOCAL ONLY: third-party text, never commit)\n",
           "Referenced by clause_id from docs/codebook_v1.md. All dev split.\n"]
    for field in CODEBOOK:
        out += [f"## {field}\n", table([e for e in EXAMPLES if e[0] == field], text), ""]
    Path(args.examples_out).write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"{len(EXAMPLES)} examples ({len(example_ids())} clauses) -> {args.codebook}, {args.examples_out}")


if __name__ == "__main__":
    main()
