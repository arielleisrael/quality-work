# Tool A: Test Strategy Generator — Design

**Date:** 2026-08-13
**Status:** Approved
**Location:** `projects/test-strategy-generator/test_strategy_generator.py` (quality-work repo)

---

## Overview

A Python script that reads a requirements document and uses Claude to produce a comprehensive test strategy. Designed to work with any requirements markdown file, with a default path pointing at the release-ready project. Output is a markdown file (and optionally a shareable HTML artifact) written to the same directory as the requirements file.

---

## Structure & CLI

Single runnable script with auto-installed dependencies (`anthropic`, `python-dotenv`). No package setup required — mirrors the Knowledge Gatherer pattern.

```
python test_strategy_generator.py
    [--requirements PATH]   # default: ../../release-ready/docs/requirements.md (relative to script location)
    [--sections NAMES]      # comma-separated filter, e.g. "RR-001,RR-002" or "Functional Requirements"
    [--output PATH]         # default: same directory as --requirements, named test-strategy.md
    [--artifact]            # also generate a shareable HTML file alongside the markdown
```

- With no arguments: reads release-ready's requirements, writes `docs/test-strategy.md` there
- With `--requirements`: reads any markdown requirements file and writes output to that file's directory
- With `--sections`: partial run — output filename gets a slug suffix (e.g. `test-strategy-nfr.md`) so it doesn't overwrite a full strategy run
- With `--artifact`: also writes `test-strategy.html` (or `test-strategy-nfr.html`)

---

## Requirements Parsing

The script reads the file as plain text and splits it into sections by markdown heading level. Any `##` or `###` line begins a new section; content runs until the next same-or-higher heading.

**Section filtering** (`--sections`) matches against heading text, case-insensitive substring:
- `--sections "RR-001,RR-002"` → captures those two requirements
- `--sections "NFR"` → captures all three non-functional requirements
- `--sections "Functional Requirements"` → captures the entire functional block

The top-level `#` heading and any intro prose before the first `##` are always included regardless of filter — they provide product context Claude needs to write meaningful test cases.

If no filter is given, all sections pass through.

---

## Claude Interaction

**Model:** `claude-sonnet-5`
**Thinking:** adaptive
**Output:** streaming

Single API call. The system prompt establishes the role of a senior QE reviewing a requirements document. The user message contains the filtered requirements content and asks for four output components in order:

1. **Test coverage by requirement** — for each requirement: applicable test types (unit / integration / E2E / manual), a rationale, and 2–4 concrete test case outlines with enough detail to act on
2. **Risk-based priority ordering** — rank requirements by testing risk (likelihood × impact of a miss), one sentence of rationale per item
3. **Coverage gaps** — areas the requirements don't address that a tester would normally cover (error states, edge inputs, performance boundaries, security surface)
4. **Recommended test approach** — short synthesis: what to automate, what to test manually, suggested entry points for CI

The prompt asks Claude to write in markdown so the streamed output can be written directly to the output file without post-processing.

If `--artifact` is set, a second `claude-sonnet-5` call (non-streaming, adaptive thinking) takes the generated markdown and produces a self-contained HTML page.

---

## Output Format

### Markdown file

The script prepends a metadata header, then writes Claude's streamed output directly:

```markdown
# Test Strategy
**Generated:** 2026-08-13 14:32
**Source:** docs/requirements.md
**Sections:** all

---

[Claude's output: four sections in order]
```

### HTML artifact (`--artifact`)

A second Claude call generates a **self-contained HTML page** — inline CSS, no external dependencies. Visual treatment includes:
- Color-coded test type chips (unit / integration / E2E / manual)
- Risk priority displayed as an ordered table with severity indicators
- Coverage gaps highlighted as a warning list
- Clean, responsive design suitable for sharing with a team

Written alongside the markdown as `test-strategy.html` (or `test-strategy-{slug}.html` for filtered runs).

---

## File Structure

```
quality-work/
  projects/
    test-strategy-generator/
      test_strategy_generator.py
```

Output (default run, no args):
```
release-ready/
  docs/
    test-strategy.md
    test-strategy.html   (if --artifact)
```

---

## Dependencies

Auto-installed at script start:
- `anthropic` — Claude API SDK
- `python-dotenv` — loads `ANTHROPIC_API_KEY` from `.env`

Standard library only otherwise: `argparse`, `pathlib`, `datetime`, `re`, `sys`, `subprocess`.

---

## Reference

Knowledge Gatherer (`projects/knowledge-gatherer/knowledge_gatherer.py`) established the structural pattern this tool follows: sections separated by `# ─── Section ───` comments, auto-install deps, Opus/Sonnet + adaptive thinking + streaming.
