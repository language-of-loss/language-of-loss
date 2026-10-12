import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

from .collectors import RAW, group_hash, log_run
from .http import ROOT, USER_AGENT, now_iso

load_dotenv(ROOT / ".env")
X_COST_PER_READ = 0.005


def _get(url, params=None, headers=None, tries=3):
    for attempt in range(tries):
        r = requests.get(url, params=params, headers={"User-Agent": USER_AGENT, **(headers or {})}, timeout=30)
        if r.status_code == 429:
            reset = int(r.headers.get("x-rate-limit-reset", 0))
            wait = max(reset - time.time(), 15) if reset else 30 * (attempt + 1)
            if wait > 900:
                return r
            time.sleep(wait)
            continue
        if r.status_code >= 500:
            time.sleep(5 * (attempt + 1))
            continue
        return r
    return r


def youtube(queries_file, max_videos_per_query=5, max_threads_per_video=25):
    key = os.environ.get("YOUTUBE_API_KEY", "").strip()
    out_dir = RAW / "youtube"
    out_dir.mkdir(parents=True, exist_ok=True)
    if not key:
        log_run(collector="collect_api.youtube", source="YouTube Data API v3", batch=0, records_retrieved=0,
                note="NOT RUN: YOUTUBE_API_KEY missing in environment/.env")
        print("YOUTUBE_API_KEY is not set. Add it to .env (see .env.example). Nothing was collected.")
        return 2
    ck_path = out_dir / "api_checkpoint.json"
    ck = json.loads(ck_path.read_text()) if ck_path.exists() else {"done_videos": [], "quota_units": 0}
    out = out_dir / "api_comments.jsonl"
    base = "https://www.googleapis.com/youtube/v3/"
    n = failed = 0
    deadline = (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat()
    for q in [l.strip() for l in Path(queries_file).read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]:
        r = _get(base + "search", {"part": "snippet", "q": q, "type": "video", "maxResults": max_videos_per_query, "key": key})
        ck["quota_units"] += 100
        if r.status_code != 200:
            failed += 1
            print(f"search failed [{r.status_code}] for query {q!r}: {r.json().get('error', {}).get('message', '')[:120]}")
            continue
        for item in r.json().get("items", []):
            vid = item["id"]["videoId"]
            if vid in ck["done_videos"]:
                continue
            token, got = None, 0
            while got < max_threads_per_video:
                p = {"part": "snippet,replies", "videoId": vid, "maxResults": min(100, max_threads_per_video - got),
                     "order": "time", "textFormat": "plainText", "key": key}
                if token:
                    p["pageToken"] = token
                cr = _get(base + "commentThreads", p)
                ck["quota_units"] += 1
                if cr.status_code != 200:
                    failed += 1
                    break
                body = cr.json()
                with out.open("a", encoding="utf-8") as fh:
                    for th in body.get("items", []):
                        top = th["snippet"]["topLevelComment"]
                        for c, parent in [(top, None)] + [(rp, top["id"]) for rp in th.get("replies", {}).get("comments", [])]:
                            sn = c["snippet"]
                            fh.write(json.dumps({"source_record_id": c["id"], "thread_id": vid, "parent_id": parent,
                                                 "author_group": group_hash("ya", (sn.get("authorChannelId") or {}).get("value")),
                                                 "text": sn.get("textOriginal", ""), "published_at": sn.get("publishedAt"),
                                                 "like_count": sn.get("likeCount"), "video_title": item["snippet"]["title"],
                                                 "query": q, "collected_at": now_iso(), "retention_deadline": deadline},
                                                ensure_ascii=False) + "\n")
                            n += 1
                        got += 1
                token = body.get("nextPageToken")
                if not token:
                    break
            ck["done_videos"].append(vid)
            ck_path.write_text(json.dumps(ck))
    log_run(collector="collect_api.youtube", source="YouTube Data API v3", batch=1, records_retrieved=n, records_failed=failed,
            output_file=str(out.relative_to(ROOT)), note=f"quota units used (conservative) {ck['quota_units']}; retention deadline {deadline}")
    print(f"retrieved {n} comments; failed calls {failed}; quota units ~{ck['quota_units']}")
    return 0


def x_search(query, lang, max_reads=1000):
    token = os.environ.get("X_BEARER_TOKEN", "").strip()
    ceiling = float(os.environ.get("X_MAX_SPEND_USD", "0") or 0)
    out_dir = RAW / "x"
    out_dir.mkdir(parents=True, exist_ok=True)
    if not token or ceiling <= 0:
        why = "X_BEARER_TOKEN missing" if not token else "X_MAX_SPEND_USD is 0 (no spend authorised)"
        log_run(collector="collect_api.x", source="X API v2 recent search", batch=0, records_retrieved=0, note=f"NOT RUN: {why}")
        print(f"X collector refused to run: {why}. Nothing was collected and nothing was spent.")
        return 2
    spend_path = out_dir / "spend_ledger.json"
    ledger = json.loads(spend_path.read_text()) if spend_path.exists() else {"reads": 0}
    out = out_dir / "search_posts.jsonl"
    nxt, n = None, 0
    while n < max_reads:
        if (ledger["reads"] + 100) * X_COST_PER_READ > ceiling:
            print(f"spend guard: next page would exceed ${ceiling:.2f}; stopping at {ledger['reads']} reads")
            break
        p = {"query": f"({query}) lang:{lang} -is:retweet", "max_results": 100,
             "tweet.fields": "created_at,lang,conversation_id,referenced_tweets,author_id"}
        if nxt:
            p["next_token"] = nxt
        r = _get("https://api.x.com/2/tweets/search/recent", p, {"Authorization": f"Bearer {token}"})
        if r.status_code != 200:
            print(f"X API error {r.status_code}: {r.text[:200]}")
            break
        body = r.json()
        with out.open("a", encoding="utf-8") as fh:
            for t in body.get("data", []):
                fh.write(json.dumps({"source_record_id": t["id"], "thread_id": t.get("conversation_id"),
                                     "parent_id": next((x["id"] for x in t.get("referenced_tweets", []) if x["type"] == "replied_to"), None),
                                     "author_group": group_hash("xa", t.get("author_id")), "text": t["text"],
                                     "published_at": t.get("created_at"), "platform_lang": t.get("lang"), "query": query,
                                     "collected_at": now_iso()}, ensure_ascii=False) + "\n")
                n += 1
        ledger["reads"] += len(body.get("data", []))
        spend_path.write_text(json.dumps(ledger))
        nxt = body.get("meta", {}).get("next_token")
        if not nxt:
            break
    log_run(collector="collect_api.x", source="X API v2 recent search", batch=1, records_retrieved=n,
            output_file=str(out.relative_to(ROOT)), note=f"cumulative reads {ledger['reads']} = ${ledger['reads'] * X_COST_PER_READ:.2f} of ${ceiling:.2f}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    y = sub.add_parser("youtube")
    y.add_argument("--queries-file", default=str(ROOT / "config" / "youtube_pilot_queries.txt"))
    x = sub.add_parser("x")
    x.add_argument("--query", required=True)
    x.add_argument("--lang", required=True, choices=["hi", "en"])
    x.add_argument("--max-reads", type=int, default=1000)
    a = ap.parse_args()
    sys.exit(youtube(a.queries_file) if a.cmd == "youtube" else x_search(a.query, a.lang, a.max_reads))
