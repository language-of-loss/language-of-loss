import hashlib
import re
import unicodedata

DEV = re.compile(r"[ऀ-ॿ]")
LATIN = re.compile(r"[A-Za-z]")
WORD = re.compile(r"[^\W\d_]+(?:[ऀ-ॿ‌‍]|[^\W\d_]|['’](?=[^\W\d_]))*", re.UNICODE)

HI_DEV_FUNC = {"है", "हैं", "का", "की", "के", "में", "से", "को", "और", "नहीं", "था", "थी", "थे", "भी", "पर", "कि", "यह", "वह", "मैं", "हम", "तो", "ही", "हो", "गया", "गई", "गए", "रहा", "रही", "लिए"}
MR_FUNC = {"आहे", "आहेत", "आणि", "नाही", "मी", "होते", "होती", "होता", "पण", "तर", "माझ्या", "माझे", "माझी", "आम्ही", "त्यांनी", "झाले", "झाला", "काही", "म्हणून"}
NE_FUNC = {"छ", "छन्", "थियो", "भयो", "हुन्छ", "मेरो", "गर्न", "पनि", "तर", "भने", "हुनुहुन्छ", "गरेको", "भएको", "तपाईं", "हामी", "थिए"}
HI_ROM_FUNC = {"hai", "hain", "nahi", "nahin", "nhi", "mera", "meri", "mere", "ka", "ki", "ke", "ko", "se", "aur", "tha", "thi", "kya", "bhi", "gaye", "gaya", "gayi", "raha", "rahe", "rahi", "mujhe", "humne", "unka", "unki", "unke", "kuch", "bahut", "bohot", "jab", "tab", "yeh", "woh", "wo", "kar", "karna", "hum", "aap", "apne", "liye", "hoga", "hota", "hoti", "hue", "hui", "sab", "par", "lekin", "kyunki", "toh", "mein", "main", "ek", "kabhi", "aaj", "ab", "kisi", "yaad", "baad"}
EN_FUNC = {"the", "and", "of", "to", "was", "is", "my", "in", "that", "he", "she", "with", "for", "his", "her", "it", "had", "on", "at", "but", "not", "we", "i", "a", "as", "be", "have", "this", "when", "from", "you", "were", "they", "would", "there", "been", "after", "about", "what", "so", "an"}

AMBIG_ROM_EN = {"to", "is", "me", "he", "the", "so", "in", "par", "main", "hi", "ho", "ab", "tab", "jab", "a", "i", "be", "an", "as", "at", "on", "we", "bhi"} - {"bhi", "jab", "tab", "ab", "ho"}


def words(text):
    return WORD.findall(text or "")


def word_count(text):
    return len(words(text))


def detect_language(text):
    toks = [w.lower() for w in words(text)]
    n = len(toks)
    dev = len(DEV.findall(text or ""))
    lat = len(LATIN.findall(text or ""))
    letters = sum(ch.isalpha() for ch in (text or ""))
    d = {"n_words": n, "dev_share": round(dev / max(dev + lat, 1), 3),
         "other_script_share": round(max(letters - dev - lat, 0) / max(letters, 1), 3)}
    if n < 4:
        return "uncertain", {**d, "reason": "too_short"}
    if d["other_script_share"] > 0.4:
        return "other_language", {**d, "reason": "other_script"}
    dev_toks = [t for t in toks if DEV.search(t)]
    lat_toks = [t for t in toks if not DEV.search(t)]
    hi_dev = sum(t in HI_DEV_FUNC for t in dev_toks)
    mr = sum(t in MR_FUNC for t in dev_toks)
    ne = sum(t in NE_FUNC for t in dev_toks)
    amb = sum(t in AMBIG_ROM_EN for t in lat_toks)
    hi_u = sum(t in HI_ROM_FUNC and t not in AMBIG_ROM_EN for t in lat_toks)
    en_u = sum(t in EN_FUNC and t not in AMBIG_ROM_EN for t in lat_toks)
    hi_rom, en = (hi_u + amb, en_u) if hi_u > en_u else (hi_u, en_u + amb)
    d.update(hi_dev_func=hi_dev, mr_func=mr, ne_func=ne, hi_rom_func=hi_rom, en_func=en)
    dev_tok_share = len(dev_toks) / n
    if dev_tok_share >= 0.5 and max(mr, ne) > hi_dev and max(mr, ne) >= 3:
        return "other_language", {**d, "reason": "devanagari_non_hindi_markers"}
    rom_rate = hi_rom / max(len(lat_toks), 1)
    en_rate = en / max(len(lat_toks), 1)
    lat_is_hi = len(lat_toks) >= 4 and rom_rate >= 0.12 and rom_rate > en_rate
    lat_is_en = len(lat_toks) >= 4 and en_rate >= 0.15 and en_rate >= rom_rate
    if dev_tok_share >= 0.85:
        if hi_dev == 0 and n >= 12:
            return "uncertain", {**d, "reason": "devanagari_without_hindi_function_words"}
        return "devanagari_hindi", d
    if dev_tok_share >= 0.15:
        if lat_is_en or (len(lat_toks) / n) >= 0.25:
            return "mixed_hi_en", d
        return "devanagari_hindi", d
    if lat_is_hi and en_rate >= 0.10:
        return "mixed_hi_en", d
    if lat_is_hi:
        return "romanized_hindi", d
    if lat_is_en and rom_rate >= 0.05 and hi_rom >= 3:
        return "mixed_hi_en", d
    if lat_is_en:
        return "english", d
    return "uncertain", {**d, "reason": "no_clear_function_word_profile"}


def normalize_for_analysis(text):
    t = unicodedata.normalize("NFC", text or "").replace("\r\n", "\n").replace("\r", "\n")
    t = "".join(ch for ch in t if ch in "\n\t‌‍" or unicodedata.category(ch) not in ("Cc", "Cf"))
    t = re.sub(r"[ \t ]+", " ", t)
    t = re.sub(r" *\n *", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def dedup_key(text):
    t = unicodedata.normalize("NFKC", text or "").lower()
    t = re.sub(r"https?://\S+|[@#]\w+", " ", t)
    t = "".join(ch for ch in t if ch.isalnum() or ch.isspace() or "ऀ" <= ch <= "ॿ")
    return hashlib.sha1(" ".join(t.split()).encode("utf-8")).hexdigest()


def shingles(text, k=5):
    toks = [w.lower() for w in words(text)]
    if len(toks) < k:
        return {" ".join(toks)} if toks else set()
    return {" ".join(toks[i:i + k]) for i in range(len(toks) - k + 1)}


def jaccard(a, b):
    return len(a & b) / max(len(a | b), 1)


KIN_EN = r"(?:mother|mom|mum|mummy|amma|father|dad|daddy|papa|appa|brother|sister|husband|wife|son|daughter|child|baby|grand(?:ma|pa|mother|father)|granny|nani|dadi|nana|dada|uncle|aunt|aunty|cousin|friend|bhai|didi|chacha|mama|mausi)"
DEATH_EN = r"(?:passed away|died|death|demise|is no more|was no more|lost (?:my|our|him|her)|funeral|cremat\w+|last rites|left us|left this world|breathed (?:his|her) last|bereave\w+|grie(?:f|ving|ve)|mourn\w*)"
EN_FIRST = re.compile(r"\b(?:my|our)\s+(?:late\s+|beloved\s+|dear\s+|dearest\s+)?" + KIN_EN + r"\b", re.I)
EN_DEATH = re.compile(r"\b" + DEATH_EN, re.I)

KIN_HI = r"(?:पापा|पिता|पिताजी|बाबूजी|बाबा|पप्पा|डैडी|माँ|मां|मम्मी|अम्मा|माता|माताजी|भाई|भैया|बहन|दीदी|पति|पत्नी|बेटा|बेटी|बेटे|दादी|दादा|दादाजी|नानी|नाना|नानाजी|चाचा|चाची|मामा|मौसी|बुआ|दोस्त|मित्र|सहेली)"
HI_FIRST = re.compile(r"(?:मेरे|मेरी|मेरा|हमारे|हमारी|हमारा|अपने|अपनी)\s+(?:प्यारे\s+|प्यारी\s+|स्वर्गीय\s+|पूज्य\s+)?" + KIN_HI)
HI_DEATH = re.compile(r"(?:निधन|देहांत|देहान्त|देहावसान|स्वर्गवास|गुज़र ग|गुजर ग|चल बसे|चल बसी|चल बसा|नहीं रहे|नहीं रहीं|नहीं रही|मृत्यु|मौत|अंतिम संस्कार|अंतिम विदाई|अंतिम सांस|पुण्यतिथि|बरसी|तेरहवीं|छोड़कर चले|छोड़ कर चले|छोड़ के चले|छोड़ गए|छोड़ गई|छोड़ गईं|चले गए|चली गई|चली गईं|गुजर गए|गुज़र गए|इस दुनिया में नहीं|दुनिया में नहीं है|दुनिया से चले|दुनिया छोड़|खो दिया|खो चुक|शोक|श्रद्धांजलि|स्वर्ग सिधार)")

KIN_ROM = r"(?:papa|pitaji|pita|daddy|dad|maa|mummy|mumma|mom|amma|bhai|bhaiya|behen|behan|didi|pati|patni|beta|beti|dadi|dada|dadaji|nani|nana|nanaji|chacha|mama|mausi|bua|dost)"
ROM_FIRST = re.compile(r"\b(?:mere|meri|mera|hamare|hamari|humare|humari|apne|apni)\s+(?:pyare\s+|pyari\s+)?" + KIN_ROM + r"\b", re.I)
ROM_DEATH = re.compile(r"\b(?:nidhan|dehant|swargwas|swargvas|guzar ga\w*|gujar ga\w*|chal base|chal basi|nahi+n? rah[ei]|nhi rah[ei]|mrityu|maut|death ho|expire ho|antim sanskar|antim vidai|punyatithi|barsi|terahvi\w*|chhod kar chale|chod kar chale|ch+od ke chale|ch+od ga[yi]e?|chale ga[yi]e?|chale gye|chali ga[yi]i?|guzar gye|gujar gye|is duniya me\w* nahi\w*|is duniya me\w* nhi|duniya me\w* nahi\w* h\w*|duniya chh?od|kho diya|kho chuk\w+|shradhanjali|shraddhanjali|death ho ga?[yi]\w*|death hui|death ho chuki|expire ho ga?[yi]\w*|expired ho ga?[yi]\w*|off ho ga[yi]e?|nhi rh[ei]|nahi rh[ei]|swarg sidhar\w*)\b", re.I)


def bereavement_screen(text):
    out = {"hit": False, "side": None, "n_kin": 0, "n_death": 0}
    window = 400
    for side, first, death in (("en", EN_FIRST, EN_DEATH), ("hi", HI_FIRST, HI_DEATH), ("hi-Latn", ROM_FIRST, ROM_DEATH)):
        kin_pos = [m.start() for m in first.finditer(text or "")]
        death_pos = [m.start() for m in death.finditer(text or "")]
        if kin_pos and death_pos and any(abs(k - d_) <= window for k in kin_pos for d_ in death_pos):
            if not out["hit"] or len(kin_pos) + len(death_pos) > out["n_kin"] + out["n_death"]:
                out.update(hit=True, side=side, n_kin=len(kin_pos), n_death=len(death_pos))
    return out
