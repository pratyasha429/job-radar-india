# Fresher Job Radar – India

A live web tool that collects fresher / internship posts in India from public sources,
removes duplicates, tags every post by **role** and **city** with an LLM, and refreshes daily.

**Live app:** _paste your Streamlit link here_

## How it works

```
Adzuna API + Greenhouse/Lever career feeds
        │  sources.py      fetch, convert to one common shape
        ▼
   dedupe.py               same-id, exact (company+title+city) and fuzzy (>=90% similar title) duplicates
        ▼
     db.py                 SQLite file data/jobs.db (posts, dupes, runs tables)
        ▼
   tagger.py               Gemini (free tier), 10 posts per request, JSON-schema output:
                           role (fixed list), city, is_fresher
        ▼
     app.py                Streamlit page: filters, table, charts, CSV download
```

`.github/workflows/daily.yml` runs `run_pipeline.py` every day (07:00 IST), then commits the updated
database; the Streamlit app picks it up automatically. Only **new** posts are sent to the LLM, so daily
runs are cheap.

## Run it yourself

```bash
pip install -r requirements.txt
cp .env.example .env            # then paste your keys into .env
python run_pipeline.py          # fetch + dedupe + tag
streamlit run app.py            # open the page
```

## Measuring quality

```bash
python eval_make_sample.py      # 50 random posts -> eval/to_label.csv (label them by hand first!)
python eval_score.py            # accuracy vs. the LLM, errors in eval/errors.csv
python cost_report.py           # cost per 1,000 posts from real token counts
```

## Results (fill in after measuring)

| Metric | Value |
|---|---|
| Unique posts collected | |
| Duplicates removed | |
| Tagging accuracy (role AND city, 50 hand-checked posts) | |
| Role accuracy / City accuracy | |
| Cost per 1,000 posts (paid list-price equivalent) | |

## Notes and limits

- Sources are public APIs/feeds only (no scraping of login-walled sites). Adzuna returns a description
  snippet, not the full text, which limits how well the LLM can judge some posts.
- `MOCK_LLM=1` gives fake tags for offline testing. Never use it for reported numbers.
- Job data via Adzuna and public company career feeds.
