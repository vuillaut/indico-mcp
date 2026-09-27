# indico-mcp

indico-mcp is an [MCP](https://modelcontextprotocol.io) server for [Indico](https://getindico.io), the event manager most physics labs use for meetings and conferences. With it, an AI agent such as Claude can search events, read timetables, build a meeting agenda, schedule talks, attach slides and handle registrations, on one or several Indico servers.

It works with any Indico 3.x server. I tested the read tools on indico.cern.ch, indico.in2p3.fr and indico.physi.uni-heidelberg.de.

```text
You:    What is on the ICHEP 2024 plenary program on Monday 22 July?
Claude: [calls indico_search_events, then indico_get_timetable on indico.cern.ch]
        09:00  Opening (Zdenek Dolezal)
        09:40  ATLAS Highlights (Monica Dunford)
        10:05  CMS Highlights (Maurizio Pierini)
        ...
```

## Where to start

The documentation follows the [Divio system](https://docs.divio.com/documentation-system/). Each part answers a different need.

<div class="grid cards" markdown>

- **[Tutorials](tutorials/index.md)**

    Learning by doing. Start here if you have never used the server. The first tutorial explores ICHEP 2024 on CERN's Indico and needs no account.

- **[How-to guides](how-to/index.md)**

    Steps for one task: install, connect a client, add a token, talk to several Indico servers, run it for a team.

- **[Reference](reference/index.md)**

    Every tool, every setting, every id. Look things up here.

- **[Explanation](explanation/index.md)**

    How the server talks to Indico, why writes can break after an Indico upgrade, and how it keeps an agent from deleting your conference.

</div>

## What you can do with it

| Area | Read | Write |
|---|---|---|
| Events | search by title, list a category, get details | create meetings and conferences, change title, dates, location |
| Timetable | full timetable with ids | create sessions and blocks, schedule, move and unschedule talks |
| Contributions | list with speakers and ids | create, edit, assign to sessions |
| Material | listed with the event | attach links, upload files from one allowed folder |
| Registrations | forms, registrants, answers | check in, approve, reject |

Writes are on by default and deletes are off. You can turn writes off with one setting; see [Limit what the agent can do](how-to/restrict.md).

## Status

The read tools use Indico's documented APIs. The write tools use the same internal endpoints as Indico's web pages, because Indico has no public write API. They were written from Indico 3.3's source code and unit-tested against recorded responses. Try a write tool on a test event before you rely on it. [Why writes are fragile](explanation/how-it-works.md#writes-go-through-the-web-forms) explains the risk.
