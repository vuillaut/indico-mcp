# Safety model

Giving an agent your Indico token is giving it your Indico account. The server can't make the agent careful, but it can decide which actions exist and make the dangerous ones harder. This page describes what it does and where it stops.

## What the server controls

**Which tools exist.** Tools that are not registered cannot be called. `INDICO_READ_ONLY` removes all writes. Deletes need `INDICO_ALLOW_DELETE`. File uploads need `INDICO_UPLOAD_DIR`. The defaults (writes on, deletes off, uploads off) suit someone building agendas at their desk. For anything else, start from read-only.

**Hidden deletes.** Some actions delete data without saying so. In an Indico meeting, removing a talk from the timetable deletes the talk, because meetings have no list of unscheduled talks. Removing a session block deletes its schedule. `indico_unschedule_timetable_entry` checks the event type and the entry kind first, and refuses these cases unless deletes are enabled. Its result says `deleted_data: true` when it did delete something.

**Deleting a whole event** needs the exact title as `confirm_title`. An agent that has the wrong event id in mind fails the check instead of deleting the wrong event.

**Local files.** `indico_upload_file` resolves the path, following symbolic links, and refuses anything outside the upload folder. Without the setting, the tool does not exist.

**Tokens.** Each instance's token goes only to that instance's host. The server never returns a token in a tool result. In HTTP mode, the generic token headers are ignored when several instances are configured, so a client can't send its CERN token to another Indico by mistake.

**Edits that keep data.** Form edits load the current values first and change only what was asked (see [How it works](how-it-works.md#writes-go-through-the-web-forms)). An unknown field aborts the edit before anything is sent.

## What the server does not control

- **Your rights on Indico.** If your account manages a conference, the agent can rename it, reschedule it or reject its registrations. Scope the token, or use read-only mode.
- **Emails Indico sends.** Approving or rejecting a registration makes Indico email the registrant. The tool description warns the agent, but once the call is made, the email is gone.
- **What the agent decides.** The server cannot tell a sensible request from a mistaken one. Keep your client's per-call approval on for write tools.
- **Access to the HTTP port.** In HTTP mode there is no login. See [Run the server over HTTP](../how-to/http-server.md#expose-it-safely).

## Reporting a problem

See [SECURITY.md](https://github.com/vuillaut/indico-mcp/blob/main/SECURITY.md) for how to report a vulnerability privately.
