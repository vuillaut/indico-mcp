# indico-mcp

[![CI](https://github.com/vuillaut/indico-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/vuillaut/indico-mcp/actions/workflows/ci.yml)
[![Docs](https://github.com/vuillaut/indico-mcp/actions/workflows/docs.yml/badge.svg)](https://vuillaut.github.io/indico-mcp/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)
[![Project status: active](https://www.repostatus.org/badges/latest/active.svg)](https://www.repostatus.org/#active)

An [MCP](https://modelcontextprotocol.io) server for [Indico](https://getindico.io), the event manager used by CERN and most physics labs. It lets an AI agent such as Claude search events, read timetables, build meeting agendas, schedule talks, attach material and handle registrations, on one or several Indico servers.

```text
You:    What is on the ICHEP 2024 plenary program on Monday 22 July?
Claude: [calls indico_search_events, then indico_get_timetable on indico.cern.ch]
        09:00  Opening (Zdenek Dolezal)
        09:40  ATLAS Highlights (Monica Dunford)
        10:05  CMS Highlights (Maurizio Pierini)
        ...
```

**Documentation: <https://vuillaut.github.io/indico-mcp/>**

## Quick start with CERN's Indico

You need [uv](https://docs.astral.sh/uv/) and an MCP client. With [Claude Code](https://docs.anthropic.com/en/docs/claude-code):

```sh
claude mcp add indico-cern \
  -e INDICO_URL=https://indico.cern.ch \
  -e INDICO_READ_ONLY=true \
  -- uvx --from git+https://github.com/vuillaut/indico-mcp indico-mcp
```

Then ask Claude "Find ICHEP 2024 on CERN's Indico and list Monday's plenary talks". Public events need no account. The [first tutorial](https://vuillaut.github.io/indico-mcp/tutorials/explore-cern/) walks through it.

To write to Indico, create a personal token (**My profile → Personal Tokens**, scope **Everything**), pass it as `INDICO_TOKEN`, and drop `INDICO_READ_ONLY`. The [second tutorial](https://vuillaut.github.io/indico-mcp/tutorials/build-an-agenda/) builds a meeting agenda this way.

For Claude Desktop, Cursor and VS Code, see [Connect an MCP client](https://vuillaut.github.io/indico-mcp/how-to/connect-clients/).

## Several Indico servers

One process can serve several Indico servers. Every tool then takes an `instance` argument: a name, or any link on that server.

```sh
claude mcp add indico \
  -e INDICO_INSTANCES=cern=https://indico.cern.ch,in2p3=https://indico.in2p3.fr,heidelberg=https://indico.physi.uni-heidelberg.de \
  -e INDICO_TOKEN_CERN=indp_... -e INDICO_TOKEN_IN2P3=indp_... \
  -- uvx --from git+https://github.com/vuillaut/indico-mcp indico-mcp
```

Each token goes only to its own server. See [Connect to several Indico servers](https://vuillaut.github.io/indico-mcp/how-to/multiple-instances/).

## What it can do

| Area | Read | Write |
|---|---|---|
| Events | search, list a category, details | create meetings and conferences, edit title, dates, location |
| Timetable | full timetable with ids | sessions and blocks, schedule, move, unschedule |
| Contributions | list with speakers | create, edit, assign to sessions |
| Material | listed with the event | attach links, upload files from one allowed folder |
| Registrations | forms, registrants, answers | check in, approve, reject |

The [tools reference](https://vuillaut.github.io/indico-mcp/reference/tools/) lists all 29 tools.

## Safety

- `INDICO_READ_ONLY=true` removes every write tool.
- Delete tools exist only with `INDICO_ALLOW_DELETE=true`. Deleting an event also needs its exact title.
- Removing a timetable entry that would delete data (a talk in a meeting, a session block) is refused unless deletes are on.
- File uploads need `INDICO_UPLOAD_DIR` and are limited to that folder.
- Edits load Indico's form first and change only the fields you ask for.

A token acts with your Indico rights. Read the [safety model](https://vuillaut.github.io/indico-mcp/explanation/safety/) before giving an agent write access.

## Compatibility

Reads use Indico's documented export and check-in APIs and work with any Indico 3.x server. They were tested on indico.cern.ch, indico.in2p3.fr and indico.physi.uni-heidelberg.de.

Indico has no public write API, so writes use the same internal endpoints as Indico's web pages. They were written for Indico 3.3 and can break when Indico changes a form. When that happens, the tool stops with an error naming the missing field; it does not guess. Try write tools on a test event first. [How it works](https://vuillaut.github.io/indico-mcp/explanation/how-it-works/) explains the details.

## Development

```sh
git clone https://github.com/vuillaut/indico-mcp.git && cd indico-mcp
uv sync
uv run pytest
uv run ruff check . && uv run ruff format .
uv run --group docs mkdocs serve
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and the [development guide](https://vuillaut.github.io/indico-mcp/how-to/develop/).

## Citation

If you use indico-mcp in your work, cite it using [CITATION.cff](CITATION.cff) (GitHub shows a "Cite this repository" button). Software metadata is in [codemeta.json](codemeta.json).

## License

[MIT](LICENSE). This project is not affiliated with CERN or the Indico project.
