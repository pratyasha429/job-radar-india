"""Duplicate removal.

Three kinds of duplicates are caught:
  1. same_id : the very same ad returned twice (e.g. by two different searches)
  2. exact   : same company + same title + same city (after cleaning the text)
  3. fuzzy   : same company + same city + titles that are >= 90% similar
               ("SDE Intern" vs "SDE - Intern")
"""
import difflib
import re

LEGAL_WORDS = {"pvt", "ltd", "private", "limited", "inc", "llp", "llc", "corp", "co"}
FUZZY_THRESHOLD = 0.90


def norm(s):
    s = re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())
    return re.sub(r"\s+", " ", s).strip()


def norm_company(s):
    return " ".join(w for w in norm(s).split() if w not in LEGAL_WORDS)


def norm_city(location):
    first = re.split(r"[,/;|]", location or "")[0]
    return norm(first)


def exact_key(p):
    return f"{norm_company(p['company'])}|{norm(p['title'])}|{norm_city(p['location_raw'])}"


class Deduper:
    def __init__(self):
        self.by_key = {}       # exact key -> reference id
        self.by_company = {}   # company -> [(ref, title, city)]

    def add(self, p, ref):
        company = norm_company(p["company"])
        title = norm(p["title"])
        city = norm_city(p["location_raw"])
        self.by_key[f"{company}|{title}|{city}"] = ref
        self.by_company.setdefault(company, []).append((ref, title, city))

    def check(self, p):
        """Return (reason, ref_of_original) if p is a duplicate, else None."""
        company = norm_company(p["company"])
        if not company:            # unknown company: too risky to merge
            return None
        key = exact_key(p)
        if key in self.by_key:
            return "exact", self.by_key[key]
        title = norm(p["title"])
        city = norm_city(p["location_raw"])
        for ref, t2, c2 in self.by_company.get(company, []):
            if c2 == city and difflib.SequenceMatcher(None, title, t2).ratio() >= FUZZY_THRESHOLD:
                return "fuzzy", ref
        return None
