PY := .venv/bin/python

LLM ?= 0

.PHONY: core core-dry setup setup-xlit shortform check merge preprocess flags lexmatch referents eligibility decompose text_meta all repro-snapshot run-summary predictions collocation a1-score a1-dry a1 muril-pair muril-pair-smoke llm-plan audit-chat-plan audit-local reader-kit audit-readers register gold agreement agreement-pilot assemble figures figures-v2 tables synthetic code-appendix test test-pipeline help optional-entropy optional-predictions optional-figures optional-a1 optional-component-map optional-decompose-dative

core:
	$(PY) src/analysis/core.py $(if $(filter 1,$(LLM)),--llm,)

core-dry:
	$(PY) src/analysis/core.py --dry-run


setup:
	.venv/bin/pip install -r requirements.txt -r requirements-analysis.txt
	$(PY) -c "import stanza; stanza.download('hi'); stanza.download('en')"
	$(PY) -c "import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')"

check:
	$(PY) -c "import stanza, networkx, sklearn, statsmodels, datasketch; print('env ok')"
	$(PY) lexicon/src/build_v02.py --check

merge:
	$(PY) scripts/apply_review.py --from-ledger

preprocess:
	$(PY) src/analysis/preprocess.py --in data/clean/blogs_merged.jsonl --out data/processed/clauses.jsonl

flags:
	$(PY) src/analysis/flags.py --in data/processed/clauses.jsonl --out data/processed/flags.csv

lexmatch:
	$(PY) src/analysis/lexmatch.py --lexicon lexicon/lexicon.csv --in data/processed/clauses.jsonl --flags data/processed/flags.csv --out data/processed/clause_features.csv

referents:
	$(PY) src/analysis/referents.py --in data/processed/clauses.jsonl --out data/processed/referents.csv

eligibility:
	$(PY) src/analysis/eligibility.py --in data/processed/clauses.jsonl --out data/processed/eligibility.csv --flags data/processed/flags.csv

decompose:
	$(PY) src/analysis/decompose.py --marker relational --out results/decompose_relational_dev.csv

text_meta:
	$(PY) src/analysis/text_meta.py

all:
	$(PY) src/analysis/make_all.py

repro-snapshot:
	$(PY) src/analysis/make_all.py --snapshot

setup-xlit:
	bash scripts/setup_xlit.sh

shortform:
	$(PY) src/analysis/shortform.py
	$(PY) src/analysis/flags.py --in data/processed/shortform/clauses.jsonl --out data/processed/shortform/flags.csv
	$(PY) src/analysis/lexmatch.py --lexicon lexicon/lexicon.csv --in data/processed/shortform/clauses.jsonl --flags data/processed/shortform/flags.csv --out data/processed/shortform/clause_features.csv
	$(PY) src/analysis/referents.py --in data/processed/shortform/clauses.jsonl --records data/processed/shortform/records.jsonl --out data/processed/shortform/referents.csv
	$(PY) src/analysis/shortform.py --report

run-summary:
	$(PY) src/analysis/make_all.py --summary

predictions:
	$(PY) src/analysis/predictions.py

collocation:
	$(PY) src/analysis/collocation.py

assemble:
	$(PY) src/analysis/assemble.py

figures:
	$(PY) src/analysis/figures.py

figures-v2:
	$(PY) scripts/figures_v2.py

tables:
	$(PY) src/analysis/assemble_tables.py

synthetic:
	$(PY) src/analysis/synthetic_results.py
	$(PY) src/analysis/figures.py --results results/synthetic
	$(PY) src/analysis/assemble_tables.py --results results/synthetic

code-appendix:
	$(PY) src/analysis/code_appendix.py

a1-score:
	$(PY) src/analysis/translation_bias.py --score

a1-dry:
	$(PY) src/analysis/translation_bias.py --dry-run

a1:
	@test -f data/annotation/a1_gold.csv || { echo "data/annotation/a1_gold.csv not found: A1 waits for gold codes (use make a1-dry)"; exit 1; }
	$(PY) src/analysis/translation_bias.py --score
	$(PY) src/analysis/translation_bias.py --gold data/annotation/a1_gold.csv

muril-pair:
	$(PY) src/analysis/train_muril_pair.py

muril-pair-smoke:
	$(PY) src/analysis/train_muril_pair.py --smoke --only native --device cpu

llm-plan:
	$(PY) src/analysis/llm_coder.py --plan-only

audit-chat-plan:
	$(PY) src/analysis/audit_chat.py --plan-only

audit-local:
	$(PY) src/analysis/audit_chat.py --provider ollama --confirm
	Rscript R/audit.R --run

reader-kit:
	$(PY) src/analysis/reader_kit.py

audit-readers:
	$(PY) src/analysis/reader_ingest.py
	$(PY) src/analysis/audit_match.py --readers data/annotation/reader_ratings.csv
	Rscript R/audit.R --run

register:
	$(PY) src/analysis/register.py

gold:
	$(PY) src/analysis/gold.py --dry-run --in data/processed/clauses.jsonl --features data/processed/clause_features.csv

agreement:
	$(PY) src/analysis/agreement.py --a data/annotation/gold_sheet_v1_coder1.csv --b data/annotation/gold_sheet_v1_coder2.csv
	$(PY) src/analysis/agreement.py --a data/annotation/gold_components_v1_coder1.csv --b data/annotation/gold_components_v1_coder2.csv

agreement-pilot:
	$(PY) src/analysis/agreement.py --a data/annotation/gold_pilot_r1.csv --b data/annotation/gold_pilot_r2.csv

test:
	$(PY) -m pytest -q tests

test-pipeline:
	$(PY) -m pytest -q tests/test_preprocess.py tests/test_flags.py tests/test_lexmatch.py tests/test_referents.py tests/test_eligibility.py tests/test_relational_sites.py tests/test_decompose.py tests/test_text_meta.py tests/test_make_all.py tests/test_shortform.py tests/test_core.py

optional-entropy:
	$(PY) src/optional/entropy.py

optional-predictions:
	$(PY) src/optional/predictions_extra.py

optional-figures:
	$(PY) src/optional/figures.py

optional-component-map:
	$(PY) src/optional/component_map.py

optional-decompose-dative:
	$(PY) src/analysis/decompose.py --out results/optional/decompose_dev.csv

optional-a1:
	$(PY) src/optional/translation_extra.py --dry-run

help:
	@grep -E '^[a-z0-9_-]+:' Makefile | cut -d: -f1
