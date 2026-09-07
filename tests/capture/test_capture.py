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
