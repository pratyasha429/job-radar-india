"""LLM tagging with Google Gemini (REST API, so no extra library needed).

tag_batch(posts) -> (results, tokens_in, tokens_out)
  results = {post_id: {"role":..., "city":..., "is_fresher":...}}
"""
import json
import os
import time

import requests

import config

SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "id": {"type": "INTEGER"},
            "role": {"type": "STRING", "enum": config.ROLES},
            "city": {"type": "STRING"},
            "is_fresher": {"type": "BOOLEAN"},
        },
        "required": ["id", "role", "city", "is_fresher"],
    },
}

INSTRUCTIONS = f"""You label job posts from India for a fresher/internship job board.
For EACH post return: id (copy it exactly), role, city, is_fresher.

role: exactly one of {config.ROLES}. Choose by the actual work in the post, not by the company.
city: the main Indian city where the job is based, in standard English spelling
  (Bengaluru, Gurugram, Mumbai, Pune, Hyderabad, Chennai, Delhi, Noida, Kolkata, ...).
  If several cities are listed, use the first one. If the job is fully remote / work from home
  with no city, use "Remote". If no location can be determined, use "Unknown".
is_fresher: true if suitable for freshers / interns / new graduates (internship, trainee,
  0-1 or 0-2 years, entry level). false if it needs 2+ years of experience or is senior."""


def normalize_city(city):
    c = (city or "").strip()
    if not c:
        return "Unknown"
    return config.CITY_ALIASES.get(c.lower(), c.title() if c.islower() else c)


def _mock(posts):
    """Offline fake tagger so you can test the pipeline WITHOUT an API key.
    Never use it for your real accuracy numbers."""
    res = {}
    for p in posts:
        t = (p["title"] or "").lower()
        role = "Other"
        for kw, r in [("backend", "Backend"), ("frontend", "Frontend"), ("data", "Data/Analytics"),
                      ("market", "Marketing/Content"), ("sales", "Sales/BD"), ("ml", "ML/AI")]:
            if kw in t:
                role = r
                break
        res[p["id"]] = {"role": role, "city": normalize_city((p["location_raw"] or "").split(",")[0]),
                        "is_fresher": True}
    return res, 0, 0


def tag_batch(posts):
    if os.getenv("MOCK_LLM") == "1":
        return _mock(posts)
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing. Put it in the .env file.")
    items = [{
        "id": p["id"], "title": p["title"], "company": p["company"],
        "location": p["location_raw"], "description": (p["description"] or "")[:config.MAX_DESC_CHARS],
    } for p in posts]
    body = {
        "contents": [{"role": "user", "parts": [
            {"text": INSTRUCTIONS + "\n\nPOSTS:\n" + json.dumps(items, ensure_ascii=False)}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                             "responseSchema": SCHEMA},
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent"
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}

    data = None
    for attempt in range(5):
        r = requests.post(url, headers=headers, json=body, timeout=120)
        if r.status_code == 200:
            data = r.json()
            break
        if r.status_code in (429, 500, 503):
            wait = 20 * (attempt + 1)
            print(f"  [llm] HTTP {r.status_code}, waiting {wait}s then retrying...")
            time.sleep(wait)
            continue
        raise RuntimeError(f"Gemini error {r.status_code}: {r.text[:300]}")
    if data is None:
        raise RuntimeError("Gemini kept failing (rate limit?). Try again later.")

    text = data["candidates"][0]["content"]["parts"][0]["text"]
    usage = data.get("usageMetadata", {})
    tokens_in = usage.get("promptTokenCount", 0)
    # "thinking" tokens are billed like output tokens, so count them too.
    tokens_out = usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0)

    results = {}
    valid_ids = {p["id"] for p in posts}
    for row in json.loads(text):
        if row.get("id") not in valid_ids:
            continue
        role = row.get("role") if row.get("role") in config.ROLES else "Other"
        results[row["id"]] = {"role": role, "city": normalize_city(row.get("city")),
                              "is_fresher": bool(row.get("is_fresher"))}
    return results, tokens_in, tokens_out
