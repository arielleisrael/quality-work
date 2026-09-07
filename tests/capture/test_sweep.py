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
