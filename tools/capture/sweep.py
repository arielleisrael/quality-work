"""Move captures from the capture folder into the inbox.

The sweep is the only part of the system that moves user data, so it is
built to be safe to run repeatedly: files are moved rather than copied,
and content hashes are checked against both the inbox and the archive so
a thought never lands twice.

It makes no judgments. Every note arrives with empty projects and themes
for the command layer to fill in.
"""

import argparse
import collections
import datetime as dt
import re
import sys

from tools.capture import config, frontmatter, naming

MIN_CHARS = 15
TEXT_SUFFIXES = (".txt", ".md")
FILENAME_PATTERN = re.compile(
    r"^capture-(?P<source>[a-z]+)-(?P<date>\d{8})-(?P<time>\d{6})"
)

SweepResult = collections.namedtuple(
    "SweepResult", ["imported", "dropped", "duplicates"]
)


def parse_capture_meta(path):
    """Return (source, datetime) from the filename, falling back to mtime."""
    match = FILENAME_PATTERN.match(path.name)
    if match:
        stamp = "{}{}".format(match.group("date"), match.group("time"))
        try:
            return match.group("source"), dt.datetime.strptime(stamp, "%Y%m%d%H%M%S")
        except ValueError:
            pass
    return "unknown", dt.datetime.fromtimestamp(path.stat().st_mtime)


def _known_hashes():
    """Content hashes of every note already in the inbox or the archive."""
    hashes = set()
    for directory in (config.inbox_dir(), config.archive_dir()):
        if not directory.is_dir():
            continue
        for note in directory.glob("*.md"):
            _, body = frontmatter.parse(note.read_text(encoding="utf-8"))
            hashes.add(naming.body_hash(body))
    return hashes


def _unique_path(inbox, stem):
    candidate = inbox / "{}.md".format(stem)
    counter = 2
    while candidate.exists():
        candidate = inbox / "{}-{}.md".format(stem, counter)
        counter += 1
    return candidate


def sweep():
    """Import every pending capture. Safe to run any number of times."""
    capture = config.capture_dir()
    inbox = config.inbox_dir()
    imported, dropped, duplicates = [], [], []

    if not capture.is_dir():
        return SweepResult(imported, dropped, duplicates)

    inbox.mkdir(parents=True, exist_ok=True)
    hashes = _known_hashes()

    for path in sorted(capture.iterdir()):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue

        body = path.read_text(encoding="utf-8").strip()

        if len(body) < MIN_CHARS:
            dropped.append((path.name, "too short"))
            path.unlink()
            continue

        digest = naming.body_hash(body)
        if digest in hashes:
            duplicates.append(path.name)
            path.unlink()
            continue

        source, captured = parse_capture_meta(path)
        stem = "{}-{}".format(
            captured.strftime("%Y-%m-%d-%H%M"), naming.slugify(body)
        )
        destination = _unique_path(inbox, stem)
        destination.write_text(
            frontmatter.serialize(
                collections.OrderedDict(
                    [
                        ("captured", captured.strftime("%Y-%m-%dT%H:%M")),
                        ("source", source),
                        ("projects", []),
                        ("themes", []),
                        ("status", "raw"),
                    ]
                ),
                body,
            ),
            encoding="utf-8",
        )
        path.unlink()
        hashes.add(digest)
        imported.append(destination)

    return SweepResult(imported, dropped, duplicates)


def main():
    parser = argparse.ArgumentParser(description="Sweep captures into the inbox.")
    parser.parse_args()

    result = sweep()
    print("Imported {} note(s).".format(len(result.imported)))
    for note in result.imported:
        print("  + {}".format(note.name))
    for name, reason in result.dropped:
        print("  - dropped {} ({})".format(name, reason))
    for name in result.duplicates:
        print("  = skipped {} (duplicate)".format(name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
