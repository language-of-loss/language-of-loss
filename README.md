# The Language of Loss: Relational Grief in Hindi and Indian English

This repository holds the analysis code, the grief lexicon and the aggregate results of a corpus study of grief
writing in Hindi and Indian English (blogs and personal essays). The study asks whether Hindi grief writing frames
loss more relationally, through dative "experiencer" constructions (*mujhe dukh hua*, "to me grief happened") and
references to kin and the deceased, and how much of any difference the grammar forces rather than the writer chooses.
Clause-level choice, forced and opportunity shares are separated by a decomposition and tested with a mixed model that
was fixed in advance; a 205-entry Hindi-English lexicon built on Natural Semantic Metalanguage (24 semantic components)
supplies the dictionary channel, and two audits test translation-based resources and machine readers on the same texts.

## Repository structure

```
src/griefcorpus/   corpus collection and cleaning (release v1 collectors; official APIs and open downloads only)
src/analysis/      analysis pipeline: preprocessing (Stanza), flags, eligibility, referents, lexicon matching,
                   agreement, validation, decomposition, predictions, audits, tables and figures
src/analysis/providers/   api_client.py (commercial LLM API) and ollama.py (local model on a loopback address)
src/optional/      optional and exploratory analyses
R/                 mixed models (h1_glmm.R), audit models (audit.R), publication figures
scripts/           collection, screening, ingestion and robustness scripts
tests/             pytest suite (no corpus text)
config/            pipeline settings and source decisions
lexicon/           grief lexicon v0.2: generated CSVs, the Python sources they are built from, methodology notes
results/           aggregate result tables (CSV / Markdown); RESULTS_LOG.md records the command behind every number
figures/final/     figures (PDF + PNG) and captions
supplementary/     supplementary material: lexicon CSVs, codebook, predicate rule table, result tables,
                   full-resolution figures; supplementary/README.md describes every file
docs/codebook_v1.md   the annotation codebook
tools/             annotation helper page and reader-study form generator
fonts/             Noto Sans Devanagari (SIL Open Font License) for the figures
```

## Reproducing the results

The corpus texts are third-party writing and are **not redistributed** here; neither are clause-level files,
annotation sheets or model caches. The scripts rebuild everything from the texts: the collectors in
`src/griefcorpus/` and `scripts/` fetch the sources through their official APIs or open downloads (credentials go in
`.env`, see `.env.example`), and the analysis runs from the cleaned files.

```bash
make setup        # create the Python environment and install the analysis dependencies
make check        # environment and lexicon consistency checks
make core-dry     # plan: which steps would run and which inputs are missing
make core         # outputs 1-9; the two API steps run only with: make core LLM=1
make test         # test suite
```

The LLM coding channel (`src/analysis/llm_coder.py`) and one arm of the machine-reader audit
(`src/analysis/audit_chat.py`) used a commercial large language model API. To run them, install that provider's
Python SDK and set three environment variables (there are no defaults):

```bash
export LLM_PROVIDER=...   # import name of the provider's Python SDK
export LLM_MODEL=...      # model identifier
export LLM_API_KEY=...    # API key (read at run time, never logged)
```

The audit's local arm runs an open model through Ollama on the same machine (`make audit-local`). Labels in the
results are reviewed machine-prefilled labels; their provenance is stated in every result table.

## Requirements

- Python 3.12 (`requirements.txt`, `requirements-analysis.txt`; `requirements-llm.txt` for the API steps)
- Stanza 1.15 (Hindi and English models)
- R 4.6 with lme4, lmerTest, clubSandwich and glmnet

## Licences

- Code: MIT (`LICENSE`)
- Lexicon (`lexicon/`): CC BY 4.0 (`lexicon/LICENSE`)
- Fonts: SIL Open Font License (`fonts/OFL.txt`)
