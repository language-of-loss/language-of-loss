"""Reader study kit (output 5 human standard from outside readers): blocks, reply exchanges, the Forms script."""
import argparse
import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEED = 20261011
N_BLOCKS = 10
PER_LANG = 15
N_REPLIES_PER_LANG = 5
OUT = ROOT / "docs" / "reader_study"
CACHES = [("api", ROOT / "data/processed/audit_chat_cache"), ("ollama", ROOT / "data/processed/audit/chat")]
TEMPLATE = ROOT / "tools" / "make_reader_forms.gs"
DATA_MARK = "/*@@KIT_DATA@@*/null"
REPLY_PROMPT_NOTE = "Someone has shared the following. Respond to them as a supportive assistant would."


def read(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    return path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def assign_blocks(passages, loss, seed=SEED, n_blocks=N_BLOCKS, per_lang=PER_LANG):
    rng = random.Random(seed)
    blocks = defaultdict(list)
    for lang in ("hi", "en"):
        rows = sorted((p for p in passages if p["lang"] == lang), key=lambda p: p["passage_id"])
        if len(rows) != n_blocks * per_lang:
            raise SystemExit(f"{lang}: {len(rows)} long-form passages, need exactly {n_blocks * per_lang}")
        text_key = {r: rng.random() for r in sorted({p["record_id"] for p in rows})}
        own_key = {p["passage_id"]: rng.random() for p in rows}
        rows.sort(key=lambda p: (loss.get(p["record_id"], "unknown"), text_key[p["record_id"]], own_key[p["passage_id"]]))
        for i, p in enumerate(rows):
            blocks[i % n_blocks].append(dict(p, loss_type=loss.get(p["record_id"], "unknown")))
    out = []
    for b in range(n_blocks):
        items = sorted(blocks[b], key=lambda p: p["passage_id"])
        rng.shuffle(items)
        out += [dict(p, block=b + 1, position=i + 1) for i, p in enumerate(items)]
    return out


def cached_answers(cache_dir):
    out = {}
    d = Path(cache_dir)
    if not d.is_dir():
        return out
    for f in sorted(d.glob("*.json")):
        try:
            c = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        k = c.get("key") or {}
        if k.get("cue") != "none" or int(k.get("sample", 0)) != 0 or c.get("text") is None:
            continue
        out[(k.get("passage_id"), k.get("kind"))] = (c["text"], (c.get("meta") or {}).get("served_model", ""),
                                                      k.get("model", ""))
    return out


def parse_rating(text):
    try:
        v = json.loads(text)["rating"]
    except (ValueError, KeyError, TypeError):
        return None
    return int(v) if isinstance(v, (int, float)) and 1 <= v <= 7 else None


def candidates(answers, passages, provider):
    out = []
    for p in passages:
        rep, rat = answers.get((p["passage_id"], "reply")), answers.get((p["passage_id"], "rating"))
        if not rep or not rat or parse_rating(rat[0]) is None:
            continue
        out.append(dict(passage_id=p["passage_id"], lang=p["lang"], record_id=p["record_id"],
                        passage_text=p["passage_text"], reply=rep[0], served_model=rep[1],
                        system=f"{provider}:{rep[2].split('@')[0] if provider == 'ollama' else rep[2]}",
                        cue="none", model_rating=parse_rating(rat[0])))
    return out


def spread(cands, k=N_REPLIES_PER_LANG, seed=SEED):
    if len(cands) <= k:
        return sorted(cands, key=lambda c: (c["model_rating"], c["passage_id"]))
    rng = random.Random(seed)
    tie = {c["passage_id"]: rng.random() for c in sorted(cands, key=lambda c: c["passage_id"])}
    lo, hi = min(c["model_rating"] for c in cands), max(c["model_rating"] for c in cands)
    targets = [lo + (hi - lo) * i / (k - 1) for i in range(k)]
    chosen, texts = [], set()
    for t in targets:
        pool = [c for c in cands if c not in chosen]
        best = min(pool, key=lambda c: (abs(c["model_rating"] - t), c["record_id"] in texts, tie[c["passage_id"]]))
        chosen.append(best)
        texts.add(best["record_id"])
    return sorted(chosen, key=lambda c: (c["model_rating"], c["passage_id"]))


def select_replies(passages, caches=CACHES, k=N_REPLIES_PER_LANG, seed=SEED):
    per_source = [(name, candidates(cached_answers(d), passages, name)) for name, d in caches]
    rows, shortfall, sources = [], {}, {}
    for lang in ("hi", "en"):
        options = [(name, [c for c in cands if c["lang"] == lang]) for name, cands in per_source]
        full = [o for o in options if len(o[1]) >= k]
        name, pool = full[0] if full else max(options, key=lambda o: len(o[1]))
        picked = spread(pool, k, seed)
        sources[lang] = name if picked else None
        if len(picked) < k:
            shortfall[lang] = k - len(picked)
        rows += picked
    for i, r in enumerate(rows):
        r["exchange_id"] = f"R{i + 1:02d}"
    return rows, shortfall, sources


def section(md_path, heading=None):
    text = Path(md_path).read_text(encoding="utf-8") if Path(md_path).exists() else ""
    return "\n".join(l for l in text.splitlines() if not l.startswith("<!--")).strip()


def split_parts(text):
    parts, cur = {"passages": [], "replies": []}, None
    for line in text.splitlines():
        if line.startswith("## Part 1"):
            cur = "passages"
        elif line.startswith("## Part 2"):
            cur = "replies"
        elif line.startswith("#"):
            cur = None if line.startswith("# ") else cur
        elif cur:
            parts[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in parts.items()}


def forms_script(blocks, replies, consent, instructions, template=TEMPLATE):
    data = dict(
        title="Grief reading study, Block ",
        consent=consent,
        instructions=split_parts(instructions),
        blocks={str(b): [dict(code=f"B{b:02d}-{r['position']:02d}", passage_id=r["passage_id"],
                              text=r["passage_text"]) for r in sorted(blocks, key=lambda r: r["position"])
                         if r["block"] == b]
                for b in sorted({r["block"] for r in blocks})},
        replies=[dict(code=r["exchange_id"], passage_id=r["passage_id"], passage=r["passage_text"], reply=r["reply"])
                 for r in replies],
    )
    src = Path(template).read_text(encoding="utf-8")
    if DATA_MARK not in src:
        raise SystemExit(f"{template}: data marker {DATA_MARK} not found")
    return src.replace(DATA_MARK, json.dumps(data, ensure_ascii=False, indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--passages", default=str(ROOT / "data/annotation/audit_passages.csv"))
    ap.add_argument("--text-meta", default=str(ROOT / "data/processed/text_meta.csv"))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--seed", type=int, default=SEED)
    a = ap.parse_args(argv)
    out = Path(a.out)
    passages = [p for p in read(a.passages) if p["register"] == "long"]
    loss = {r["record_id"]: r["loss_type"] for r in read(a.text_meta)}
    blocks = assign_blocks(passages, loss, a.seed)
    write(out / "blocks.csv", blocks, ["block", "position", "passage_id", "lang", "loss_type", "record_id",
                                       "passage_text"])
    write(out / "block_assignment.csv", blocks, ["block", "position", "passage_id", "lang"])
    replies, shortfall, sources = select_replies(passages, seed=a.seed)
    write(out / "replies.csv", replies, ["exchange_id", "passage_id", "lang", "system", "served_model", "cue",
                                         "model_rating", "passage_text", "reply"])
    gs = forms_script(blocks, replies, section(out / "consent.md"), section(out / "instructions.md"))
    (out / "make_reader_forms.gs").write_text(gs, encoding="utf-8")
    manifest = dict(seed=a.seed, passages_sha256=sha(a.passages), text_meta_sha256=sha(a.text_meta),
                    n_blocks=N_BLOCKS, per_block=Counter(r["block"] for r in blocks),
                    loss_type_by_lang=Counter(f"{r['lang']}:{r['loss_type']}" for r in blocks),
                    replies=[{k: r[k] for k in ("exchange_id", "passage_id", "lang", "system", "served_model",
                                                "model_rating")} for r in replies],
                    reply_source=sources, reply_shortfall=shortfall)
    (out / "kit_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"{len(blocks)} passages in {N_BLOCKS} blocks -> {out}/blocks.csv; replies: {len(replies)} "
          f"(source {sources}; shortfall {shortfall or 'none'}) -> {out}/replies.csv, make_reader_forms.gs")
    if shortfall:
        print("WARNING: too few cached no-cue replies; re-run `make reader-kit` when the audit_chat cache is complete")


if __name__ == "__main__":
    main()
