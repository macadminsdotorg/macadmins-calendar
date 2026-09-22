#!/usr/bin/env python3
"""Validate data/events.yaml: required fields, date format, end >= start."""

import re
import sys
from datetime import date, datetime
from pathlib import Path

import yaml

REQUIRED = ("name", "start_date", "end_date", "location", "website", "type")
ALLOWED_TYPES = {"conference", "meetup", "workshop", "webinar"}
URL_FIELDS = ("website", "videos", "archive")
URL_RE = re.compile(r"^https?://\S+$")
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
EVENTS_PATH = DATA_DIR / "events.yaml"
LANGUAGES_PATH = DATA_DIR / "languages.yaml"


def parse_date(value, field, label):
    # datetime is a subclass of date; exclude it so timestamps are rejected.
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ValueError(
            f"{label}: {field} must be a date or YYYY-MM-DD string, got {type(value).__name__}"
        )
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError(
            f"{label}: {field} must be in YYYY-MM-DD format, got {value!r}"
        )


def load_languages():
    """ISO codes from data/languages.yaml, so the form dropdown, the parser's
    LANGUAGE_MAP and the data can't drift apart unnoticed."""
    try:
        with open(LANGUAGES_PATH) as f:
            return set((yaml.safe_load(f) or {}).get("languages", {}))
    except FileNotFoundError:
        return set()


def validate(events, languages=frozenset()):
    if not isinstance(events, list):
        return [f"top-level 'events' must be a list, got {type(events).__name__}"]

    errors = []
    for i, event in enumerate(events):
        label = f"events[{i}]"
        if not isinstance(event, dict):
            errors.append(f"{label}: must be a mapping, got {type(event).__name__}")
            continue
        if event.get("name"):
            label = f"events[{i}] ({event['name']!r})"

        for field in REQUIRED:
            if event.get(field) in (None, ""):
                errors.append(f"{label}: missing required field {field!r}")

        for field in URL_FIELDS:
            value = event.get(field)
            if value and not URL_RE.match(str(value)):
                errors.append(
                    f"{label}: {field} must be an absolute http(s) URL, got {value!r}"
                )

        if event.get("type") and event["type"] not in ALLOWED_TYPES:
            errors.append(
                f"{label}: type {event['type']!r} not in {sorted(ALLOWED_TYPES)}"
            )

        language = event.get("language")
        if language == "en":
            errors.append(
                f"{label}: language \"en\" is redundant — the field marks the "
                f"exception, so omit it for English-language events"
            )
        elif language and languages and language not in languages:
            errors.append(
                f"{label}: language {language!r} is not in languages.yaml; add it "
                f"there (and to LANGUAGE_MAP and the issue form) or fix the code"
            )

        if event.get("start_date") and event.get("end_date"):
            try:
                start = parse_date(event["start_date"], "start_date", label)
                end = parse_date(event["end_date"], "end_date", label)
                if end < start:
                    errors.append(
                        f"{label}: end_date {end} is before start_date {start}"
                    )
            except ValueError as e:
                errors.append(str(e))
    return errors


def main():
    with open(EVENTS_PATH) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "events" not in data:
        print(f"{EVENTS_PATH}: top-level 'events' key missing", file=sys.stderr)
        return 1
    errors = validate(data["events"], load_languages())
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        print(f"\n{len(errors)} error(s) in {EVENTS_PATH}", file=sys.stderr)
        return 1
    print(f"OK: {len(data['events'])} events validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
