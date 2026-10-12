import struct


def _varint(buf, pos):
    v = 0
    for i in range(9):
        b = buf[pos + i]
        if i == 8:
            return (v << 8) | b, pos + 9
        v = (v << 7) | (b & 0x7F)
        if not b & 0x80:
            return v, pos + i + 1
    return v, pos + 9


def _decode_record(payload, n_cols):
    hsize, p = _varint(payload, 0)
    types = []
    while p < hsize:
        t, p = _varint(payload, p)
        types.append(t)
    vals, q = [], hsize
    for t in types[:n_cols]:
        if t == 0:
            vals.append(None)
        elif t in (1, 2, 3, 4, 5, 6):
            n = (1, 2, 3, 4, 6, 8)[t - 1]
            vals.append(int.from_bytes(payload[q:q + n], "big", signed=True))
            q += n
        elif t == 7:
            vals.append(struct.unpack(">d", payload[q:q + 8])[0])
            q += 8
        elif t in (8, 9):
            vals.append(t - 8)
        elif t >= 13 and t % 2 == 1:
            n = (t - 13) // 2
            vals.append(payload[q:q + n].decode("utf-8", errors="replace"))
            q += n
        elif t >= 12:
            n = (t - 12) // 2
            vals.append(payload[q:q + n])
            q += n
        else:
            vals.append(None)
    return vals


def scan(path, start_page=2, n_cols=8, page_size=4096, max_bytes=None):
    import os
    size = os.path.getsize(path) if max_bytes is None else max_bytes
    n_pages = size // page_size
    usable = page_size
    max_local = usable - 35
    stats = {"pages_scanned": 0, "leaf_pages": 0, "rows": 0, "overflow_rows_skipped": 0, "bad_cells": 0,
             "first_page": start_page, "last_page": n_pages}
    with open(path, "rb") as fh:
        fh.seek((start_page - 1) * page_size)
        for page_no in range(start_page, n_pages + 1):
            page = fh.read(page_size)
            if len(page) < page_size:
                stats["last_page"] = page_no - 1
                break
            stats["pages_scanned"] += 1
            off = 100 if page_no == 1 else 0
            if page[off] != 0x0D:
                continue
            stats["leaf_pages"] += 1
            n_cells = struct.unpack(">H", page[off + 3:off + 5])[0]
            for i in range(n_cells):
                try:
                    cp = struct.unpack(">H", page[off + 8 + 2 * i:off + 10 + 2 * i])[0]
                    psize, p = _varint(page, cp)
                    rowid, p = _varint(page, p)
                    if psize > max_local:
                        stats["overflow_rows_skipped"] += 1
                        continue
                    vals = _decode_record(page[p:p + psize], n_cols)
                    if len(vals) == n_cols:
                        stats["rows"] += 1
                        yield page_no, rowid, vals
                    else:
                        stats["bad_cells"] += 1
                except Exception:
                    stats["bad_cells"] += 1
    yield "stats", None, stats
