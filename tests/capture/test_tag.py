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
