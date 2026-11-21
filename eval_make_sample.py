"""Step 1 of the accuracy check: pick 50 random posts for you to label BY HAND.

Creates:
  eval/to_label.csv           <- open this, fill the 3 'true_' columns yourself
  eval/predictions_hidden.csv <- the LLM's answers. DON'T open it until you finish labelling,
                                 otherwise you will be biased and the accuracy is meaningless.
"""
import csv
import os
import random

import config
import db

N = 50
con = db.connect()
rows = con.execute(
    "SELECT id, title, company, location_raw, description, url, role, city, is_fresher "
    "FROM posts WHERE role IS NOT NULL AND tagger != 'mock'"
).fetchall()
if len(rows) < N:
    raise SystemExit(f"Only {len(rows)} real-tagged posts in the database; need at least {N}.")

random.seed(42)                       # fixed seed so the sample is reproducible
sample = random.sample(rows, N)
os.makedirs("eval", exist_ok=True)

with open("eval/to_label.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["id", "title", "company", "location_raw", "description_start", "url",
                "true_role", "true_city", "true_is_fresher"])
    for r in sample:
        w.writerow([r["id"], r["title"], r["company"], r["location_raw"],
                    (r["description"] or "")[:500], r["url"], "", "", ""])

with open("eval/predictions_hidden.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["id", "pred_role", "pred_city", "pred_is_fresher"])
    for r in sample:
        w.writerow([r["id"], r["role"], r["city"], "yes" if r["is_fresher"] else "no"])

print(f"Wrote eval/to_label.csv ({N} posts).")
print("Fill true_role (one of the roles below), true_city (e.g. Pune, Remote, Unknown),")
print("true_is_fresher (yes/no). Allowed roles:")
print("  " + " | ".join(config.ROLES))
