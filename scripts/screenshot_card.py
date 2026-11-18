#!/usr/bin/env python3
"""Screenshot an event's card on the macadmins.org submit page.

Usage: screenshot_card.py URL OUTPUT.png

URL is the submit page with the submission's answers in the query string
(issue_to_event.py --card-url). The page fills its form in from them and
renders the card in #p-timeline. Exits non-zero, writing nothing, if the
page didn't fill the form in (for example before macadmins.org supports
it), so the preview workflow can carry on without an image.
"""

import sys
from urllib.parse import parse_qs, urlparse

from playwright.sync_api import sync_playwright


def main():
    url, out = sys.argv[1:3]
    expected_name = parse_qs(urlparse(url).query).get("name", [""])[0]
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 900, "height": 900}, device_scale_factor=2)
        page.goto(url, wait_until="networkidle", timeout=30000)
        # A page that ignored the query string would show a placeholder card.
        if page.input_value("#f-name").strip() != expected_name.strip():
            print("The submit page didn't fill the form in from the link; no screenshot.", file=sys.stderr)
            return 2
        card = page.wait_for_selector("#p-timeline .timeline__item", timeout=10000)
        card.screenshot(path=out)
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
