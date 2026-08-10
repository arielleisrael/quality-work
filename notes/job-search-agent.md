# Notes: Job Search Agent

## Why I built this

I was applying to jobs and spending way too much time just getting to the starting line — opening tabs, skimming listings, deciding "is this even worth reading?" across five different boards. That filtering work is low value and high volume. I wanted to automate it.

The goal was simple: run it in the morning, get a ranked list, start my day on the actual work (tailoring, researching, applying).

## What I learned building it

**Scraping is fragile by nature.** LinkedIn and Indeed's HTML structures change without warning, and there's no API without a paid plan. I added `--skip-linkedin` and `--skip-indeed` flags specifically for when those scrapers break — so the tool stays useful even when two boards are down.

**Transparent scoring matters more than accurate scoring.** I could have used an LLM to score listings, and it probably would have been more nuanced. But I went with a rule-based scorer because every result shows you exactly why it scored the way it did. If the model is wrong, you can see why and fix the profile — rather than wondering why the black box said 62.

**Profile tuning is ongoing.** The `domain_avoid_keywords` field exists entirely because "quality engineer" shows up in manufacturing job listings, ISO 9001 cert roles, and food production QA — none of which are relevant to software QE. First version didn't have that field and the results were noisy.

**Generic > personal for sharing.** The original version had my profile hardcoded. I refactored it to use `profile.json` so anyone could use it — which also forced me to make the profile schema explicit and document it properly.

## What I'd improve

- Add support for Lever ATS boards (many companies use it alongside Greenhouse/Ashby)
- Better date parsing — some boards use inconsistent date formats and listings fall through the recency filter
- A `--dry-run` flag that shows how many listings each board would return without scoring
- Potentially: a small SQLite db to track which jobs you've already seen across runs, so you don't re-review the same listings each day
