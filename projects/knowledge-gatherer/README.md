# Knowledge Gatherer

A Python script that aggregates content from Slack, Confluence, Jira, and GitHub for a product area, then uses Claude to organize everything by feature into markdown files with citations.

## Why I Built This

Every time I joined a new product area — or someone new joined the team — there was an unavoidable tax: weeks of hunting through old Slack threads, half-finished Confluence pages, and buried Jira epics just to understand what had already been decided. The knowledge existed. It was just distributed across every tool the company used, with no way to ask it a question.

This tool answers: *what do we actually know about this product, and where is it?*

---

## What It Does

- Searches Slack, Confluence, Jira, and GitHub for content about a product or feature area
- Sends everything to Claude, which groups it by feature (not by source)
- Writes a directory of markdown files — one per feature — with summaries and source citations

**Example output for `--product "Checkout Flow"`:**

```
output/checkout-flow/
  payment-processing.md
  cart-management.md
  order-confirmation.md
  address-validation.md
```

Each file looks like:

```markdown
# Feature: Payment Processing

## Summary
Checkout uses Stripe for all payment processing...

## What We Know
The Stripe integration was added in Q3 2023 (see [CHECKOUT-47](link)).
Card validation happens client-side before the API call...

## Sources
- [Confluence: Payment Architecture v2](link)
- [Jira Epic CHECKOUT-47: Stripe Integration](link)
- [Slack thread in #checkout-eng (2024-03-15)](link)
```

---

## Setup

**Requirements:** Python 3.8+ (dependencies install automatically on first run)

```bash
# 1. Enter the project
cd projects/knowledge-gatherer

# 2. Create your config file
cp config_template.json config.json
# Edit config.json with your API tokens — see Credentials below
# config.json is gitignored and never committed

# 3. Run it
python3 knowledge_gatherer.py --product "Your Product Name"

# 4. Narrow to a specific feature
python3 knowledge_gatherer.py --product "Your Product Name" --feature "Authentication"
```

---

## Options

| Flag | Required | What it does |
|------|----------|-------------|
| `--product` | Yes | Product or area to search for across all sources |
| `--feature` | No | Narrow the search to a specific feature |

---

## Credentials

All credentials go in `config.json` (copied from `config_template.json`, gitignored).

| Source | What you need | Where to get it |
|--------|--------------|-----------------|
| **Slack** | User token (`xoxp-...`) | Slack app with `search:read`, `channels:history` scopes |
| **Confluence** | Atlassian API token | atlassian.com → Account Settings → Security → API tokens |
| **Jira** | Same Atlassian API token | Same as Confluence — one token works for both |
| **GitHub** | Personal access token | GitHub → Settings → Developer Settings → Fine-grained tokens |
| **Anthropic** | API key | console.anthropic.com |

**Note on Slack tokens:** `search.messages` requires a *user* token (`xoxp-`), not a bot token (`xoxb-`). Bot tokens don't have search permissions. Create a Slack app, add the user token scopes, and install it to your workspace.

**Note on Confluence + Jira:** They share the same Atlassian account credentials. The `url` fields are different (`/wiki` suffix for Confluence), but the `username` and `api_token` are the same.

---

## Known Limitations

- **Slack canvases not included** — only messages are searched. Canvas content requires additional API calls and is a planned improvement.
- **Content is truncated at 3,000 characters per item** — for very long Confluence pages or Jira descriptions, the script takes the first 3,000 characters and notes that it was truncated.
- **Slack search scope** — only searches message text in channels the token has access to. Private channels require explicit membership.
- **GitHub rate limits** — authenticated requests allow 30/min. Large products with many results may hit this; the script will show a hint if it does.
- **Quality reflects documentation quality** — if a product lives mostly in undocumented code or DMs, the output will reflect that.
