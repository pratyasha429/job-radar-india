"""The daily job:  fetch -> dedupe -> store -> tag new posts with the LLM -> log the run.

Run it:   python run_pipeline.py
Test without an API key:   MOCK_LLM=1 python run_pipeline.py     (Windows: set MOCK_LLM=1)
"""
import os

import config
import db
import dedupe
import sources
import tagger


def main():
    con = db.connect()
    fetched = sources.fetch_all(con)

    stats = {"fetched": len(fetched), "already_known": 0, "new_unique": 0, "dup_same_id": 0,
             "dup_exact": 0, "dup_fuzzy": 0, "tagged": 0, "tokens_in": 0, "tokens_out": 0,
             "tagger": "mock" if os.getenv("MOCK_LLM") == "1" else config.GEMINI_MODEL}

    # Rebuild the duplicate-detector from what we already stored.
    deduper = dedupe.Deduper()
    for row in db.all_posts(con):
        deduper.add(row, row["id"])
    known = db.known_source_ids(con)
    seen_this_run = set()

    for p in fetched:
        sid = (p["source"], p["source_id"])
        if sid in known:                      # we saw this ad on an earlier day: just refresh it
            db.touch(con, sid)
            stats["already_known"] += 1
            continue
        if sid in seen_this_run:              # same ad returned twice in this run
            stats["dup_same_id"] += 1
            continue
        seen_this_run.add(sid)
        found = deduper.check(p)
        if found:
            reason, original = found
            db.insert_dupe(con, p, original, reason)
            stats["dup_" + reason] += 1
            continue
        post_id = db.insert_post(con, p)
        deduper.add(p, post_id)
        stats["new_unique"] += 1
    con.commit()

    # Tag only the posts that have no tags yet (so daily runs stay cheap).
    todo = db.untagged(con, config.TAG_LIMIT_PER_RUN)
    print(f"[tagger] {len(todo)} posts to tag with {stats['tagger']}")
    for i in range(0, len(todo), config.BATCH_SIZE):
        batch = [dict(r) for r in todo[i:i + config.BATCH_SIZE]]
        try:
            results, t_in, t_out = tagger.tag_batch(batch)
        except Exception as e:                # quota or network problem: stop, retry tomorrow
            print(f"[tagger] stopped early: {e}")
            break
        for post_id, tags in results.items():
            db.set_tags(con, post_id, tags["role"], tags["city"], tags["is_fresher"], stats["tagger"])
        stats["tagged"] += len(results)
        stats["tokens_in"] += t_in
        stats["tokens_out"] += t_out
        con.commit()
        print(f"  tagged {stats['tagged']}/{len(todo)}")

    db.log_run(con, stats)
    con.commit()
    total = con.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    print("\n=== RUN SUMMARY ===")
    for k, v in stats.items():
        print(f"{k:14}: {v}")
    print(f"{'total in db':14}: {total}")


if __name__ == "__main__":
    main()
