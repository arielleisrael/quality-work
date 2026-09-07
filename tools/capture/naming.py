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
