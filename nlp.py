import re
from typing import Optional, Tuple, List

# Simple category synonyms (extend anytime)
CAT_MAP = {
    # uz
    "taksi": "transport",
    "transport": "transport",
    "ovqat": "food",
    "oziq": "food",
    "kafe": "food",
    "restoran": "food",
    "dorixona": "health",
    "dori": "health",
    "internet": "internet",
    "aloqa": "internet",
    "kommunal": "utilities",
    "ijara": "rent",

    # ru
    "еда": "food",
    "такси": "transport",
    "транспорт": "transport",
    "аптека": "health",
    "интернет": "internet",
    "связь": "internet",
    "коммуналка": "utilities",
    "аренда": "rent",

    # en
    "food": "food",
    "taxi": "transport",
    "transport": "transport",
    "pharmacy": "health",
    "internet": "internet",
    "rent": "rent",
    "utilities": "utilities",
}

AMOUNT_RE = re.compile(r"(\d[\d\s.,]{1,20})")

def _norm_amount(s: str) -> Optional[int]:
    digits = "".join(ch for ch in s if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except:
        return None

def normalize_category(word: str) -> str:
    w = word.strip().lower()
    return CAT_MAP.get(w, w)

def parse_one(text: str) -> Optional[Tuple[str, int, Optional[str]]]:
    """
    Accept:
      - "taksi 2000"
      - "food 97500 lunch"
      - "2000 taksi"
      - "ovqat 120000"
    """
    t = (text or "").strip()
    if not t:
        return None

    # amount anywhere
    m = AMOUNT_RE.search(t)
    if not m:
        return None
    amount = _norm_amount(m.group(1))
    if amount is None:
        return None

    # remove amount part
    before = t[:m.start()].strip()
    after = t[m.end():].strip()

    # choose category: first token in before OR first token in after
    cat = None
    desc_parts: List[str] = []

    if before:
        parts = before.split()
        cat = normalize_category(parts[0])
        desc_parts += parts[1:]
        if after:
            desc_parts += after.split()
    else:
        # amount first -> category likely after
        parts = after.split()
        if not parts:
            return None
        cat = normalize_category(parts[0])
        desc_parts += parts[1:]

    desc = " ".join(desc_parts).strip() or None
    return (cat, amount, desc)

def parse_multi(text: str) -> List[Tuple[str, int, Optional[str]]]:
    """
    Support multi-item:
      "taksi 2000; ovqat 45000; internet 50000"
      or separated by newline.
    """
    t = (text or "").strip()
    if not t:
        return []
    chunks = []
    for part in re.split(r"[;\n]+", t):
        part = part.strip()
        if not part:
            continue
        one = parse_one(part)
        if one:
            chunks.append(one)
    return chunks

def looks_like_expense_text(text: str) -> bool:
    return parse_one(text) is not None
