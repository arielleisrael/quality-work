---
description: Sweep new captures, cluster them into themes, and pick what to write
---

## 1. Sweep

```bash
python3 -m tools.capture.sweep
```

## 2. Read the whole inbox

```bash
python3 -c "
from tools.capture import promote
for path, meta, body in promote.list_notes():
    print('---', path.name, meta.get('captured'), meta.get('projects'))
    print(body)
"
```

Read every note, not just the new ones. Themes are re-derived from the
full inbox on every run.

## 3. Cluster

Group notes into themes. A theme is a recognizable argument that several
notes are circling, not a topic label. "checklist-decay" is a theme;
"testing" is a category and is useless here.

Classify each cluster:

- **RIPE** — enough notes, captured across enough time, forming one
  argument. Starting heuristic: 3+ notes spanning more than a week. This
  is a judgment call, not a threshold — 2 notes that genuinely complete
  an argument beat 5 that circle vaguely.
- **GROWING** — a thread is forming, not there yet. Say what is missing.
- **ORPHANS** — good notes with no current cluster.

Flag orphans older than 90 days as "let go?".

## 4. Present one screen

```
14 new thoughts since Aug 31.

RIPE
  Checklist decay (5 notes, spanning 3 weeks)
    The thread: checklists fail by growing, not by being skipped.
    Suggested angle: "Your release checklist is a graveyard."

GROWING
  AI readiness ≠ AI adoption (2 notes)
    Needs a concrete example of the gap.

ORPHANS (4)
  ...one line each...
```

Keep it to one screen. This review has to be survivable in twenty minutes
or it will not happen.

## 5. Write back the clustering

For each note, using its real path:

```bash
python3 -m tools.capture.tag <path> --themes "theme-a,theme-b" --projects "release-ready"
```

## 6. On request, draft

When the user picks a theme, write a draft to `posts/drafts/<slug>.md`:

- Build it from the user's own words and examples. Their phrasing in the
  notes is the voice — do not smooth it into generic content-marketing prose.
- Follow the order the thinking actually happened in. That progression is
  usually the structure of the piece.
- Fix dictation garbles now, visibly, in the draft — never in the source note.
- Frontmatter must list the source notes:

```markdown
---
title: Your release checklist is a graveyard
theme: checklist-decay
sources: [2026-09-07-0714-the-checklist-keeps-growing.md, ...]
status: draft
---
```

Then archive the sources:

```bash
python3 -m tools.capture.promote <path1> <path2> ...
```

Never archive notes the draft did not actually use.
