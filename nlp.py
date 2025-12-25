import re

ALLOWED = {
    "food", "transport", "home", "bills", "health", "shopping", "gift", "education", "fun", "other",
    "salary", "bonus",
}

def parse_quick_add(text: str):
    """
    Examples:
      "food 97500"
      "transport 12000 taxi"
    Returns: (category_key, amount, desc) or None
    """
    if not text:
        return None

    parts = text.strip().split()
    if len(parts) < 2:
        return None

    cat = parts[0].lower()
    if cat not in ALLOWED:
        return None

    amount_str = re.sub(r"[^\d]", "", parts[1])
    if not amount_str:
        return None

    amount = int(amount_str)
    desc = " ".join(parts[2:]).strip() if len(parts) > 2 else None
    return (cat, amount, desc)
