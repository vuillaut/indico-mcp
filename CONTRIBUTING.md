# Contributing

Thanks for helping. Bug reports, fixes for newer Indico versions, and new tools are all welcome.

## Report a bug

Open an [issue](https://github.com/vuillaut/indico-mcp/issues) with:

- the Indico server and its version (shown at the bottom of every Indico page);
- the tool, its arguments and the error message;
- your settings, without tokens.

If a write tool fails with `the form has no field(s)`, Indico probably changed that form. Say which Indico version you run; that is the most useful detail.

## Change the code

```console
$ git clone https://github.com/vuillaut/indico-mcp.git
$ cd indico-mcp
$ uv sync
$ uv run pre-commit install
$ uv run pytest
```

Before opening a pull request:

- add or update tests; they mock Indico, so they never need a network;
- run `uv run ruff check . && uv run ruff format .`;
- if you changed a tool, run `uv run python scripts/gen_tools_reference.py`;
- add a line under `Unreleased` in `CHANGELOG.md`.

The [development guide](https://vuillaut.github.io/indico-mcp/how-to/develop/) explains how the code is organized and how to add a tool.

## Documentation

The docs live in `docs/` and follow the [Divio system](https://docs.divio.com/documentation-system/). Preview them with `uv run --group docs mkdocs serve`.

## Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
