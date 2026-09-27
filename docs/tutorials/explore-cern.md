# Explore a conference on CERN's Indico

In this tutorial you connect Claude Code to [indico.cern.ch](https://indico.cern.ch) and use it to read the program of ICHEP 2024, the International Conference on High Energy Physics held in Prague in July 2024. The event is public, so you don't need a CERN account.

By the end you will have:

- a working `indico-cern` MCP server in Claude Code, limited to reading;
- asked Claude questions it answers from live Indico data;
- seen the ids Indico uses, which you need for the second tutorial.

## Before you start

You need:

- [uv](https://docs.astral.sh/uv/getting-started/installation/), the Python package manager. It installs Python 3.12 or later for you if needed.
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Any other MCP client works too; see [Connect an MCP client](../how-to/connect-clients.md). This tutorial uses Claude Code because one command sets it up.

Check both are installed:

```console
$ uv --version
uv 0.11.x
$ claude --version
```

## Step 1: check the server runs

uv can run the server straight from GitHub without cloning anything:

```console
$ uvx --from git+https://github.com/vuillaut/indico-mcp indico-mcp --help
usage: indico-mcp [-h] [--transport {stdio,http}] [--host HOST] [--port PORT]
                  [--path PATH]

MCP server for Indico (configured via INDICO_* env vars)
```

The first run downloads the dependencies and takes a few seconds. Later runs use uv's cache.

## Step 2: register the server with Claude Code

```console
$ claude mcp add indico-cern \
    -e INDICO_URL=https://indico.cern.ch \
    -e INDICO_READ_ONLY=true \
    -- uvx --from git+https://github.com/vuillaut/indico-mcp indico-mcp
```

Three things happen in this command:

- `indico-cern` is the name Claude Code shows for the server.
- `INDICO_URL` tells the server which Indico to talk to.
- `INDICO_READ_ONLY=true` hides every tool that changes data. You are only reading in this tutorial, so there is no reason to give Claude more.

There is no token. Without one, the server reads Indico as an anonymous visitor and sees public events only.

Start Claude Code and type `/mcp`. You should see `indico-cern` marked as connected, with 10 tools.

!!! tip "If the server shows as failed"
    Run the `uvx` command from step 1 again. It prints the real error, usually a network or proxy problem.

## Step 3: find the event

Ask Claude:

> Find ICHEP 2024 on CERN's Indico.

Claude calls `indico_search_events` with the query `ICHEP 2024` and finds one event:

```json
{"id": 1291157, "title": "ICHEP 2024", "start": "2024-07-17T06:00:00", "timezone": "UTC"}
```

`1291157` is the **event id**, the number in the event's address, `https://indico.cern.ch/event/1291157/`. Every event tool takes it.

The search result holds only a few fields, and Indico gives its start time in UTC. The next step gets the full details. Claude Code asks your permission before each tool call the first time; answer "yes, and don't ask again" for the `indico-cern` read tools to keep the tutorial moving.

## Step 4: read the event details

> When and where does it take place, and in which timezone?

Claude calls `indico_get_event` with `detail="events"`, which returns metadata without the contribution list:

```json
{
  "title": "ICHEP 2024",
  "type": "conference",
  "timezone": "Europe/Prague",
  "startDate": {"date": "2024-07-17", "time": "08:00:00", "tz": "Europe/Prague"},
  "endDate": {"date": "2024-07-24", "time": "23:00:00", "tz": "Europe/Prague"},
  "location": "Prague",
  "url": "https://indico.cern.ch/event/1291157/"
}
```

All times the server returns are in the event's own timezone. When you later schedule a talk, you give the time in that same timezone.

## Step 5: read the timetable

> What is on the plenary program on Monday 22 July?

Claude calls `indico_get_timetable`. ICHEP has 1466 timetable entries, so Claude filters them for Monday's plenary blocks and their talks. You get something like:

| Time | Talk | Speaker |
|---|---|---|
| 09:00 | Opening | Zdenek Dolezal |
| 09:20 | Practical information | Tomas Davidek |
| 09:40 | ATLAS Highlights | Monica Dunford |
| 10:05 | CMS Highlights | Maurizio Pierini |
| 11:00 | ALICE Highlights | Nicolo Jacazio |
| 11:20 | LHCb Highlights | Yasmine Sara Amhis |
| 11:40 | B-factories Highlights (BaBar, Belle, Belle II) | James Libby |

Each timetable entry has a `kind`:

- `session_block`: a time slot of a session, such as "Plenary session, 09:40 to 10:30 in Congress Hall";
- `contribution`: a talk, placed inside a block through `parent_entry_id`;
- `break`: coffee and lunch.

## Step 6: search across the program

> List the talks about the Higgs boson on Thursday 18 July, with their speakers.

This is where an agent beats the web page. Claude reads the whole timetable once and filters it:

```text
08:40  Measurements of Higgs boson cross-sections and their interpretation with the ATLAS experiment (Xiao Yang)
08:57  Higgs boson cross section and coupling measurements at CMS (Jan Lukas Spaeh)
09:14  Measurements of the Higgs boson mass with the ATLAS detector (Rafael Coelho Lopes De Sa)
09:31  Measurements of the Higgs boson mass and width at CMS (Badder Marzocchi)
09:48  NNLO+PS predictions for Higgs production via bottom fusion (Christian Biello)
...
```

Ask for a link to one of them:

> Give me the link to the ATLAS Higgs mass talk.

Claude answers `https://indico.cern.ch/event/1291157/contributions/5888282/`.

## Step 7: look at the ids

One talk carries several ids. For the ATLAS Higgs mass talk, the timetable entry reads:

```json
{
  "entry_id": 6525026,
  "kind": "contribution",
  "title": "Measurements of the Higgs boson mass with the ATLAS detector",
  "start": "2024-07-18T09:14:00",
  "end": "2024-07-18T09:31:00",
  "parent_entry_id": 6477312,
  "room": "South Hall 2A ",
  "contribution_id": 5888282,
  "public_id": 495,
  "session_id": 542907,
  "session_block_id": 560058,
  "speakers": ["Rafael Coelho Lopes De Sa"]
}
```

- `contribution_id` is the database id. It appears in the talk's address, and the write tools take it.
- `public_id` is the contribution number shown on the conference pages.
- `entry_id` is the talk's slot in the timetable. You move or remove the slot with it.
- `session_id` is the session ("Higgs Physics"), and `session_block_id` is the one time slot of that session the talk sits in. `parent_entry_id` is that block's `entry_id`.

You don't have to track these yourself; Claude reads them from the tool results. They matter when a result looks wrong. [Ids](../reference/ids.md) lists them all.

## What you learned

- `uvx --from git+...` runs the server without a local install.
- `INDICO_URL` picks the Indico server, and `INDICO_READ_ONLY` limits Claude to reading.
- Without a token, you see what an anonymous visitor sees.
- Times are local to the event's timezone.
- Talks have a database id, a public number and a timetable entry id.

## Next

- [Build a meeting agenda](build-an-agenda.md) adds a token and writes to Indico.
- [Connect to several Indico servers](../how-to/multiple-instances.md) adds indico.in2p3.fr or your lab's Indico next to CERN.
