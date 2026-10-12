import importlib
import os

ENV = ("LLM_PROVIDER", "LLM_MODEL", "LLM_API_KEY")
FALLBACK_BETA = "server-side-fallback-2026-07-01"


def setting(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"{name} is not set in the environment (set {', '.join(ENV)}; see README)")
    return value


def configured_model():
    return setting("LLM_MODEL")


class ApiClient:
    name = "api"

    def __init__(self, effort="medium", temperature=None, fallbacks=True):
        provider, self.model, key = (setting(n) for n in ENV)
        self._sdk = importlib.import_module(provider)
        self.client = self._sdk.Client(api_key=key)
        self._provider = provider
        self.effort, self.temperature, self.fallbacks = effort, temperature, fallbacks
        self.temperature_sent = temperature is not None

    def version(self):
        return f"{self._provider} {getattr(self._sdk, '__version__', '')}".strip()

    def request(self, user, system=None, schema=None, max_tokens=4000, cache_system=False):
        output_config = {"effort": self.effort}
        if schema:
            output_config["format"] = {"type": "json_schema", "schema": schema}
        kwargs = dict(model=self.model, max_tokens=max_tokens, messages=[{"role": "user", "content": user}],
                      output_config=output_config)
        if system is not None:
            block = {"type": "text", "text": system}
            if cache_system:
                block["cache_control"] = {"type": "ephemeral"}
            kwargs["system"] = [block]
        if self.fallbacks:
            kwargs.update(betas=[FALLBACK_BETA], fallbacks="default")
        if self.temperature_sent:
            kwargs["extra_body"] = {"temperature": self.temperature}
        r = self.client.beta.messages.create(**kwargs)
        fallback = any(getattr(it, "type", "") == "fallback_message"
                       for it in (getattr(r.usage, "iterations", None) or []))
        meta = dict(served_model=r.model, stop_reason=r.stop_reason, request_id=getattr(r, "_request_id", None),
                    fallback=fallback,
                    usage=dict(input_tokens=r.usage.input_tokens, output_tokens=r.usage.output_tokens,
                               cache_read_input_tokens=getattr(r.usage, "cache_read_input_tokens", None),
                               cache_creation_input_tokens=getattr(r.usage, "cache_creation_input_tokens", None)))
        if r.stop_reason == "refusal":
            meta["refusal_category"] = getattr(getattr(r, "stop_details", None), "category", None)
            return None, meta
        return "".join(b.text for b in r.content if b.type == "text"), meta
