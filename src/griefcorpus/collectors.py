import csv
import hashlib
import io
import json
import os
import re
import sys
import warnings
import zipfile
from pathlib import Path

from .http import ROOT, now_iso
from .textutil import bereavement_screen, detect_language

warnings.filterwarnings("ignore")
RAW = ROOT / "data" / "raw"
LOG = ROOT / "docs" / "collection_log.csv"
LOG_FIELDS = ["timestamp", "collector", "source", "batch", "records_scanned", "records_retrieved", "records_failed",
              "output_file", "note"]
SALT = "grief-hi-en-corpus/group/v1"


def log_run(**kw):
    LOG.parent.mkdir(exist_ok=True)
    new = not LOG.exists()
    with LOG.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=LOG_FIELDS)
        if new:
            w.writeheader()
        w.writerow({"timestamp": now_iso(), **{k: kw.get(k, "") for k in LOG_FIELDS if k != "timestamp"}})


def group_hash(prefix, value):
    return f"{prefix}_" + hashlib.sha1((SALT + str(value)).encode()).hexdigest()[:12] if value else None


def collect_ytcv(max_new_pages=None):
    from .sqlite_leafscan import scan
    src = RAW / "reused_datasets" / "ytcommentverse" / "YT-30M.db"
    out_dir = RAW / "youtube"
    out_dir.mkdir(parents=True, exist_ok=True)
    ck_path = out_dir / "ytcv_checkpoint.json"
    ck = json.loads(ck_path.read_text()) if ck_path.exists() else {
        "next_page": 2, "rows": 0, "overflow_skipped": 0, "hits": 0, "lang_sample": {}, "batches": 0}
    size = os.path.getsize(src)
    safe_pages = size // 4096 if size >= 10843156480 else size // 4096 - 64
    if safe_pages <= ck["next_page"]:
        print("nothing new to scan")
        return ck
    last = min(safe_pages, ck["next_page"] + max_new_pages) if max_new_pages else safe_pages
    hits_path = out_dir / "ytcv_screen_hits.jsonl"
    vid_path = out_dir / "ytcv_video_counts.json"
    vids = json.loads(vid_path.read_text()) if vid_path.exists() else {}
    rows = hits = 0
    lang = ck["lang_sample"]
    with hits_path.open("a", encoding="utf-8") as fh:
        for page, rowid, v in scan(str(src), start_page=ck["next_page"], max_bytes=last * 4096):
            if page == "stats":
                ck["overflow_skipped"] += v["overflow_rows_skipped"]
                break
            rows += 1
            video_id, comment_id, _name, commenter, text, votes, _chan, category = v
            text = text or ""
            vids[video_id] = vids.get(video_id, 0) + 1
            if (ck["rows"] + rows) % 20 == 0:
                lab = detect_language(text)[0]
                lang[lab] = lang.get(lab, 0) + 1
            s = bereavement_screen(text)
            if s["hit"]:
                hits += 1
                fh.write(json.dumps({"source_record_id": comment_id, "thread_id": video_id,
                                     "author_group": group_hash("yc", commenter), "text": text, "votes": votes,
                                     "video_category": category, "screen_side": s["side"], "sqlite_rowid": rowid,
                                     "collected_at": now_iso()}, ensure_ascii=False) + "\n")
    ck.update(next_page=last + 1, rows=ck["rows"] + rows, hits=ck["hits"] + hits, lang_sample=lang,
              batches=ck["batches"] + 1, file_bytes_seen=last * 4096, file_bytes_total=10843156480,
              videos=len(vids), updated=now_iso())
    ck_path.write_text(json.dumps(ck, indent=1))
    vid_path.write_text(json.dumps(vids))
    log_run(collector="collect_ytcv", source="YTCommentVerse (Zenodo 15678816)", batch=ck["batches"],
            records_scanned=rows, records_retrieved=hits, records_failed=0, output_file=str(hits_path.relative_to(ROOT)),
            note=f"pages to {last}; {ck['file_bytes_seen'] / ck['file_bytes_total']:.1%} of file; cumulative rows {ck['rows']}, hits {ck['hits']}")
    print(f"batch {ck['batches']}: scanned {rows} rows, {hits} screen hits; cumulative {ck['rows']} rows / {ck['hits']} hits; "
          f"{ck['file_bytes_seen'] / ck['file_bytes_total']:.1%} of file")
    return ck


def collect_reddit():
    import pandas as pd
    src = RAW / "reused_datasets" / "socialgrep_confessions" / "one-million-reddit-confessions.csv"
    out_dir = RAW / "reddit"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "confessions_screen_hits.jsonl"
    n = kept = removed = 0
    with out.open("w", encoding="utf-8") as fh:
        for chunk in pd.read_csv(src, dtype=str, keep_default_na=False, chunksize=100_000):
            for r in chunk.itertuples(index=False):
                n += 1
                body = r.selftext.strip()
                if body in ("", "[removed]", "[deleted]"):
                    removed += 1
                    continue
                full = r.title + "\n\n" + r.selftext
                s = bereavement_screen(full)
                if not s["hit"]:
                    continue
                kept += 1
                fh.write(json.dumps({"source_record_id": r.id, "thread_id": r.id, "subreddit": getattr(r, "_3"),
                                     "created_utc": int(r.created_utc), "permalink": r.permalink, "title": r.title,
                                     "text": r.selftext, "score": r.score, "screen_side": s["side"],
                                     "focus_early": bereavement_screen(full[:500])["hit"], "author_group": None,
                                     "collected_at": now_iso()}, ensure_ascii=False) + "\n")
    log_run(collector="collect_reddit", source="SocialGrep/one-million-reddit-confessions", batch=1, records_scanned=n,
            records_retrieved=kept, records_failed=0, output_file=str(out.relative_to(ROOT)),
            note=f"{removed} removed/deleted/empty posts skipped (deletions honoured); screen hits only")
    print(f"scanned {n}; removed/deleted/empty {removed}; screen hits {kept}")


def collect_reused():
    import openpyxl
    out_dir = RAW / "reused_datasets"
    samples = ROOT / "data" / "discovery" / "samples"
    z = zipfile.ZipFile(str(samples / "zenodo_22041925" / "hinemo9.zip"))
    name = next(x for x in z.namelist() if x.endswith("data/full.jsonl"))
    recs = [json.loads(l) for l in io.TextIOWrapper(z.open(name), encoding="utf-8")]
    out = out_dir / "hinemo9_screen_hits.jsonl"
    k = 0
    with out.open("w", encoding="utf-8") as fh:
        for r in recs:
            s = bereavement_screen(r["text"])
            if s["hit"]:
                k += 1
                fh.write(json.dumps({"source_record_id": r["id"], "text": r["text"], "dataset_language_label": r["language_label"],
                                     "dataset_genre_seed": r["genre"], "screen_side": s["side"], "collected_at": now_iso()},
                                    ensure_ascii=False) + "\n")
    log_run(collector="collect_reused", source="HinEmo-9 (Zenodo 22041925)", batch=1, records_scanned=len(recs),
            records_retrieved=k, output_file=str(out.relative_to(ROOT)), note="broad screen hits only")
    ws = openpyxl.load_workbook(str(samples / "url_https_reshare_ukdataservice_ac_uk_856067_" / "survey.xlsx"), read_only=True)["Sheet 1 - Bereavement"]
    rows = list(ws.iter_rows(values_only=True))
    hdr = [str(h) for h in rows[0]]
    qcols = [i for i, h in enumerate(hdr) if re.match(r"[AB]\d\d\.", h)]
    out2 = out_dir / "york_survey_respondents.jsonl"
    m = 0
    with out2.open("w", encoding="utf-8") as fh:
        for r in rows[1:]:
            if r[0] is None:
                continue
            m += 1
            text = "\n\n".join(f"[{hdr[i].split('.')[0]}] {r[i].strip()}" for i in qcols if isinstance(r[i], str) and r[i].strip())
            fh.write(json.dumps({"source_record_id": f"york_{r[0]}", "text": text, "age_band": r[1], "gender": r[2],
                                 "nationality_self_reported": r[3], "past_or_present": r[4], "person_who_died": r[5],
                                 "collected_at": now_iso()}, ensure_ascii=False) + "\n")
    log_run(collector="collect_reused", source="York grief survey (UKDA 856067)", batch=1, records_scanned=m,
            records_retrieved=m, output_file=str(out2.relative_to(ROOT)), note="all bereavement-sheet respondents; answer columns only")
    print(f"HinEmo-9 hits {k} of {len(recs)}; York respondents {m}")


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    {"ytcv": collect_ytcv, "reddit": collect_reddit, "reused": collect_reused}[what]()
