import hashlib
import json
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

warnings.filterwarnings("ignore", message=".*OpenSSL.*")
import requests

ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = ROOT / "logs" / "requests.jsonl"
USER_AGENT = "grief-hi-en-corpus/0.1 (academic research; data discovery)"


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class PoliteClient:
    def __init__(self, min_delay_s=1.0, timeout_s=30, max_retries=3, host_delays=None):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.min_delay_s = min_delay_s
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.host_delays = host_delays or {}
        self._last_call = {}
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    def _wait(self, host):
        delay = self.host_delays.get(host, self.min_delay_s)
        elapsed = time.monotonic() - self._last_call.get(host, 0)
        if elapsed < delay:
            time.sleep(delay - elapsed)
        self._last_call[host] = time.monotonic()

    def get(self, url, params=None, headers=None, stream=False, max_bytes=None):
        host = urlparse(url).netloc
        resp, body, error = None, None, None
        for attempt in range(1, self.max_retries + 1):
            self._wait(host)
            try:
                resp = self.session.get(url, params=params, headers=headers,
                                        timeout=self.timeout_s, stream=stream or bool(max_bytes))
                if max_bytes:
                    body = resp.raw.read(max_bytes, decode_content=True)
                    resp.close()
                else:
                    body = resp.content
                error = None
            except requests.RequestException as exc:
                error = repr(exc)
                resp, body = None, None
            status = resp.status_code if resp is not None else None
            if status in (429, 502, 503, 504) or error:
                retry_after = 0
                if resp is not None:
                    try:
                        retry_after = int(resp.headers.get("Retry-After", 0))
                    except ValueError:
                        retry_after = 0
                if attempt < self.max_retries:
                    time.sleep(min(max(retry_after, 5 * attempt), 90))
                    continue
            break
        self._log(url, params, resp, body, error)
        return resp, body

    def get_json(self, url, params=None, headers=None):
        resp, body = self.get(url, params=params, headers=headers)
        if resp is None or resp.status_code != 200:
            return None, (resp.status_code if resp is not None else None)
        try:
            return json.loads(body), 200
        except ValueError:
            return None, resp.status_code

    def _log(self, url, params, resp, body, error):
        rec = {
            "ts": now_iso(),
            "url": resp.url if resp is not None else url,
            "params": params,
            "status": resp.status_code if resp is not None else None,
            "bytes": len(body) if body else 0,
            "sha256": hashlib.sha256(body).hexdigest() if body else None,
            "error": error,
        }
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
