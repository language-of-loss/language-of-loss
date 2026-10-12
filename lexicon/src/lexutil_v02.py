L = r"(?<![ऀ-ॣ०-९ॱ-ॿ‌‍A-Za-z0-9_'])"
R = r"(?![ऀ-ॣ०-९ॱ-ॿ‌‍A-Za-z0-9_'])"

def P(core: str) -> str:
    return L + "(?:" + core + ")" + R

COLS = ["entry_id", "headword_deva", "headword_roman_variants", "headword_en", "pos",
        "corpus_freq_hi", "corpus_freq_en", "nsm_explication", "component_vector",
        "orientation", "process", "function", "register", "cultural_script", "idiom_flag",
        "grammar_forced", "counterpart", "overlap", "example_hi", "example_en", "source_notes",
        "pattern", "lang", "status"]

def E(entry_id, deva, roman, en, pos, expl, comps, ori, proc, func, reg, script, idiom, gf,
      cp, ov, ex_hi, ex_en, notes, pattern="", lang="hi"):
    return {
        "entry_id": entry_id, "headword_deva": deva, "headword_roman_variants": roman,
        "headword_en": en, "pos": pos, "corpus_freq_hi": "", "corpus_freq_en": "",
        "nsm_explication": expl, "component_vector": "; ".join(comps),
        "orientation": ori, "process": proc, "function": func, "register": reg,
        "cultural_script": script, "idiom_flag": idiom, "grammar_forced": gf,
        "counterpart": cp, "overlap": ov, "example_hi": ex_hi, "example_en": ex_en,
        "source_notes": notes, "pattern": pattern, "lang": lang, "status": "proposed",
    }
