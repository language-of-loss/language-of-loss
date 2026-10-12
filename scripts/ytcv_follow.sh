#!/bin/bash
cd "$(dirname "$0")/.."; export PYTHONPATH=src
while true; do
  .venv/bin/python -m griefcorpus.collectors ytcv 2>&1 | grep -v -i warn
  SZ=$(stat -f %z data/raw/reused_datasets/ytcommentverse/YT-30M.db)
  if [ "$SZ" -ge 10843156480 ] && grep -q "nothing new" <(.venv/bin/python -m griefcorpus.collectors ytcv 2>&1); then echo "COMPLETE $(date -u +%FT%TZ)"; break; fi
  sleep 900
done
