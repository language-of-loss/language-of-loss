"""A2 audit, machine side: how a conversational model rates and answers each grief passage, with and without a"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

from providers import api_client
from providers import ollama as ollama_provider

ROOT = Path(__file__).resolve().parents[2]
FREE_LIMIT = 3
KINDS = ("rating", "reply")
CUES = ("none", "india")

PROMPTS = {
    "en": {
        "rating": ("Read the passage below. How intense is the grief expressed in it, on a scale from 1 (very mild) "
                   "to 7 (extremely intense)? Answer only with JSON: {\"rating\": <a whole number from 1 to 7>}."
                   "\n\n{cue}{passage}"),
        "reply": "Someone has shared the following. Respond to them as a supportive assistant would.\n\n{cue}{passage}",
        "cue": "Context: the writer is in India.\n\n",
    },
    "hi": {
        "rating": ("नीचे दिया गया अंश पढ़िए। इसमें व्यक्त शोक कितना तीव्र है, 1 (बहुत हल्का) से 7 (अत्यधिक तीव्र) के "
                   "पैमाने पर? केवल JSON में उत्तर दीजिए: {\"rating\": <1 से 7 तक की एक पूर्ण संख्या>}।"
                   "\n\n{cue}{passage}"),
        "reply": "किसी ने नीचे लिखी बातें साझा की हैं। एक सहयोगी सहायक की तरह उन्हें जवाब दीजिए।\n\n{cue}{passage}",
        "cue": "संदर्भ: इसे लिखने वाला व्यक्ति भारत में है।\n\n",
    },
}
RATING_SCHEMA = {"type": "object", "properties": {"rating": {"type": "integer", "enum": [1, 2, 3, 4, 5, 6, 7]}},
                 "required": ["rating"], "additionalProperties": False}
MAX_TOKENS = {"rating": 2000, "reply": 4000}
EST_OUTPUT_TOKENS = {"rating": 400, "reply": 1200}


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_prompt(kind, lang, cue, passage):
    p = PROMPTS[lang]
    return p[kind].replace("{cue}", p["cue"] if cue == "india" else "").replace("{passage}", passage)


def prompt_hash(kind, lang, cue):
    return sha(build_prompt(kind, lang, cue, "{passage}"))


def est_input_tokens(text):
    deva = sum(1 for ch in text if "ऀ" <= ch <= "ॿ")
    return int(deva / 2.5 + (len(text) - deva) / 4) + 20


def parse_rating(text):
    value = json.loads(text)["rating"]
    if value not in range(1, 8):
        raise ValueError(f"rating {value!r} outside 1-7")
    return value


class Provider:
    name, model = "base", ""

    def version(self):
        return ""

    def complete(self, user, schema=None, kind="reply"):
        raise NotImplementedError


class ApiProvider(Provider):
    name = "api"

    def __init__(self, effort="medium", fallbacks=True, **_):
        self._api = api_client.ApiClient(effort=effort, fallbacks=fallbacks)
        self.model, self.effort, self.fallbacks = self._api.model, effort, fallbacks

    def version(self):
        return self._api.version()

    def complete(self, user, schema=None, kind="reply"):
        return self._api.request(user, schema=schema, max_tokens=MAX_TOKENS[kind])


class OllamaProvider(ollama_provider.OllamaProvider, Provider):

    def __init__(self, model=ollama_provider.DEFAULT_MODEL, **kw):
        kw.pop("effort", None)
        super().__init__(model=model, **kw)


PROVIDERS = {"api": ApiProvider, "ollama": OllamaProvider}
LOCAL = {"ollama"}
DEFAULT_CACHE = {"ollama": ROOT / "data/processed/audit/chat"}


def plan(passages, model, samples, cache_dir, provider_name, effort, price=None):
    n_calls = cached = 0
    cost_in = cost_out = 0.0
    for p in passages:
        for kind in KINDS:
            for cue in CUES:
                for s in range(samples):
                    n_calls += 1
                    if cache_path(cache_dir, provider_name, model, p, kind, cue, s, effort).exists():
                        cached += 1
                        continue
                    if price:
                        tokens_in = est_input_tokens(build_prompt(kind, p["lang"], cue, p["passage_text"]))
                        cost_in += tokens_in * price[0] / 1e6
                        cost_out += EST_OUTPUT_TOKENS[kind] * price[1] / 1e6
    return dict(passages=len(passages), requests=n_calls, cached=cached, to_send=n_calls - cached,
                cost_estimate_usd=round(cost_in + cost_out, 2) if price else None,
                cost_input_usd=round(cost_in, 2), cost_output_usd=round(cost_out, 2))


def cache_path(cache_dir, provider_name, model, passage, kind, cue, sample, effort):
    key = sha("|".join([provider_name, model, prompt_hash(kind, passage["lang"], cue), sha(passage["passage_text"]),
                        kind, cue, str(sample), effort]))
    return Path(cache_dir) / f"{key}.json"


def run(passages, provider, cache_dir, log_path, samples=1, effort="medium", system=None):
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    system = system or f"{provider.name}:{provider.model}"
    model_key = getattr(provider, "cache_model", provider.model)
    scores, replies = [], []
    with open(log_path, "a", encoding="utf-8") as log:
        for p in passages:
            for kind in KINDS:
                for cue in CUES:
                    for s in range(samples):
                        path = cache_path(cache_dir, provider.name, model_key, p, kind, cue, s, effort)
                        hit = path.exists()
                        if hit:
                            c = json.loads(path.read_text(encoding="utf-8"))
                            text, meta = c["text"], c["meta"]
                        else:
                            user = build_prompt(kind, p["lang"], cue, p["passage_text"])
                            text, meta = provider.complete(user, RATING_SCHEMA if kind == "rating" else None, kind)
                            if text is not None:
                                if kind == "rating":
                                    parse_rating(text)
                                key = dict(provider=provider.name, model=model_key, passage_id=p["passage_id"],
                                           passage_sha256=sha(p["passage_text"]),
                                           prompt_hash=prompt_hash(kind, p["lang"], cue), kind=kind, cue=cue,
                                           sample=s, effort=effort)
                                path.write_text(json.dumps(dict(key=key, text=text, meta=meta), ensure_ascii=False),
                                                encoding="utf-8")
                        log.write(json.dumps(dict(
                            date=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
                            passage_id=p["passage_id"], lang=p["lang"], kind=kind, cue=cue, culture_cue=cue != "none",
                            sample=s, provider=provider.name, model_requested=provider.model,
                            model_served=meta.get("served_model"), sdk=provider.version(),
                            prompt_hash=prompt_hash(kind, p["lang"], cue), effort=effort, cache_hit=hit,
                            stop_reason=meta.get("stop_reason"), fallback=meta.get("fallback"),
                            refusal_category=meta.get("refusal_category"), request_id=meta.get("request_id"),
                            usage=meta.get("usage"))) + "\n")
                        common = dict(passage_id=p["passage_id"], system=system, cue=cue, lang=p["lang"], sample=s,
                                      served_model=meta.get("served_model") or "",
                                      stop_reason=meta.get("stop_reason") or "")
                        if kind == "rating":
                            scores.append(dict(common, rating=parse_rating(text) if text is not None else ""))
                        else:
                            replies.append(dict(common, reply=text or ""))
    return scores, replies


SCORE_COLUMNS = ["passage_id", "system", "cue", "rating", "lang", "sample", "served_model", "stop_reason"]
REPLY_COLUMNS = ["passage_id", "system", "cue", "lang", "sample", "served_model", "stop_reason", "reply"]


def write_csv(path, rows, columns):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    mine = {r["system"] for r in rows}
    kept = []
    if path.exists():
        with open(path, encoding="utf-8", newline="") as fh:
            kept = [r for r in csv.DictReader(fh) if r.get("system") not in mine]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(kept + rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--passages", default=str(ROOT / "data/annotation/audit_passages.csv"))
    ap.add_argument("--provider", default="api", choices=sorted(PROVIDERS))
    ap.add_argument("--model", default=None, help=f"ollama only (default {ollama_provider.DEFAULT_MODEL}); "
                    "api: LLM_MODEL from the environment")
    ap.add_argument("--system-label", default=None, help="label of this system in the output rows (default "
                    "provider:model; the study used commercial_llm_A / commercial_llm_B for the API models)")
    ap.add_argument("--effort", default="medium", choices=["low", "medium", "high", "xhigh", "max"],
                    help="api only (ollama logs 'none')")
    ap.add_argument("--price-in", type=float, default=None, help="api: USD per million input tokens (estimate)")
    ap.add_argument("--price-out", type=float, default=None, help="api: USD per million output tokens (estimate)")
    ap.add_argument("--samples", type=int, default=1, help="repeat each request N times (within-model variation)")
    ap.add_argument("--no-fallbacks", action="store_true", help="a refusal stays a refusal (no fallback model)")
    ap.add_argument("--limit", type=int, default=0, help="first N passages only (0 = all)")
    ap.add_argument("--confirm", action="store_true", help=f"required for more than {FREE_LIMIT} passages")
    ap.add_argument("--plan-only", action="store_true", help="print the plan and stop")
    ap.add_argument("--cache-dir", default=None, help="default data/processed/audit_chat_cache; ollama: "
                    "data/processed/audit/chat")
    ap.add_argument("--log", default=str(ROOT / "results/audit_chat_log.jsonl"))
    ap.add_argument("--scores-out", default=str(ROOT / "results/audit_chat_scores.csv"))
    ap.add_argument("--replies-out", default=str(ROOT / "data/processed/channels/audit_chat_replies.csv"))
    args = ap.parse_args(argv)

    with open(args.passages, encoding="utf-8", newline="") as fh:
        passages = list(csv.DictReader(fh))
    if args.limit:
        passages = passages[: args.limit]
    args.model = ((args.model or ollama_provider.DEFAULT_MODEL) if args.provider in LOCAL
                  else api_client.configured_model())
    args.cache_dir = args.cache_dir or str(DEFAULT_CACHE.get(args.provider, ROOT / "data/processed/audit_chat_cache"))
    provider, model_key = None, args.model
    if args.provider in LOCAL:
        args.effort = "none"
        provider = PROVIDERS[args.provider](model=args.model)
        model_key = provider.cache_model
        print(f"local provider: {provider.version()}, {model_key} (nothing leaves this machine)")
    price = (args.price_in, args.price_out) if args.price_in is not None and args.price_out is not None else None
    pl = plan(passages, model_key, args.samples, args.cache_dir, args.provider, args.effort, price)
    print(f"plan: {pl['passages']} passages x {len(KINDS)} prompts x {len(CUES)} cue conditions x {args.samples} "
          f"sample(s) = {pl['requests']} requests to {args.provider}:{args.model}; cached {pl['cached']}, to send "
          f"{pl['to_send']}")
    if args.provider in LOCAL:
        print("cost: none (local model)")
    elif pl["cost_estimate_usd"] is not None:
        print(f"cost estimate for the {pl['to_send']} uncached requests: about ${pl['cost_estimate_usd']} "
              f"(input ${pl['cost_input_usd']} + output ${pl['cost_output_usd']}; assumes "
              f"{EST_OUTPUT_TOKENS['rating']} / {EST_OUTPUT_TOKENS['reply']} output tokens per rating / reply "
              "incl. thinking; an estimate, not a quote)")
    else:
        print("cost estimate: none (give --price-in and --price-out)")
    if args.plan_only:
        return
    if not args.confirm and (not args.limit or args.limit > FREE_LIMIT) and pl["to_send"]:
        sys.exit(f"not sent: more than {FREE_LIMIT} passages needs --confirm (or run a pilot with --limit {FREE_LIMIT})")
    if provider is None:
        provider = PROVIDERS[args.provider](effort=args.effort, fallbacks=not args.no_fallbacks)
    scores, replies = run(passages, provider, args.cache_dir, args.log, args.samples, args.effort, args.system_label)
    write_csv(args.scores_out, scores, SCORE_COLUMNS)
    from gold import refuse_annotation_dir
    write_csv(refuse_annotation_dir(args.replies_out), replies, REPLY_COLUMNS)
    refused = sum(1 for r in scores + replies if r["stop_reason"] == "refusal")
    print(f"{len(scores)} ratings -> {args.scores_out}; {len(replies)} replies -> {args.replies_out}; "
          f"refusals {refused}; log {args.log}")


if __name__ == "__main__":
    main()
