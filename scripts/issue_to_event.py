#!/usr/bin/env python3
"""Convert an event-submission issue form into a data/events.yaml entry.

Reads the issue body from the ISSUE_BODY environment variable, parses the
structured markdown that GitHub renders for issue forms, and inserts the
event into data/events.yaml in start-date order, preserving the file's
formatting. Intended to run from the event-submission workflow.
"""

import json
import os
import re
import sys
from pathlib import Path

EVENTS_PATH = Path(__file__).resolve().parent.parent / "data" / "events.yaml"

# Issue form label -> events.yaml field
FIELD_MAP = {
    "Event name": "name",
    "Full name (optional)": "full_name",
    "Event website": "website",
    "Start date": "start_date",
    "End date": "end_date",
    "Location": "location",
    "Organizing group (optional)": "organizer",
    "Event type": "type",
    "Session videos (optional)": "videos",
}

# Issue form dropdown option -> events.yaml type. Unmapped options fall
# through lowercased so validation flags them on the PR instead of a
# wrong value being merged silently.
TYPE_MAP = {
    "Conference": "conference",
    "Meetup": "meetup",
    "User group": "meetup",
    "Workshop": "workshop",
    "Webinar": "webinar",
}

FIELD_ORDER = (
    "name",
    "full_name",
    "start_date",
    "end_date",
    "location",
    "organizer",
    "website",
    "type",
    "videos",
)

DATE_RE = re.compile(r'start_date:\s*"?(\d{4}-\d{2}-\d{2})')

URL_FIELDS = ("website", "videos")


def normalize_url(value):
    """Prefix a bare host such as 'macadmins.psu.edu' with 'https://'.

    A scheme-relative '//host/path' keeps its path but gains 'https:'. Values
    that already carry a scheme are returned untouched.
    """
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", value):
        return value
    if value.startswith("//"):
        return f"https:{value}"
    return f"https://{value.lstrip('/')}"


def parse_issue_body(body):
    """Parse '### Label\n\nvalue' sections into a dict of stripped values."""
    sections = {}
    current = None
    for line in body.splitlines():
        heading = re.match(r"^### (.+)$", line)
        if heading:
            current = heading.group(1).strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return {label: "\n".join(lines).strip() for label, lines in sections.items()}


def build_event(sections):
    event = {}
    for label, field in FIELD_MAP.items():
        value = sections.get(label, "")
        if not value or value == "_No response_":
            continue
        # Single-line fields only; collapse any stray newlines.
        event[field] = " ".join(value.split())
    if event.get("type"):
        event["type"] = TYPE_MAP.get(event["type"], event["type"].lower())
    for field in URL_FIELDS:
        if event.get(field):
            event[field] = normalize_url(event[field])
    return event


def format_entry(event):
    lines = []
    for field in FIELD_ORDER:
        if field not in event:
            continue
        prefix = "  - " if not lines else "    "
        # JSON string escaping is valid YAML double-quoted style, matching
        # the house format of the file.
        lines.append(f"{prefix}{field}: {json.dumps(event[field], ensure_ascii=False)}")
    return "\n".join(lines)


def split_blocks(text):
    head, sep, body = text.partition("events:\n")
    if not sep:
        raise ValueError(f"{EVENTS_PATH}: top-level 'events:' key not found")
    return head + sep, re.split(r"\n{2,}", body.strip("\n"))


def is_duplicate(blocks, event):
    name_line = f"name: {json.dumps(event['name'], ensure_ascii=False)}"
    date_line = f'start_date: "{event["start_date"]}"'
    return any(name_line in block and date_line in block for block in blocks)


def insert_sorted(header, blocks, entry_text, start_date):
    insert_at = len(blocks)
    for i, block in enumerate(blocks):
        match = DATE_RE.search(block)
        if match and match.group(1) > start_date:
            insert_at = i
            break
    blocks.insert(insert_at, entry_text)
    return header + "\n\n".join(blocks) + "\n"


def write_output(name, value):
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a") as f:
            f.write(f"{name}={value}\n")


def main():
    body = os.environ.get("ISSUE_BODY")
    if not body:
        print("ISSUE_BODY environment variable is empty", file=sys.stderr)
        return 1

    event = build_event(parse_issue_body(body))
    missing = [f for f in ("name", "start_date") if f not in event]
    if missing:
        print(
            f"could not parse required field(s) from issue body: {missing}",
            file=sys.stderr,
        )
        return 1

    header, blocks = split_blocks(EVENTS_PATH.read_text())
    if is_duplicate(blocks, event):
        print(
            f"event {event['name']!r} starting {event['start_date']} already exists",
            file=sys.stderr,
        )
        return 1

    EVENTS_PATH.write_text(
        insert_sorted(header, blocks, format_entry(event), event["start_date"])
    )
    write_output("name", event["name"].replace("\n", " "))
    print(f"added {event['name']!r} ({event['start_date']}) to {EVENTS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
