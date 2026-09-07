"""Parse and serialize the capture system's frontmatter.

This is deliberately NOT a YAML implementation. The schema is fixed and
tiny — scalar strings plus three list fields — so a 30-line parser beats
a dependency the user would have to maintain. If the schema ever needs
nesting, quoting, or multi-line values, replace this with PyYAML rather
than growing it.
"""

DELIMITER = "---"
LIST_KEYS = ("projects", "themes", "sources")


def parse(text):
    """Return (meta, body). Missing frontmatter yields ({}, stripped text)."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != DELIMITER:
        return {}, text.strip()

    meta = {}
    body_start = len(lines)
    for index in range(1, len(lines)):
        line = lines[index]
        if line.strip() == DELIMITER:
            body_start = index + 1
            break
        if not line.strip() or ":" not in line:
            continue
        key, _, raw = line.partition(":")
        meta[key.strip()] = _parse_value(raw.strip())

    return meta, "\n".join(lines[body_start:]).strip()


def _parse_value(raw):
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [item.strip() for item in inner.split(",") if item.strip()]
    return raw


def serialize(meta, body):
    """Render meta and body back into a note file."""
    lines = [DELIMITER]
    for key, value in meta.items():
        lines.append("{}: {}".format(key, _render_value(value)))
    lines.append(DELIMITER)
    lines.append("")
    lines.append(body.strip())
    lines.append("")
    return "\n".join(lines)


def _render_value(value):
    if isinstance(value, (list, tuple)):
        return "[{}]".format(", ".join(value))
    return str(value)
