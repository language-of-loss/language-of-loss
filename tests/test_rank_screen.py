import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import rank_screen as RS


def test_first_person_grief_narrative_scores_high():
    s = RS.score("मेरे पिता का निधन पिछले साल हुआ था। मैं उस दिन अस्पताल में था और मुझे कुछ समझ नहीं आया।", "hi")
    assert s["kin"] == 1 and s["death_near_kin"] > 0 and s["first_person"] == 1.0 and s["score"] > 2.5


def test_news_style_text_without_first_person_scores_lower():
    a = RS.score("My mother died in March. I sat with her and I held her hand when she was gone.", "en")
    b = RS.score("The minister died in March. Officials will announce a state funeral tomorrow.", "en")
    assert a["score"] > b["score"] and b["kin"] == 0 and b["first_person"] == 0


def test_death_far_from_kin_does_not_count():
    filler = " ".join(["word"] * 250)
    s = RS.score(f"my father liked tea. {filler} the old tree died.", "en")
    assert s["kin"] == 1 and s["death_near_kin"] == 0


def test_bare_kin_word_is_not_first_person_kin():
    assert RS.score("उनकी माँग पूरी हुई और पिता जी आए", "hi")["kin"] == 0
    assert RS.score("Asha's father sang", "en")["kin"] == 0
