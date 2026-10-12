import hashlib
import ipaddress
import json
import urllib.parse
import urllib.request

DEFAULT_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "llama3.1:8b-instruct-q4_K_M"
OPTIONS = {"temperature": 0, "seed": 20261011, "num_ctx": 8192}
MAX_TOKENS = {"rating": 2000, "reply": 1024}
TIMEOUT_S = 900


def is_loopback(host_url):
    host = urllib.parse.urlparse(host_url).hostname or ""
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class OllamaProvider:
    name = "ollama"

    def __init__(self, model=DEFAULT_MODEL, host=DEFAULT_HOST, max_tokens=None, schema_ok=True, **_):
        if not is_loopback(host):
            raise SystemExit(f"refusing: Ollama host {host!r} is not a loopback address; the local provider must "
                             "never send passage text off this machine")
        self.model, self.host = model, host.rstrip("/")
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.max_tokens = dict(max_tokens or MAX_TOKENS)
        self._version = self._get("/api/version")["version"]
        tags = {m["name"]: m for m in self._get("/api/tags")["models"]}
        if model not in tags:
            raise SystemExit(f"model {model!r} is not pulled on this Ollama server (have: {sorted(tags) or 'none'}); "
                             f"run `ollama pull {model}`")
        self.digest = tags[model]["digest"]
        self.details = tags[model].get("details", {})
        self.model_id = f"{model}@sha256:{self.digest}"
        config = json.dumps(dict(options=OPTIONS, max_tokens=self.max_tokens), sort_keys=True)
        self.config_hash = hashlib.sha256(config.encode()).hexdigest()[:12]
        self.cache_model = f"{self.model_id}|gen:{self.config_hash}"

    def _get(self, path):
        with self._opener.open(self.host + path, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))

    def _post(self, path, body):
        req = urllib.request.Request(self.host + path, data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        with self._opener.open(req, timeout=TIMEOUT_S) as r:
            return json.loads(r.read().decode("utf-8"))

    def version(self):
        return f"ollama {self._version}"

    def complete(self, user, schema=None, kind="reply"):
        body = dict(model=self.model, messages=[{"role": "user", "content": user}], stream=False,
                    options=dict(OPTIONS, num_predict=self.max_tokens[kind]))
        if schema:
            body["format"] = schema
        r = self._post("/api/chat", body)
        stop = r.get("done_reason") or ("stop" if r.get("done") else "")
        meta = dict(served_model=self.model_id, stop_reason="max_tokens" if stop == "length" else stop,
                    request_id=None, fallback=False,
                    usage=dict(input_tokens=r.get("prompt_eval_count"), output_tokens=r.get("eval_count"),
                               total_duration_ns=r.get("total_duration"), eval_duration_ns=r.get("eval_duration")),
                    options=OPTIONS, max_tokens=self.max_tokens[kind])
        return r.get("message", {}).get("content", ""), meta
