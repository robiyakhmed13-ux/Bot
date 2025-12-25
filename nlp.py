# nlp.py
import re
from typing import Optional, Tuple

# Accepts:
# "food 97500"
# "transport 12000 taxi"
# "coffee 25k"
# "food 97_500 lunch"
def parse_quick_add(text: str) -> Optional[Tuple[str, int, str | None]]:
    if not text:
        return None

    t = text.strip()
    # category = first word, amount = second token
    parts = t.split()
    if len(parts) < 2:
        return None

    cat = parts[0].strip().lower()

    amt_raw = parts[1].strip().lower().replace("_", "").replace(",", "")
    amt_raw = amt_raw.replace(" ", "")

    m = re.match(r"^(\d+(?:\.\d+)?)(k)?$", amt_raw)
    if not m:
        # fallback: digits only
        digits = "".join(ch for ch in amt_raw if ch.isdigit())
        if not digits:
            return None
        amount = int(digits)
    else:
        num = float(m.group(1))
        if m.group(2) == "k":
            num *= 1000
        amount = int(num)

    desc = " ".join(parts[2:]).strip() if len(parts) > 2 else None
    desc = desc if desc else None
    return cat, amount, desc
