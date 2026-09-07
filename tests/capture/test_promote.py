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
