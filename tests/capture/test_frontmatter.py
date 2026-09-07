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
