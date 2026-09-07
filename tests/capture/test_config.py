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
