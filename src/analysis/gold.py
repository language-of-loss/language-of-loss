"""Stage 6 prep -- dev/confirmatory split and the blind gold-set annotation sheets."""
import argparse
import csv
import hashlib
import json
import sys
import random
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPLIT_NS = "grief-hi-en/split/v1|"
DEV_SHARE = 0.30
SEED = 20261009

CODEBOOK = {
    "orientation": ["I", "F", "C", "R", "NA"],
    "experiencer": ["self", "kin", "community", "deceased", "God", "impersonal", "other"],
    "predicate_type": ["state", "action", "event_befalling", "speech", "other"],
    "target": ["self", "kin", "community", "deceased", "God", "impersonal", "other", "none"],
    "process": ["L", "Rs", "NA"],
    "function": ["Sk", "Of", "NA"],
    "grammar_forced": ["Y", "N", "context"],
    "dative_alternative_available": ["Y", "N", "NA"],
}
SHEET_TEXT = ["gold_id", "lang", "context_before", "clause_text", "span_text", "context_after"]
SHEET_COLUMNS = SHEET_TEXT + list(CODEBOOK) + ["notes"]
KEY_COLUMNS = ["gold_id", "clause_id", "record_id", "lang", "position", "in_component_subset", "lexicon_hit",
               "clause_sha1"]
COMPONENT_VALUES = ["0", "1"]


ANNOTATION_DIR = ROOT / "data" / "annotation"
CHANNELS_DIR = ROOT / "data" / "processed" / "channels"


def refuse_annotation_dir(path):
    p = Path(path).resolve()
    if p == ANNOTATION_DIR.resolve() or ANNOTATION_DIR.resolve() in p.parents:
        sys.exit(f"refusing to write machine output into {ANNOTATION_DIR}: use {CHANNELS_DIR} ({p.name})")
    return path


def split_of(record_id):
    h = hashlib.sha256((SPLIT_NS + record_id).encode("utf-8")).digest()
    return "dev" if int.from_bytes(h[:8], "big") / 2 ** 64 < DEV_SHARE else "confirmatory"


def load_clauses(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def water_fill(sizes, n, cap, rng):
    caps = {t: min(s, cap) for t, s in sizes.items()}
    alloc = dict.fromkeys(caps, 0)
    order = sorted(caps, key=lambda t: (caps[t], t))
    remaining = n
    for i, t in enumerate(order):
        give = min(caps[t], remaining // (len(order) - i))
        alloc[t] = give
        remaining -= give
    spare = [t for t in sorted(caps) if alloc[t] < caps[t]]
    rng.shuffle(spare)
    for t in spare:
        if remaining == 0:
            break
        alloc[t] += 1
        remaining -= 1
    return alloc


def context(by_record, clause):
    seq = by_record[clause["record_id"]]
    i = next(k for k, c in enumerate(seq) if c["clause_id"] == clause["clause_id"])
    before = seq[i - 1]["span_text"] if i > 0 else ""
    after = seq[i + 1]["span_text"] if i + 1 < len(seq) else ""
    return before, after


def new_ids(n, taken, rng):
    out = []
    while len(out) < n:
        gid = "GRF-%010x" % rng.getrandbits(40)
        if gid not in taken:
            taken.add(gid)
            out.append(gid)
    return out


def load_lexicon_hits(path):
    if not Path(path).exists():
        return {}
    hits = {}
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        entry_cols = [i for i, h in enumerate(header) if h[:2] in ("L-", "P-")]
        for row in reader:
            hits[row[0]] = any(row[i] == "1" for i in entry_cols)
    return hits


def draw(clauses, n_per_lang, cap_share, n_components, hits, taken, seed, exclude=frozenset()):
    rng = random.Random(seed)
    by_record = defaultdict(list)
    for c in clauses:
        by_record[c["record_id"]].append(c)
    for seq in by_record.values():
        seq.sort(key=lambda c: c["position"])
    cap = int(cap_share * n_per_lang)
    rows, key, report = [], [], {}
    for lang in ("hi", "en"):
        pools = {r: [c for c in seq if c["is_finite"] and c["clause_id"] not in exclude]
                 for r, seq in sorted(by_record.items()) if seq[0]["lang"] == lang and split_of(r) == "dev"}
        pools = {r: p for r, p in pools.items() if p}
        alloc = water_fill({r: len(p) for r, p in pools.items()}, n_per_lang, cap, rng)
        picked = []
        for r in sorted(pools):
            picked += rng.sample(pools[r], alloc[r])
        rng.shuffle(picked)
        k = min(n_components // 2, len(picked))
        yes = [c for c in picked if hits.get(c["clause_id"])]
        no = [c for c in picked if not hits.get(c["clause_id"])]
        take_yes = min(len(yes), (k + 1) // 2)
        take_no = min(len(no), k - take_yes)
        take_yes = min(len(yes), k - take_no)
        comp = {c["clause_id"] for c in rng.sample(yes, take_yes) + rng.sample(no, take_no)}
        ids = new_ids(len(picked), taken, rng)
        for gid, c in zip(ids, picked):
            before, after = context(by_record, c)
            rows.append(dict(gold_id=gid, lang=lang, context_before=before, clause_text=c["clause_text"],
                             span_text=c["span_text"], context_after=after, _comp=c["clause_id"] in comp))
            key.append(dict(gold_id=gid, clause_id=c["clause_id"], record_id=c["record_id"], lang=lang,
                            position=c["position"], in_component_subset=int(c["clause_id"] in comp),
                            lexicon_hit="" if not hits else int(bool(hits.get(c["clause_id"]))),
                            clause_sha1=hashlib.sha1(c["clause_text"].encode("utf-8")).hexdigest()))
        n_dev = len({r for r in by_record if by_record[r][0]["lang"] == lang and split_of(r) == "dev"})
        n_all = len({r for r in by_record if by_record[r][0]["lang"] == lang})
        report[lang] = dict(texts_total=n_all, texts_dev=n_dev, dev_share=round(n_dev / n_all, 3) if n_all else 0,
                            texts_drawn_from=sum(1 for v in alloc.values() if v), target=n_per_lang,
                            drawn=len(picked), shortfall=n_per_lang - len(picked), cap_per_text=cap,
                            max_per_text=max(alloc.values(), default=0),
                            component_subset=len(comp), component_subset_lexicon_hit=take_yes)
    return rows, key, report


def pilot_exclusions(pilot_key_path):
    path = Path(pilot_key_path)
    if not path.exists():
        return set(), set()
    with open(path, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return {r["clause_id"] for r in rows}, {r["gold_id"] for r in rows if r.get("gold_id")}


def draw_pilot(clauses, n_per_lang, exclude, taken, seed):
    rng = random.Random(seed)
    by_record = defaultdict(list)
    for c in clauses:
        by_record[c["record_id"]].append(c)
    for seq in by_record.values():
        seq.sort(key=lambda c: c["position"])
    rows, key = [], []
    for lang in ("hi", "en"):
        pools = {r: [c for c in seq if c["is_finite"] and c["clause_id"] not in exclude]
                 for r, seq in sorted(by_record.items()) if seq[0]["lang"] == lang and split_of(r) == "dev"}
        texts = sorted(r for r, p in pools.items() if p)
        rng.shuffle(texts)
        picked, used = [], set()
        while len(picked) < n_per_lang and texts:
            for r in texts:
                left = [c for c in pools[r] if c["clause_id"] not in used]
                if left and len(picked) < n_per_lang:
                    c = rng.choice(left)
                    used.add(c["clause_id"])
                    picked.append(c)
            if not any(c["clause_id"] not in used for r in texts for c in pools[r]):
                break
        for gid, c in zip(new_ids(len(picked), taken, rng), picked):
            before, after = context(by_record, c)
            rows.append(dict(gold_id=gid, lang=lang, context_before=before, clause_text=c["clause_text"],
                             span_text=c["span_text"], context_after=after))
            key.append(dict(gold_id=gid, clause_id=c["clause_id"], record_id=c["record_id"], lang=lang,
                            position=c["position"], in_component_subset=0, lexicon_hit="",
                            clause_sha1=hashlib.sha1(c["clause_text"].encode("utf-8")).hexdigest()))
    rng.shuffle(rows)
    return rows, key


def shortform_placeholders(n, taken, rng):
    ids = new_ids(n, taken, rng)
    return [dict(slot_id=f"SF-{i + 1:03d}", gold_id=gid, lang="hi" if i < n // 2 else "en",
                 genre="short_form", status="pending: short-form clauses not parsed yet")
            for i, gid in enumerate(ids)]


def components_list(lexicon_dir):
    with open(Path(lexicon_dir) / "entry_vectors.csv", encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    return [c for c in header if c not in ("entry_id", "lang", "names_emotion")]


PROVENANCE_COLUMNS = {"provenance", "corrections"}
MACHINE_COLUMNS = {"clause_id", "record_id", "split", "lexicon_hit", "in_component_subset", "source_url", "position",
                   "clause_sha1", "evidence", "referent_class", "target_class", "honorific"}


def assert_blind(path, allowed):
    with open(path, encoding="utf-8", newline="") as fh:
        header = next(csv.reader(fh))
    extra = [c for c in header if (c not in allowed and c not in PROVENANCE_COLUMNS) or c in MACHINE_COLUMNS]
    if extra:
        raise ValueError(f"{path}: not blind, columns {extra}")
    return header


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def loss_mix(key_rows, text_meta_path):
    if not Path(text_meta_path).exists():
        return {}
    with open(text_meta_path, encoding="utf-8", newline="") as fh:
        loss = {r["record_id"]: r["loss_type"] for r in csv.DictReader(fh)}
    out = defaultdict(lambda: defaultdict(int))
    for k in key_rows:
        out[k["lang"]][loss.get(k["record_id"], "unknown")] += 1
    return {lg: dict(sorted(v.items())) for lg, v in out.items()}


def coded_sheets(out, version, comps):
    fields = {f"gold_sheet_{version}_coder1.csv": list(CODEBOOK), f"gold_sheet_{version}_coder2.csv": list(CODEBOOK),
              f"gold_components_{version}_coder1.csv": comps, f"gold_components_{version}_coder2.csv": comps,
              "gold_pilot_r1.csv": list(CODEBOOK), "gold_pilot_r2.csv": list(CODEBOOK)}
    found = []
    for name, cols in fields.items():
        path = Path(out) / name
        if path.exists():
            with open(path, encoding="utf-8", newline="") as fh:
                if any((r.get(c) or "").strip() for r in csv.DictReader(fh) for c in cols + ["notes"]):
                    found.append(name)
    return found


def write_csv(path, rows, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--in", dest="inp", default=str(ROOT / "data/processed/clauses.jsonl"))
    ap.add_argument("--features", default=str(ROOT / "data/processed/clause_features.csv"))
    ap.add_argument("--lexicon-dir", default=str(ROOT / "lexicon"))
    ap.add_argument("--released-ids", default=str(ROOT / "data/annotation/released_annotation_ids.csv"))
    ap.add_argument("--split-out", default=str(ROOT / "data/processed/split.csv"))
    ap.add_argument("--out-dir", default=str(ROOT / "data/annotation"))
    ap.add_argument("--version", default="v1")
    ap.add_argument("--n-per-lang", type=int, default=100)
    ap.add_argument("--max-text-share", type=float, default=0.07)
    ap.add_argument("--n-components", type=int, default=100)
    ap.add_argument("--n-shortform", type=int, default=400)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--dry-run", action="store_true", help="provisional draw; may be overwritten later")
    ap.add_argument("--pilot", action="store_true", help="draw only the calibration pilot (gold_pilot_*)")
    ap.add_argument("--replace-final", action="store_true",
                    help="replace a final draw of this --version; refused unless every coder and pilot sheet of the "
                         "version is still blank; the replaced manifest is archived next to it")
    ap.add_argument("--pilot-n", type=int, default=20)
    args = ap.parse_args(argv)

    out = Path(args.out_dir)
    v = args.version
    from codebook_examples import example_ids
    if args.pilot:
        clauses = load_clauses(args.inp)
        exclude = set(example_ids())
        main_key = out / f"gold_key_{v}.csv"
        if main_key.exists():
            with open(main_key, encoding="utf-8") as fh:
                exclude |= {r["clause_id"] for r in csv.DictReader(fh)}
        taken = set()
        for path in (Path(args.released_ids), main_key):
            if path.exists():
                with open(path, encoding="utf-8") as fh:
                    taken |= {r.get("annotation_id") or r.get("gold_id") for r in csv.DictReader(fh)}
        rows, key = draw_pilot(clauses, args.pilot_n, exclude, taken, args.seed + 2)
        for coder in ("_r1", "_r2"):
            write_csv(out / f"gold_pilot{coder}.csv", rows, SHEET_COLUMNS)
            assert_blind(out / f"gold_pilot{coder}.csv", SHEET_COLUMNS)
        write_csv(out / "gold_pilot_key.csv", key, KEY_COLUMNS)
        for lang in ("hi", "en"):
            ks = [k for k in key if k["lang"] == lang]
            print(f"pilot {lang}: {len(ks)} clauses from {len({k['record_id'] for k in ks})} dev texts")
        return
    manifest_path = out / f"gold_manifest_{v}.json"
    if manifest_path.exists() and json.loads(manifest_path.read_text())["draw_status"] == "final":
        if not args.replace_final:
            raise SystemExit(f"{manifest_path} is a final draw; refusing to overwrite (use a new --version, or "
                             "--replace-final while nothing has been coded)")
        coded = coded_sheets(out, v, components_list(args.lexicon_dir))
        if coded:
            raise SystemExit(f"refusing --replace-final: coding has begun in {coded}")
        archive = manifest_path.with_name(f"gold_manifest_{v}.replaced-{time.strftime('%Y%m%dT%H%M%S')}.json")
        archive.write_text(manifest_path.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"replacing the uncoded final draw; previous manifest archived as {archive.name}")

    clauses = load_clauses(args.inp)
    records = sorted({(c["record_id"], c["lang"]) for c in clauses})
    write_csv(Path(args.split_out), [dict(record_id=r, split=split_of(r)) for r, _ in records],
              ["record_id", "split"])

    taken = set()
    if Path(args.released_ids).exists():
        with open(args.released_ids, encoding="utf-8") as fh:
            taken = {r["annotation_id"] for r in csv.DictReader(fh)}
    exclude, pilot_taken = pilot_exclusions(out / "gold_pilot_key.csv")
    taken |= pilot_taken
    hits = load_lexicon_hits(args.features)
    rows, key, report = draw(clauses, args.n_per_lang, args.max_text_share, args.n_components, hits, taken,
                             args.seed, exclude=set(example_ids()) | exclude)
    placeholders = shortform_placeholders(args.n_shortform, taken, random.Random(args.seed + 1))

    comps = components_list(args.lexicon_dir)
    comp_rows = [r for r in rows if r["_comp"]]
    for coder in ("", "_coder1", "_coder2"):
        write_csv(out / f"gold_sheet_{v}{coder}.csv", rows, SHEET_COLUMNS)
        write_csv(out / f"gold_components_{v}{coder}.csv", comp_rows, SHEET_TEXT + comps + ["notes"])
        assert_blind(out / f"gold_sheet_{v}{coder}.csv", SHEET_COLUMNS)
        assert_blind(out / f"gold_components_{v}{coder}.csv", SHEET_TEXT + comps + ["notes"])
    write_csv(out / f"gold_shortform_placeholder_{v}.csv", placeholders,
              ["slot_id", "gold_id", "lang", "genre", "status"])
    write_csv(out / f"gold_key_{v}.csv", key, KEY_COLUMNS)

    manifest = dict(draw_status="dry_run" if args.dry_run else "final",
                    drawn_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"), seed=args.seed, input=args.inp,
                    input_records=len(records), dev_share_rule=f"sha256('{SPLIT_NS}'+record_id) < {DEV_SHARE}",
                    max_text_share=args.max_text_share, per_language=report,
                    shortform_placeholders=len(placeholders), codebook=CODEBOOK, components=comps,
                    lexicon_hits_available=bool(hits), input_sha256=sha256_file(args.inp),
                    excluded=dict(codebook_examples=len(example_ids()), pilot_clauses=len(exclude)),
                    loss_type_mix=loss_mix(key, Path(args.split_out).with_name("text_meta.csv")))
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(draw_status=manifest["draw_status"], per_language=report), indent=2))
    for lang, r in report.items():
        if r["shortfall"]:
            print(f"WARNING {lang}: {r['shortfall']} clauses short of {r['target']} -- {r['texts_drawn_from']} dev "
                  f"texts x cap {r['cap_per_text']}; the cap is not relaxed, the corpus needs more dev texts")


if __name__ == "__main__":
    main()
