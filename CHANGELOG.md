# Changelog

All notable changes are listed here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [semantic versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-09-27

First public release.

### Added

- Read tools: search events, list a category, event details, timetable, contributions, registration forms and registrations.
- Write tools: create and edit events, sessions, session blocks and contributions; schedule, move and unschedule timetable entries; attach links and files; check in, approve and reject registrations.
- Delete tools for contributions, sessions and events, off unless `INDICO_ALLOW_DELETE` is set.
- Several Indico servers in one process with `INDICO_INSTANCES`, per-instance tokens and an `instance` argument on every tool, which also accepts a URL on the instance's host.
- `indico_list_instances`.
- Read-only mode, restricted upload folder, and a guard against timetable removals that delete data.
- Streamable HTTP transport with per-request tokens.
- Documentation site with tutorials, how-to guides, reference and explanation.

### Fixed

- Event and category results gave times in the Indico server's timezone instead of the event's. They are now converted to the event's timezone. Search results, which Indico gives in UTC, now say so.
- Timezones failed on Windows, which has no system timezone database. The package now depends on `tzdata` there.

[Unreleased]: https://github.com/vuillaut/indico-mcp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/vuillaut/indico-mcp/releases/tag/v0.1.0
