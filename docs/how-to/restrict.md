# Limit what the agent can do

An agent with your token can do what you can do on Indico. The server gives you four controls, from strongest to finest.

## Read only

```console
-e INDICO_READ_ONLY=true
```

The server registers only the read tools. The agent cannot change anything, whatever the token allows. Use this whenever you only need to look things up.

For a second layer, give the server a token with only the **Classic API (read only)** scope.

## Deletes

Delete tools are off by default. With `INDICO_ALLOW_DELETE=true` the server adds:

- `indico_delete_contribution`
- `indico_delete_session`
- `indico_delete_event`, which asks for the exact event title, so the agent must read the event before deleting it.

Without that setting, `indico_unschedule_timetable_entry` also refuses removals that delete data. In a meeting, removing a talk from the timetable deletes the talk, because meetings have no list of unscheduled talks. Removing a session block deletes its schedule. Only conferences keep unscheduled talks, so only there does unscheduling work without deletes enabled.

Turn deletes on for a task, then off again.

## Uploads

`indico_upload_file` exists only when you set an upload folder:

```console
-e INDICO_UPLOAD_DIR=~/talks/to-upload
```

The tool refuses any path outside that folder, including `../` tricks and symbolic links leading out. Without the setting, an agent cannot send files from your disk to Indico.

## Client permissions

Most clients ask before each tool call. The tools carry MCP hints the client can use: read tools are marked read-only, and deletes and `indico_unschedule_timetable_entry` are marked destructive. In Claude Code, you can allow the read tools permanently and keep the prompt for the rest.

## Emails

`indico_moderate_registration` makes Indico email the registrant when it approves or rejects a registration, as the web page does. The agent has no tool that sends free-form email.
