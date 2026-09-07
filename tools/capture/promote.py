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
