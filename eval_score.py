"""Step 2 of the accuracy check: compare your hand labels with the LLM's answers."""
import csv

import config
from tagger import normalize_city

labels = {r["id"]: r for r in csv.DictReader(open("eval/to_label.csv", encoding="utf-8"))}
preds = {r["id"]: r for r in csv.DictReader(open("eval/predictions_hidden.csv", encoding="utf-8"))}

blank = [i for i, r in labels.items()
         if not (r["true_role"].strip() and r["true_city"].strip() and r["true_is_fresher"].strip())]
if blank:
    raise SystemExit(f"{len(blank)} posts are not fully labelled yet (ids: {blank[:10]}...). Finish labelling first.")

role_ok = city_ok = fresh_ok = 0
errors = []
for i, lab in labels.items():
    p = preds[i]
    t_role, t_city, t_fresh = lab["true_role"].strip(), normalize_city(lab["true_city"]), lab["true_is_fresher"].strip().lower()
    r_ok, c_ok, f_ok = (p["pred_role"] == t_role, normalize_city(p["pred_city"]) == t_city,
                        p["pred_is_fresher"] == t_fresh)
    role_ok += r_ok
    city_ok += c_ok
    fresh_ok += f_ok
    if not (r_ok and c_ok and f_ok):
        errors.append({"id": i, "title": lab["title"], "location_raw": lab["location_raw"],
                       "true_role": t_role, "pred_role": p["pred_role"],
                       "true_city": t_city, "pred_city": p["pred_city"],
                       "true_fresher": t_fresh, "pred_fresher": p["pred_is_fresher"]})

n = len(labels)
both = n - len([e for e in errors if e["true_role"] != e["pred_role"] or e["true_city"] != normalize_city(e["pred_city"])])
print(f"Posts checked          : {n}")
print(f"Role accuracy          : {role_ok}/{n} = {role_ok / n:.1%}")
print(f"City accuracy          : {city_ok}/{n} = {city_ok / n:.1%}")
print(f"Fresher-flag accuracy  : {fresh_ok}/{n} = {fresh_ok / n:.1%}")
print(f"Role AND city correct  : {both}/{n} = {both / n:.1%}   <- use this as your headline 'tagging accuracy'")

if errors:
    with open("eval/errors.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(errors[0].keys()))
        w.writeheader()
        w.writerows(errors)
    print(f"\n{len(errors)} posts had at least one mistake -> see eval/errors.csv and describe the patterns in your doc.")
