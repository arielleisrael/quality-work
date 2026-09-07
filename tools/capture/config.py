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
