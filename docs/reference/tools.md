# Tools

This page is generated from the server code by `scripts/gen_tools_reference.py`. Do not edit it by hand.

Every tool also takes `instance`; see [Configuration](configuration.md#choosing-an-instance).
Times are local to the event's timezone, written like `2026-10-05T14:30`.

| Group | Registered when |
|---|---|
| Read | always |
| Write | `INDICO_READ_ONLY` is not set |
| Delete | `INDICO_ALLOW_DELETE=true` |

`indico_upload_file` also needs `INDICO_UPLOAD_DIR`.

## Read

### `indico_list_instances`

List the Indico instances this server can reach; pass a name as `instance` to the other tools.

### `indico_whoami`

Return the Indico user the token belongs to (null when anonymous).

### `indico_search_events`

Search events by title. Only returns events the token's user can see.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `query` | string | required | Words from the event title |
| `from_date` | string | `null` | YYYY-MM-DD, 'today', or relative like '-30d' |
| `to_date` | string | `null` | YYYY-MM-DD, 'today', or relative like '+30d' |
| `limit` | integer | `50` | (1 to 500) |

### `indico_list_category_events`

List events in a category (and its subcategories) within a date range.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `category_id` | integer | required | Category id; 0 is the root, covering the whole instance |
| `from_date` | string | `"today"` | YYYY-MM-DD, 'today', or relative like '-30d' |
| `to_date` | string | `null` | YYYY-MM-DD, 'today', or relative like '+30d' |
| `limit` | integer | `50` | (1 to 500) |
| `newest_first` | boolean | `false` |  |

### `indico_get_event`

Get an event's details: dates, location, chairs, material, and optionally contributions or sessions.

In the contributions list, `id` is the public number and `db_id` is the id management tools need.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |
| `detail` | `events` / `contributions` / `subcontributions` / `sessions` | `"contributions"` | How much to include: 'events' is metadata only |

### `indico_get_timetable`

Get an event's timetable as a flat list of entries in start order.

Each entry has `entry_id` (for indico_move_timetable_entry / indico_unschedule_timetable_entry),
and depending on its kind `contribution_id`, `session_id`, `session_block_id`, `parent_entry_id`.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |

### `indico_list_contributions`

List all contributions of an event with database ids, session, schedule and people.

Needs management rights on the event.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |

### `indico_list_registration_forms`

List an event's registration forms with registration counts. Needs the 'Registrants' token scope.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |

### `indico_list_registrations`

List registrations of a registration form (state, payment, check-in, tags).

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |
| `form_id` | integer | required |  |

### `indico_get_registration`

Get one registration, including the answers to the form fields.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |
| `form_id` | integer | required |  |
| `registration_id` | integer | required |  |

## Write

### `indico_create_event`

Create a meeting or conference and return its id.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `category_id` | integer | required | Category to create the event in |
| `title` | string | required |  |
| `start` | string | required | Local time in the event's timezone, ISO format without offset, e.g. 2026-10-05T14:30 |
| `end` | string | required | Local time in the event's timezone, ISO format without offset, e.g. 2026-10-05T14:30 |
| `timezone` | string | required | IANA timezone, e.g. Europe/Zurich or Europe/Paris |
| `event_type` | `meeting` / `conference` | `"meeting"` |  |
| `venue_name` | string | `""` |  |
| `room_name` | string | `""` |  |
| `address` | string | `""` |  |
| `listed` | boolean | `true` | Show the event in the category listing |
| `protection_mode` | `inheriting` / `public` / `protected` | `"inheriting"` |  |

### `indico_update_event`

Change an event's title, description, dates or location. Fields left out keep their value.

Changing dates also shifts the timetable, as the Indico UI does by default.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |
| `title` | string | `null` |  |
| `description` | string | `null` | HTML allowed |
| `start` | string | `null` |  |
| `end` | string | `null` |  |
| `timezone` | string | `null` | IANA timezone |
| `venue_name` | string | `null` |  |
| `room_name` | string | `null` |  |
| `address` | string | `null` |  |

### `indico_create_session`

Create a session. It has no time slot until you add one with indico_create_session_block.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |
| `title` | string | required |  |
| `description` | string | `null` |  |
| `code` | string | `null` | Book of abstracts code; conferences only |
| `default_contribution_minutes` | integer | `null` |  |

### `indico_update_session`

Change a session's title, description, code or default contribution length.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |
| `session_id` | integer | required |  |
| `title` | string | `null` |  |
| `description` | string | `null` |  |
| `code` | string | `null` |  |
| `default_contribution_minutes` | integer | `null` |  |

### `indico_create_session_block`

Add a time slot (session block) for a session to the timetable; contributions of the session go inside it.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |
| `session_id` | integer | required |  |
| `start` | string | required | Local time in the event's timezone, ISO format without offset, e.g. 2026-10-05T14:30 |
| `duration_minutes` | integer | required | (at least 1) |
| `title` | string | `""` | Optional block title, e.g. 'Part 1' |

### `indico_update_session_block`

Change a session block's duration or title. It cannot become shorter than the entries inside it.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |
| `entry_id` | integer | required | The block's timetable entry id (see indico_get_timetable) |
| `duration_minutes` | integer | `null` |  |
| `title` | string | `null` |  |

### `indico_create_contribution`

Create an unscheduled contribution. Use indico_schedule_contribution to place it in the timetable.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |
| `title` | string | required |  |
| `description` | string | `null` |  |
| `duration_minutes` | integer | `null` |  |
| `persons` | list of Person | `null` |  |
| `session_id` | integer | `null` | Assign to this session right away |

### `indico_update_contribution`

Change a contribution's title, description, duration or people. Fields left out keep their value.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |
| `contribution_id` | integer | required | Database id (see indico_list_contributions) |
| `title` | string | `null` |  |
| `description` | string | `null` |  |
| `duration_minutes` | integer | `null` |  |
| `persons` | list of Person | `null` | Replaces the whole list of speakers/authors when given |

### `indico_assign_contribution_session`

Move a contribution into a session, or out of it. Indico may unschedule it if its slot no longer fits.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |
| `contribution_id` | integer | required |  |
| `session_id` | integer | required | null removes the contribution from its session |

### `indico_schedule_contribution`

Put an unscheduled contribution in the timetable at a given time.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |
| `contribution_id` | integer | required |  |
| `start` | string | required | Local time in the event's timezone, ISO format without offset, e.g. 2026-10-05T14:30 |
| `session_block_id` | integer | `null` | Put it inside this session block; required if the contribution is in a session |

### `indico_move_timetable_entry`

Change the start time of a timetable entry (contribution or session block).

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |
| `entry_id` | integer | required |  |
| `start` | string | required | Local time in the event's timezone, ISO format without offset, e.g. 2026-10-05T14:30 |

### `indico_unschedule_timetable_entry`

Remove an entry from the timetable.

In a conference, a contribution goes back to the unscheduled list. Anything else deletes data:
in meetings the contribution itself is deleted, and a session block is deleted with its schedule.
Those cases are refused unless the server runs with INDICO_ALLOW_DELETE=true.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |
| `entry_id` | integer | required |  |

### `indico_add_link`

Attach a link (slides, recording, document) to an event, a session or a contribution.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |
| `url` | string | required |  |
| `title` | string | required |  |
| `contribution_id` | integer | `null` | Attach to this contribution |
| `session_id` | integer | `null` | Attach to this session |

### `indico_set_checkin`

Mark a registrant as checked in at the venue, or undo it.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |
| `form_id` | integer | required |  |
| `registration_id` | integer | required |  |
| `checked_in` | boolean | required |  |

### `indico_moderate_registration`

Approve or reject a pending registration. Indico emails the registrant either way.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |
| `form_id` | integer | required |  |
| `registration_id` | integer | required |  |
| `action` | `approve` / `reject` | required |  |
| `reason` | string | `""` | Rejection reason, kept in Indico |
| `send_reason` | boolean | `false` | Include the reason in the rejection email |

### `indico_upload_file`

Upload a file as material of an event, a session or a contribution. Only files inside INDICO_UPLOAD_DIR can be uploaded.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |
| `file_path` | string | required | Path of the file, inside the upload directory |
| `contribution_id` | integer | `null` | Attach to this contribution |
| `session_id` | integer | `null` | Attach to this session |

## Delete

### `indico_delete_contribution`

Delete a contribution, with its timetable entry and material.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |
| `contribution_id` | integer | required |  |

### `indico_delete_session`

Delete a session and its blocks. Its contributions stay, unscheduled and without a session.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |
| `session_id` | integer | required |  |

### `indico_delete_event`

Delete a whole event. Only an Indico admin can restore it.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `event_id` | integer | required | Indico event id (the number in /event/&lt;id&gt;/) |
| `confirm_title` | string | required | The event's exact title, as a safety check |

## Person

A speaker or author, entered by name; Indico links an existing account by email.

| Field | Type | Default |
|---|---|---|
| `first_name` | string | `""` |
| `last_name` | string | required |
| `email` | string | `""` |
| `affiliation` | string | `""` |
| `speaker` | boolean | `true` |
| `author_type` | `none` / `primary` / `secondary` | `"none"` |
