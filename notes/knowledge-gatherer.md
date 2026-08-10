# Notes: Knowledge Gatherer

## Why I rebuilt this

I originally built a version of this at my last company. Every time a new engineer joined, or a QE moved to a new product area, there was this unavoidable "domain tax" — two weeks of just trying to understand what had already been decided before you could do anything useful. The knowledge existed; it just lived in Slack threads from 18 months ago, Confluence pages that were last edited before anyone thought they'd need to be found again, Jira epics that were "done" but full of context, and GitHub issues with comment threads nobody remembered.

The original version was internal-only and assumed our specific Jira project structure, our Confluence space names, our Slack channel conventions. This rebuild strips all of that out and makes it work for anyone — same design principle as the job search agent. If I'm going to build something like this, I want other people to be able to use it, and I want to be able to show how it works.

## Architecture decision: Python collects, Claude thinks

The clearest design decision was the split between what Python does and what Claude does.

Python is good at making authenticated API calls, handling pagination, normalizing different date formats, and writing files to disk. It does not care what the content means.

Claude is good at reading a pile of heterogeneous text from completely different sources and deciding what belongs together. That grouping — "this Slack thread, this Jira epic, and this Confluence page are all about the same feature" — is genuinely hard to do with rules. You'd be writing regex forever and still getting it wrong.

If I'd tried to make Claude drive the API calls, I'd have needed tool use and a more complex loop. If I'd tried to do the feature grouping with rules, I'd have been hand-writing cluster logic that breaks on every edge case. The split keeps both sides simple and lets each do what it's actually good at.

## Things I learned

**Slack user tokens are different from bot tokens.** The `search.messages` endpoint requires an `xoxp-` user token — a bot token (`xoxb-`) doesn't have the permissions scope for message search. This is a very common gotcha that I didn't see called out in most Slack API documentation I read. If you get an `invalid_auth` or `not_authed` error and your token looks right, check whether it's actually a user token.

**Jira v3 API descriptions aren't plain text.** The Jira v3 REST API returns issue descriptions in Atlassian Document Format (ADF) — a nested JSON structure, not a string. Most Jira API tutorials I've seen are based on v2, which does return plain text or Markdown. Took me longer than it should have to realize why `description` was a dict and not a string. I wrote a recursive extractor that traverses the ADF node tree — it handles the common cases well but may miss some formatting edge cases.

**Confluence and Jira share credentials.** One Atlassian account, one API token, two different `url` values. The config template keeps them as separate sections anyway — it makes it self-documenting and means you can configure them independently if you're at a company that uses one but not the other.

**The output format has to be parseable by a regex.** I spent some time on how Claude should communicate the file structure back to the Python script. Options were: JSON (Claude outputs a JSON array of files), separate API calls per feature, or delimited text blocks. I went with delimited text blocks (`===FILE: name.md===...===END===`) because it's natural to write in streaming output, the delimiters are distinctive enough that they won't appear in content, and parsing it is three lines of Python. JSON with large amounts of Markdown embedded inside it is unpleasant to write and to debug.

**Adaptive thinking is the right call for grouping.** Deciding what "belongs together" as a feature requires reasoning about context, not just keyword matching. A Jira story about "adding retry logic" and a Slack thread about "why the payment API sometimes fails" might both belong to a "Payment Reliability" feature file even though neither of them says "payment reliability." That kind of inference is exactly what adaptive thinking is designed for.

## What I'd improve

- **Slack canvas support** — Canvases are increasingly where teams write structured knowledge, but they require a separate API call and a different content format. Worth adding.
- **Date range filtering** — A `--since` flag (like the job search agent) so you can scope to recent content instead of everything ever
- **Local caching** — Re-running with the same product shouldn't re-hit all four APIs. A simple JSON cache of fetched content by source + query would make iteration much faster
- **Smarter truncation** — Right now it truncates at a fixed character limit, which can cut off mid-sentence. Truncating at sentence boundaries would be cleaner
- **`--sources` flag** — Skip specific sources (e.g., `--sources slack,jira` to skip Confluence and GitHub)
