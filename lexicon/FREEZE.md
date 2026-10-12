# Lexicon freeze: v0.2 (re-frozen 2026-10-10)

Frozen 2026-10-10 23:25 by `src/analysis/freeze.py --write`. Reason: investigators' decisions of 2026-10-10: DUTY_UNDONE dropped from P-HI-44 / P-EN-44, the four DUTY counterpart links made two-way; lexicon stays v0.2

Every stage reads the lexicon through these files. `tests/test_lexicon_freeze.py` recomputes the hashes and fails on any difference: a change to the instrument must be a new freeze (new version, reason, RESULTS_LOG row), never a silent edit. Rule (draft v4 §3.3): the lexicon is revised on the development split only and frozen before the confirmatory split is opened; after that it does not change.

| file | sha256 | bytes |
|---|---|---|
| `lexicon/lexicon.csv` | `99dbabc2a2260388f04a9b1f32bc578a347694303950be921f933d4752d3f0c2` | 126125 |
| `lexicon/entry_vectors.csv` | `b2da848c19e883178d90301e7e1f397f5b7c3e1a06b78b93495862ab385be6d6` | 12963 |
| `lexicon/components.csv` | `2016f827979ec165e975a30ba42290fc0e61c9d128c6be51176d4d759b3c8ff3` | 9617 |
| `lexicon/flag_components.csv` | `09b6709082cdf6177d4fde469f5e0e383d1da4ad76b5687b44a5ba24de0fd28f` | 2312 |
| `lexicon/molecules.csv` | `30fee1e3d272ed5d980effc89dda0017842696ec886b16a8ac5c150481dd63f6` | 1710 |
| `lexicon/primes.csv` | `6f405ee0b1a03b6f26741cbf6c637d945f0c1477b8b3ca1cbb476552245f6eb0` | 32966 |
| `lexicon/constructions.yaml` | `913dbb2d9a3d1673f714d58a93711853a636e48378e21f0a58b07b8b539d61a0` | 28605 |
| `lexicon/src/build_v02.py` | `22f019b5fc6cd92efc7eaa483feee6fdbd4167abe838756bbeb473db7f0bf9a2` | 9893 |
| `lexicon/src/components.py` | `b9f05754e04c95fd0e9a6832b2afb6b31820eedf509aa5edf60a5e3e7a5952a8` | 5959 |
| `lexicon/src/entries_hi.py` | `4ff7f22c338ce9ce9e1064d883d1b6cf8d241f242435c05b7b72e1cdb28750f0` | 64109 |
| `lexicon/src/entries_en.py` | `8359bf462c0c6170c37ed38b9dd61ee53262654560d2b6a61702f1e4db7fb506` | 57558 |
| `lexicon/src/lexutil_v02.py` | `98415008ca3f98f6af5f13c78dcc4b0530f5f011cee217974683258d61919078` | 1304 |
| `lexicon/src/write_support_files.py` | `b4026d3553b04c972bff927c296d53dce06c74789e0b317406d20fa31e594e0c` | 25725 |

## Resolved before this freeze (investigators' decisions, 2026-10-10)

- DUTY_UNDONE dropped from P-HI-44 and P-EN-44.
- The four one-way DUTY counterpart links made two-way (list-valued counterpart / overlap).
- Lexicon stays v0.2 (no v0.3 revision before the confirmatory split).

## Still open (not blocking the freeze)

- 21 one-way counterpart links outside the DUTY entries (e.g. L-HI-22 -> L-EN-21 -> L-HI-24); the 2026-10-10 decision covered the four DUTY links only. build_v02.py --check still does not require symmetry.

## Public release

The example sentences quoted from the corpus were removed for the public release: the `example_hi` and `example_en` columns are dropped from `lexicon.csv` and `components.csv`, and the example strings in `src/entries_hi.py`, `src/entries_en.py` and `src/components.py` are blank. No headword, explication, component, pattern or rule changed; the hashes above are of the released files. Hashes of the files as frozen on 2026-10-10:

- `lexicon/lexicon.csv`: `f4e65da0fac84aac5344ed2eca28a784f64462c5df5a77ad9f18d522fb8d9b3f` (138035 bytes)
- `lexicon/components.csv`: `1f42e7756aaaac64f390c42f7e76847d2013106ccd589218704a76780e38c5d3` (11240 bytes)
- `lexicon/src/components.py`: `1fbee7bbecc07426a882a99ce8226223fe5c3b22a2913d3149c6d31c376a1d4b` (7974 bytes)
- `lexicon/src/entries_hi.py`: `a70589162cf7e73e68500c1cb060f6f6aab373e6c6af5ce02b6086a5d41bb0e5` (72985 bytes)
- `lexicon/src/entries_en.py`: `034d075872a318eec582f92c9594500b0276d1ded33269aa163820af045caf6b` (61148 bytes)

Comments and docstrings were then removed from the code for the public release (the parsed code and data are unchanged, checked by comparing syntax trees and parsed YAML), which changed the hashes of the following files. Their hashes before that step:

- `lexicon/constructions.yaml`: `5c97cd7d411ea7ea9fc7f766aee1581f2ddaea3c7958273b09b140cc128a068a` (29820 bytes)
- `lexicon/src/build_v02.py`: `5198082ecf67ff991950fd89b3734b4ec866254cbfd724e777a015d93ec99094` (10800 bytes)
- `lexicon/src/components.py`: `2ace85e414174e526c6dde01fe1d805dea4b4331357ba0dc3a5e4b99246ce457` (6427 bytes)
- `lexicon/src/entries_hi.py`: `f4ade2f28efb276f633a4c3d23d8bfeca2f385a6d378dd398eb87281079c2157` (64709 bytes)
- `lexicon/src/entries_en.py`: `a2df6bbaec82b5b766d16bd94ea50b84614333b53c0e7b9666e4c80a13b32c42` (57990 bytes)
- `lexicon/src/lexutil_v02.py`: `4a0b05ea35ae8e6666c3a4ff9b9a95a31c96282971135518fdfeeeb17cad6818` (1560 bytes)
- `lexicon/src/write_support_files.py`: `c7008fef5cec1301f0da70baea4642832b8763b89c23e4930552261533b636a8` (26866 bytes)
