import re

CATEGORY_ALIASES = {
    "food": ["food", "ovqat", "oziq", "oziq-ovqat", "еда"],
    "transport": ["transport", "taxi", "taksi", "metro", "bus", "авто"],
    "rent": ["rent", "ijara", "аренда"],
    "salary": ["salary", "oylik", "зарплата"],
}

def normalize_amount(text: str) -> int | None:
    # accepts "97 500", "97500", "97,500"
    digits = re.sub(r"[^\d]", "", text)
    if not digits:
        return None
    return int(digits)

def guess_category(text: str) -> str:
    t = text.lower().strip()
    for key, aliases in CATEGORY_ALIASES.items():
        if any(a in t for a in aliases):
            return key
    return "food"  # default

def parse_quick_add(text: str):
    """
    Examples:
      "food 97500"
      "ovqat 97 500"
      "transport 12000 taxi"
      "97500 food"
    Returns: (category_key, amount, description)
    """
    t = text.strip()
    amt = normalize_amount(t)
    cat = guess_category(t)

    # Remove amount from description
    desc = re.sub(r"[\d\s,]+", " ", t).strip()
    if not desc:
        desc = None

    if amt is None:
        return None
    return cat, amt, desc
