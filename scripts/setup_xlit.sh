#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PY39="${PY39:-/usr/bin/python3}"
"$PY39" -c 'import sys; assert sys.version_info[:2] == (3, 9), sys.version' || { echo "need Python 3.9 (set PY39=...)"; exit 1; }
[ -x .venv_xlit/bin/python ] || "$PY39" -m venv .venv_xlit
.venv_xlit/bin/pip install -q "ai4bharat-transliteration==1.1.3"
.venv_xlit/bin/python -c "import ai4bharat.transliteration, torch, fairseq; print('xlit venv ok: torch', torch.__version__, 'fairseq', fairseq.__version__)"
