import csv
import math

import krippendorff
import numpy as np
import pytest

import audit_match as M
import reader_ingest as R

CONSENT = "I am 18 or older, I read both Hindi and English, and I agree to take part"


def write(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    return path


def read(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def fixture(tmp, ratings, skips=None, consent=None, replies=None, n_pos=4, blocks=(1, 2)):
    assign, key, meta = [], [], []
    for b in blocks:
        for pos in range(1, n_pos + 1):
            lang = "hi" if pos % 2 else "en"
            pid = f"AP-{b}{pos}"
            assign.append([b, pos, pid, lang])
            key.append([f"AR-{b}{pos}", pid, f"blogs:{lang}{pos}", lang, "long", "dev", "", "", 0, 0])
    for lang in ("hi", "en"):
        for pos in range(1, n_pos + 1):
            meta.append([f"blogs:{lang}{pos}", lang, "parent"])
    write(tmp / "assign.csv", ["block", "position", "passage_id", "lang"], assign)
    write(tmp / "key.csv", ["rating_id", "passage_id", "record_id", "lang", "register", "split", "source_url",
                            "passage_sha256", "order_r1", "order_r2"], key)
    write(tmp / "meta.csv", ["record_id", "lang", "loss_type"], meta)
    write(tmp / "replies.csv", ["exchange_id", "passage_id", "system"], [["R01", "AP-11", "ollama:m"],
                                                                         ["R02", "AP-12", "ollama:m"]])
    for b in blocks:
        header = ["Timestamp", "Consent"]
        for pos in range(1, n_pos + 1):
            header += [f"[B{b:02d}-{pos:02d}] (synthetic passage {pos})", f"[B{b:02d}-{pos:02d} skip]"]
        header += ["[R01] Someone wrote: (x)", "[R02] Someone wrote: (y)", "Age band",
                   "Which language do you read more comfortably?"]
        rows = []
        for i, reader in enumerate(ratings[b]):
            row = ["2026/10/12 10:00:00", CONSENT if not (consent and (b, i) in consent) else ""]
            for pos, v in enumerate(reader, 1):
                row += [str(v), "Skip this passage" if skips and (b, i, pos) in skips else ""]
            row += [str((replies or {}).get((b, i), (3, 4))[0]), str((replies or {}).get((b, i), (3, 4))[1]), "", ""]
            rows.append(row)
        write(tmp / "readers" / f"Grief reading study, Block {b}.csv", header, rows)
    return tmp


def run(tmp):
    return R.run(tmp / "readers", tmp / "assign.csv", tmp / "replies.csv", tmp / "key.csv")


def test_means_skips_and_consent(tmp_path):
    t = fixture(tmp_path, {1: [[1, 2, 3, 4], [2, 2, 5, 4], [3, 2, 4, 6]], 2: [[7, 7, 1, 1], [6, 7, 2, 1], [6, 6, 2, 2]]},
                skips={(1, 0, 3)}, consent={(2, 2)})
    rows, replies, alpha, report = run(t)
    by = {r["passage_id"]: r for r in rows}
    assert len(rows) == 8
    assert by["AP-11"]["mean_rating"] == 2.0 and by["AP-11"]["n_raters"] == 3 and by["AP-11"]["agreed"] == 0
    assert by["AP-13"]["n_raters"] == 2 and by["AP-13"]["mean_rating"] == 4.5
    assert by["AP-21"]["n_raters"] == 2 and by["AP-21"]["mean_rating"] == 6.5
    assert by["AP-12"]["agreed"] == 1 and by["AP-12"]["lang"] == "en" and by["AP-12"]["block"] == 1
    assert report["files"]["Grief reading study, Block 2.csv"]["dropped_no_consent"] == 1
    assert report["files"]["Grief reading study, Block 1.csv"]["skipped_ratings"] == 1
    assert {r["exchange_id"]: r["n_raters"] for r in replies} == {"R01": 5, "R02": 5}


def test_alpha_matches_krippendorff_per_block_and_overall(tmp_path):
    b1 = [[1, 2, 3, 4], [2, 2, 5, 4], [3, 2, 4, 6]]
    b2 = [[7, 7, 1, 1], [6, 7, 2, 1], [6, 6, 2, 2]]
    rows, _, alpha, _ = run(fixture(tmp_path, {1: b1, 2: b2}))
    got = {(a["scope"], a["items"]): a for a in alpha}
    k1 = krippendorff.alpha(reliability_data=np.array(b1, float), level_of_measurement="interval")
    both = np.array([r1 + r2 for r1, r2 in zip(b1, b2)], float)
    kall = krippendorff.alpha(reliability_data=both, level_of_measurement="interval")
    assert math.isclose(got[("block 1", "passages")]["alpha_interval"], round(k1, 4))
    assert math.isclose(got[("all blocks", "passages")]["alpha_interval"], round(kall, 4))
    assert got[("block 2", "passages")]["n_readers"] == 3 and got[("all blocks", "passages")]["n_units"] == 8
    assert ("all blocks", "replies") in got


def test_unknown_code_or_two_files_for_one_block_refuse(tmp_path):
    t = fixture(tmp_path, {1: [[1, 2, 3, 4]], 2: [[1, 2, 3, 4]]}, n_pos=4)
    write(t / "assign.csv", ["block", "position", "passage_id", "lang"], [[1, 1, "AP-11", "hi"]])
    with pytest.raises(SystemExit):
        run(t)
    t2 = fixture(tmp_path / "b", {1: [[1, 2, 3, 4]]}, blocks=(1,))
    (t2 / "readers" / "copy.csv").write_bytes((t2 / "readers" / "Grief reading study, Block 1.csv").read_bytes())
    with pytest.raises(SystemExit):
        run(t2)


def test_main_writes_outputs_and_audit_match_uses_reader_means(tmp_path):
    t = fixture(tmp_path, {1: [[3, 3, 5, 5], [3, 4, 5, 6], [4, 3, 6, 5]], 2: [[2, 2, 6, 6], [2, 3, 6, 7], [3, 2, 7, 6]]})
    R.main(["--responses", str(t / "readers"), "--assignment", str(t / "assign.csv"), "--replies",
            str(t / "replies.csv"), "--key", str(t / "key.csv"), "--out", str(t / "reader_ratings.csv"),
            "--reply-out", str(t / "reply_ratings.csv"), "--results", str(t / "res")])
    assert (t / "res" / "reader_alpha.csv").exists() and (t / "reply_ratings.csv").exists()
    M.main(["--readers", str(t / "reader_ratings.csv"), "--key", str(t / "key.csv"), "--text-meta",
            str(t / "meta.csv"), "--processed", str(t / "proc"), "--results", str(t / "res2")])
    ratings = {r["passage_id"]: r for r in read(t / "proc" / "audit_ratings.csv")}
    assert float(ratings["AP-11"]["mean_rating"]) == pytest.approx(10 / 3, abs=1e-4) and ratings["AP-11"]["r1"] == ""
    pairs = read(t / "proc" / "audit_pairs.csv")
    assert pairs and all(abs(float(p["rating_hi"]) - float(p["rating_en"])) <= 0.5 + 1e-9 for p in pairs)
    assert not (t / "res2" / "audit_rating_agreement.csv").exists()
