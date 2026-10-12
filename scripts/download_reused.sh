#!/bin/bash
set -u
cd "$(dirname "$0")/../data/raw/reused_datasets"
UA="grief-hi-en-corpus/0.1 (academic research)"
curl -L -C - --retry 5 --retry-delay 20 -A "$UA" -o socialgrep_confessions/one-million-reddit-confessions.csv \
  "https://huggingface.co/datasets/SocialGrep/one-million-reddit-confessions/resolve/main/one-million-reddit-confessions.csv"
curl -L -C - --retry 5 --retry-delay 20 -A "$UA" -o ytcommentverse/YT-30M.db \
  "https://zenodo.org/api/records/15678816/files/YT-30M.db/content"
echo "DONE $(date -u +%FT%TZ)"
