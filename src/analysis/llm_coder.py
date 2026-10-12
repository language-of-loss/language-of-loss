"""LLM coding channel: code clauses with the gold codebook through an LLM, in the gold-sheet schema."""
import argparse
import csv
import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

from gold import CODEBOOK, SHEET_COLUMNS, refuse_annotation_dir
from providers import api_client

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN_INPUTS = ("gold_sheet_", "gold_components_")
TASK = """Code the clause below with the codebook in your instructions. Code only the clause marked CLAUSE; use \
the clause before and after for context (who is speaking, dropped subjects, who died). Return one value for every \
field, spelled exactly as in the codebook, and a short note (in English) only if something was uncertain; \
otherwise an empty note.

Language: {lang_name}

CLAUSE BEFORE:
{before}

CLAUSE:
{clause}

CLAUSE AFTER:
{after}"""
LANG_NAME = {"hi": "Hindi (Devanagari)", "en": "English"}


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def output_schema():
    props = {f: {"type": "string", "enum": list(v)} for f, v in CODEBOOK.items()}
    props["notes"] = {"type": "string"}
    return {"type": "object", "properties": props, "required": list(CODEBOOK) + ["notes"],
            "additionalProperties": False}


def user_message(row):
    return TASK.format(lang_name=LANG_NAME.get(row["lang"], row["lang"]), before=row["context_before"] or "(none)",
                       clause=row["clause_text"], after=row["context_after"] or "(none)")


def validate(answer):
    for f, values in CODEBOOK.items():
        if answer.get(f) not in values:
            raise ValueError(f"{f}={answer.get(f)!r} not in codebook")
    return answer


class Provider:
    name = "base"
    model = ""

    def version(self):
        return ""

    def code(self, system, user, schema):
        raise NotImplementedError


class ApiProvider(Provider):
    name = "api"

    def __init__(self, effort="medium", temperature=None, max_tokens=4000, fallbacks=True):
        self._api = api_client.ApiClient(effort=effort, temperature=temperature, fallbacks=fallbacks)
        self.model, self.effort, self.max_tokens = self._api.model, effort, max_tokens
        self.temperature_sent = self._api.temperature_sent

    def version(self):
        return self._api.version()

    def code(self, system, user, schema):
        text, meta = self._api.request(user, system=system, schema=schema, max_tokens=self.max_tokens,
                                       cache_system=True)
        if text is None or meta["stop_reason"] == "max_tokens":
            return None, meta
        return json.loads(text), meta


PROVIDERS = {"api": ApiProvider}


def cache_key(provider_name, model, prompt_hash, schema_hash, effort, row):
    clause_hash = sha("\x1f".join([row["lang"], row["context_before"], row["clause_text"], row["context_after"]]))
    return clause_hash, sha("|".join([provider_name, model, prompt_hash, schema_hash, effort, clause_hash]))


EST_OUTPUT_TOKENS = 450


def plan(rows, system, provider_name, model, effort, cache_dir, price=None):
    from audit_chat import est_input_tokens
    prompt_hash, schema_hash = sha(system), sha(json.dumps(output_schema(), sort_keys=True))
    todo = [r for r in rows
            if not (Path(cache_dir) / f"{cache_key(provider_name, model, prompt_hash, schema_hash, effort, r)[1]}.json"
                    ).exists()]
    tok_in = sum(est_input_tokens(system) + est_input_tokens(user_message(r)) for r in todo)
    cost_in = tok_in * price[0] / 1e6 if price else None
    cost_out = len(todo) * EST_OUTPUT_TOKENS * price[1] / 1e6 if price else None
    return dict(requests=len(rows), cached=len(rows) - len(todo), to_send=len(todo), est_input_tokens=tok_in,
                cost_input_usd=round(cost_in, 2) if price else None,
                cost_output_usd=round(cost_out, 2) if price else None,
                cost_estimate_usd=round(cost_in + cost_out, 2) if price else None)


def run(rows, provider, system, cache_dir, log_path, effort=""):
    schema = output_schema()
    prompt_hash, schema_hash = sha(system), sha(json.dumps(schema, sort_keys=True))
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    out = []
    with open(log_path, "a", encoding="utf-8") as log:
        for row in rows:
            clause_hash, key = cache_key(provider.name, provider.model, prompt_hash, schema_hash, effort, row)
            path = cache_dir / f"{key}.json"
            hit = path.exists()
            if hit:
                cached = json.loads(path.read_text(encoding="utf-8"))
                answer, meta = cached["answer"], cached["meta"]
            else:
                answer, meta = provider.code(system, user_message(row), schema)
                if answer is not None:
                    validate(answer)
                    path.write_text(json.dumps(dict(answer=answer, meta=meta), ensure_ascii=False),
                                    encoding="utf-8")
            log.write(json.dumps(dict(
                date=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                gold_id=row["gold_id"], provider=provider.name, model_requested=provider.model,
                model_served=meta.get("served_model"), sdk=provider.version(), prompt_hash=prompt_hash,
                schema_hash=schema_hash, effort=effort, clause_hash=clause_hash, cache_key=key, cache_hit=hit,
                temperature_sent=getattr(provider, "temperature_sent", False), stop_reason=meta.get("stop_reason"),
                fallback=meta.get("fallback"), refusal_category=meta.get("refusal_category"),
                request_id=meta.get("request_id"), usage=meta.get("usage"))) + "\n")
            filled = {c: ("" if c in CODEBOOK else row.get(c, "")) for c in SHEET_COLUMNS}
            if answer is None:
                filled["notes"] = f"LLM: no answer (stop_reason={meta.get('stop_reason')})"
            else:
                filled.update({f: answer[f] for f in CODEBOOK})
                note = answer.get("notes", "")
                if meta.get("fallback"):
                    note = f"[served by fallback {meta.get('served_model')}] " + note
                filled["notes"] = note.strip()
            out.append(filled)
    return out


THIRD_TASK = """Code the clause below. Code only the clause marked CLAUSE; use the clause before and after for \
context (who is speaking, dropped subjects, who died). Give a value for each of these fields only: {fields}. Spell \
every value exactly as in your instructions, and add a short note (in English) only if something was uncertain; \
otherwise an empty note.

Language: {lang_name}

CLAUSE BEFORE:
{before}

CLAUSE:
{clause}

CLAUSE AFTER:
{after}"""
AG = ROOT / "data/processed/agreement"
THIRD_SHEETS = {
    "codebook": (AG / "gold_disagreements_gold_sheet_v1.csv", ROOT / "data/annotation/gold_sheet_v1_adjudicated.csv"),
    "components": (AG / "gold_disagreements_gold_components_v1.csv",
                   ROOT / "data/annotation/gold_components_v1_adjudicated.csv"),
}
THIRD_OUT = ROOT / "data/processed/channels/gold_third_coder_v1.csv"


def components_system(path=ROOT / "lexicon/components.csv"):
    with open(path, encoding="utf-8", newline="") as fh:
        comps = list(csv.DictReader(fh))
    lines = ["You code clauses from Hindi and English grief writing for semantic components. Each component is a "
             "meaning written in semantic primes. Code 1 when the clause itself carries that meaning (read with its "
             "context for who is speaking and who died), and 0 when it does not.", ""]
    for c in comps:
        lines.append(f"{c['component_id']}: \"{c['gloss_primes']}\". Hindi example: {c.get('example_hi', '')}. "
                     f"English example: {c.get('example_en', '')}.")
    return "\n".join(lines) + "\n"


def third_values(sheet, field):
    from gold import COMPONENT_VALUES
    return list(CODEBOOK[field]) if sheet == "codebook" else list(COMPONENT_VALUES)


def third_items(sheets=THIRD_SHEETS):
    items = {}
    for sheet, (dis_path, ctx_path) in sheets.items():
        with open(ctx_path, encoding="utf-8-sig", newline="") as fh:
            ctx = {r["gold_id"]: r for r in csv.DictReader(fh)}
        with open(dis_path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                c = ctx[r["gold_id"]]
                it = items.setdefault((sheet, r["gold_id"]), dict(
                    sheet=sheet, gold_id=r["gold_id"], lang=c["lang"], context_before=c["context_before"],
                    clause_text=c["clause_text"], context_after=c["context_after"], fields=[]))
                it["fields"].append(r["field"])
    return list(items.values())


def third_schema(item):
    props = {f: {"type": "string", "enum": third_values(item["sheet"], f)} for f in item["fields"]}
    props["notes"] = {"type": "string"}
    return {"type": "object", "properties": props, "required": list(item["fields"]) + ["notes"],
            "additionalProperties": False}


def third_message(item):
    return THIRD_TASK.format(fields=", ".join(item["fields"]), lang_name=LANG_NAME.get(item["lang"], item["lang"]),
                             before=item["context_before"] or "(none)", clause=item["clause_text"],
                             after=item["context_after"] or "(none)")


def third_plan(items, systems, provider_name, model, effort, cache_dir, price=None):
    from audit_chat import est_input_tokens
    todo = []
    for it in items:
        sys_text = systems[it["sheet"]]
        key = cache_key(provider_name, model, sha(sys_text), sha(json.dumps(third_schema(it), sort_keys=True)),
                        effort, it)[1]
        if not (Path(cache_dir) / f"{key}.json").exists():
            todo.append(it)
    tok_in = sum(est_input_tokens(systems[it["sheet"]]) + est_input_tokens(third_message(it)) for it in todo)
    cost = (tok_in * price[0] + len(todo) * EST_OUTPUT_TOKENS * price[1]) / 1e6 if price else None
    return dict(requests=len(items), cached=len(items) - len(todo), to_send=len(todo), est_input_tokens=tok_in,
                cost_estimate_usd=round(cost, 2) if price else None)


def run_third(items, provider, systems, cache_dir, log_path, effort=""):
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    out = []
    with open(log_path, "a", encoding="utf-8") as log:
        for it in items:
            system, schema = systems[it["sheet"]], third_schema(it)
            prompt_hash, schema_hash = sha(system), sha(json.dumps(schema, sort_keys=True))
            clause_hash, key = cache_key(provider.name, provider.model, prompt_hash, schema_hash, effort, it)
            path = cache_dir / f"{key}.json"
            hit = path.exists()
            if hit:
                cached = json.loads(path.read_text(encoding="utf-8"))
                answer, meta = cached["answer"], cached["meta"]
            else:
                answer, meta = provider.code(system, third_message(it), schema)
                if answer is not None:
                    for f in it["fields"]:
                        if answer.get(f) not in third_values(it["sheet"], f):
                            raise ValueError(f"{it['gold_id']} {f}={answer.get(f)!r} not allowed")
                    path.write_text(json.dumps(dict(answer=answer, meta=meta), ensure_ascii=False),
                                    encoding="utf-8")
            log.write(json.dumps(dict(
                date=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                task="third_coder", sheet=it["sheet"], gold_id=it["gold_id"], fields=it["fields"],
                provider=provider.name, model_requested=provider.model, model_served=meta.get("served_model"),
                sdk=provider.version(), prompt_hash=prompt_hash, schema_hash=schema_hash, effort=effort,
                clause_hash=clause_hash, cache_key=key, cache_hit=hit,
                temperature_sent=getattr(provider, "temperature_sent", False), stop_reason=meta.get("stop_reason"),
                fallback=meta.get("fallback"), refusal_category=meta.get("refusal_category"),
                request_id=meta.get("request_id"), usage=meta.get("usage"))) + "\n")
            note = "" if answer is None else (answer.get("notes") or "").strip()
            if answer is not None and meta.get("fallback"):
                note = f"[served by fallback {meta.get('served_model')}] " + note
            for f in it["fields"]:
                out.append(dict(sheet=it["sheet"], gold_id=it["gold_id"], lang=it["lang"], field=f,
                                third="" if answer is None else answer[f],
                                note=note if answer is not None
                                else f"LLM: no answer (stop_reason={meta.get('stop_reason')})",
                                model_served=meta.get("served_model") or ""))
    return out


def main_third(args):
    systems = {"codebook": Path(args.codebook).read_text(encoding="utf-8"), "components": components_system()}
    items = third_items()
    pl = third_plan(items, systems, args.provider, args.model, args.effort, args.cache_dir, price(args))
    print(f"third coder plan: {pl['requests']} requests ({sum(len(i['fields']) for i in items)} fields) to "
          f"{args.provider}:{args.model} (effort {args.effort}); cached {pl['cached']}, to send {pl['to_send']}; "
          f"upper-bound estimate ${pl['cost_estimate_usd']} (no prompt-cache discount, {EST_OUTPUT_TOKENS} output "
          f"tokens per request); cap ${args.max_usd}")
    if args.plan_only:
        return pl
    if pl["cost_estimate_usd"] is None or pl["cost_estimate_usd"] > args.max_usd:
        raise SystemExit(f"refused: estimate ${pl['cost_estimate_usd']} exceeds the cap ${args.max_usd} "
                         "(no estimate without --price-in and --price-out)")
    provider = PROVIDERS[args.provider](effort=args.effort, temperature=args.temperature)
    out = run_third(items, provider, systems, args.cache_dir, args.log, effort=args.effort)
    refuse_annotation_dir(args.out)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    missing = sum(1 for r in out if not r["third"])
    print(f"{len(out)} fields coded -> {args.out}; no answer: {missing}; log: {args.log}")
    if missing:
        sys.exit(2)
    return out


def price(args):
    return (args.price_in, args.price_out) if args.price_in is not None and args.price_out is not None else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--in", dest="inp", default=str(ROOT / "data/annotation/gold_pilot_r1.csv"))
    ap.add_argument("--out", default=str(ROOT / "data/processed/channels/gold_pilot_llm.csv"))
    ap.add_argument("--codebook", default=str(ROOT / "docs/codebook_v1.md"))
    ap.add_argument("--provider", default="api", choices=sorted(PROVIDERS))
    ap.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"])
    ap.add_argument("--temperature", type=float, default=None,
                    help="sent only when given (the model used rejects sampling parameters; logged)")
    ap.add_argument("--price-in", type=float, default=None, help="USD per million input tokens (cost estimate)")
    ap.add_argument("--price-out", type=float, default=None, help="USD per million output tokens (cost estimate)")
    ap.add_argument("--cache-dir", default=str(ROOT / "data/processed/llm_cache"))
    ap.add_argument("--log", default=str(ROOT / "results/llm_coder_log.jsonl"))
    ap.add_argument("--limit", type=int, default=0, help="code only the first N rows (0 = all)")
    ap.add_argument("--plan-only", action="store_true", help="print requests, cache hits and cost estimate; send nothing")
    ap.add_argument("--third-coder", action="store_true",
                    help="code only the disagreeing fields of the gold-set disagreements, blind (investigators' decision "
                         "2026-10-11); --out defaults to data/processed/channels/gold_third_coder_v1.csv")
    ap.add_argument("--max-usd", type=float, default=5.0, help="--third-coder: refuse if the estimate exceeds this")
    args = ap.parse_args(argv)
    args.model = api_client.configured_model()
    if args.third_coder:
        if args.out == ap.get_default("out"):
            args.out = str(THIRD_OUT)
        return main_third(args)

    if any(Path(args.inp).name.startswith(p) for p in FORBIDDEN_INPUTS):
        raise SystemExit(f"refusing {args.inp}: the LLM channel runs on the pilot only until it has been compared "
                         "with the human pilot coders")
    with open(args.inp, encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if args.limit:
        rows = rows[: args.limit]
    system = Path(args.codebook).read_text(encoding="utf-8")
    if args.plan_only:
        pl = plan(rows, system, args.provider, args.model, args.effort, args.cache_dir, price(args))
        print(f"plan: {pl['requests']} clauses to {args.provider}:{args.model} (effort {args.effort}); cached "
              f"{pl['cached']}, to send {pl['to_send']}")
        if pl["cost_estimate_usd"] is not None:
            print(f"cost estimate: about ${pl['cost_estimate_usd']} (input ${pl['cost_input_usd']}, no prompt-cache "
                  f"discount + output ${pl['cost_output_usd']} at {EST_OUTPUT_TOKENS} tokens per clause); an "
                  "estimate, not a quote")
        return pl
    provider = PROVIDERS[args.provider](effort=args.effort, temperature=args.temperature)
    out = run(rows, provider, system, args.cache_dir, args.log, effort=args.effort)
    refuse_annotation_dir(args.out)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SHEET_COLUMNS)
        w.writeheader()
        w.writerows(out)
    missing = sum(1 for r in out if r["notes"].startswith("LLM: no answer"))
    print(f"{len(out)} clauses coded -> {args.out}; no answer: {missing}; log: {args.log}")
    if missing:
        sys.exit(2)


if __name__ == "__main__":
    main()
