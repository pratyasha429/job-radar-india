"""Cost per 1,000 posts, MEASURED from the real token counts the API returned."""
import config
import db

con = db.connect()
r = con.execute(
    "SELECT COALESCE(SUM(tagged),0) n, COALESCE(SUM(tokens_in),0) tin, COALESCE(SUM(tokens_out),0) tout "
    "FROM runs WHERE tagger != 'mock'"
).fetchone()
n, tin, tout = r["n"], r["tin"], r["tout"]
if n == 0:
    raise SystemExit("No real (non-mock) tagged posts found yet. Run the pipeline with your Gemini key first.")

cost = tin / 1e6 * config.PRICE_IN_PER_M + tout / 1e6 * config.PRICE_OUT_PER_M
per_1000 = cost / n * 1000
print(f"Model                     : {config.GEMINI_MODEL}")
print(f"Posts tagged (all runs)   : {n}")
print(f"Input tokens / post       : {tin / n:.0f}")
print(f"Output tokens / post      : {tout / n:.0f}")
print(f"Prices used (USD / 1M tok): input {config.PRICE_IN_PER_M}, output {config.PRICE_OUT_PER_M}")
print(f"Cost per 1,000 posts      : ${per_1000:.4f}  (about Rs {per_1000 * 90:.2f} at Rs 90/USD)")
print("Actual amount you paid    : $0.00 on the free tier. The figure above is the paid-tier list-price equivalent.")
