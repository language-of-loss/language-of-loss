#!/bin/bash
set -u
cd "$(dirname "$0")/.." || exit 1
echo "== project root: $(pwd)"

echo "== 1. python venv (needs Python 3.10+; 3.9 is end-of-life and current packages refuse it)"
PYBIN=""
for c in python3.12 python3.11 python3.13 python3; do
  if command -v "$c" >/dev/null 2>&1; then
    if "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'; then PYBIN="$(command -v $c)"; break; fi
  fi
done
if [ -z "$PYBIN" ]; then
  echo "No Python 3.10+ found. Install Python 3.12 from https://www.python.org/downloads/macos/ (macOS 64-bit universal2 installer), then re-run this script."
  exit 1
fi
echo "using $PYBIN ($($PYBIN --version))"
if [ -x .venv/bin/python ] && ! .venv/bin/python -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'; then
  echo "existing .venv is Python 3.9 -> renaming it to .venv_py39 and creating a fresh one"
  mv .venv .venv_py39
fi
if [ ! -x .venv/bin/python ]; then "$PYBIN" -m venv .venv; fi
.venv/bin/python --version

echo "== 2. install analysis packages (a few minutes the first time)"
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt -r requirements-analysis.txt || { echo "pip install FAILED — paste the lines above into the chat"; exit 1; }

echo "== 3. Stanza models (hi + en, ~1 GB download)"
.venv/bin/python -c "import stanza; stanza.download('hi', verbose=False); stanza.download('en', verbose=False); print('stanza models ok')"

echo "== 4. WordNet data"
.venv/bin/python -c "import nltk; nltk.download('wordnet', quiet=True); nltk.download('omw-1.4', quiet=True); print('wordnet ok')"

echo "== 5. environment check"
.venv/bin/python -c "import stanza, networkx, sklearn, statsmodels, datasketch, krippendorff, regex; print('env ok')"
.venv/bin/python lexicon/src/build_v02.py --check && echo "lexicon v0.2 check ok"

echo "== 6. git"
if [ ! -d .git ]; then
  git init -q && git add -A && git commit -q -m "Analysis phase start: release v1 pipeline + lexicon v0.2 + seed v2 merge" && echo "git repo created, first commit done"
else
  echo "git repo already exists"
fi

echo "== 7. what else is installed?"
for t in R Rscript node; do
  if command -v "$t" >/dev/null 2>&1; then echo "  $t: $(command -v "$t")"; else echo "  $t: NOT installed"; fi
done
echo
echo "SETUP FINISHED. Copy everything above into the chat."
