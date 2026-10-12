import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from griefcorpus import collect_api as CA


class Resp:
    def __init__(self, status, body):
        self.status_code, self._body = status, body

    def json(self):
        return self._body


SEARCH = {"items": [{"id": {"videoId": "vid1"}, "snippet": {"title": "t"}}]}
THREADS = {"items": [{"snippet": {"topLevelComment": {"id": "c1", "snippet": {
    "textOriginal": "my father passed away last year", "authorChannelId": {"value": "UCx"},
    "publishedAt": "2024-01-01T00:00:00Z", "likeCount": 1}}},
    "replies": {"comments": [{"id": "c2", "snippet": {"textOriginal": "sorry for your loss",
                                                      "authorChannelId": {"value": "UCy"}}}]}}]}


def setup(monkeypatch, tmp_path, key):
    logs, calls = [], []
    monkeypatch.setattr(CA, "RAW", tmp_path)
    monkeypatch.setattr(CA, "ROOT", tmp_path)
    monkeypatch.setattr(CA, "log_run", lambda **kw: logs.append(kw))
    monkeypatch.setenv("YOUTUBE_API_KEY", key)

    def fake_get(url, params=None, headers=None, tries=3):
        calls.append((url, dict(params or {})))
        return Resp(200, SEARCH if url.endswith("search") else THREADS)
    monkeypatch.setattr(CA, "_get", fake_get)
    q = tmp_path / "q.txt"
    q.write_text("# comment\nmy father passed away\n", encoding="utf-8")
    return logs, calls, q


def test_missing_key_refuses_and_logs_zero(monkeypatch, tmp_path):
    logs, calls, q = setup(monkeypatch, tmp_path, "")
    assert CA.youtube(str(q)) == 2 and not calls and logs[0]["records_retrieved"] == 0


def test_key_from_env_runs_and_keeps_key_out_of_files(monkeypatch, tmp_path):
    logs, calls, q = setup(monkeypatch, tmp_path, "TESTKEY123")
    assert CA.youtube(str(q)) == 0
    assert all(p.get("key") == "TESTKEY123" for _, p in calls)
    out = (tmp_path / "youtube" / "api_comments.jsonl").read_text(encoding="utf-8")
    recs = [json.loads(l) for l in out.splitlines()]
    assert [r["parent_id"] for r in recs] == [None, "c1"] and all(r["retention_deadline"] for r in recs)
    assert "UCx" not in out and "TESTKEY123" not in out
    assert "TESTKEY123" not in json.dumps(logs) + (tmp_path / "youtube" / "api_checkpoint.json").read_text()
