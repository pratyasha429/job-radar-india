"""The live web page.  Run locally:  streamlit run app.py"""
import datetime
import json
import os
import sqlite3

import pandas as pd
import streamlit as st

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "data", "jobs.db")
STALE_DAYS = 14

st.set_page_config(page_title="Fresher Job Radar India", page_icon="🎯", layout="wide")
st.title("🎯 Fresher Job Radar – India")
st.caption("Fresher & internship posts from public sources, de-duplicated and tagged by an LLM. Refreshed daily.")

if not os.path.exists(DB):
    st.error("No database yet. Run `python run_pipeline.py` first.")
    st.stop()

con = sqlite3.connect(DB)
cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=STALE_DAYS)).isoformat()
df = pd.read_sql_query(
    "SELECT title, company, role, city, is_fresher, source, location_raw, url, posted_at, last_seen "
    "FROM posts WHERE role IS NOT NULL AND last_seen >= ?", con, params=(cutoff,))
runs = pd.read_sql_query("SELECT * FROM runs ORDER BY id DESC", con)
dupes_total = con.execute("SELECT COUNT(*) FROM dupes").fetchone()[0]
con.close()

# ---- top numbers
c1, c2, c3, c4 = st.columns(4)
c1.metric("Unique posts", len(df))
c2.metric("Duplicates removed", int(dupes_total + (runs["dup_same_id"].sum() if len(runs) else 0)))
c3.metric("Cities", df["city"].nunique())
c4.metric("Last refresh (UTC)", runs["ts"].iloc[0][:16].replace("T", " ") if len(runs) else "-")

# ---- filters
st.sidebar.header("Filters")
roles = st.sidebar.multiselect("Role", sorted(df["role"].dropna().unique()))
top_cities = df["city"].value_counts().index.tolist()
cities = st.sidebar.multiselect("City", top_cities)
only_fresher = st.sidebar.checkbox("Only posts the LLM judged fresher-friendly", value=True)
search = st.sidebar.text_input("Search title / company")

view = df.copy()
if roles:
    view = view[view["role"].isin(roles)]
if cities:
    view = view[view["city"].isin(cities)]
if only_fresher:
    view = view[view["is_fresher"] == 1]
if search:
    s = search.lower()
    view = view[view["title"].str.lower().str.contains(s, na=False) | view["company"].str.lower().str.contains(s, na=False)]

st.write(f"Showing **{len(view)}** posts")
st.dataframe(
    view[["title", "company", "role", "city", "source", "posted_at", "url"]],
    hide_index=True,
    column_config={"url": st.column_config.LinkColumn("Apply / view", display_text="open")},
)
st.download_button("⬇️ Download CSV", view.to_csv(index=False).encode("utf-8"), "fresher_jobs.csv", "text/csv")

# ---- charts
left, right = st.columns(2)
left.subheader("Posts by role")
left.bar_chart(view["role"].value_counts())
right.subheader("Posts by city (top 10)")
right.bar_chart(view["city"].value_counts().head(10))

# ---- measured quality numbers (fill data/metrics.json after your evaluation)
mpath = os.path.join(BASE, "data", "metrics.json")
if os.path.exists(mpath):
    m = json.load(open(mpath, encoding="utf-8"))
    st.subheader("Measured quality")
    st.write(f"Tagging accuracy (50 hand-checked posts): **{m.get('accuracy', '-')}**  ·  "
             f"Cost per 1,000 posts: **{m.get('cost_per_1000', '-')}**")

st.caption("Job data via Adzuna and public company career feeds. Built as a Gen AI & Engineering task.")
