# Mac Admin Conferences Calendar

A Hugo-powered static website for tracking Mac Admin conferences, meetups, and events worldwide. This site aims to provide an easy and dynamically updated resource for community members to reference major industry events.

## Subscribe

The site publishes an iCalendar feed at [`/events.ics`](https://homebysix.github.io/macadmins-calendar/events.ics) that can be subscribed to from Apple Calendar, Google Calendar, Outlook, and most other calendar clients. Events update automatically as the feed is regenerated.

## Development

Requires [Hugo](https://gohugo.io/installation/) (v0.100.0 or later).

1. Clone the repository:
   ```bash
   git clone https://github.com/homebysix/macadmins-calendar.git
   cd macadmins-calendar
   ```

2. Start the development server:
   ```bash
   hugo server -D
   ```

3. Open your browser to `http://localhost:1313`

## Contributing

Events are stored in `data/events.yaml`. This repository is the source of truth for the community calendar — [macadmins.org](https://macadmins.org/calendar/) fetches `events.yaml` from here on every site build, so events must be added here to appear on the site.

There are two ways to add an event; please ensure it meets our event eligibility criteria below.

### Submitting via the event form (easiest)

Fill in the [event submission form](https://github.com/macadminsdotorg/macadmins-calendar/issues/new?template=event-submission.yml) (also linked from [macadmins.org/calendar/submit](https://macadmins.org/calendar/submit/)). A Mac Admins Foundation volunteer will review it, and approved events are added automatically — no git knowledge required.

### Event Eligibility

Events that are a good fit for this calendar:

- Broadly relevant to the Mac admin community, or relevant to specific subgroups (e.g. geographic regions or customers of specific vendors)
- Offer high-quality technical or professionally relevant content
- Either in-person or virtual live events
- Either free or paid, but welcoming of all attendees

Events that will not be a good fit include:

- Sales pitches and non-technical product presentations
- Invite-only events
- Pre-recorded events

### Adding events by pull request

1. Fork the repository
2. Edit `data/events.yaml`
3. Add your event using this format:

    ```yaml
    - name: "Conference Name"
      full_name: "Longer More Descriptive Conference Name"  # optional
      start_date: "2025-07-15"
      end_date: "2025-07-18"
      location: "City, State/Province, Country"
      website: "https://example.com"
      type: "conference"
      videos: "https://youtube.com/channel"  # optional
      language: "en"                         # optional
    ```

4. Submit a pull request

Pull requests are automatically validated for required fields, date format, and `end_date >= start_date`. To check locally, run `python scripts/validate_events.py` (or use [pre-commit](https://pre-commit.com)).

### Event Fields

- **name**: Conference/event name (required)
- **full_name**: Longer, more descriptive conference name (optional)
- **start_date**: Start date in YYYY-MM-DD format (required)
- **end_date**: End date in YYYY-MM-DD format, same as start_date for single-day events (required)
- **location**: City, State/Province, Country (required)
- **website**: Official website URL (required)
- **type**: Event type (`conference`, `meetup`, `workshop`, `webinar`) (required)
- **videos**: Video archive/YouTube channel URL (optional)
- **archive**: Archive/documentation URL (optional)
- **language**: Primary language code if not English, e.g. "en", "de", "fr" (optional)

**Note**: Event status (upcoming/past) is calculated automatically based on dates.

## For Maintainers

### Reviewing form submissions

Form submissions arrive as issues labeled `event-submission`. To process one:

1. Check the event against the eligibility criteria above. If it isn't a fit, close the issue with a short comment.
2. If it's a fit, add the **`approved`** label. The [event-submission workflow](.github/workflows/event-submission.yml) then parses the form, inserts the event into `data/events.yaml` in date order, opens a pull request, and closes the issue with a link to it. (If the PR ends up rejected, reopen the issue.)
3. Review the PR diff and merge it. The event appears on macadmins.org after the site's next build (daily, or trigger the site repo's deploy workflow manually).

Things to know:

- The PR body reports whether `validate_events.py` passed. The separate "Validate events.yaml" status check does not run on these auto-created PRs (a GitHub limitation for PRs opened with the default workflow token), so check the PR body.
- An event type of "Other" deliberately fails validation — edit the PR branch to set a valid type (`conference`, `meetup`, `workshop`, `webinar`) before merging.
- Re-approving an event that already exists (same name and start date) makes the workflow fail rather than add a duplicate.
- The `event-submission` and `approved` labels must exist in the repository. GitHub silently skips issue-form labels that haven't been created.
- Submissions also come in via the [#macadminsfoundation](https://macadmins.slack.com/archives/C03G27DCDC4) Slack channel; add those to `data/events.yaml` by pull request, or file the issue form on the submitter's behalf and use the flow above.

## Deployment

This site supports automated deployment with GitHub Pages, including daily rebuilds to automatically update event status (past/upcoming).

## License

Copyright 2026 Elliot Jordan

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
