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
