import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

import yaml

from .http import PoliteClient, ROOT, now_iso

DISC = ROOT / "data" / "discovery"
RAW = DISC / "raw"


def _strip_html(text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()


def _cand(platform, cid, title, url, **kw):
    base = dict(platform=platform, candidate_id=str(cid), title=title or "", url=url, doi=None,
                description="", license_metadata=None, access_metadata=None, tags=[],
                created=None, updated=None, size_metadata=None, resource_type=None)
    base.update(kw)
    base["description"] = _strip_html(base["description"])[:1500]
    return base


def search_huggingface(client, q, limit):
    spec = q if isinstance(q, dict) else {"search": q}
    params = {"search": spec["search"], "limit": limit, "full": "true"}
    if spec.get("filter"):
        params["filter"] = spec["filter"]
    data, status = client.get_json("https://huggingface.co/api/datasets", params=params)
    out = []
    for d in data or []:
        card = d.get("cardData") or {}
        tags = d.get("tags") or []
        lic = card.get("license") or next((t.split(":", 1)[1] for t in tags if t.startswith("license:")), None)
        out.append(_cand("huggingface", d["id"], d["id"], f"https://huggingface.co/datasets/{d['id']}",
                         description=d.get("description") or "", license_metadata=lic,
                         access_metadata={"gated": d.get("gated"), "private": d.get("private"),
                                          "disabled": d.get("disabled")},
                         tags=tags, created=d.get("createdAt"), updated=d.get("lastModified"),
                         size_metadata={"downloads": d.get("downloads")}, resource_type="dataset"))
    return data, status, out


def search_zenodo(client, q, limit):
    data, status = client.get_json("https://zenodo.org/api/records",
                                   params={"q": q, "size": limit, "sort": "bestmatch"})
    out = []
    for r in ((data or {}).get("hits") or {}).get("hits", []):
        m = r.get("metadata", {})
        files = r.get("files") or []
        out.append(_cand("zenodo", r.get("id"), m.get("title"), (r.get("links") or {}).get("self_html")
                         or f"https://zenodo.org/records/{r.get('id')}",
                         doi=r.get("doi") or m.get("doi"), description=m.get("description") or "",
                         license_metadata=(m.get("license") or {}).get("id"),
                         access_metadata={"access_right": m.get("access_right")},
                         tags=m.get("keywords") or [], created=m.get("publication_date"),
                         updated=r.get("updated"),
                         size_metadata={"n_files": len(files), "bytes": sum(f.get("size", 0) for f in files)},
                         resource_type=(m.get("resource_type") or {}).get("type")))
    return data, status, out


def search_github(client, q, limit):
    data, status = client.get_json("https://api.github.com/search/repositories",
                                   params={"q": q, "per_page": limit},
                                   headers={"Accept": "application/vnd.github+json"})
    out = []
    for r in (data or {}).get("items", []):
        out.append(_cand("github", r["full_name"], r["full_name"], r["html_url"],
                         description=r.get("description") or "",
                         license_metadata={"code_license_only": (r.get("license") or {}).get("spdx_id")},
                         access_metadata={"archived": r.get("archived"), "private": r.get("private")},
                         tags=r.get("topics") or [], created=r.get("created_at"), updated=r.get("pushed_at"),
                         size_metadata={"repo_kb": r.get("size"), "stars": r.get("stargazers_count")},
                         resource_type="repository"))
    return data, status, out


def search_osf(client, q, limit):
    out, raw, status = [], [], None
    for field in ("title", "description"):
        data, status = client.get_json("https://api.osf.io/v2/nodes/",
                                       params={f"filter[{field}]": q, "page[size]": limit})
        raw.append(data)
        for n in (data or {}).get("data", []):
            a = n.get("attributes", {})
            out.append(_cand("osf", n["id"], a.get("title"), f"https://osf.io/{n['id']}/",
                             description=a.get("description") or "",
                             license_metadata=None,
                             access_metadata={"public": a.get("public"), "registration": a.get("registration")},
                             tags=a.get("tags") or [], created=a.get("date_created"),
                             updated=a.get("date_modified"), resource_type=a.get("category")))
    return raw, status, out


def search_dataverse(client, q, limit):
    data, status = client.get_json("https://dataverse.harvard.edu/api/search",
                                   params={"q": q, "type": "dataset", "per_page": limit})
    out = []
    for r in ((data or {}).get("data") or {}).get("items", []):
        out.append(_cand("dataverse", r.get("global_id"), r.get("name"), r.get("url"),
                         doi=(r.get("global_id") or "").replace("doi:", "") or None,
                         description=r.get("description") or "",
                         access_metadata={"file_count": r.get("fileCount")},
                         tags=(r.get("keywords") or []) + (r.get("subjects") or []),
                         created=r.get("published_at"), updated=r.get("updatedAt"),
                         size_metadata={"file_count": r.get("fileCount")}, resource_type="dataset"))
    return data, status, out


def search_datacite(client, q, limit):
    data, status = client.get_json("https://api.datacite.org/dois",
                                   params={"query": q, "resource-type-id": "dataset", "page[size]": limit})
    out = []
    for r in (data or {}).get("data", []):
        a = r.get("attributes", {})
        titles = a.get("titles") or [{}]
        descs = a.get("descriptions") or [{}]
        rights = [x.get("rightsIdentifier") or x.get("rights") for x in a.get("rightsList") or []]
        out.append(_cand("datacite", a.get("doi"), titles[0].get("title"), a.get("url") or f"https://doi.org/{a.get('doi')}",
                         doi=a.get("doi"), description=descs[0].get("description") or "",
                         license_metadata=rights or None,
                         access_metadata={"publisher": (a.get("publisher") or {}) if isinstance(a.get("publisher"), str)
                                          else a.get("publisher")},
                         tags=[s.get("subject") for s in a.get("subjects") or [] if s.get("subject")],
                         created=str(a.get("publicationYear")), updated=a.get("updated"), resource_type="dataset"))
    return data, status, out


def search_openalex(client, q, limit):
    data, status = client.get_json("https://api.openalex.org/works",
                                   params={"search": q, "per-page": limit})
    out = []
    for w in (data or {}).get("results", []):
        loc = w.get("primary_location") or {}
        inv = w.get("abstract_inverted_index") or {}
        words = sorted(((p, t) for t, ps in inv.items() for p in ps))
        out.append(_cand("openalex", w.get("id"), w.get("title"), loc.get("landing_page_url") or w.get("id"),
                         doi=(w.get("doi") or "").replace("https://doi.org/", "") or None,
                         description=" ".join(t for _, t in words),
                         license_metadata=loc.get("license"),
                         access_metadata={"is_oa": (w.get("open_access") or {}).get("is_oa")},
                         created=w.get("publication_date"), resource_type=w.get("type"),
                         size_metadata={"cited_by": w.get("cited_by_count")}))
    return data, status, out


SEARCHERS = {"huggingface": search_huggingface, "zenodo": search_zenodo, "github": search_github,
             "osf": search_osf, "dataverse": search_dataverse, "datacite": search_datacite,
             "openalex": search_openalex}


def triage(c, cfg):
    text = " ".join([c["title"], c["description"], " ".join(map(str, c["tags"]))]).lower()
    hit = lambda terms: sorted({t for t in terms if t.lower() in text})
    c["triage"] = {"grief_terms": hit(cfg["grief_terms"]), "hindi_terms": hit(cfg["hindi_terms"]),
                   "synthetic_flags": hit(cfg["synthetic_terms"])}
    c["triage"]["score"] = 2 * bool(c["triage"]["grief_terms"]) + bool(c["triage"]["hindi_terms"])
    return c


def run(config_path, platforms=None, query_set=None):
    cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    d = cfg["discovery"]
    if query_set:
        qs = d[query_set]
        d = {**d, "queries": qs["queries"], "platform_queries": qs.get("platform_queries", {}),
             "platforms": qs["platforms"] + list(qs.get("platform_queries", {}))}
    client = PoliteClient(d["min_delay_s"], d["request_timeout_s"], d["max_retries"],
                          host_delays={"api.github.com": d["github_search_delay_s"]})
    platforms = platforms or d["platforms"]
    merged, log_rows = {}, []
    for platform in platforms:
        qsets = ({"platform_specific": d["platform_queries"][platform]}
                 if platform in d.get("platform_queries", {}) else d["queries"])
        for qlang, queries in qsets.items():
            for spec in queries:
                q = json.dumps(spec, ensure_ascii=False, sort_keys=True) if isinstance(spec, dict) else spec
                raw, status, cands = SEARCHERS[platform](client, spec, d["per_query_limit"])
                qhash = hashlib.sha1(f"{platform}|{q}".encode()).hexdigest()[:12]
                pdir = RAW / platform
                pdir.mkdir(parents=True, exist_ok=True)
                (pdir / f"{qhash}.json").write_text(
                    json.dumps({"platform": platform, "query": q, "query_lang": qlang, "retrieved": now_iso(),
                                "http_status": status, "response": raw}, ensure_ascii=False), encoding="utf-8")
                for c in cands:
                    key = (c["platform"], c["candidate_id"])
                    if key not in merged:
                        merged[key] = triage(c, cfg["triage"])
                        merged[key]["matched_queries"] = []
                    merged[key]["matched_queries"].append({"q": q, "lang": qlang})
                log_rows.append(dict(ts=now_iso(), platform=platform, query=q, query_lang=qlang,
                                     http_status=status, n_results=len(cands), raw_file=f"{platform}/{qhash}.json"))
                print(f"[{platform}] {q!r}: status={status} n={len(cands)}", flush=True)
    for c in merged.values():
        c["first_seen_stage"] = 3 if query_set else 1
    out_path = DISC / "candidates.jsonl"
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            c = json.loads(line)
            if query_set or c["platform"] not in platforms:
                if (c["platform"], c["candidate_id"]) in merged:
                    merged[(c["platform"], c["candidate_id"])]["first_seen_stage"] = c.get("first_seen_stage", 1)
                    merged[(c["platform"], c["candidate_id"])]["matched_queries"] = c.get("matched_queries", []) + merged[(c["platform"], c["candidate_id"])]["matched_queries"]
                else:
                    c.setdefault("first_seen_stage", 1)
                    merged[(c["platform"], c["candidate_id"])] = c
    with out_path.open("w", encoding="utf-8") as fh:
        for c in sorted(merged.values(), key=lambda c: (-c["triage"]["score"], c["platform"], c["candidate_id"])):
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    log_path = DISC / "search_log.csv"
    new = not log_path.exists()
    with log_path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(log_rows[0]))
        if new:
            w.writeheader()
        w.writerows(log_rows)
    print(f"{len(merged)} unique candidates -> {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "config" / "pipeline.yaml"))
    ap.add_argument("--platforms", nargs="*")
    ap.add_argument("--query-set")
    a = ap.parse_args()
    run(a.config, a.platforms, a.query_set)
