# Build a meeting agenda

In this tutorial you give the server a personal token and let Claude build a small meeting on indico.cern.ch: create the event, add three talks with speakers, schedule them, then move one. You finish by deleting the test meeting.

It follows [Explore a conference on CERN's Indico](explore-cern.md). You need the `indico-cern` server from that tutorial.

!!! warning "Use a test event"
    The write tools use Indico's internal web endpoints, and they have been tested against recorded Indico responses, not on every Indico version. Run this tutorial on a throwaway meeting, never on a real event. [How it works](../explanation/how-it-works.md) explains why.

## Before you start

You need:

- a CERN account;
- a category on indico.cern.ch where you can create events. Most groups have one; your group's Indico manager can tell you. Open the category page: its id is the number in the address, `https://indico.cern.ch/category/<id>/`.

The same steps work on any other Indico. Replace `https://indico.cern.ch` with your server's address.

## Step 1: create a personal token

1. Log in to [indico.cern.ch](https://indico.cern.ch).
2. Open your profile menu, then **My profile → Personal Tokens**.
3. Click **Create new token**, name it `indico-mcp`, and tick these scopes:
    - **Everything (all methods)**, needed by every write tool;
    - **User information**, so Claude can check who it acts as.
4. Save and copy the token. It starts with `indp_`. Indico shows it only once.

The token acts with your account's rights. Anything you can do on Indico, an agent holding it can do. Keep it out of shared files and git.

## Step 2: give the token to the server

Replace the read-only server from the first tutorial:

```console
$ claude mcp remove indico-cern
$ claude mcp add indico-cern \
    -e INDICO_URL=https://indico.cern.ch \
    -e INDICO_TOKEN=indp_your_token_here \
    -- uvx --from git+https://github.com/vuillaut/indico-mcp indico-mcp
```

`INDICO_READ_ONLY` is gone, so the write tools appear. Delete tools stay hidden: they need `INDICO_ALLOW_DELETE=true`, and you don't need them here.

Claude Code keeps the token in `~/.claude.json`. For other ways to store it, see [Manage tokens](../how-to/tokens.md).

Restart Claude Code, then ask:

> Who am I on CERN Indico?

Claude calls `indico_whoami` and answers with your name and email. If it says you are anonymous, the token is missing or lacks the **User information** scope.

## Step 3: create the meeting

Pick a category id from "Before you start", then ask (replace `1234` and the date):

> Create a meeting called "indico-mcp tutorial" in category 1234, next Friday from 10:00 to 11:30 Geneva time. Don't list it in the category and make it protected.

Claude calls `indico_create_event`:

```json
{
  "category_id": 1234,
  "title": "indico-mcp tutorial",
  "start": "2026-10-09T10:00",
  "end": "2026-10-09T11:30",
  "timezone": "Europe/Zurich",
  "event_type": "meeting",
  "listed": false,
  "protection_mode": "protected"
}
```

and gets back the new event:

```json
{"event_id": 1740001, "url": "https://indico.cern.ch/event/1740001/"}
```

Open the link. The meeting exists, with an empty timetable. Being protected, it is visible only to you and the category managers.

## Step 4: add talks

> Add three 20-minute talks: "Status of the detector" by Ada Lovelace, "Data quality" by Alan Turing, and "Next steps" by Grace Hopper.

Claude calls `indico_create_contribution` three times. For the first one:

```json
{
  "event_id": 1740001,
  "title": "Status of the detector",
  "duration_minutes": 20,
  "persons": [{"first_name": "Ada", "last_name": "Lovelace"}]
}
```

Each call returns a `contribution_id`. The talks exist but have no time yet. Indico calls them unscheduled.

If you give an email for a speaker, Indico links the person to the matching Indico account.

## Step 5: schedule them

> Schedule them back to back from 10:00, in that order.

Claude calls `indico_schedule_contribution` three times with `start` at `10:00`, `10:20` and `10:40`. The times are Geneva times, the meeting's timezone; you never convert to UTC.

Reload the event page. The timetable shows the three talks.

## Step 6: change your mind

> Move "Data quality" to 11:00.

Claude needs the timetable entry id of the talk, not its contribution id. It calls `indico_get_timetable`, finds the entry, and calls `indico_move_timetable_entry` with `start="2026-10-09T11:00"`.

This is the pattern for most edits: read first to get the right id, then change.

## Step 7: clean up

Delete the test meeting in the browser: open the event, click **Manage**, and use the **Delete** action of the event. You can also enable the delete tools for this one step:

```console
$ claude mcp remove indico-cern
$ claude mcp add indico-cern -e INDICO_URL=https://indico.cern.ch -e INDICO_TOKEN=indp_... \
    -e INDICO_ALLOW_DELETE=true -- uvx --from git+https://github.com/vuillaut/indico-mcp indico-mcp
```

> Delete the event "indico-mcp tutorial".

`indico_delete_event` asks for the exact event title as a safety check, so Claude has to read the title before it can delete. Turn deletes off again afterwards.

## What you learned

- A personal token with **Everything (all methods)** unlocks the write tools.
- New talks start unscheduled; scheduling puts them in the timetable.
- Times are always given in the event's timezone.
- Edits in the timetable use `entry_id`; edits to the talk itself use `contribution_id`.
- Deletes stay off unless you turn them on.

## Next

- [Limit what the agent can do](../how-to/restrict.md)
- [Attach slides and links](../how-to/attach-material.md)
- [Tools reference](../reference/tools.md)
