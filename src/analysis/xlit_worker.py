import argparse
import contextlib
import json
import sys

import torch

torch.serialization.add_safe_globals([argparse.Namespace])


def main():
    req = json.load(sys.stdin)
    with contextlib.redirect_stdout(sys.stderr):
        from ai4bharat.transliteration import XlitEngine
        if req["direction"] == "rom2deva":
            eng = XlitEngine("hi", beam_width=max(4, req.get("topk", 1)), rescore=False)
            out = {w: eng.translit_word(w, topk=req.get("topk", 1))["hi"] for w in req["words"]}
        elif req["direction"] == "deva2rom":
            eng = XlitEngine(src_script_type="indic", beam_width=max(4, req.get("topk", 1)), rescore=False)
            out = {w: eng.translit_word(w, lang_code="hi", topk=req.get("topk", 1)) for w in req["words"]}
        else:
            raise SystemExit(f"unknown direction {req['direction']!r}")
    json.dump(out, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
