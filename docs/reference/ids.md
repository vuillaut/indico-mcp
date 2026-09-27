# Ids

Indico gives one object several numbers. The tools say which one they take; this page says where to find it.

| Id | Identifies | Where you find it | Taken by |
|---|---|---|---|
| event id | an event | the event address `/event/<id>/`; `id` in search and category results | every event tool, as `event_id` |
| category id | a category | the address `/category/<id>/`; `category_id` in event results | `indico_list_category_events`, `indico_create_event` |
| contribution id (database) | a talk | `contribution_id` in the timetable; `id` in `indico_list_contributions`; `db_id` in `indico_get_event`; the address `/contributions/<id>/` | contribution tools, `indico_add_link`, `indico_upload_file` |
| public contribution number | a talk, as shown on conference pages | `public_id` in the timetable and contribution list; `id` in `indico_get_event` | no tool; for display only |
| session id | a session, such as "Higgs Physics" | `session_id` in the timetable | session tools, `indico_assign_contribution_session` |
| session block id | one time slot of a session | `session_block_id` in the timetable; returned by `indico_create_session_block` | `indico_schedule_contribution` |
| timetable entry id | a slot in the timetable: a talk, a block or a break | `entry_id` in the timetable | `indico_move_timetable_entry`, `indico_unschedule_timetable_entry`, `indico_update_session_block` |
| registration form id | a registration form | `indico_list_registration_forms` | registration tools, as `form_id` |
| registration id | one registrant | `indico_list_registrations` | `indico_get_registration`, `indico_set_checkin`, `indico_moderate_registration` |

## The trap

`indico_get_event` uses Indico's export API, which calls the public number `id` and the database id `db_id`. Everywhere else, `id` or `contribution_id` is the database id. Management tools always take the database id.

## Example

The talk "Measurements of the Higgs boson mass with the ATLAS detector" at ICHEP 2024 on indico.cern.ch:

| Id | Value |
|---|---|
| event id | 1291157 |
| contribution id | 5888282 |
| public number | 495 |
| session id ("Higgs Physics") | 542907 |
| session block id | 560058 |
| timetable entry id | 6525026 |
| parent entry id (the block's entry) | 6477312 |
