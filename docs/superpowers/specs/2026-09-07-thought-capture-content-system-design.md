# Thought Capture → Content System

**Date:** 2026-09-07
**Status:** Approved, ready for implementation planning

## Problem

Thoughts about in-flight projects (Release Ready, job search agent, AI readiness assessment) arrive constantly and are lost. There is no capture surface, no organization, and therefore no raw material for the build-in-public content goal: blog posts on *Built and Tested* that become newsletters, plus LinkedIn short-form.

The best thoughts arrive away from the laptop, when writing them down is hardest. Time is scarce and the system must be low-maintenance or it will be abandoned.

## Goals

1. Capture a thought in one tap, from phone or laptop, without categorizing it.
2. Accumulate captures into recognizable themes over time.
3. Turn ripe themes into drafts in `posts/drafts/`, and drafts into LinkedIn posts.
4. Keep raw, unfiltered material off the public GitHub repo.

## Non-goals (v1)

- Auto-publishing to Substack or LinkedIn. Drafts stop at draft.
- Scheduling, editorial calendar, or pipeline stages.
- Web UI or database. Markdown files and slash commands only.
- Audio-file transcription. Dictation happens on-device at capture time.
- Performance analytics.

## Architecture

Four stages, each independently understandable and testable:

```
CAPTURE            SWEEP              REVIEW             DRAFT
phone Shortcut ─┐
                ├─→ iCloud folder ─→ inbox/*.md ─→ theme clusters ─→ posts/drafts/
/capture cmd  ──┘   (raw text)       (enriched)     (derived)         (committed)
                                                                          │
                                                                    /linkedin
```

### 1. Capture

Capture is deliberately dumb. No tags, no project selection, no prompts — anything requiring a decision at capture time is friction that kills the habit. Enrichment happens later.

**Door 1 — phone.** An iOS Shortcut named "Capture", pinned to the home screen and Action Button. One tap → `Dictate Text` → speak → done. It appends a timestamped `.md` file to an iCloud Drive folder. Dictation is on-device and produces text, so no audio file ever needs transcription.

**Door 2 — laptop.** A `/capture <text>` slash command in Claude Code, writing to the same iCloud folder. No context switch out of the terminal.

**Fallback.** The sweep also reads raw Voice Memos transcripts and a designated Apple Notes folder, so a thought captured the lazy way is still collected — just less tidy.

### 2. Sweep

Moves files from the iCloud capture folder into `quality-work/inbox/`, one Markdown file per thought, and enriches frontmatter.

Filename: `inbox/YYYY-MM-DD-HHMM-<slug>.md`

```markdown
---
captured: 2026-09-07T07:14
source: phone          # phone | laptop | voice-memo | notes
projects: [release-ready]
themes: [checklist-decay, process-quality]
status: raw            # raw | used | let-go
---

The release checklist keeps growing because nobody ever deletes items
from it. That's the real failure mode — not that teams skip the
checklist, but that it becomes noise.
```

Rules:

- Body text is stored **verbatim**. Dictation errors are never silently corrected; cleanup happens at draft time where it is visible.
- `projects` and `themes` are assigned during sweep, not by the user.
- Files are **moved**, not copied, and deduped on content hash. The sweep is idempotent — running it repeatedly is safe.
- Captures under ~15 characters are dropped as accidental, and the drop is reported.
- `captured` comes from capture time, not sweep time, so late iCloud arrivals sort into the correct week.

### 3. Review

`/review-inbox` re-clusters the **entire** inbox and prints one screen:

- **RIPE** — enough notes, spanning enough time, forming one recognizable argument. Includes a one-line statement of the thread and a suggested angle.
- **GROWING** — a theme forming but not yet sufficient.
- **ORPHANS** — good notes with no current cluster.

The core insight: a single thought is almost never a post; five thoughts on one subject captured across three weeks is, and it is better than anything written in one sitting because it has time in it. The system's job is noticing when scattered notes have become an argument.

**Themes are derived on every run, never maintained by hand.** They may merge, split, or be renamed as thinking moves. There is no taxonomy for the user to keep tidy — that is the component of note systems that reliably collapses.

Orphans older than 90 days are flagged "let go?" so the inbox self-prunes rather than becoming a guilt pile.

**On-demand entry point.** The same machinery answers ad-hoc queries ("what do I have on release readiness?") without waiting for the weekly ritual — either drafting, or reporting that the theme is not ripe.

### 4. Draft

Promoting a theme writes a draft to `posts/drafts/`, built from the source notes — the user's own phrasing and examples, in the order the thinking happened — with source note paths in frontmatter for provenance. Source notes move to `inbox/archive/` with `status: used`, so they stop surfacing in review but remain readable.

`/linkedin <draft>` produces a short-form version **from an existing draft**, not from raw notes. One idea, developed once, distributed twice.

## Storage and privacy

- `inbox/` and `inbox/archive/` live inside `quality-work` but are **gitignored**. Raw material never reaches the public repo.
- The iCloud capture folder serves as the backup, so raw notes being unversioned carries no real loss risk.
- Only `posts/drafts/` and `posts/published/` are committed.
- The `.gitignore` entry is verified with `git check-ignore` at build time rather than assumed correct.

## Failure modes

| Risk | Handling |
|---|---|
| Sweep run twice | Move-not-copy plus content-hash dedupe; idempotent. |
| iCloud not yet synced | Nothing lost; next sweep collects it, timestamps keep ordering correct. |
| Garbled dictation | Verbatim storage, corrected visibly at draft time. |
| Accidental empty capture | Dropped under ~15 chars, reported. |
| Review skipped for weeks | Nothing breaks; age is shown, stale orphans flagged. |
| Raw note nearly committed | Gitignored, verified with `git check-ignore`. |

## Verification

Behavioral success (does the button get tapped, does a post ship) takes two weeks and cannot be tested mechanically. Verifiable before handoff:

1. A phone capture lands in `inbox/` with correct frontmatter and verbatim body.
2. Sweep is idempotent across repeated runs — no duplicates, no loss.
3. `git status` is clean after a sweep; `git check-ignore inbox/` passes.
4. Sub-15-character captures are dropped and reported.
5. `/review-inbox` over seeded notes produces sensible clusters and ripeness calls.
6. Promotion writes a draft with correct provenance and archives its sources.

## Known risk

**The weekly review is the load-bearing habit.** Capture is frictionless and will work. If review never happens, this becomes a tidy graveyard. The correct response to that failure is to make review *smaller* — three notes at a time rather than a week's worth — not to add automation.
