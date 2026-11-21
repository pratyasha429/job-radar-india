"""All settings live here. Edit this file to change sources, cities, roles or the model."""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "data", "jobs.db")


def _load_dotenv(path):
    """Tiny .env reader so you don't need any extra package."""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv(os.path.join(BASE, ".env"))

# ---------------- LLM (Google Gemini, free tier) ----------------
# Model names change over time. Check https://ai.google.dev/gemini-api/docs/pricing
# and pick a Flash-Lite model that has a Free Tier. Override with GEMINI_MODEL in .env.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
# List prices (USD per 1M tokens) used ONLY to compute "cost per 1,000 posts".
# The free tier charges you nothing, but the task asks for cost, so we report what it
# WOULD cost at paid prices. Verify these on the pricing page and update if different.
PRICE_IN_PER_M = float(os.getenv("PRICE_IN_PER_M", "0.25"))
PRICE_OUT_PER_M = float(os.getenv("PRICE_OUT_PER_M", "1.50"))

BATCH_SIZE = 10            # posts sent to the LLM in one request
MAX_DESC_CHARS = 700       # description characters sent to the LLM (controls cost)
TAG_LIMIT_PER_RUN = 400    # safety cap so one run never burns the whole free quota

# ---------------- Tag vocabulary ----------------
ROLES = [
    "Backend", "Frontend", "Full Stack", "Mobile", "Data/Analytics", "ML/AI",
    "DevOps/Cloud", "QA/Testing", "Product/Design", "Marketing/Content",
    "Sales/BD", "HR/Ops", "Finance/Accounting", "Customer Support", "Other",
]

CITY_ALIASES = {
    "bangalore": "Bengaluru", "bengaluru": "Bengaluru", "bengalooru": "Bengaluru",
    "gurgaon": "Gurugram", "gurugram": "Gurugram",
    "bombay": "Mumbai", "navi mumbai": "Navi Mumbai", "calcutta": "Kolkata",
    "madras": "Chennai", "poona": "Pune", "new delhi": "Delhi", "delhi ncr": "Delhi",
    "work from home": "Remote", "wfh": "Remote", "remote": "Remote", "pan india": "Remote",
}

# ---------------- Sources ----------------
# 1) Adzuna API (free key: https://developer.adzuna.com). ~42 calls per run with these settings.
# A new Adzuna account is "Pending Activation: 25 test calls" IN TOTAL, so we spend them carefully:
# 2 queries x 5 places x 2 pages = 20 calls, and a hard lifetime budget (tracked in the database)
# stops the code from ever going over. Each call can return up to 50 posts.
ADZUNA_QUERIES = ["fresher", "internship"]
ADZUNA_CITIES = ["", "Bengaluru", "Pune", "Hyderabad", "Mumbai"]  # "" = all India
ADZUNA_PAGES = 2           # pages of 50 results per query+city
ADZUNA_MAX_DAYS_OLD = 30
ADZUNA_CALL_BUDGET = 22    # lifetime cap. Raise it only if your Adzuna account gets activated.

# 2) Company career boards that expose a public JSON feed (no key needed).
# These slugs are STARTER GUESSES. The script prints which ones exist and skips the rest.
# Find more: Google  site:boards.greenhouse.io India intern   or   site:jobs.lever.co India intern
# "karya", "hackerrank" (Greenhouse) and "mindtickle", "Sprinto" (Lever, case-sensitive) were seen live
# with India intern posts. The rest are guesses; the script just skips the ones that don't exist.
GREENHOUSE_BOARDS = [
    "karya", "hackerrank",
    "razorpaysoftwareprivatelimited", "groww", "postman", "druva", "freshworks", "browserstack",
    "chargebee", "clevertap", "zeta", "sharechat", "unacademy", "vedantu", "whatfix", "darwinbox",
]
LEVER_SITES = [
    "mindtickle", "Sprinto",
    "cred", "meesho", "paytm", "upgrad", "dream11", "games24x7", "slice", "navi", "zeta", "uniphore",
]

INDIA_WORDS = [
    "india", "bengaluru", "bangalore", "mumbai", "pune", "hyderabad", "delhi", "gurgaon",
    "gurugram", "noida", "chennai", "kolkata", "ahmedabad", "jaipur", "kochi", "chandigarh",
    "indore", "coimbatore", "thiruvananthapuram", "lucknow", "nagpur", "bhubaneswar",
]
FRESHER_REGEX = (
    r"\b(intern|interns|internship|fresher|freshers|graduate|graduates|trainee|"
    r"entry[- ]level|new grad|junior|apprentice|0\s*[-–to]+\s*[12]\s*(years|yrs|year))\b"
)

# Posts not seen in this many days are hidden from the web page.
STALE_AFTER_DAYS = 14
