# Design choices

## Times are local to the event

Indico stores each event in a timezone, and people think in it: a CERN meeting at 14:00 means 14:00 in Geneva. The tools take and return times in the event's timezone, written without an offset (`2026-10-05T14:30`).

This needs some work behind the scenes. Indico's export API returns event and category times in the server's own timezone, which is `Europe/Zurich` on indico.cern.ch whatever the event's timezone. A meeting in São Paulo at 10:00 comes back as 15:00. The server converts those times to the event's timezone before returning them. The timetable export already uses the event's timezone.

Search is the exception. Indico's search returns times in UTC without the event's timezone, so search results say `"timezone": "UTC"`. The agent can call `indico_get_event` for local times.

When a tool takes a time, it refuses one with an offset. `2026-10-05T14:30+02:00` could disagree with the event's timezone, and the server would rather fail than pick one.

## Ids are passed through as they are

Indico has several ids per talk (see [Ids](../reference/ids.md)). The server could hide them behind titles, but titles are not unique and an agent matching by title will sooner or later edit the wrong talk. So the tools take Indico's ids, the read tools return them with clear names (`contribution_id`, `entry_id`), and the tool descriptions say which one each tool expects.

One tool has to guess. Indico does not return the id of a contribution it just created, so `indico_create_contribution` reads the contribution list and takes the newest one with that title.

## One process, several instances

Early versions served one Indico per process. That works, but an agent then sees the same 29 tools two or three times under different server names, and a physicist who uses CERN's and their lab's Indico has to configure both. Now one process can serve several instances, and each tool takes an `instance` argument.

Accepting any URL on the instance's host as `instance` is deliberate. Users paste event links, and the agent can pass the link without first matching it to a name.

With several instances and no default, a call that leaves out `instance` fails. Guessing would be convenient for reads and dangerous for writes, and one rule for both is simpler to reason about.

Settings like read-only apply to the whole process, not per instance. Per-instance rights would need per-instance tool lists, which MCP clients don't show well. Two server entries do the same job and are easy to understand.

## Not covered yet

- Protection and access lists. They need signed user identifiers from Indico's user search.
- Abstracts, paper reviewing, surveys and room booking.
- Editing event chairpersons and contact information.
- Creating lectures, which need a list of occurrences.

Contributions are welcome; see [Develop and contribute](../how-to/develop.md).
