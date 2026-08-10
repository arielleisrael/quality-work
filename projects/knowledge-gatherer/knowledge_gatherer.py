#!/usr/bin/env python3
"""
Knowledge Gatherer — aggregates Slack, Confluence, Jira, and GitHub content
and uses Claude to organize it by product feature into markdown files.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


# ─── Dependencies ─────────────────────────────────────────────────────────────

def _install_deps():
    import subprocess
    for pkg in ["anthropic", "requests", "slack-sdk"]:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])


try:
    import anthropic
    import requests
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
except ImportError:
    print("Installing dependencies...")
    _install_deps()
    import anthropic
    import requests
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError


# ─── Config ───────────────────────────────────────────────────────────────────

CONFIG_PATH = Path(__file__).parent / "config.json"
MAX_ITEMS_PER_SOURCE = 50
MAX_BODY_CHARS = 3000


def load_config():
    if not CONFIG_PATH.exists():
        print("Error: config.json not found.")
        print("Copy config_template.json to config.json and fill in your credentials.")
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return json.load(f)


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _escape(s):
    return s.replace('"', '\\"')


# ─── Slack ────────────────────────────────────────────────────────────────────

def fetch_slack(config, product, feature=None):
    if not config.get("slack", {}).get("token"):
        print("  [slack] skipped — no token in config")
        return []

    client = WebClient(token=config["slack"]["token"])
    query = product + (f" {feature}" if feature else "")

    results = []
    try:
        response = client.search_messages(query=query, count=MAX_ITEMS_PER_SOURCE)
        messages = response["messages"]["matches"]
        print(f"  [slack] {len(messages)} messages found")

        for msg in messages:
            text = (msg.get("text") or "").strip()
            if not text:
                continue

            channel = msg.get("channel", {}).get("name", "unknown")
            user = msg.get("username") or msg.get("user", "unknown")
            ts = msg.get("ts", "")
            permalink = msg.get("permalink", "")

            date = ""
            if ts:
                try:
                    date = datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d")
                except Exception:
                    pass

            # Fetch thread replies for parent messages
            thread_text = ""
            thread_ts = msg.get("thread_ts")
            if thread_ts and thread_ts == ts:
                try:
                    channel_id = msg.get("channel", {}).get("id", "")
                    if channel_id:
                        replies = client.conversations_replies(
                            channel=channel_id, ts=thread_ts, limit=20
                        ).get("messages", [])[1:]
                        lines = [
                            f"  @{r.get('username', r.get('user', ''))}: {r.get('text', '').strip()}"
                            for r in replies[:10] if r.get("text")
                        ]
                        if lines:
                            thread_text = "\nThread replies:\n" + "\n".join(lines)
                except Exception:
                    pass

            entry = f"[SLACK] #{channel} | {date} | @{user}\n{text}{thread_text}"
            if permalink:
                entry += f"\nURL: {permalink}"
            results.append(entry)

    except SlackApiError as e:
        err = e.response.get("error", "unknown")
        print(f"  [slack] API error: {err}")
        if err in ("not_authed", "invalid_auth"):
            print("  [slack] hint: search.messages requires a user token (xoxp-), not a bot token (xoxb-)")

    return results


# ─── Confluence ───────────────────────────────────────────────────────────────

def fetch_confluence(config, product, feature=None):
    if not config.get("confluence", {}).get("api_token"):
        print("  [confluence] skipped — no credentials in config")
        return []

    conf = config["confluence"]
    base_url = conf["url"].rstrip("/")  # e.g. https://org.atlassian.net/wiki
    auth = (conf["username"], conf["api_token"])

    cql_parts = [f'text ~ "{_escape(product)}"', 'type = "page"']
    if feature:
        cql_parts.append(f'text ~ "{_escape(feature)}"')

    results = []
    try:
        resp = requests.get(
            f"{base_url}/rest/api/content/search",
            params={
                "cql": " AND ".join(cql_parts),
                "limit": MAX_ITEMS_PER_SOURCE,
                "expand": "body.view,version,space",
            },
            auth=auth,
            timeout=30,
        )
        resp.raise_for_status()
        pages = resp.json().get("results", [])
        print(f"  [confluence] {len(pages)} pages found")

        for page in pages:
            title = page.get("title", "Untitled")
            space = page.get("space", {}).get("key", "")
            updated = (page.get("version", {}).get("when") or "")[:10]
            webui = page.get("_links", {}).get("webui", "")
            page_url = base_url + webui

            body_html = page.get("body", {}).get("view", {}).get("value", "")
            body_text = re.sub(r"<[^>]+>", " ", body_html)
            body_text = re.sub(r"\s+", " ", body_text).strip()
            if len(body_text) > MAX_BODY_CHARS:
                body_text = body_text[:MAX_BODY_CHARS] + "... [truncated]"

            entry = f"[CONFLUENCE] {title} | Space: {space} | Updated: {updated}\n{body_text}"
            if webui:
                entry += f"\nURL: {page_url}"
            results.append(entry)

    except requests.HTTPError as e:
        print(f"  [confluence] HTTP {e.response.status_code}: {e}")
    except Exception as e:
        print(f"  [confluence] error: {e}")

    return results


# ─── Jira ─────────────────────────────────────────────────────────────────────

def fetch_jira(config, product, feature=None):
    if not config.get("jira", {}).get("api_token"):
        print("  [jira] skipped — no credentials in config")
        return []

    jira = config["jira"]
    base_url = jira["url"].rstrip("/")
    auth = (jira["username"], jira["api_token"])

    jql_parts = [f'text ~ "{_escape(product)}"', "issuetype in (Epic, Story, Task, Bug)"]
    if feature:
        jql_parts.append(f'text ~ "{_escape(feature)}"')
    jql = " AND ".join(jql_parts) + " ORDER BY updated DESC"

    results = []
    try:
        resp = requests.get(
            f"{base_url}/rest/api/3/search",
            params={
                "jql": jql,
                "maxResults": MAX_ITEMS_PER_SOURCE,
                "fields": "summary,description,issuetype,status,updated",
            },
            auth=auth,
            timeout=30,
        )
        resp.raise_for_status()
        issues = resp.json().get("issues", [])
        print(f"  [jira] {len(issues)} issues found")

        for issue in issues:
            key = issue.get("key", "")
            fields = issue.get("fields", {})
            summary = fields.get("summary", "Untitled")
            issue_type = fields.get("issuetype", {}).get("name", "")
            status = fields.get("status", {}).get("name", "")
            updated = (fields.get("updated") or "")[:10]

            desc = fields.get("description")
            description = ""
            if desc:
                description = _extract_adf_text(desc) if isinstance(desc, dict) else str(desc)
            if len(description) > MAX_BODY_CHARS:
                description = description[:MAX_BODY_CHARS] + "... [truncated]"

            entry = f"[JIRA] {key}: {summary} | Type: {issue_type} | Status: {status} | Updated: {updated}"
            if description:
                entry += f"\n{description}"
            entry += f"\nURL: {base_url}/browse/{key}"
            results.append(entry)

    except requests.HTTPError as e:
        print(f"  [jira] HTTP {e.response.status_code}: {e}")
    except Exception as e:
        print(f"  [jira] error: {e}")

    return results


def _extract_adf_text(node):
    """Recursively extract plain text from Atlassian Document Format (Jira API v3)."""
    if isinstance(node, str):
        return node
    if not isinstance(node, dict):
        return ""
    parts = []
    if node.get("type") == "text":
        parts.append(node.get("text", ""))
    for child in node.get("content", []):
        parts.append(_extract_adf_text(child))
    return " ".join(p for p in parts if p)


# ─── GitHub ───────────────────────────────────────────────────────────────────

def fetch_github(config, product, feature=None):
    if not config.get("github", {}).get("token"):
        print("  [github] skipped — no token in config")
        return []

    github = config["github"]
    headers = {
        "Authorization": f"Bearer {github['token']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    query = product + (f" {feature}" if feature else "")
    if github.get("org"):
        query += f" org:{github['org']}"

    results = []
    try:
        resp = requests.get(
            "https://api.github.com/search/issues",
            params={"q": query, "per_page": MAX_ITEMS_PER_SOURCE, "sort": "updated"},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        print(f"  [github] {len(items)} issues/PRs found")

        for item in items:
            number = item.get("number", "")
            title = item.get("title", "Untitled")
            state = item.get("state", "")
            item_type = "PR" if "pull_request" in item else "Issue"
            updated = (item.get("updated_at") or "")[:10]
            url = item.get("html_url", "")
            body = (item.get("body") or "").strip()
            if len(body) > MAX_BODY_CHARS:
                body = body[:MAX_BODY_CHARS] + "... [truncated]"

            entry = f"[GITHUB] {item_type} #{number}: {title} | State: {state} | Updated: {updated}"
            if body:
                entry += f"\n{body}"
            if url:
                entry += f"\nURL: {url}"
            results.append(entry)

    except requests.HTTPError as e:
        status = e.response.status_code
        print(f"  [github] HTTP {status}: {e}")
        if status == 403:
            print("  [github] hint: you may have hit the rate limit (30 req/min authenticated)")
    except Exception as e:
        print(f"  [github] error: {e}")

    return results


# ─── Claude ───────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a product knowledge organizer. You receive raw content from multiple sources (Slack, Confluence, Jira, GitHub) and organize it into feature-grouped markdown files.

Output ONLY a series of file blocks in this exact format — no preamble, no commentary, nothing outside the blocks:

===FILE: feature-name.md===
# Feature: [Feature Name]

## Summary
[2-3 sentence overview of what this feature does and its current state]

## What We Know
[Detailed information organized by sub-topic. Weave together information from all sources into a coherent narrative — do not organize by source.]

## Open Questions / Decisions
[Unresolved questions, conflicting information, or explicit open decisions. Omit this section if there are none.]

## Sources
- [Description of source](URL)
===END===

Rules:
- Group by feature, not by source
- Write as if explaining to a new team member
- Cite sources — link URLs inline in the text or list them in Sources
- If information conflicts across sources, note the conflict
- Use kebab-case for filenames (e.g., payment-processing.md)
- Create as many or as few files as the content warrants"""


def call_claude(config, product, feature, all_content):
    client = anthropic.Anthropic(api_key=config["anthropic"]["api_key"])

    focus = f"Product: {product}"
    if feature:
        focus += f"\nFeature focus: {feature}"

    user_message = (
        f"{focus}\n\n"
        f"--- RAW CONTENT FROM ALL SOURCES ---\n\n"
        f"{chr(10).join(all_content)}\n\n"
        f"--- END ---\n\n"
        f"Organize the above into feature-grouped markdown files."
    )

    print(f"\nSending {len(user_message):,} characters to Claude (streaming)...\n")

    full_text = ""
    with client.messages.stream(
        model="claude-opus-5",
        max_tokens=32000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_text += text

    print()
    return full_text


# ─── Output ───────────────────────────────────────────────────────────────────

def parse_output(response_text):
    files = {}
    for match in re.finditer(r"===FILE:\s*(.+?\.md)===\n(.*?)===END===", response_text, re.DOTALL):
        files[match.group(1).strip()] = match.group(2).strip()
    return files


def write_output(product, files):
    output_dir = Path(__file__).parent / "output" / slugify(product)
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, content in files.items():
        path = output_dir / name
        path.write_text(content + "\n", encoding="utf-8")
        written.append(path)
    return output_dir, written


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Aggregate product knowledge from Slack, Confluence, Jira, and GitHub"
    )
    parser.add_argument("--product", required=True, help="Product or area to search for")
    parser.add_argument("--feature", help="Narrow to a specific feature (optional)")
    args = parser.parse_args()

    config = load_config()

    print(f"\nKnowledge Gatherer")
    print(f"Product: {args.product}")
    if args.feature:
        print(f"Feature: {args.feature}")
    print()

    print("Fetching from sources...")
    slack_items = fetch_slack(config, args.product, args.feature)
    confluence_items = fetch_confluence(config, args.product, args.feature)
    jira_items = fetch_jira(config, args.product, args.feature)
    github_items = fetch_github(config, args.product, args.feature)

    all_items = slack_items + confluence_items + jira_items + github_items

    if not all_items:
        print("\nNo content found. Check your credentials and search terms.")
        sys.exit(1)

    print(f"\nCollected: {len(slack_items)} Slack, {len(confluence_items)} Confluence, "
          f"{len(jira_items)} Jira, {len(github_items)} GitHub")

    response = call_claude(config, args.product, args.feature, all_items)

    files = parse_output(response)
    if not files:
        fallback = Path(__file__).parent / "output" / "raw_response.txt"
        fallback.parent.mkdir(exist_ok=True)
        fallback.write_text(response)
        print(f"\nCould not parse file blocks from response. Raw output saved to {fallback}")
        sys.exit(1)

    output_dir, written = write_output(args.product, files)

    print(f"\nWrote {len(written)} file(s) to {output_dir}/")
    for path in written:
        print(f"  {path}")


if __name__ == "__main__":
    main()
