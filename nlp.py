import re

CAT_ALIASES = {
  # uz
  "ovqat":"food", "oziq":"food", "restoran":"food", "kafe":"food",
  "taksi":"transport", "transport":"transport", "metro":"transport",
  "ijara":"rent", "komunal":"bills", "telefon":"bills", "internet":"bills",
  "dori":"health", "apteka":"health",
  # ru
  "еда":"food", "такси":"transport", "транспорт":"transport",
  "аренда":"rent", "коммуналка":"bills", "связь":"bills",
  # en
  "food":"food", "taxi":"transport", "rent":"rent", "bills":"bills"
}

def normalize_cat(word: str) -> str:
    w = (word or "").strip().lower()
    return CAT_ALIASES.get(w, w)

AMOUNT_RE = re.compile(r"(\d[\d\s.,]*)")

def parse_single_line(text: str):
    """
    Examples:
      "taksi 20000"
      "ovqat 97 500 lunch"
    Returns: (cat, amount:int, desc|None) or None
    """
    s = (text or "").strip()
    if not s:
        return None
    parts = s.split()
    if len(parts) < 2:
        return None
    cat = normalize_cat(parts[0])
    m = AMOUNT_RE.search(s)
    if not m:
        return None
    raw = m.group(1)
    amount = int(re.sub(r"[^\d]", "", raw))
    # desc = everything after amount match
    desc = s[m.end():].strip()
    if desc == "":
        desc = None
    return (cat, amount, desc)

def parse_multi(text: str):
    """
    Very simple multi-item split:
      "taksi 20000, ovqat 85000"
    returns list of (cat, amount, desc)
    """
    s = (text or "").strip()
    if not s:
        return []
    chunks = re.split(r"[,\n;]+", s)
    out = []
    for ch in chunks:
        p = parse_single_line(ch.strip())
        if p:
            out.append(p)
    return out
