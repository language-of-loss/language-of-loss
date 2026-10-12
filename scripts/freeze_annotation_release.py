import csv, sys, shutil
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from griefcorpus.ids import annotation_id
from griefcorpus.http import now_iso

RELEASE = "v1"
sheet_p, key_p = ROOT / "docs" / "annotation_sheet.csv", ROOT / "data" / "annotation" / "annotation_key.csv"
sheet = list(csv.DictReader(sheet_p.open(encoding="utf-8")))
key = list(csv.DictReader(key_p.open(encoding="utf-8")))
assert [r["annotation_id"] for r in sheet] == [r["annotation_id"] for r in key], "sheet/key order differs"
if not sheet[0]["annotation_id"].startswith("ann_"):
    sys.exit("already migrated")
taken, mapping = {}, []
for k in key:
    new = annotation_id(k["record_id"], taken)
    assert new not in taken, f"collision {new}"
    taken[new] = k["record_id"]
    mapping.append({"old_id": k["annotation_id"], "new_id": new, "record_id": k["record_id"]})
assert len({m["new_id"] for m in mapping}) == len(mapping) == len({m["record_id"] for m in mapping})
old2new = {m["old_id"]: m["new_id"] for m in mapping}
texts = ROOT / "data" / "annotation" / "texts"
for s, k in zip(sheet, key):
    old = s["annotation_id"]
    s["annotation_id"] = k["annotation_id"] = old2new[old]
    if s["full_text_path"]:
        src, dst = texts / f"{old}.txt", texts / f"{old2new[old]}.txt"
        shutil.move(str(src), str(dst))
        s["full_text_path"] = f"texts/{dst.name}"
        s["text_or_excerpt"] = s["text_or_excerpt"]
for p, rows in ((sheet_p, sheet), (key_p, key)):
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
ts = now_iso()
with (ROOT / "data" / "annotation" / "id_mapping_v1.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["old_id", "new_id", "record_id"]); w.writeheader(); w.writerows(mapping)
with (ROOT / "data" / "annotation" / "released_annotation_ids.csv").open("w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["annotation_id", "record_id", "first_release", "released_at"]); w.writeheader()
    w.writerows({"annotation_id": m["new_id"], "record_id": m["record_id"], "first_release": RELEASE, "released_at": ts} for m in mapping)
left = list(texts.glob("ann_*.txt"))
print(f"migrated {len(mapping)} IDs; collisions 0; leftover positional text files: {len(left)}")
