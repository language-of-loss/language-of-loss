import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "optional"))
from entropy import MOVES

OUT = Path(__file__).with_name("moves_synthetic.csv")


def ordered(rng, n):
    seq, i = [], 0
    for _ in range(n):
        seq.append(MOVES[i])
        if rng.random() < 0.8:
            i = (i + 1) % len(MOVES)
        else:
            i = MOVES.index(rng.choice(["memory", "regret"]))
    return seq


def rows(seed=7):
    rng = random.Random(seed)
    out = []
    for t in range(8):
        for lang, seq in (("hi", ordered(rng, rng.randint(25, 40))),
                          ("en", [rng.choice(MOVES) for _ in range(rng.randint(25, 40))])):
            out += [dict(text_id=f"syn:{lang}{t}", lang=lang, position=p, move=m) for p, m in enumerate(seq, 1)]
    return out


if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["text_id", "lang", "position", "move"])
        w.writeheader()
        w.writerows(rows())
    print(OUT)
