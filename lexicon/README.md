# lexicon/ — Bilingual grief lexicon v0.2 (Plan v3 layout)

| File | What | Canonical for |
|---|---|---|
| `lexicon.csv` | 205 entries (96 hi, 109 en) in Plan v3 L2 column order + `component_vector`, `lang`, `status`; constructions carry `pattern` | L2, L4 matcher |
| `primes.csv` | 65 primes, proposed Hindi exponents, allolexes, polysemy, two canonical-context test sentences, confidence, v0.1 exponent for comparison | L3 |
| `components.csv` | K = 24 components in prime language with examples, status, carrier counts and carriers | L6, N1 |
| `entry_vectors.csv` | entry × component binary matrix + `names_emotion` form flag | L6, N1 |
| `flag_components.csv` | construction flags → components, grammar_forced, sub-flags, N2 eligibility rule | N1 step 2, P8b |
| `constructions.yaml` | the same flags with their regexes (copied from lexicon.csv), kin lexicons, matcher rules R1–R8 | P8 |
| `molecules.csv` | every semantic molecule used, where, and why; tolerated non-prime words with reasons | L2 rule |
| `CHANGELOG.md` | every v0.1 entry touched and why; component changes | — |
| `src/` | the Python sources that regenerate every CSV (`python src/build_v02.py`), plus the checker (`--check`) | reproducibility |
| `scripts/` | embedding protocol (4 scripts + helper) and the component classifier; real models named in each header, not downloaded here | Recommendation Part 2 |
| `docs/` | draft document (prime table narrative, protocol, classifier spec, validation checklist) and the v0.1 file | — |

Status: everything `proposed`. Nothing here is a result; `corpus_freq_*` are blank until ground_entries.py is run on the corpus and the numbers are copied in by hand with the corpus version.

Checks the build enforces: prime-only explications (molecules marked [m]); 2–8 lines; every tag traceable to a line (R ⇐ RITUAL_WORDS; F ⇐ KIN/BOND; C ⇐ WITH_OTHERS/EVERYONE/HONOUR; FEEL_BAD ⇐ a feel line; AVOID_DIE ⇐ the die line; ABOVE ⇐ an above line); no two entries in a language share an explication; counterpart ids exist and overlap is symmetric; every pattern compiles, uses no `\b`, and matches its own example.
