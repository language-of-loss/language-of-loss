import bisect
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from griefcorpus.textutil import EN_DEATH, EN_FIRST, HI_DEATH, HI_FIRST, WORD

FP_CAP = {"hi": 4.7, "en": 9.1}
PAST_CAP = {"hi": 6.9, "en": 10.4}
DEATH_COUNT_CAP = 3
WINDOW = 200
B, E = r"(?<![ऀ-ॿA-Za-z])", r"(?![ऀ-ॿA-Za-z])"
FIRST = {"hi": re.compile(B + r"(?:मैं|मैंने|मुझे|मुझको|मुझ|मेरा|मेरी|मेरे|मैने)" + E),
         "en": re.compile(r"(?<![A-Za-z'])(?:I|me|my|mine|myself|I'm|I've|I'd)(?![A-Za-z])")}
PAST = {"hi": re.compile(B + r"(?:था|थी|थे|थीं|गया|गई|गयी|गए|गये|गईं|हुआ|हुई|हुए|लिया|दिया|किया|कहा|रहा|रही|रहे)" + E),
        "en": re.compile(r"(?<![A-Za-z])(?:[A-Za-z]{3,}ed|was|were|had|did|went|came|said|told|took|gave|saw|knew|"
                         r"thought|felt|left|died|lost|got|made|became|began|kept|held|sat|stood|heard|ran|fell)(?![A-Za-z])",
                         re.I)}
KIN = {"hi": HI_FIRST, "en": EN_FIRST}
DEATH = {"hi": HI_DEATH, "en": EN_DEATH}


def word_spans(text):
    return [m.start() for m in WORD.finditer(text)]


def score(text, lang):
    starts = word_spans(text)
    n = max(len(starts), 1)
    word_at = lambda pos: bisect.bisect_right(starts, pos)
    fp = len(FIRST[lang].findall(text)) * 100 / n
    past = len(PAST[lang].findall(text)) * 100 / n
    kin_pos = [word_at(m.start()) for m in KIN[lang].finditer(text)]
    death_pos = [word_at(m.start()) for m in DEATH[lang].finditer(text)]
    near = sum(1 for d in death_pos if any(abs(k - d) <= WINDOW for k in kin_pos))
    parts = dict(first_person=round(min(fp / FP_CAP[lang], 1.0), 3), kin=1.0 if kin_pos else 0.0,
                 death_near_kin=round(min(near, DEATH_COUNT_CAP) / DEATH_COUNT_CAP, 3),
                 past=round(min(past / PAST_CAP[lang], 1.0), 3))
    parts["score"] = round(sum(parts.values()), 3)
    parts["n_words"] = len(starts)
    return parts
