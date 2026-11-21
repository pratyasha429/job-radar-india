"""Fetch job posts from public sources and return them in ONE common shape:
{source, source_id, title, company, location_raw, description, url, posted_at}
"""
import datetime
import html
import os
import re
import time

import requests

import config
import db

HEADERS = {"User-Agent": "job-radar-student-project/1.0"}


def clean(text):
    """HTML -> plain text."""
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def is_india(location):
    loc = (location or "").lower()
    return any(w in loc for w in config.INDIA_WORDS)


def looks_fresher(text):
    return re.search(config.FRESHER_REGEX, text or "", flags=re.I) is not None


# ---------------------------------------------------------------- Adzuna
def fetch_adzuna(con):
    app_id, app_key = os.getenv("ADZUNA_APP_ID"), os.getenv("ADZUNA_APP_KEY")
    if not (app_id and app_key):
        print("[adzuna] ADZUNA_APP_ID / ADZUNA_APP_KEY missing -> skipping")
        return []
    out = []
    for query in config.ADZUNA_QUERIES:
        for city in config.ADZUNA_CITIES:
            for page in range(1, config.ADZUNA_PAGES + 1):
                if db.get_meta(con, "adzuna_calls") >= config.ADZUNA_CALL_BUDGET:
                    print(f"[adzuna] lifetime budget of {config.ADZUNA_CALL_BUDGET} calls used up -> "
                          f"stopping (fetched {len(out)} posts this run)")
                    return out
                db.add_meta(con, "adzuna_calls")   # count the call BEFORE making it
                params = {
                    "app_id": app_id, "app_key": app_key, "results_per_page": 50,
                    "what": query, "max_days_old": config.ADZUNA_MAX_DAYS_OLD,
                    "content-type": "application/json",
                }
                if city:
                    params["where"] = city
                try:
                    r = requests.get(f"https://api.adzuna.com/v1/api/jobs/in/search/{page}",
                                     params=params, headers=HEADERS, timeout=30)
                except requests.RequestException as e:
                    print(f"[adzuna] network error: {e} -> stopping Adzuna to save your calls")
                    return out
                if r.status_code != 200:
                    # stop everything: retrying would only waste the few calls we have
                    print(f"[adzuna] HTTP {r.status_code} for '{query}'/{city or 'India'}: {r.text[:150]}")
                    print("[adzuna] stopping Adzuna to save your calls")
                    return out
                results = r.json().get("results", [])
                for j in results:
                    out.append({
                        "source": "adzuna",
                        "source_id": str(j.get("id")),
                        "title": clean(j.get("title")),
                        "company": clean((j.get("company") or {}).get("display_name")),
                        "location_raw": clean((j.get("location") or {}).get("display_name")),
                        "description": clean(j.get("description")),
                        "url": j.get("redirect_url"),
                        "posted_at": j.get("created"),
                    })
                time.sleep(2.5)  # Adzuna free limit is 25 calls/minute
                if len(results) < 50:
                    break
    print(f"[adzuna] fetched {len(out)} posts")
    return out


# ---------------------------------------------------------------- Greenhouse
def fetch_greenhouse():
    out = []
    for token in config.GREENHOUSE_BOARDS:
        try:
            r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
                             params={"content": "true"}, headers=HEADERS, timeout=30)
        except requests.RequestException as e:
            print(f"[greenhouse:{token}] network error: {e}")
            continue
        if r.status_code != 200:
            print(f"[greenhouse:{token}] not available (HTTP {r.status_code}) -> skipped")
            continue
        kept = 0
        for j in r.json().get("jobs", []):
            loc = (j.get("location") or {}).get("name", "")
            title = clean(j.get("title"))
            desc = clean(j.get("content"))
            if is_india(loc) and looks_fresher(title + " " + desc[:1500]):
                kept += 1
                out.append({
                    "source": "greenhouse", "source_id": f"{token}:{j.get('id')}",
                    "title": title, "company": j.get("company_name") or token,
                    "location_raw": loc, "description": desc,
                    "url": j.get("absolute_url"), "posted_at": j.get("updated_at"),
                })
        print(f"[greenhouse:{token}] kept {kept} India fresher/intern posts")
    return out


# ---------------------------------------------------------------- Lever
def fetch_lever():
    out = []
    for site in config.LEVER_SITES:
        data = None
        for host in ("api.lever.co", "api.eu.lever.co"):
            try:
                r = requests.get(f"https://{host}/v0/postings/{site}", params={"mode": "json"},
                                 headers=HEADERS, timeout=30)
            except requests.RequestException as e:
                print(f"[lever:{site}] network error: {e}")
                break
            if r.status_code == 200:
                data = r.json()
                break
        if data is None:
            print(f"[lever:{site}] not available -> skipped")
            continue
        kept = 0
        for j in data:
            loc = (j.get("categories") or {}).get("location", "") or ""
            title = clean(j.get("text"))
            desc = clean(j.get("descriptionPlain") or j.get("description"))
            if is_india(loc) and looks_fresher(title + " " + desc[:1500]):
                kept += 1
                created = j.get("createdAt")
                posted = (datetime.datetime.fromtimestamp(created / 1000, datetime.timezone.utc)
                          .isoformat(timespec="seconds") if created else None)
                out.append({
                    "source": "lever", "source_id": f"{site}:{j.get('id')}",
                    "title": title, "company": site, "location_raw": loc,
                    "description": desc, "url": j.get("hostedUrl"), "posted_at": posted,
                })
        print(f"[lever:{site}] kept {kept} India fresher/intern posts")
    return out


def fetch_all(con):
    posts = fetch_greenhouse() + fetch_lever() + fetch_adzuna(con)
    print(f"[sources] total fetched: {len(posts)}")
    return posts
