"""
NLP Module for Hamyon Bot
Parses expense/income text in multiple languages
"""

import re
from typing import Optional, Tuple, List

# ══════════════════════════════════════════════════════════════════════════════
# CATEGORY MAPPING - Extended for uz/ru/en
# ══════════════════════════════════════════════════════════════════════════════

CAT_MAP = {
    # ─────────────────────────────────────────────────────────────────────────
    # Uzbek
    # ─────────────────────────────────────────────────────────────────────────
    "taksi": "transport",
    "taxi": "transport",
    "transport": "transport",
    "avtobus": "transport",
    "metro": "transport",
    "benzin": "transport",
    "yoqilgi": "transport",
    
    "ovqat": "food",
    "oziq": "food",
    "oziq-ovqat": "food",
    "taom": "food",
    "nonushta": "food",
    "tushlik": "food",
    "kechki": "food",
    "kafe": "food",
    "restoran": "food",
    "choy": "food",
    "qahva": "food",
    "kofe": "food",
    
    "dorixona": "health",
    "dori": "health",
    "shifoxona": "health",
    "klinika": "health",
    "vrach": "health",
    "doktor": "health",
    
    "internet": "internet",
    "aloqa": "internet",
    "telefon": "internet",
    "mobil": "internet",
    "ucell": "internet",
    "beeline": "internet",
    "mobiuz": "internet",
    "uzmobile": "internet",
    
    "kommunal": "utilities",
    "gaz": "utilities",
    "suv": "utilities",
    "elektr": "utilities",
    "issiqlik": "utilities",
    
    "ijara": "rent",
    "kvartira": "rent",
    "uy": "rent",
    
    "kino": "entertainment",
    "teatr": "entertainment",
    "kontsert": "entertainment",
    "park": "entertainment",
    
    "kiyim": "shopping",
    "poyabzal": "shopping",
    "magazin": "shopping",
    "bozor": "shopping",
    "market": "shopping",
    "supermarket": "shopping",
    
    "kurs": "education",
    "kitob": "education",
    "talim": "education",
    "maktab": "education",
    "universitet": "education",
    
    "maosh": "salary",
    "oylik": "salary",
    "ish": "salary",
    
    "biznes": "business",
    "savdo": "business",
    "foyda": "business",
    
    "sovga": "gift",
    "hadya": "gift",
    "tug'ilgan": "gift",
    
    "qarz": "debt",
    "kredit": "debt",
    "nasiya": "debt",
    
    # ─────────────────────────────────────────────────────────────────────────
    # Russian
    # ─────────────────────────────────────────────────────────────────────────
    "такси": "transport",
    "транспорт": "transport",
    "автобус": "transport",
    "метро": "transport",
    "бензин": "transport",
    
    "еда": "food",
    "обед": "food",
    "ужин": "food",
    "завтрак": "food",
    "кафе": "food",
    "ресторан": "food",
    "продукты": "food",
    "магазин": "shopping",
    "супермаркет": "shopping",
    
    "аптека": "health",
    "лекарства": "health",
    "больница": "health",
    "врач": "health",
    "клиника": "health",
    
    "интернет": "internet",
    "связь": "internet",
    "телефон": "internet",
    "мобильный": "internet",
    
    "коммуналка": "utilities",
    "газ": "utilities",
    "вода": "utilities",
    "свет": "utilities",
    "электричество": "utilities",
    
    "аренда": "rent",
    "квартира": "rent",
    
    "кино": "entertainment",
    "театр": "entertainment",
    "развлечения": "entertainment",
    
    "одежда": "shopping",
    "обувь": "shopping",
    "покупки": "shopping",
    "рынок": "shopping",
    
    "курсы": "education",
    "книги": "education",
    "обучение": "education",
    "учеба": "education",
    
    "зарплата": "salary",
    "оклад": "salary",
    "работа": "salary",
    
    "бизнес": "business",
    "прибыль": "business",
    "доход": "income",
    
    "подарок": "gift",
    
    "долг": "debt",
    "кредит": "debt",
    "займ": "debt",
    
    # ─────────────────────────────────────────────────────────────────────────
    # English
    # ─────────────────────────────────────────────────────────────────────────
    "food": "food",
    "lunch": "food",
    "dinner": "food",
    "breakfast": "food",
    "cafe": "food",
    "restaurant": "food",
    "groceries": "food",
    "coffee": "food",
    
    "pharmacy": "health",
    "medicine": "health",
    "hospital": "health",
    "doctor": "health",
    "health": "health",
    
    "rent": "rent",
    "apartment": "rent",
    "housing": "rent",
    
    "utilities": "utilities",
    "electricity": "utilities",
    "water": "utilities",
    "heating": "utilities",
    
    "phone": "internet",
    "mobile": "internet",
    "data": "internet",
    
    "movie": "entertainment",
    "cinema": "entertainment",
    "entertainment": "entertainment",
    "fun": "entertainment",
    
    "clothes": "shopping",
    "shoes": "shopping",
    "shopping": "shopping",
    "store": "shopping",
    
    "course": "education",
    "book": "education",
    "education": "education",
    "school": "education",
    "university": "education",
    
    "salary": "salary",
    "wage": "salary",
    "paycheck": "salary",
    "income": "income",
    
    "business": "business",
    "profit": "business",
    
    "gift": "gift",
    "present": "gift",
    "birthday": "gift",
    
    "debt": "debt",
    "loan": "debt",
    "borrow": "debt",
}

# Amount pattern - supports various formats
AMOUNT_RE = re.compile(r"(\d[\d\s.,]*\d|\d+)")

def _normalize_amount(s: str) -> Optional[int]:
    """Extract integer from amount string"""
    digits = "".join(ch for ch in s if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except:
        return None

def normalize_category(word: str) -> str:
    """Normalize category word to standard key"""
    w = word.strip().lower()
    return CAT_MAP.get(w, w)

def parse_one(text: str) -> Optional[Tuple[str, int, Optional[str]]]:
    """
    Parse a single expense/income entry.
    
    Accepts formats:
    - "taksi 20000"
    - "food 45000 lunch"
    - "20000 taksi"
    - "ovqat 120000 tushlik uchun"
    - "50k taxi" (k = thousand)
    
    Returns: (category, amount, description) or None
    """
    t = (text or "").strip()
    if not t:
        return None
    
    # Handle "k" suffix for thousands (50k = 50000)
    t = re.sub(r"(\d+)\s*k\b", lambda m: str(int(m.group(1)) * 1000), t, flags=re.IGNORECASE)
    t = re.sub(r"(\d+)\s*ming\b", lambda m: str(int(m.group(1)) * 1000), t, flags=re.IGNORECASE)
    t = re.sub(r"(\d+)\s*тыс\b", lambda m: str(int(m.group(1)) * 1000), t, flags=re.IGNORECASE)
    
    # Find amount
    match = AMOUNT_RE.search(t)
    if not match:
        return None
    
    amount = _normalize_amount(match.group(1))
    if amount is None or amount <= 0:
        return None
    
    # Remove amount from text
    before = t[:match.start()].strip()
    after = t[match.end():].strip()
    
    # Determine category and description
    cat = None
    desc_parts: List[str] = []
    
    if before:
        parts = before.split()
        cat = normalize_category(parts[0])
        desc_parts += parts[1:]
        if after:
            desc_parts += after.split()
    else:
        parts = after.split()
        if not parts:
            return None
        cat = normalize_category(parts[0])
        desc_parts += parts[1:]
    
    # If category wasn't recognized, use it as description
    if cat not in CAT_MAP.values() and cat in CAT_MAP:
        cat = CAT_MAP[cat]
    elif cat not in CAT_MAP.values():
        # Unknown category - treat first word as category anyway
        pass
    
    desc = " ".join(desc_parts).strip() or None
    return (cat, amount, desc)

def parse_multi(text: str) -> List[Tuple[str, int, Optional[str]]]:
    """
    Parse multiple entries separated by ; or newline.
    
    Example: "taksi 20000; ovqat 45000; internet 50000"
    """
    t = (text or "").strip()
    if not t:
        return []
    
    results = []
    for part in re.split(r"[;\n]+", t):
        part = part.strip()
        if not part:
            continue
        parsed = parse_one(part)
        if parsed:
            results.append(parsed)
    
    return results

def looks_like_expense_text(text: str) -> bool:
    """Check if text looks like an expense entry"""
    return parse_one(text) is not None

def get_type_from_category(cat: str) -> str:
    """Suggest transaction type based on category"""
    income_cats = {"salary", "business", "income", "gift"}
    debt_cats = {"debt", "loan"}
    
    normalized = normalize_category(cat)
    if normalized in income_cats:
        return "income"
    elif normalized in debt_cats:
        return "debt"
    return "expense"
