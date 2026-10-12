import argparse
import csv
import io
import json
import re
from pathlib import Path
from urllib.parse import quote

import yaml

from .http import PoliteClient, ROOT, now_iso

EVID = ROOT / "data" / "discovery" / "evidence"
TEXT_EXT = (".csv", ".tsv", ".txt", ".json", ".jsonl", ".md", ".xml")
DATA_EXT = TEXT_EXT + (".xlsx", ".xls", ".parquet", ".zip", ".gz", ".tar", ".7z", ".pkl", ".arrow", ".sav", ".rds")
CODE_EXT = (".py", ".ipynb", ".r", ".js", ".java", ".sh", ".cpp", ".m")
DEVANAGARI = re.compile(r"[ऀ-ॿ]")
LONG_ID = re.compile(r"(?<!\d)\d{15,20}(?!\d)")
URL = re.compile(r"https?://\S+")
SAMPLE_BYTES = 6000


def profile_text(sample):
    if not sample:
        return None
    letters = [ch for ch in sample if ch.isalpha()]
    dev = len(DEVANAGARI.findall(sample))
    words = re.findall(r"[^\W\d_]+", sample)
    return {"chars": len(sample), "devanagari_share_of_letters": round(dev / max(len(letters), 1), 3),
            "n_long_numeric_ids": len(LONG_ID.findall(sample)), "n_urls": len(URL.findall(sample)),
            "n_word_tokens": len(words),
            "looks_like": ("ids_only" if len(LONG_ID.findall(sample)) >= 5 and len(words) < 3 * len(LONG_ID.findall(sample))
                           else "urls_only" if len(URL.findall(sample)) >= 5 and len(words) < 12 * len(URL.findall(sample))
                           else "text")}


def classify_files(paths):
    data = [p for p in paths if p.lower().endswith(DATA_EXT) and not re.search(r"(^|/)(readme|license|requirements)", p.lower())]
    code = [p for p in paths if p.lower().endswith(CODE_EXT)]
    return {"n_files": len(paths), "n_data_like": len(data), "n_code": len(code),
            "data_like_files": data[:40], "license_files": [p for p in paths if re.search(r"(^|/)(licen[cs]e|copying)", p.lower())]}


def _head(client, url, headers=None):
    resp, body = client.get(url, headers=headers, max_bytes=SAMPLE_BYTES)
    if resp is None:
        return {"status": None, "sample": None}
    text = body.decode("utf-8", errors="replace") if resp.status_code == 200 and body else None
    return {"status": resp.status_code, "sample": text}


def verify_huggingface(client, cid):
    ev = {}
    info, st = client.get_json(f"https://huggingface.co/api/datasets/{cid}")
    ev["api_status"] = st
    if not info:
        return ev
    card = info.get("cardData") or {}
    ev.update(gated=info.get("gated"), private=info.get("private"), disabled=info.get("disabled"),
              card_license=card.get("license"), card_languages=card.get("language"),
              card_size_categories=card.get("size_categories"), card_source_datasets=card.get("source_datasets"),
              tags=info.get("tags"), last_modified=info.get("lastModified"), downloads=info.get("downloads"))
    tree, tst = client.get_json(f"https://huggingface.co/api/datasets/{cid}/tree/main", params={"recursive": "true"})
    files = [f for f in tree or [] if f.get("type") == "file"]
    ev["files"] = [{"path": f["path"], "bytes": f.get("size")} for f in files][:200]
    ev["file_summary"] = classify_files([f["path"] for f in files])
    ev["total_bytes"] = sum(f.get("size") or 0 for f in files)
    size, sst = client.get_json("https://datasets-server.huggingface.co/size", params={"dataset": cid})
    ev["viewer_size_status"] = sst
    if size:
        ev["verified_rows"] = ((size.get("size") or {}).get("dataset") or {}).get("num_rows")
        splits = (size.get("size") or {}).get("splits") or []
        ev["splits"] = [{k: s.get(k) for k in ("config", "split", "num_rows")} for s in splits]
        if splits:
            s0 = splits[0]
            rows, rst = client.get_json("https://datasets-server.huggingface.co/first-rows",
                                        params={"dataset": cid, "config": s0["config"], "split": s0["split"]})
            ev["first_rows_status"] = rst
            if rows:
                ev["features"] = [f.get("name") for f in rows.get("features", [])]
                sample_rows = [r.get("row") for r in rows.get("rows", [])[:8]]
                ev["sample_rows"] = [{k: (str(v)[:400]) for k, v in (r or {}).items()} for r in sample_rows]
                ev["sample_profile"] = profile_text(" ".join(str(v) for r in sample_rows for v in (r or {}).values()))
    readme = _head(client, f"https://huggingface.co/datasets/{cid}/raw/main/README.md")
    ev["readme_status"] = readme["status"]
    ev["readme_head"] = (readme["sample"] or "")[:3000]
    return ev


def verify_zenodo(client, cid):
    ev = {}
    rec, st = client.get_json(f"https://zenodo.org/api/records/{cid}")
    ev["api_status"] = st
    if not rec:
        return ev
    m = rec.get("metadata", {})
    ev.update(doi=rec.get("doi"), access_right=m.get("access_right"), license=(m.get("license") or {}).get("id"),
              publication_date=m.get("publication_date"), languages=m.get("language"),
              related=[{"rel": r.get("relation"), "id": r.get("identifier")} for r in m.get("related_identifiers") or []],
              description=re.sub(r"<[^>]+>", " ", m.get("description") or "")[:3000])
    files = rec.get("files") or []
    ev["files"] = [{"path": f.get("key"), "bytes": f.get("size")} for f in files]
    ev["total_bytes"] = sum(f.get("size") or 0 for f in files)
    ev["file_summary"] = classify_files([f.get("key") or "" for f in files])
    for f in files:
        if (f.get("key") or "").lower().endswith(TEXT_EXT) and m.get("access_right") == "open":
            h = _head(client, (f.get("links") or {}).get("self") or f"https://zenodo.org/api/records/{cid}/files/{quote(f['key'])}/content")
            ev["sampled_file"] = f.get("key")
            ev["sample_status"] = h["status"]
            ev["sample_head"] = (h["sample"] or "")[:2500]
            ev["sample_profile"] = profile_text(h["sample"])
            break
    return ev


def verify_github(client, cid):
    ev = {}
    hdr = {"Accept": "application/vnd.github+json"}
    repo, st = client.get_json(f"https://api.github.com/repos/{cid}", headers=hdr)
    ev["api_status"] = st
    if not repo:
        return ev
    branch = repo.get("default_branch")
    ev.update(code_license=(repo.get("license") or {}).get("spdx_id"), archived=repo.get("archived"),
              pushed_at=repo.get("pushed_at"), created_at=repo.get("created_at"), repo_kb=repo.get("size"),
              description=repo.get("description"), default_branch=branch)
    tree, tst = client.get_json(f"https://api.github.com/repos/{cid}/git/trees/{branch}", params={"recursive": "1"}, headers=hdr)
    blobs = [t for t in (tree or {}).get("tree", []) if t.get("type") == "blob"]
    ev["files"] = [{"path": b["path"], "bytes": b.get("size")} for b in blobs][:300]
    ev["file_summary"] = classify_files([b["path"] for b in blobs])
    ev["total_bytes"] = sum(b.get("size") or 0 for b in blobs)
    ev["tree_truncated"] = (tree or {}).get("truncated")
    raw = f"https://raw.githubusercontent.com/{cid}/{branch}/"
    for name in ("README.md", "readme.md", "README.rst", "README"):
        if any(b["path"] == name for b in blobs):
            ev["readme_head"] = (_head(client, raw + name)["sample"] or "")[:3000]
            break
    cands = sorted((b for b in blobs if b["path"].lower().endswith(TEXT_EXT)
                    and not re.search(r"readme|license|requirements|package", b["path"].lower())),
                   key=lambda b: -(b.get("size") or 0))
    if cands:
        h = _head(client, raw + quote(cands[0]["path"]))
        ev["sampled_file"] = cands[0]["path"]
        ev["sample_status"] = h["status"]
        ev["sample_head"] = (h["sample"] or "")[:2500]
        ev["sample_profile"] = profile_text(h["sample"])
    return ev


def verify_osf(client, cid):
    ev = {}
    node, st = client.get_json(f"https://api.osf.io/v2/nodes/{cid}/", params={"embed": "license"})
    ev["api_status"] = st
    if not node:
        return ev
    a = node["data"]["attributes"]
    lic = (((node["data"].get("embeds") or {}).get("license") or {}).get("data") or {}).get("attributes") or {}
    ev.update(public=a.get("public"), node_license=lic.get("name"), date_created=a.get("date_created"),
              date_modified=a.get("date_modified"), description=(a.get("description") or "")[:3000], category=a.get("category"))
    files, stack = [], [f"https://api.osf.io/v2/nodes/{cid}/files/osfstorage/"]
    while stack and len(files) < 300:
        listing, _ = client.get_json(stack.pop())
        for item in (listing or {}).get("data", []):
            ia = item["attributes"]
            if ia.get("kind") == "folder":
                stack.append(item["relationships"]["files"]["links"]["related"]["href"])
            else:
                files.append({"path": ia.get("materialized_path"), "bytes": ia.get("size"),
                              "download": (item.get("links") or {}).get("download")})
        nxt = ((listing or {}).get("links") or {}).get("next")
        if nxt:
            stack.append(nxt)
    ev["files"] = [{"path": f["path"], "bytes": f["bytes"]} for f in files]
    ev["total_bytes"] = sum(f["bytes"] or 0 for f in files)
    ev["file_summary"] = classify_files([f["path"] or "" for f in files])
    for f in files:
        if (f["path"] or "").lower().endswith(TEXT_EXT) and f.get("download"):
            h = _head(client, f["download"])
            ev.update(sampled_file=f["path"], sample_status=h["status"], sample_head=(h["sample"] or "")[:2500],
                      sample_profile=profile_text(h["sample"]))
            break
    return ev


def verify_dataverse(client, cid):
    ev = {}
    ds, st = client.get_json("https://dataverse.harvard.edu/api/datasets/:persistentId/", params={"persistentId": cid})
    ev["api_status"] = st
    if not ds:
        return ev
    v = (ds.get("data") or {}).get("latestVersion") or {}
    ev.update(license=(v.get("license") or {}).get("name") if isinstance(v.get("license"), dict) else v.get("license"),
              terms_of_use=v.get("termsOfUse"), terms_of_access=v.get("termsOfAccess"),
              file_access_request=v.get("fileAccessRequest"), release_time=v.get("releaseTime"))
    files = v.get("files") or []
    ev["files"] = [{"path": (f.get("dataFile") or {}).get("filename"), "bytes": (f.get("dataFile") or {}).get("filesize"),
                    "restricted": f.get("restricted")} for f in files]
    ev["total_bytes"] = sum(f["bytes"] or 0 for f in ev["files"])
    ev["file_summary"] = classify_files([f["path"] or "" for f in ev["files"]])
    ev["n_restricted_files"] = sum(bool(f["restricted"]) for f in ev["files"])
    return ev


def verify_url(client, cid):
    h = _head(client, cid)
    text = re.sub(r"\s+", " ", re.sub(r"<(script|style)[\s\S]*?</\1>|<[^>]+>", " ", h["sample"] or ""))
    return {"api_status": h["status"], "page_head": text[:2500]}


VERIFIERS = {"huggingface": verify_huggingface, "zenodo": verify_zenodo, "github": verify_github,
             "osf": verify_osf, "dataverse": verify_dataverse, "url": verify_url}


def run(shortlist_path, only=None, force=False):
    shortlist = yaml.safe_load(Path(shortlist_path).read_text(encoding="utf-8"))["candidates"]
    client = PoliteClient(min_delay_s=1.0, host_delays={"api.github.com": 2.0})
    EVID.mkdir(parents=True, exist_ok=True)
    for item in shortlist:
        platform, cid = item["platform"], str(item["id"])
        if only and platform not in only:
            continue
        out = EVID / (f"{platform}__" + re.sub(r"[^A-Za-z0-9._-]+", "_", cid)[:120] + ".json")
        if out.exists() and not force:
            continue
        ev = {"platform": platform, "candidate_id": cid, "verified_at": now_iso()}
        try:
            ev.update(VERIFIERS[platform](client, cid))
        except Exception as exc:
            ev["error"] = repr(exc)
        out.write_text(json.dumps(ev, ensure_ascii=False, indent=1), encoding="utf-8")
        fs = ev.get("file_summary") or {}
        print(f"[{platform}] {cid}: status={ev.get('api_status')} files={fs.get('n_files')} "
              f"data_like={fs.get('n_data_like')} rows={ev.get('verified_rows')} "
              f"looks_like={(ev.get('sample_profile') or {}).get('looks_like')}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--shortlist", default=str(ROOT / "config" / "shortlist.yaml"))
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    run(a.shortlist, a.only, a.force)
