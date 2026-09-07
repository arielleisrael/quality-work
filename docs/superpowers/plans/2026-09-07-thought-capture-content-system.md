# Thought Capture → Content System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a two-door thought-capture system that collects half-formed ideas from phone and laptop into a private local inbox, and turns accumulated themes into blog drafts and LinkedIn posts.

**Architecture:** Deterministic Python scripts under `tools/capture/` do all mechanical work — writing capture files, moving them into the inbox, deduping, slugging, archiving. All judgment work — assigning projects, clustering themes, deciding ripeness, drafting — lives in Claude Code slash commands under `.claude/commands/`. This split is deliberate: the mechanical half is unit-testable and the judgment half is not, so keeping them apart means the tested code is genuinely tested.

**Tech Stack:** Python 3.9 (system interpreter, no venv), pytest 8.4.2, Markdown files, Claude Code slash commands, iOS Shortcuts.

## Global Constraints

- **No third-party Python dependencies.** Standard library only. The frontmatter schema is fixed and tiny, so PyYAML is not worth a venv the user has to maintain.
- **Python 3.9 compatible.** No `match`, no `X | Y` type unions, no `tomllib`.
- **Capture bodies are stored verbatim.** No spell-correction, no reflowing, no trimming beyond surrounding whitespace.
- **`inbox/` is never committed.** Verified with `git check-ignore`, not assumed.
- **Scripts never make judgment calls.** No script assigns a theme, decides ripeness, or edits prose. Scripts that would need to guess must instead write empty values for the command layer to fill.
- **All paths are environment-overridable** via `CAPTURE_DIR`, `INBOX_DIR`, `DRAFTS_DIR` so tests never touch real iCloud or the real inbox.
- Minimum viable capture length: **15 characters** after stripping.

## Deviations from the spec

Two, both deliberate, both worth the reader knowing about:

1. **Fallback capture is folder-based, not app-based.** The spec describes sweeping Voice Memos and a designated Apple Notes folder directly. That needs an AppleScript/Shortcuts subsystem for a path the user will rarely take, since the Shortcut is the primary door. v1 instead sweeps *any* `.txt` or `.md` file dropped into the Capture folder by any means — including a Voice Memos transcript or a note shared via the Files app — tagged `source: unknown`. Same outcome, no subsystem.

2. **`themes` in frontmatter is a cache, not a record.** The spec shows themes in frontmatter but also says themes are re-derived on every review and never maintained. Those pull against each other. Resolution: `projects` is assigned once at sweep time (it is a stable fact about a note); `themes` is overwritten by every `/review-inbox` run and is authoritative only as of the last run.

---

## File Structure

**Created:**

| Path | Responsibility |
|---|---|
| `tools/capture/config.py` | Path resolution and env overrides. The only module that knows where things live. |
| `tools/capture/frontmatter.py` | Parse and serialize the fixed frontmatter schema. No I/O. |
| `tools/capture/naming.py` | Slug generation and body hashing. Pure functions. |
| `tools/capture/capture.py` | Write a new capture file to the capture folder. CLI entry point. |
| `tools/capture/sweep.py` | Move capture files into the inbox: dedupe, drop empties, add frontmatter. CLI entry point. |
| `tools/capture/tag.py` | Set frontmatter fields on an existing inbox note. CLI entry point. |
| `tools/capture/promote.py` | Archive notes used by a draft. CLI entry point. |
| `tests/capture/test_*.py` | One test module per source module. |
| `.claude/commands/capture.md` | `/capture` — laptop door. |
| `.claude/commands/review-inbox.md` | `/review-inbox` — sweep, cluster, present, tag. |
| `.claude/commands/linkedin.md` | `/linkedin` — short-form from an existing draft. |
| `docs/capture-shortcut-setup.md` | iOS Shortcut build instructions for the user. |

**Modified:** `.gitignore` (ignore `inbox/`, un-ignore `.claude/commands/`).

---

### Task 1: Repo setup and path configuration

**Files:**
- Modify: `.gitignore`
- Create: `tools/capture/__init__.py`, `tools/capture/config.py`
- Create: `tests/__init__.py`, `tests/capture/__init__.py`, `tests/capture/test_config.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `config.capture_dir() -> Path`, `config.inbox_dir() -> Path`, `config.archive_dir() -> Path`, `config.drafts_dir() -> Path`. Every later task uses these instead of hardcoding paths.

- [ ] **Step 1: Update `.gitignore`**

Replace the contents of `.gitignore` with:

```gitignore
.DS_Store
*.swp
*.swo

# Local Claude config stays private, but the capture commands are part
# of the system and belong in the repo.
.claude/*
!.claude/commands/
!.claude/commands/**

# Raw captured thoughts are private and never committed.
inbox/
```

- [ ] **Step 2: Create package directories**

```bash
mkdir -p tools/capture tests/capture
touch tools/capture/__init__.py tests/__init__.py tests/capture/__init__.py
```

- [ ] **Step 3: Write the failing test**

Create `tests/capture/test_config.py`:

```python
from pathlib import Path

from tools.capture import config


def test_capture_dir_defaults_to_icloud():
    assert config.capture_dir() == (
        Path.home()
        / "Library"
        / "Mobile Documents"
        / "com~apple~CloudDocs"
        / "Capture"
    )


def test_capture_dir_respects_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("CAPTURE_DIR", str(tmp_path / "cap"))
    assert config.capture_dir() == tmp_path / "cap"


def test_inbox_and_archive_are_nested(monkeypatch, tmp_path):
    monkeypatch.setenv("INBOX_DIR", str(tmp_path / "inbox"))
    assert config.inbox_dir() == tmp_path / "inbox"
    assert config.archive_dir() == tmp_path / "inbox" / "archive"


def test_drafts_dir_respects_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("DRAFTS_DIR", str(tmp_path / "drafts"))
    assert config.drafts_dir() == tmp_path / "drafts"
```

- [ ] **Step 4: Run test to verify it fails**

Run: `python3 -m pytest tests/capture/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools'` or `AttributeError`.

- [ ] **Step 5: Write the implementation**

Create `tools/capture/config.py`:

```python
"""Path resolution for the capture system.

Every path used anywhere in the system comes from this module, and every
one honours an environment override so tests never touch the real iCloud
folder or the real inbox.
"""

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

ICLOUD_CAPTURE = (
    Path.home()
    / "Library"
    / "Mobile Documents"
    / "com~apple~CloudDocs"
    / "Capture"
)


def _from_env(var, default):
    value = os.environ.get(var)
    return Path(value) if value else default


def capture_dir():
    """Where phone and laptop captures land before being swept."""
    return _from_env("CAPTURE_DIR", ICLOUD_CAPTURE)


def inbox_dir():
    """Where swept notes live. Gitignored."""
    return _from_env("INBOX_DIR", REPO_ROOT / "inbox")


def archive_dir():
    """Where notes go once a draft has used them."""
    return inbox_dir() / "archive"


def drafts_dir():
    """Where promoted drafts are written. Committed."""
    return _from_env("DRAFTS_DIR", REPO_ROOT / "posts" / "drafts")
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python3 -m pytest tests/capture/test_config.py -v`
Expected: 4 passed.

- [ ] **Step 7: Verify the gitignore actually protects the inbox**

Do not trust that the pattern was typed correctly — prove it:

```bash
mkdir -p inbox && echo "secret thought" > inbox/probe.md
git check-ignore -v inbox/probe.md
git status --porcelain | grep inbox || echo "OK: inbox is invisible to git"
rm inbox/probe.md
git check-ignore -v .claude/commands 2>/dev/null && echo "PROBLEM: commands are ignored" || echo "OK: commands are trackable"
```

Expected: `git check-ignore` reports a match on `inbox/`, `git status` shows nothing under `inbox`, and `.claude/commands` is NOT ignored.

- [ ] **Step 8: Commit**

```bash
git add .gitignore tools tests
git commit -m "feat: add capture path config and inbox gitignore"
```

---

### Task 2: Frontmatter parsing and serialization

**Files:**
- Create: `tools/capture/frontmatter.py`
- Create: `tests/capture/test_frontmatter.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `frontmatter.parse(text) -> (dict, str)` returning metadata and body; `frontmatter.serialize(meta, body) -> str`. List-valued keys are `projects`, `themes`, and `sources`; every other value is a plain string. Round-tripping is lossless for this schema.

- [ ] **Step 1: Write the failing test**

Create `tests/capture/test_frontmatter.py`:

```python
from tools.capture import frontmatter

NOTE = """---
captured: 2026-09-07T07:14
source: phone
projects: [release-ready]
themes: [checklist-decay, process-quality]
status: raw
---

The checklist keeps growing.

Nobody deletes anything.
"""


def test_parse_returns_scalar_fields():
    meta, _ = frontmatter.parse(NOTE)
    assert meta["captured"] == "2026-09-07T07:14"
    assert meta["source"] == "phone"
    assert meta["status"] == "raw"


def test_parse_returns_list_fields():
    meta, _ = frontmatter.parse(NOTE)
    assert meta["projects"] == ["release-ready"]
    assert meta["themes"] == ["checklist-decay", "process-quality"]


def test_parse_preserves_body_including_blank_lines():
    _, body = frontmatter.parse(NOTE)
    assert body == "The checklist keeps growing.\n\nNobody deletes anything."


def test_parse_handles_empty_lists():
    meta, _ = frontmatter.parse("---\nthemes: []\n---\n\nbody\n")
    assert meta["themes"] == []


def test_parse_handles_missing_frontmatter():
    meta, body = frontmatter.parse("just a body\n")
    assert meta == {}
    assert body == "just a body"


def test_parse_keeps_colons_inside_values():
    meta, _ = frontmatter.parse("---\nnote: this: that\n---\n\nx\n")
    assert meta["note"] == "this: that"


def test_serialize_round_trips():
    meta, body = frontmatter.parse(NOTE)
    reparsed_meta, reparsed_body = frontmatter.parse(
        frontmatter.serialize(meta, body)
    )
    assert reparsed_meta == meta
    assert reparsed_body == body


def test_serialize_writes_empty_list_as_brackets():
    text = frontmatter.serialize({"themes": []}, "body")
    assert "themes: []" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/capture/test_frontmatter.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.capture.frontmatter'`.

- [ ] **Step 3: Write the implementation**

Create `tools/capture/frontmatter.py`:

```python
"""Parse and serialize the capture system's frontmatter.

This is deliberately NOT a YAML implementation. The schema is fixed and
tiny — scalar strings plus three list fields — so a 30-line parser beats
a dependency the user would have to maintain. If the schema ever needs
nesting, quoting, or multi-line values, replace this with PyYAML rather
than growing it.
"""

DELIMITER = "---"
LIST_KEYS = ("projects", "themes", "sources")


def parse(text):
    """Return (meta, body). Missing frontmatter yields ({}, stripped text)."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != DELIMITER:
        return {}, text.strip()

    meta = {}
    body_start = len(lines)
    for index in range(1, len(lines)):
        line = lines[index]
        if line.strip() == DELIMITER:
            body_start = index + 1
            break
        if not line.strip() or ":" not in line:
            continue
        key, _, raw = line.partition(":")
        meta[key.strip()] = _parse_value(raw.strip())

    return meta, "\n".join(lines[body_start:]).strip()


def _parse_value(raw):
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [item.strip() for item in inner.split(",") if item.strip()]
    return raw


def serialize(meta, body):
    """Render meta and body back into a note file."""
    lines = [DELIMITER]
    for key, value in meta.items():
        lines.append("{}: {}".format(key, _render_value(value)))
    lines.append(DELIMITER)
    lines.append("")
    lines.append(body.strip())
    lines.append("")
    return "\n".join(lines)


def _render_value(value):
    if isinstance(value, (list, tuple)):
        return "[{}]".format(", ".join(value))
    return str(value)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/capture/test_frontmatter.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/capture/frontmatter.py tests/capture/test_frontmatter.py
git commit -m "feat: add frontmatter parser for capture notes"
```

---

### Task 3: Slug and hash helpers

**Files:**
- Create: `tools/capture/naming.py`
- Create: `tests/capture/test_naming.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `naming.slugify(text, max_words=6) -> str` and `naming.body_hash(text) -> str` (16-char hex digest of the whitespace-normalized, lowercased body). The hash is what makes sweeping idempotent, so it must ignore differences that do not change meaning.

- [ ] **Step 1: Write the failing test**

Create `tests/capture/test_naming.py`:

```python
from tools.capture import naming


def test_slugify_takes_first_words_lowercased():
    assert naming.slugify("The checklist keeps growing") == "the-checklist-keeps-growing"


def test_slugify_truncates_to_max_words():
    text = "one two three four five six seven eight"
    assert naming.slugify(text) == "one-two-three-four-five-six"


def test_slugify_strips_punctuation():
    assert naming.slugify("Won't it, though?") == "won-t-it-though"


def test_slugify_collapses_repeated_separators():
    assert naming.slugify("a  --  b") == "a-b"


def test_slugify_falls_back_when_no_usable_characters():
    assert naming.slugify("!!! ???") == "untitled"


def test_body_hash_is_stable():
    assert naming.body_hash("hello world") == naming.body_hash("hello world")


def test_body_hash_ignores_whitespace_and_case():
    assert naming.body_hash("Hello   world\n") == naming.body_hash("hello world")


def test_body_hash_distinguishes_different_text():
    assert naming.body_hash("hello world") != naming.body_hash("goodbye world")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/capture/test_naming.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.capture.naming'`.

- [ ] **Step 3: Write the implementation**

Create `tools/capture/naming.py`:

```python
"""Filename slugs and content hashes.

The hash normalizes whitespace and case so that the same thought swept
twice — or dictated once and typed once — collapses to one note.
"""

import hashlib
import re

HASH_LENGTH = 16


def slugify(text, max_words=6):
    """Build a filename-safe slug from the first few words of a note."""
    words = text.strip().split()[:max_words]
    lowered = " ".join(words).lower()
    hyphenated = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return hyphenated or "untitled"


def body_hash(text):
    """Short digest of a note body, ignoring whitespace and case."""
    normalized = " ".join(text.lower().split())
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return digest[:HASH_LENGTH]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/capture/test_naming.py -v`
Expected: 8 passed.

Note on `test_slugify_strips_punctuation`: `"Won't"` becomes `won-t`, not `wont`. That is intended — the slug only has to be stable and readable, and preserving the character boundary is simpler than maintaining an apostrophe special case.

- [ ] **Step 5: Commit**

```bash
git add tools/capture/naming.py tests/capture/test_naming.py
git commit -m "feat: add slug and content-hash helpers"
```

---

### Task 4: The sweep

**Files:**
- Create: `tools/capture/sweep.py`
- Create: `tests/capture/test_sweep.py`

**Interfaces:**
- Consumes: `config.capture_dir()`, `config.inbox_dir()`, `config.archive_dir()`, `frontmatter.serialize`, `frontmatter.parse`, `naming.slugify`, `naming.body_hash`.
- Produces: `sweep.sweep() -> SweepResult` where `SweepResult` is a `namedtuple` with fields `imported` (list of `Path`), `dropped` (list of `(name, reason)`), and `duplicates` (list of `str` filenames). Also `sweep.parse_capture_meta(path) -> (source, datetime)` (takes a `Path`, reads `.name` and falls back to `.stat().st_mtime`). Task 8's `/review-inbox` command calls the CLI and parses its printed summary.

Capture filenames follow `capture-<source>-YYYYMMDD-HHMMSS.txt`. Anything else is swept with `source: unknown` and a timestamp from the file's modification time — that is what makes the "lazy" fallback path work.

- [ ] **Step 1: Write the failing test**

Create `tests/capture/test_sweep.py`:

```python
import datetime as dt
import os

import pytest

from tools.capture import frontmatter, sweep


@pytest.fixture
def dirs(monkeypatch, tmp_path):
    capture = tmp_path / "capture"
    inbox = tmp_path / "inbox"
    capture.mkdir()
    monkeypatch.setenv("CAPTURE_DIR", str(capture))
    monkeypatch.setenv("INBOX_DIR", str(inbox))
    return capture, inbox


def write_capture(capture, name, text):
    path = capture / name
    path.write_text(text, encoding="utf-8")
    return path


def test_sweep_imports_a_capture_with_frontmatter(dirs):
    capture, inbox = dirs
    write_capture(
        capture,
        "capture-phone-20260907-071400.txt",
        "The release checklist keeps growing because nobody deletes items.",
    )

    result = sweep.sweep()

    assert len(result.imported) == 1
    note = result.imported[0]
    assert note.parent == inbox
    meta, body = frontmatter.parse(note.read_text(encoding="utf-8"))
    assert meta["source"] == "phone"
    assert meta["captured"] == "2026-09-07T07:14"
    assert meta["status"] == "raw"
    assert meta["projects"] == []
    assert meta["themes"] == []
    assert body == (
        "The release checklist keeps growing because nobody deletes items."
    )


def test_sweep_names_file_from_timestamp_and_slug(dirs):
    capture, _ = dirs
    write_capture(
        capture,
        "capture-phone-20260907-071400.txt",
        "The release checklist keeps growing",
    )

    note = sweep.sweep().imported[0]

    assert note.name == "2026-09-07-0714-the-release-checklist-keeps-growing.md"


def test_sweep_removes_the_source_file(dirs):
    capture, _ = dirs
    source = write_capture(
        capture, "capture-phone-20260907-071400.txt", "a real thought worth keeping"
    )

    sweep.sweep()

    assert not source.exists()


def test_sweep_is_idempotent(dirs):
    capture, inbox = dirs
    write_capture(
        capture, "capture-phone-20260907-071400.txt", "a real thought worth keeping"
    )

    sweep.sweep()
    second = sweep.sweep()

    assert second.imported == []
    assert len(list(inbox.glob("*.md"))) == 1


def test_sweep_skips_duplicate_content_already_in_inbox(dirs):
    capture, inbox = dirs
    write_capture(capture, "capture-phone-20260907-071400.txt", "the same exact thought")
    sweep.sweep()
    write_capture(capture, "capture-laptop-20260908-090000.txt", "The Same   Exact Thought")

    result = sweep.sweep()

    assert result.imported == []
    assert result.duplicates == ["capture-laptop-20260908-090000.txt"]
    assert len(list(inbox.glob("*.md"))) == 1


def test_sweep_skips_content_already_archived(dirs):
    capture, inbox = dirs
    archive = inbox / "archive"
    archive.mkdir(parents=True)
    (archive / "old.md").write_text(
        frontmatter.serialize({"status": "used"}, "an archived thought"),
        encoding="utf-8",
    )
    write_capture(capture, "capture-phone-20260907-071400.txt", "an archived thought")

    result = sweep.sweep()

    assert result.imported == []
    assert result.duplicates == ["capture-phone-20260907-071400.txt"]


def test_sweep_drops_pocket_taps(dirs):
    capture, inbox = dirs
    write_capture(capture, "capture-phone-20260907-071400.txt", "hm")

    result = sweep.sweep()

    assert result.imported == []
    assert result.dropped == [("capture-phone-20260907-071400.txt", "too short")]
    assert list(inbox.glob("*.md")) == []


def test_sweep_reports_dropped_files_but_removes_them(dirs):
    capture, _ = dirs
    source = write_capture(capture, "capture-phone-20260907-071400.txt", "ok")

    sweep.sweep()

    assert not source.exists()


def test_sweep_handles_unknown_filenames_using_mtime(dirs):
    capture, _ = dirs
    path = write_capture(capture, "voice-memo-transcript.txt", "a thought from a voice memo")
    stamp = dt.datetime(2026, 9, 5, 15, 30).timestamp()
    os.utime(path, (stamp, stamp))

    note = sweep.sweep().imported[0]

    meta, _ = frontmatter.parse(note.read_text(encoding="utf-8"))
    assert meta["source"] == "unknown"
    assert meta["captured"] == "2026-09-05T15:30"


def test_sweep_ignores_non_text_files(dirs):
    capture, inbox = dirs
    (capture / "photo.jpg").write_bytes(b"\xff\xd8\xff")

    result = sweep.sweep()

    assert result.imported == []
    assert (capture / "photo.jpg").exists()


def test_sweep_stores_body_verbatim_including_typos(dirs):
    capture, _ = dirs
    write_capture(
        capture,
        "capture-phone-20260907-071400.txt",
        "the reelase cheklist keeps growing and nobody prunes it",
    )

    note = sweep.sweep().imported[0]

    _, body = frontmatter.parse(note.read_text(encoding="utf-8"))
    assert body == "the reelase cheklist keeps growing and nobody prunes it"


def test_sweep_avoids_filename_collisions(dirs):
    capture, inbox = dirs
    write_capture(
        capture,
        "capture-phone-20260907-071400.txt",
        "the checklist keeps growing and nobody prunes the list",
    )
    sweep.sweep()
    write_capture(
        capture,
        "capture-laptop-20260907-071400.txt",
        "the checklist keeps growing and nobody deletes a thing",
    )

    result = sweep.sweep()

    # Same timestamp and same first six words, so the same stem - the
    # second note must be suffixed rather than overwriting the first.
    assert len(result.imported) == 1
    assert result.imported[0].name.endswith("-2.md")
    assert len(list(inbox.glob("*.md"))) == 2


def test_sweep_creates_inbox_if_missing(dirs):
    capture, inbox = dirs
    assert not inbox.exists()
    write_capture(capture, "capture-phone-20260907-071400.txt", "a real thought worth keeping")

    sweep.sweep()

    assert inbox.is_dir()


def test_sweep_handles_missing_capture_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("CAPTURE_DIR", str(tmp_path / "nope"))
    monkeypatch.setenv("INBOX_DIR", str(tmp_path / "inbox"))

    result = sweep.sweep()

    assert result.imported == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/capture/test_sweep.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.capture.sweep'`.

- [ ] **Step 3: Write the implementation**

Create `tools/capture/sweep.py`:

```python
"""Move captures from the capture folder into the inbox.

The sweep is the only part of the system that moves user data, so it is
built to be safe to run repeatedly: files are moved rather than copied,
and content hashes are checked against both the inbox and the archive so
a thought never lands twice.

It makes no judgments. Every note arrives with empty projects and themes
for the command layer to fill in.
"""

import argparse
import collections
import datetime as dt
import re
import sys

from tools.capture import config, frontmatter, naming

MIN_CHARS = 15
TEXT_SUFFIXES = (".txt", ".md")
FILENAME_PATTERN = re.compile(
    r"^capture-(?P<source>[a-z]+)-(?P<date>\d{8})-(?P<time>\d{6})"
)

SweepResult = collections.namedtuple(
    "SweepResult", ["imported", "dropped", "duplicates"]
)


def parse_capture_meta(path):
    """Return (source, datetime) from the filename, falling back to mtime."""
    match = FILENAME_PATTERN.match(path.name)
    if match:
        stamp = "{}{}".format(match.group("date"), match.group("time"))
        try:
            return match.group("source"), dt.datetime.strptime(stamp, "%Y%m%d%H%M%S")
        except ValueError:
            pass
    return "unknown", dt.datetime.fromtimestamp(path.stat().st_mtime)


def _known_hashes():
    """Content hashes of every note already in the inbox or the archive."""
    hashes = set()
    for directory in (config.inbox_dir(), config.archive_dir()):
        if not directory.is_dir():
            continue
        for note in directory.glob("*.md"):
            _, body = frontmatter.parse(note.read_text(encoding="utf-8"))
            hashes.add(naming.body_hash(body))
    return hashes


def _unique_path(inbox, stem):
    candidate = inbox / "{}.md".format(stem)
    counter = 2
    while candidate.exists():
        candidate = inbox / "{}-{}.md".format(stem, counter)
        counter += 1
    return candidate


def sweep():
    """Import every pending capture. Safe to run any number of times."""
    capture = config.capture_dir()
    inbox = config.inbox_dir()
    imported, dropped, duplicates = [], [], []

    if not capture.is_dir():
        return SweepResult(imported, dropped, duplicates)

    inbox.mkdir(parents=True, exist_ok=True)
    hashes = _known_hashes()

    for path in sorted(capture.iterdir()):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue

        body = path.read_text(encoding="utf-8").strip()

        if len(body) < MIN_CHARS:
            dropped.append((path.name, "too short"))
            path.unlink()
            continue

        digest = naming.body_hash(body)
        if digest in hashes:
            duplicates.append(path.name)
            path.unlink()
            continue

        source, captured = parse_capture_meta(path)
        stem = "{}-{}".format(
            captured.strftime("%Y-%m-%d-%H%M"), naming.slugify(body)
        )
        destination = _unique_path(inbox, stem)
        destination.write_text(
            frontmatter.serialize(
                collections.OrderedDict(
                    [
                        ("captured", captured.strftime("%Y-%m-%dT%H:%M")),
                        ("source", source),
                        ("projects", []),
                        ("themes", []),
                        ("status", "raw"),
                    ]
                ),
                body,
            ),
            encoding="utf-8",
        )
        path.unlink()
        hashes.add(digest)
        imported.append(destination)

    return SweepResult(imported, dropped, duplicates)


def main():
    parser = argparse.ArgumentParser(description="Sweep captures into the inbox.")
    parser.parse_args()

    result = sweep()
    print("Imported {} note(s).".format(len(result.imported)))
    for note in result.imported:
        print("  + {}".format(note.name))
    for name, reason in result.dropped:
        print("  - dropped {} ({})".format(name, reason))
    for name in result.duplicates:
        print("  = skipped {} (duplicate)".format(name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/capture/test_sweep.py -v`
Expected: 14 passed.

- [ ] **Step 5: Run the whole suite**

Run: `python3 -m pytest tests/ -v`
Expected: all passed. Nothing in Tasks 1–3 should have regressed.

- [ ] **Step 6: Commit**

```bash
git add tools/capture/sweep.py tests/capture/test_sweep.py
git commit -m "feat: add idempotent capture sweep"
```

---

### Task 5: The laptop capture door

**Files:**
- Create: `tools/capture/capture.py`
- Create: `tests/capture/test_capture.py`

**Interfaces:**
- Consumes: `config.capture_dir()`.
- Produces: `capture.write_capture(text, source="laptop", now=None) -> Path`. Writes a file named `capture-<source>-YYYYMMDD-HHMMSS.txt` that `sweep.parse_capture_meta` can read back. CLI: `python3 -m tools.capture.capture "text"`.

The `now` parameter exists so tests control the timestamp rather than sleeping or mocking the clock.

- [ ] **Step 1: Write the failing test**

Create `tests/capture/test_capture.py`:

```python
import datetime as dt

import pytest

from tools.capture import capture, sweep


@pytest.fixture
def capture_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("CAPTURE_DIR", str(tmp_path / "capture"))
    return tmp_path / "capture"


def test_write_capture_creates_file_with_expected_name(capture_dir):
    path = capture.write_capture(
        "a thought about checklists", now=dt.datetime(2026, 9, 7, 7, 14, 0)
    )

    assert path.name == "capture-laptop-20260907-071400.txt"
    assert path.parent == capture_dir


def test_write_capture_stores_text_verbatim(capture_dir):
    path = capture.write_capture("  spacing   and Caps preserved  ")

    assert path.read_text(encoding="utf-8") == "  spacing   and Caps preserved  "


def test_write_capture_creates_directory_if_missing(capture_dir):
    assert not capture_dir.exists()

    capture.write_capture("a thought worth keeping around")

    assert capture_dir.is_dir()


def test_write_capture_rejects_empty_text(capture_dir):
    with pytest.raises(ValueError):
        capture.write_capture("   ")


def test_capture_filename_is_readable_by_sweep(capture_dir):
    path = capture.write_capture("x", now=dt.datetime(2026, 9, 7, 7, 14, 0))

    source, captured = sweep.parse_capture_meta(path)

    assert source == "laptop"
    assert captured == dt.datetime(2026, 9, 7, 7, 14, 0)


def test_write_capture_avoids_overwriting_same_second(capture_dir):
    stamp = dt.datetime(2026, 9, 7, 7, 14, 0)
    first = capture.write_capture("first thought here", now=stamp)
    second = capture.write_capture("second thought here", now=stamp)

    assert first != second
    assert first.exists() and second.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/capture/test_capture.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.capture.capture'`.

- [ ] **Step 3: Write the implementation**

Create `tools/capture/capture.py`:

```python
"""Write a capture from the laptop.

Deliberately trivial: it drops raw text into the same folder the phone
Shortcut writes to, so both doors converge before the sweep sees them.
"""

import argparse
import datetime as dt
import sys

from tools.capture import config


def write_capture(text, source="laptop", now=None):
    """Write raw text to the capture folder and return the file path."""
    if not text.strip():
        raise ValueError("Refusing to write an empty capture.")

    now = now or dt.datetime.now()
    directory = config.capture_dir()
    directory.mkdir(parents=True, exist_ok=True)

    stem = "capture-{}-{}".format(source, now.strftime("%Y%m%d-%H%M%S"))
    path = directory / "{}.txt".format(stem)
    counter = 2
    while path.exists():
        path = directory / "{}-{}.txt".format(stem, counter)
        counter += 1

    path.write_text(text, encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser(description="Capture a thought.")
    parser.add_argument("text", nargs="+", help="The thought to capture.")
    args = parser.parse_args()

    path = write_capture(" ".join(args.text))
    print("Captured to {}".format(path.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Note: a same-second collision produces `capture-laptop-20260907-071400-2.txt`, which the `FILENAME_PATTERN` regex still matches because it is anchored only at the start. `test_capture_filename_is_readable_by_sweep` covers the base case; the collision case is covered by `test_sweep_avoids_filename_collisions` in Task 4.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/capture/test_capture.py -v`
Expected: 6 passed.

- [ ] **Step 5: Verify the CLI end to end**

```bash
CAPTURE_DIR=/tmp/cap-check python3 -m tools.capture.capture "checklists fail by growing not by being skipped"
ls /tmp/cap-check
CAPTURE_DIR=/tmp/cap-check INBOX_DIR=/tmp/inbox-check python3 -m tools.capture.sweep
cat /tmp/inbox-check/*.md
rm -rf /tmp/cap-check /tmp/inbox-check
```

Expected: the capture file appears, the sweep imports exactly one note, and the note has correct frontmatter with `source: laptop`.

- [ ] **Step 6: Commit**

```bash
git add tools/capture/capture.py tests/capture/test_capture.py
git commit -m "feat: add laptop capture entry point"
```

---

### Task 6: Tagging notes

**Files:**
- Create: `tools/capture/tag.py`
- Create: `tests/capture/test_tag.py`

**Interfaces:**
- Consumes: `frontmatter.parse`, `frontmatter.serialize`, `config.inbox_dir()`.
- Produces: `tag.set_fields(path, projects=None, themes=None, status=None) -> None`. Only the fields passed are changed; `None` means "leave alone". Used by `/review-inbox` to write back clustering results without touching the body.

- [ ] **Step 1: Write the failing test**

Create `tests/capture/test_tag.py`:

```python
import pytest

from tools.capture import frontmatter, tag

NOTE = """---
captured: 2026-09-07T07:14
source: phone
projects: []
themes: []
status: raw
---

The checklist keeps growing.
"""


@pytest.fixture
def note(tmp_path):
    path = tmp_path / "note.md"
    path.write_text(NOTE, encoding="utf-8")
    return path


def test_set_fields_updates_themes(note):
    tag.set_fields(note, themes=["checklist-decay"])

    meta, _ = frontmatter.parse(note.read_text(encoding="utf-8"))
    assert meta["themes"] == ["checklist-decay"]


def test_set_fields_leaves_unspecified_fields_alone(note):
    tag.set_fields(note, themes=["checklist-decay"])

    meta, _ = frontmatter.parse(note.read_text(encoding="utf-8"))
    assert meta["source"] == "phone"
    assert meta["status"] == "raw"
    assert meta["projects"] == []


def test_set_fields_never_touches_the_body(note):
    tag.set_fields(note, projects=["release-ready"], status="used")

    _, body = frontmatter.parse(note.read_text(encoding="utf-8"))
    assert body == "The checklist keeps growing."


def test_set_fields_overwrites_existing_themes(note):
    tag.set_fields(note, themes=["first"])
    tag.set_fields(note, themes=["second", "third"])

    meta, _ = frontmatter.parse(note.read_text(encoding="utf-8"))
    assert meta["themes"] == ["second", "third"]


def test_set_fields_can_clear_themes(note):
    tag.set_fields(note, themes=["first"])
    tag.set_fields(note, themes=[])

    meta, _ = frontmatter.parse(note.read_text(encoding="utf-8"))
    assert meta["themes"] == []


def test_set_fields_rejects_unknown_status(note):
    with pytest.raises(ValueError):
        tag.set_fields(note, status="bogus")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/capture/test_tag.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.capture.tag'`.

- [ ] **Step 3: Write the implementation**

Create `tools/capture/tag.py`:

```python
"""Update frontmatter fields on an existing note.

Used by the review command to write clustering results back without
rewriting the note body, which must stay verbatim.
"""

import argparse
import sys

from tools.capture import frontmatter

VALID_STATUSES = ("raw", "used", "let-go")


def set_fields(path, projects=None, themes=None, status=None):
    """Update only the fields provided. None means leave unchanged."""
    if status is not None and status not in VALID_STATUSES:
        raise ValueError(
            "status must be one of {}, got {!r}".format(VALID_STATUSES, status)
        )

    meta, body = frontmatter.parse(path.read_text(encoding="utf-8"))

    if projects is not None:
        meta["projects"] = list(projects)
    if themes is not None:
        meta["themes"] = list(themes)
    if status is not None:
        meta["status"] = status

    path.write_text(frontmatter.serialize(meta, body), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Tag an inbox note.")
    parser.add_argument("path", help="Path to the note.")
    parser.add_argument("--projects", default=None, help="Comma-separated.")
    parser.add_argument("--themes", default=None, help="Comma-separated.")
    parser.add_argument("--status", default=None, choices=VALID_STATUSES)
    args = parser.parse_args()

    def split(value):
        if value is None:
            return None
        return [item.strip() for item in value.split(",") if item.strip()]

    from pathlib import Path

    set_fields(
        Path(args.path),
        projects=split(args.projects),
        themes=split(args.themes),
        status=args.status,
    )
    print("Tagged {}".format(args.path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/capture/test_tag.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add tools/capture/tag.py tests/capture/test_tag.py
git commit -m "feat: add note tagging for review clustering"
```

---

### Task 7: Promotion and archiving

**Files:**
- Create: `tools/capture/promote.py`
- Create: `tests/capture/test_promote.py`

**Interfaces:**
- Consumes: `config.inbox_dir()`, `config.archive_dir()`, `tag.set_fields`, `frontmatter.parse`.
- Produces: `promote.archive(paths) -> list` of new archive paths, and `promote.list_notes(status="raw") -> list` of `(path, meta, body)` triples sorted by capture time. `/review-inbox` uses `list_notes` to gather material; the drafting step uses `archive` once a draft is written.

- [ ] **Step 1: Write the failing test**

Create `tests/capture/test_promote.py`:

```python
import pytest

from tools.capture import frontmatter, promote


def note_text(captured, status="raw", body="a thought"):
    return frontmatter.serialize(
        {
            "captured": captured,
            "source": "phone",
            "projects": [],
            "themes": [],
            "status": status,
        },
        body,
    )


@pytest.fixture
def inbox(monkeypatch, tmp_path):
    path = tmp_path / "inbox"
    path.mkdir()
    monkeypatch.setenv("INBOX_DIR", str(path))
    return path


def test_archive_moves_note_and_marks_it_used(inbox):
    note = inbox / "a.md"
    note.write_text(note_text("2026-09-07T07:14"), encoding="utf-8")

    moved = promote.archive([note])

    assert not note.exists()
    assert moved[0] == inbox / "archive" / "a.md"
    meta, _ = frontmatter.parse(moved[0].read_text(encoding="utf-8"))
    assert meta["status"] == "used"


def test_archive_preserves_body(inbox):
    note = inbox / "a.md"
    note.write_text(note_text("2026-09-07T07:14", body="verbatim text"), encoding="utf-8")

    moved = promote.archive([note])

    _, body = frontmatter.parse(moved[0].read_text(encoding="utf-8"))
    assert body == "verbatim text"


def test_archive_creates_archive_dir(inbox):
    note = inbox / "a.md"
    note.write_text(note_text("2026-09-07T07:14"), encoding="utf-8")

    promote.archive([note])

    assert (inbox / "archive").is_dir()


def test_archive_handles_name_collision(inbox):
    archive = inbox / "archive"
    archive.mkdir()
    (archive / "a.md").write_text(note_text("2026-01-01T00:00"), encoding="utf-8")
    note = inbox / "a.md"
    note.write_text(note_text("2026-09-07T07:14"), encoding="utf-8")

    moved = promote.archive([note])

    assert moved[0].name == "a-2.md"
    assert len(list(archive.glob("*.md"))) == 2


def test_list_notes_returns_raw_notes_sorted_by_capture_time(inbox):
    (inbox / "b.md").write_text(note_text("2026-09-08T09:00", body="second"), encoding="utf-8")
    (inbox / "a.md").write_text(note_text("2026-09-07T07:14", body="first"), encoding="utf-8")

    notes = promote.list_notes()

    assert [body for _, _, body in notes] == ["first", "second"]


def test_list_notes_excludes_archived_notes(inbox):
    archive = inbox / "archive"
    archive.mkdir()
    (archive / "old.md").write_text(note_text("2026-01-01T00:00", status="used"), encoding="utf-8")
    (inbox / "a.md").write_text(note_text("2026-09-07T07:14"), encoding="utf-8")

    assert len(promote.list_notes()) == 1


def test_list_notes_excludes_let_go_notes(inbox):
    (inbox / "a.md").write_text(note_text("2026-09-07T07:14", status="let-go"), encoding="utf-8")

    assert promote.list_notes() == []


def test_list_notes_on_missing_inbox(monkeypatch, tmp_path):
    monkeypatch.setenv("INBOX_DIR", str(tmp_path / "nope"))

    assert promote.list_notes() == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/capture/test_promote.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'tools.capture.promote'`.

- [ ] **Step 3: Write the implementation**

Create `tools/capture/promote.py`:

```python
"""Read the inbox and archive notes once a draft has used them.

Archiving is how a note stops surfacing in review without being deleted:
provenance for a published post has to stay readable.
"""

import argparse
import sys
from pathlib import Path

from tools.capture import config, frontmatter, tag


def list_notes(status="raw"):
    """Return (path, meta, body) for inbox notes with the given status."""
    inbox = config.inbox_dir()
    if not inbox.is_dir():
        return []

    notes = []
    for path in inbox.glob("*.md"):
        meta, body = frontmatter.parse(path.read_text(encoding="utf-8"))
        if status is None or meta.get("status") == status:
            notes.append((path, meta, body))

    return sorted(notes, key=lambda item: item[1].get("captured", ""))


def archive(paths):
    """Mark notes used and move them into the archive. Returns new paths."""
    destination_dir = config.archive_dir()
    destination_dir.mkdir(parents=True, exist_ok=True)

    moved = []
    for path in paths:
        tag.set_fields(path, status="used")

        destination = destination_dir / path.name
        counter = 2
        while destination.exists():
            destination = destination_dir / "{}-{}{}".format(
                path.stem, counter, path.suffix
            )
            counter += 1

        path.replace(destination)
        moved.append(destination)

    return moved


def main():
    parser = argparse.ArgumentParser(description="Archive notes used by a draft.")
    parser.add_argument("paths", nargs="+", help="Note paths to archive.")
    args = parser.parse_args()

    for destination in archive([Path(p) for p in args.paths]):
        print("Archived {}".format(destination.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/capture/test_promote.py -v`
Expected: 8 passed.

- [ ] **Step 5: Run the whole suite**

Run: `python3 -m pytest tests/ -v`
Expected: 54 passed (4 + 8 + 8 + 14 + 6 + 6 + 8).

- [ ] **Step 6: Commit**

```bash
git add tools/capture/promote.py tests/capture/test_promote.py
git commit -m "feat: add note listing and archiving"
```

---

### Task 8: Slash commands

**Files:**
- Create: `.claude/commands/capture.md`
- Create: `.claude/commands/review-inbox.md`
- Create: `.claude/commands/linkedin.md`

**Interfaces:**
- Consumes: every CLI from Tasks 4–7.
- Produces: the three user-facing entry points. These are prompt files, not code — they hold the judgment work the scripts deliberately avoid.

- [ ] **Step 1: Write the capture command**

Create `.claude/commands/capture.md`:

```markdown
---
description: Capture a raw thought into the inbox
---

Run this immediately, without commentary or follow-up questions:

```bash
python3 -m tools.capture.capture "$ARGUMENTS"
```

Then reply with exactly one short line confirming it was captured.

Do not analyze the thought, ask what project it belongs to, offer to
develop it, or suggest what to do with it. The entire value of this
command is that it costs the user nothing. Capture and get out of the way.
```

- [ ] **Step 2: Write the review command**

Create `.claude/commands/review-inbox.md`:

```markdown
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
```

- [ ] **Step 3: Write the linkedin command**

Create `.claude/commands/linkedin.md`:

```markdown
---
description: Turn an existing draft into a LinkedIn post
---

Read the draft at `$ARGUMENTS` (a path in `posts/drafts/`). If no path is
given, list what is in `posts/drafts/` and ask which one.

Write a LinkedIn version below the draft's existing content, under a
`## LinkedIn` heading, so the long and short forms stay together.

Rules:

- One idea. A LinkedIn post that carries three points carries none.
- Open with the sharpest concrete observation in the draft, not a
  throat-clearing setup line.
- Keep the user's voice. Specific and opinionated beats broadly relatable.
- No hashtag stacks, no "Thoughts? 👇", no engagement bait.
- Aim for 150–250 words.
- End by pointing at the full post on Built and Tested.

Never write a LinkedIn post from raw inbox notes. The long-form piece is
where the thinking gets done; short form is a distillation of finished
thinking, not a shortcut past it.
```

- [ ] **Step 4: Verify the commands are trackable by git**

```bash
git check-ignore -v .claude/commands/capture.md && echo "PROBLEM: ignored" || echo "OK: trackable"
git status --porcelain .claude/commands
```

Expected: not ignored, and all three files show as untracked.

- [ ] **Step 5: Commit**

```bash
git add .claude/commands
git commit -m "feat: add capture, review-inbox, and linkedin commands"
```

---

### Task 9: iOS Shortcut setup and end-to-end verification

**Files:**
- Create: `docs/capture-shortcut-setup.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: the capture folder contract from Task 5 — filename `capture-phone-YYYYMMDD-HHMMSS.txt`, plain text body.
- Produces: nothing consumed by code. This task closes the loop for the user.

The Shortcut cannot be built from here; it is built in the Shortcuts app on the phone. The doc must be precise enough to follow without guessing.

- [ ] **Step 1: Write the setup doc**

Create `docs/capture-shortcut-setup.md`:

```markdown
# Capture Shortcut Setup

The phone door into the capture system. Build once, use for years.

## Before you start

In the Files app, create a folder named `Capture` at the top level of
iCloud Drive. The sweep reads from there.

## Build the Shortcut

Shortcuts app → **+** → name it **Capture**.

Add these five actions in order:

1. **Dictate Text**
   - Language: English
   - Stop Listening: **After Pause**

2. **Text**
   - Content: the `Dictated Text` variable from step 1.
   - (This action exists so step 5 has a clean text input to write.)

3. **Format Date**
   - Date: **Current Date**
   - Format: **Custom**
   - Format String: `yyyyMMdd-HHmmss`

4. **Text**
   - Content: `capture-phone-`, then the `Formatted Date` variable from
     step 3, then `.txt` — all on one line with no spaces.

5. **Save File**
   - File: the `Text` from step 2
   - Service: **iCloud Drive**
   - Destination: `Capture` folder
   - **Ask Where to Save: OFF** ← this is the one that matters. Leave it
     on and the Shortcut stops to ask you a question every single time,
     which defeats the point.
   - **Overwrite If File Exists: OFF**
   - File Name: the `Text` from step 4

## Put it within reach

- **Home screen:** long-press the Shortcut → Share → Add to Home Screen.
- **Action Button** (iPhone 15 Pro and later): Settings → Action Button →
  Shortcut → Capture. This is the fastest path — one press from a locked
  phone, no unlocking to find an icon.
- **Back Tap** (any recent iPhone): Settings → Accessibility → Touch →
  Back Tap → Double Tap → Capture.

## Test it

1. Run the Shortcut and say: "testing the capture shortcut, this is a
   real thought about release checklists."
2. In Files, confirm `capture-phone-<timestamp>.txt` is in iCloud/Capture.
3. On the Mac, wait for iCloud to sync, then run `/review-inbox`.
4. Confirm the note appears with `source: phone` and the right timestamp.

## If a thought comes and the Shortcut feels like too much

Record a plain Voice Memo, or type into Apple Notes. Later, drop the text
into the iCloud `Capture` folder as a `.txt` file. The sweep picks up any
text file in that folder and tags it `source: unknown`. A messy capture
beats a lost thought.

## Troubleshooting

**Nothing appears in the inbox.** Check iCloud has synced — open the
Capture folder in Files on the Mac and confirm the file is there and
fully downloaded, not showing a cloud icon.

**The Shortcut asks where to save.** "Ask Where to Save" is still on in
the Save File action.

**Two notes for one thought.** Not possible — the sweep dedupes on
content, so re-running it is always safe.
```

- [ ] **Step 2: Add a line to the README**

Add this row to the Projects table in `README.md`, after the Knowledge Gatherer row:

```markdown
| [Capture System](./docs/capture-shortcut-setup.md) | Two-door thought capture that turns scattered notes into drafts | 🔨 In progress |
```

- [ ] **Step 3: Run the full test suite**

Run: `python3 -m pytest tests/ -v`
Expected: 54 passed.

- [ ] **Step 4: Verify the real end-to-end path**

This runs against the actual iCloud folder and the actual inbox, not temp dirs:

```bash
mkdir -p ~/Library/Mobile\ Documents/com~apple~CloudDocs/Capture
python3 -m tools.capture.capture "release checklists fail by growing, not by being skipped — nobody ever deletes an item"
python3 -m tools.capture.sweep
cat inbox/*.md
python3 -m tools.capture.sweep   # second run must import nothing
git status --porcelain
```

Expected: one note imported on the first sweep with correct frontmatter
and verbatim body; the second sweep reports `Imported 0 note(s).`; and
`git status` shows nothing under `inbox/`.

- [ ] **Step 5: Clean up the verification note**

```bash
rm inbox/*release-checklists*.md
```

- [ ] **Step 6: Commit**

```bash
git add docs/capture-shortcut-setup.md README.md
git commit -m "docs: add capture Shortcut setup guide"
```

---

## Post-implementation

The system is built when all 54 tests pass and the end-to-end check in
Task 9 succeeds. What it is not yet is *used* — and per the spec's known
risk, the weekly review is the load-bearing habit.

Suggest to the user, but do not build:

- A weekly reminder to run `/review-inbox`. If review keeps not happening,
  the fix is a smaller review (three notes at a time), not more automation.
- After two weeks of real use, revisit whether clustering is producing
  themes that feel true. That is the one part of this system that cannot
  be validated by tests — only by whether the drafts are any good.
