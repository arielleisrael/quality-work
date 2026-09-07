"""Write a capture from the laptop.

Deliberately trivial: it drops raw text into the same folder the phone
Shortcut writes to, so both doors converge before the sweep sees them.
"""

import argparse
import datetime as dt
import sys

from tools.capture import config


def write_capture(text, source="laptop", now=None):
    """Write raw text to the capture folder and return the file path."""
    if not text.strip():
        raise ValueError("Refusing to write an empty capture.")

    now = now or dt.datetime.now()
    directory = config.capture_dir()
    directory.mkdir(parents=True, exist_ok=True)

    stem = "capture-{}-{}".format(source, now.strftime("%Y%m%d-%H%M%S"))
    path = directory / "{}.txt".format(stem)
    counter = 2
    while path.exists():
        path = directory / "{}-{}.txt".format(stem, counter)
        counter += 1

    path.write_text(text, encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser(description="Capture a thought.")
    parser.add_argument("text", nargs="+", help="The thought to capture.")
    args = parser.parse_args()

    path = write_capture(" ".join(args.text))
    print("Captured to {}".format(path.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
