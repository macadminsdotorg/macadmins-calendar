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

# Issue form label -> events.yaml field. The current form's labels come
# first; the rest are earlier labels, kept so an issue filed before a form
# change still converts when it is approved. full_name and archive are no
# longer on the form (maintainers add them by hand) but are still read from
# older issues.
FIELD_MAP = {
    "Event name": "name",
    "Organizing group (optional)": "organizer",
    "Event type": "type",
    "Date": "start_date",
    "End date (multi-day events only)": "end_date",
    "Location": "location",
    "Event website or sign-up page": "website",
    "Recordings (optional)": "videos",
    "Event language (optional)": "language",
    # Earlier labels
    "Full name (optional)": "full_name",
    "Event website": "website",
    "Start date": "start_date",
    "End date": "end_date",
    "Session videos (optional)": "videos",
    "Documentation archive (optional)": "archive",
}

# Issue form dropdown option -> events.yaml type. Unmapped options fall
# through lowercased so validation flags them on the PR instead of a
# wrong value being merged silently.
TYPE_MAP = {
    "Conference": "conference",
    "Meetup": "meetup",
    "User group": "meetup",  # earlier form option
    "Workshop": "workshop",
    "Webinar": "webinar",
}

# Issue form dropdown option -> ISO 639-1 code, mirroring TYPE_MAP. Kept in
# step with data/languages.yaml; validate_events.py rejects a code that file
# does not carry, so the two cannot drift silently. English is deliberately
# absent: the field marks the exception, and an event with no language is
# English.
LANGUAGE_MAP = {
    "Arabic": "ar",
    "Chinese": "zh",
    "Czech": "cs",
    "Danish": "da",
    "Dutch": "nl",
    "Finnish": "fi",
    "French": "fr",
    "German": "de",
    "Hindi": "hi",
    "Hungarian": "hu",
    "Italian": "it",
    "Japanese": "ja",
    "Korean": "ko",
    "Norwegian": "no",
    "Polish": "pl",
    "Portuguese": "pt",
    "Russian": "ru",
    "Spanish": "es",
    "Swedish": "sv",
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
    "archive",
    "language",
)

# An unanswered optional field renders differently depending on its type:
# a text input gives "_No response_", a dropdown gives "None". Only the
# dropdown-backed fields get the second reading, so a text field whose answer
# is legitimately the word "None" is left alone.
DROPDOWN_FIELDS = ("type", "language")
UNANSWERED = "_No response_"

DATE_RE = re.compile(r'start_date:\s*"?(\d{4}-\d{2}-\d{2})')

URL_FIELDS = ("website", "videos", "archive")


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
        if not value or value == UNANSWERED:
            continue
        if field in DROPDOWN_FIELDS and value == "None":
            continue
        # Single-line fields only; collapse any stray newlines.
        event[field] = " ".join(value.split())
    if event.get("type"):
        event["type"] = TYPE_MAP.get(event["type"], event["type"].lower())
    # An unmapped language falls through as-is so validation flags it on the
    # PR rather than a wrong value being merged silently, same as type.
    if event.get("language"):
        event["language"] = LANGUAGE_MAP.get(event["language"], event["language"].lower())
    for field in URL_FIELDS:
        if event.get(field):
            event[field] = normalize_url(event[field])
    # The form only asks for an end date on multi-day events; a blank one
    # means the event is a single day.
    if event.get("start_date") and not event.get("end_date"):
        event["end_date"] = event["start_date"]
    # Drop a full name or organizer that only repeats the event name, so the
    # card doesn't print the same text twice.
    for field in ("full_name", "organizer"):
        if event.get(field) and event[field].casefold() == event.get("name", "").casefold():
            del event[field]
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


PREVIEW_MARKER = "<!-- event-submission-preview -->"

MONTHS = (
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
)


def style_warnings(event):
    """Advisory notes for things that pass validation but read badly on the
    site. They never block approval."""
    notes = []
    name = event.get("name", "")
    lowered = name.lower()
    if any(re.search(rf"\b{m}\b", lowered) for m in MONTHS) or re.search(r"\b20\d\d\b", name):
        notes.append(
            "The event name contains a month or year. The calendar already shows "
            "the date, so consider removing it."
        )
    location = event.get("location", "")
    if location and location.lower() != "online":
        if re.match(r"^\d", location):
            notes.append(
                "The location looks like a street address. Use the city, region "
                "and country instead, e.g. `Las Vegas, NV, USA`."
            )
        elif "," not in location:
            notes.append(
                "The location has no country. Use `City, Region, Country` "
                "or `Online`."
            )
    if event.get("type") == "meetup" and not event.get("organizer"):
        notes.append(
            "No organizing group is set. If the event name doesn't already say "
            "who runs it, add one."
        )
    return notes


def format_dates(start, end):
    from datetime import date

    try:
        s, e = date.fromisoformat(start), date.fromisoformat(end)
    except ValueError:
        return f"{start} – {end}" if end != start else start
    if s == e:
        return f"{s:%B} {s.day}, {s.year}"
    return f"{s:%B} {s.day} – {e:%B} {e.day}, {e.year}"


def build_preview(body):
    """Return (markdown, ok) describing how the submission would land."""
    import yaml
    from validate_events import load_languages, validate

    event = build_event(parse_issue_body(body))
    errors = []
    for field in ("name", "start_date"):
        if field not in event:
            errors.append(f"Could not read the {field.replace('_', ' ')} from the issue.")

    entry = format_entry(event) if event else ""
    if not errors:
        header, blocks = split_blocks(EVENTS_PATH.read_text())
        if is_duplicate(blocks, event):
            errors.append("An event with this name and start date is already on the calendar.")
        else:
            merged = insert_sorted(header, blocks, entry, event["start_date"])
            all_events = yaml.safe_load(merged)["events"]
            mine = [e for e in all_events if e.get("name") == event["name"]
                    and str(e.get("start_date")) == event["start_date"]]
            errors.extend(
                err.split(": ", 1)[-1] for err in validate(mine, load_languages())
            )

    lines = [PREVIEW_MARKER, "### Calendar preview", ""]
    if event.get("name"):
        title = event.get("full_name") or event["name"]
        meta = [format_dates(event.get("start_date", "?"), event.get("end_date", "?")),
                event.get("location", "(no location)")]
        if event.get("organizer"):
            meta.append(event["organizer"])
        meta.append(event.get("type", "(no type)").upper())
        links = [f"[Website]({event['website']})"] if event.get("website") else []
        if event.get("videos"):
            links.append(f"[Videos]({event['videos']})")
        if event.get("archive"):
            links.append(f"[Archive]({event['archive']})")
        lines += [f"> **{title}**", "> ", "> " + " · ".join(meta)]
        if event.get("language"):
            lines += ["> ", f"> _Language: {event['language']}_"]
        if links:
            lines += ["> ", "> " + "  ".join(links)]
        lines.append("")

    if errors:
        lines += ["**This needs fixing before it can be approved:**", ""]
        lines += [f"- {e}" for e in errors]
    else:
        lines.append("Validation passed.")
    notes = style_warnings(event)
    if notes:
        lines += ["", "**Suggestions** (optional):", ""]
        lines += [f"- {n}" for n in notes]
    lines += [
        "",
        "Edit the issue to change anything; this comment updates automatically.",
        "",
        "<details><summary>events.yaml entry</summary>",
        "",
        "```yaml",
        entry,
        "```",
        "",
        "</details>",
    ]
    return "\n".join(lines) + "\n", not errors


def main():
    body = os.environ.get("ISSUE_BODY")
    if not body:
        print("ISSUE_BODY environment variable is empty", file=sys.stderr)
        return 1

    # --preview writes a Markdown summary for the issue comment and leaves
    # events.yaml untouched. It exits 0 even when the submission has
    # problems; those are reported in the summary.
    if "--preview" in sys.argv[1:]:
        markdown, ok = build_preview(body)
        out = os.environ.get("PREVIEW_PATH")
        if out:
            Path(out).write_text(markdown)
        else:
            print(markdown)
        write_output("valid", "true" if ok else "false")
        return 0

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
