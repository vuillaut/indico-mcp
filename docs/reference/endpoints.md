# Indico endpoints

The Indico URLs each tool calls, relative to the instance address. Use this when a tool breaks after an Indico upgrade: open the same page in your browser and compare.

Kinds:

- **export**: Indico's documented [HTTP export API](https://docs.getindico.io/en/stable/http-api/). Stable.
- **api**: documented JSON API (user, check-in). Stable.
- **rest**: internal JSON endpoint used by Indico's own pages. May change.
- **form**: internal HTML form. The server loads it, changes some fields and submits it. May change.

| Tool | Method and path | Kind |
|---|---|---|
| `indico_whoami` | `GET /api/user/` | api |
| `indico_search_events` | `GET /export/event/search/<query>.json` | export |
| `indico_list_category_events` | `GET /export/categ/<category>.json` | export |
| `indico_get_event` | `GET /export/event/<event>.json` | export |
| `indico_get_timetable` | `GET /export/timetable/<event>.json?nc=yes` | export |
| `indico_list_contributions` | `GET /event/<event>/manage/contributions/contributions.json` | rest |
| `indico_list_registration_forms` | `GET /api/checkin/event/<event>/forms/` | api |
| `indico_list_registrations` | `GET /api/checkin/event/<event>/forms/<form>/registrations/` | api |
| `indico_get_registration` | `GET /api/checkin/event/<event>/forms/<form>/registrations/<reg>` | api |
| `indico_create_event` | `/event/create/<meeting or conference>` | form |
| `indico_update_event` | `/event/<event>/manage/settings/data`, `.../dates`, `.../location` | form |
| `indico_create_session` | `/event/<event>/manage/sessions/create` | form |
| `indico_update_session` | `/event/<event>/manage/sessions/<session>/modify` | form |
| `indico_create_session_block` | `/event/<event>/manage/timetable/add-session-block` | form |
| `indico_update_session_block` | `/event/<event>/manage/timetable/entry/<entry>/edit/` | form |
| `indico_create_contribution` | `/event/<event>/manage/contributions/create`, then the contribution list | form, rest |
| `indico_update_contribution` | `/event/<event>/manage/contributions/<contribution>/edit` | form |
| `indico_assign_contribution_session` | `PATCH /event/<event>/manage/contributions/<contribution>` | rest |
| `indico_schedule_contribution` | `POST /event/<event>/manage/timetable/` | rest |
| `indico_move_timetable_entry` | `PATCH /event/<event>/manage/timetable/<entry>` | rest |
| `indico_unschedule_timetable_entry` | `DELETE /event/<event>/manage/timetable/<entry>` | rest |
| `indico_add_link` | `.../attachments/add/link` on the event, session or contribution | form |
| `indico_upload_file` | `.../attachments/add/files` on the event, session or contribution | form |
| `indico_set_checkin` | `PATCH /api/checkin/event/<event>/forms/<form>/registrations/<reg>` | api |
| `indico_moderate_registration` | `/event/<event>/manage/registration/<form>/registrations/<reg>/approve` or `/reject` | form |
| `indico_delete_contribution` | `DELETE /event/<event>/manage/contributions/<contribution>` | rest |
| `indico_delete_session` | `DELETE /event/<event>/manage/sessions/<session>` | rest |
| `indico_delete_event` | `/event/<event>/manage/delete` | form |

Form and rest calls send `X-Requested-With: XMLHttpRequest`, which makes Indico answer dialogs with JSON instead of a full page. Every call sends the token as `Authorization: Bearer <token>`.
