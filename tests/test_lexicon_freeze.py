import freeze as F


def test_lexicon_matches_the_freeze():
    rec = F.recorded()
    assert set(rec) == set(F.FROZEN), "FREEZE.md does not list exactly the frozen set"
    d = F.diff(rec, F.current())
    assert not d, ("lexicon changed since lexicon/FREEZE.md (silent change): " + "; ".join(d)
                   + " -> rebuild, bump the version and run src/analysis/freeze.py --write --reason ...")


def test_a_silent_change_is_detected(tmp_path):
    rec = {f: (h, n) for f, (h, n) in F.current().items()}
    f = F.FROZEN[0]
    rec[f] = ("0" * 64, rec[f][1])
    assert F.diff(rec, F.current()) == [f"{f}: sha256 {'0' * 12} -> {F.current()[f][0][:12]}"]
    fake = tmp_path / "FREEZE.md"
    fake.write_text("| `lexicon/lexicon.csv` | `" + "a" * 64 + "` | 1 |\n")
    assert F.recorded(fake) == {"lexicon/lexicon.csv": ("a" * 64, 1)}
