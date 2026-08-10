# Job Search Agent

A Python script that searches remote job boards daily, scores each role against your profile, and delivers a ranked shortlist — so you spend time evaluating and applying, not filtering.

## Why I Built This

Job searching at volume means reviewing hundreds of listings across multiple boards, most of which aren't relevant. I built this to automate the filtering and ranking layer so I could focus on the actual work of applying: tailoring a resume, writing a real cover note, doing company research.

The scoring model is rule-based and transparent — every result shows exactly why it scored the way it did, so you can tune it rather than trust a black box.

---

## What It Does

- Searches 7 job boards simultaneously: We Work Remotely, Jobicy, Remote OK, Greenhouse (direct company boards), Ashby (direct company boards), LinkedIn, and Indeed
- Deduplicates across sources
- Scores each listing 0–100 against your profile: title relevance, seniority signals, remote confirmation, US eligibility, skills match, salary range, and recency
- Outputs a ranked list to the terminal, and optionally to CSV + Markdown files

## Fit Score

| Score | Label | What to do |
|-------|-------|-----------|
| 75–100 | 🟢 STRONG FIT | Apply first, tailor your resume fully |
| 55–74 | 🟡 GOOD FIT | Apply with light tailoring |
| 35–54 | 🟠 POSSIBLE | Review manually — context matters |
| < 35 | 🔴 WEAK | Skip |

---

## Setup

**Requirements:** Python 3.8+ (dependencies install automatically on first run)

```bash
# 1. Clone and enter the project
cd projects/job-search-agent

# 2. Create your profile
cp profile_template.json profile.json
# Edit profile.json — fill in your target titles, skills, salary range, etc.
# profile.json is gitignored and never committed

# 3. Run a search
python3 job_search_agent.py --since 3

# 4. Save results to CSV + Markdown
python3 job_search_agent.py --since 3 --save
```

## Options

| Flag | Default | What it does |
|------|---------|-------------|
| `--since N` | 3 | Only include jobs posted in the last N days |
| `--save` | off | Save results to `results/jobs_YYYY-MM-DD.csv` and `.md` |
| `--min-score N` | 35 | Raise or lower the score threshold |
| `--skip-linkedin` | off | Skip LinkedIn scraping (faster runs) |
| `--skip-indeed` | off | Skip Indeed scraping (faster runs) |

---

## Scheduling (runs automatically)

**macOS — cron** (runs at 8am weekdays):
```bash
crontab -e
```
```
0 8 * * 1-5 cd /path/to/job-search-agent && python3 job_search_agent.py --since 1 --save >> logs/search.log 2>&1
```

**Windows — Task Scheduler:**
1. Create Basic Task → Daily, 8:00 AM
2. Action: `python C:\path\to\job_search_agent.py --since 1 --save`

---

## Configuring Your Profile

All behavior is controlled by `profile.json` (copy from `profile_template.json`). Key fields:

- **`target_titles`** — exact titles you're targeting; these get the highest title-match score
- **`job_keywords`** — broader terms used to filter boards that don't support exact searches
- **`domain_avoid_keywords`** — useful if your role name appears in unrelated industries (e.g. "quality engineer" also appears in manufacturing — add `"iso 9001"`, `"manufacturing quality"` here)
- **`greenhouse_companies` / `ashby_companies`** — target companies to query directly; most Series B–D startups use one of these two ATS platforms

---

## Known Limitations

- LinkedIn and Indeed scrape public HTML, which can break when they update their markup. Both can be skipped with `--skip-linkedin` / `--skip-indeed` if they're failing.
- Scoring is keyword-based — it won't catch a great job described in unusual language, and it won't catch a bad one with the right keywords.
- No login-required boards (LinkedIn Jobs API, Lever, Workday) are supported without credentials.
