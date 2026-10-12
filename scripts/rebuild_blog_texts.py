import argparse
import csv
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
PKG = HERE.parents[2] if HERE.parents[1].name == "code" else HERE.parents[1]
SRC = PKG / "code" / "src" if (PKG / "code" / "src").exists() else PKG / "src"
sys.path.insert(0, str(SRC))

import trafilatura
from griefcorpus.clean import clean_doc_text
from griefcorpus.collect_blogs import robots_allows
from griefcorpus.http import PoliteClient


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--annotation", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--metadata", default=str(PKG / "data" / "blogs" / "blogs_metadata.csv"))
    ap.add_argument("--key", default=str(PKG / "annotation" / "restricted_machine_key" / "annotation_key_v1.csv"))
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.metadata, encoding="utf-8")))
    ann = {}
    if a.annotation:
        ann = {r["record_id"]: r["annotation_id"] for r in csv.DictReader(open(a.key, encoding="utf-8")) if r["source"] == "blogs"}
    out = PKG / "data" / "blogs" / "rebuilt_texts"
    out.mkdir(parents=True, exist_ok=True)
    ann_out = PKG / "annotation" / "reviewer_pack" / "texts"
    client = PoliteClient(min_delay_s=3.0, timeout_s=40, max_retries=2)
    report = []
    for r in rows[: a.limit] if a.limit else rows:
        status = "unavailable"
        try:
            if not robots_allows(client, r["source_url"]):
                status = "robots_disallow"
            else:
                resp, body = client.get(r["source_url"])
                if resp is not None and resp.status_code == 200 and body:
                    html = body.decode(resp.encoding or "utf-8", errors="replace")
                    text = trafilatura.extract(html, include_comments=False, include_tables=False,
                                               favor_precision=True, deduplicate=True) or ""
                    clean, _ = clean_doc_text(text)
                    status = "match" if hashlib.sha256(clean.encode("utf-8")).hexdigest() == r["sha256_text_clean"] else "changed"
                    (out / f"{r['source_record_id']}.txt").write_text(clean, encoding="utf-8")
                    if r["record_id"] in ann:
                        ann_out.mkdir(parents=True, exist_ok=True)
                        (ann_out / f"{ann[r['record_id']]}.txt").write_text(clean, encoding="utf-8")
        except Exception as exc:
            status = f"error: {repr(exc)[:120]}"
        report.append({"record_id": r["record_id"], "source_url": r["source_url"], "status": status})
        print(status, r["source_url"][:100], flush=True)
    with (out / "rebuild_report.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["record_id", "source_url", "status"])
        w.writeheader()
        w.writerows(report)
    from collections import Counter
    print(dict(Counter(x["status"].split(":")[0] for x in report)))


if __name__ == "__main__":
    main()
