# Develop and contribute

## Set up

```console
$ git clone https://github.com/vuillaut/indico-mcp.git
$ cd indico-mcp
$ uv sync
$ uv run pre-commit install    # optional: run ruff before each commit
```

## Run the checks

```console
$ uv run pytest
$ uv run ruff check .
$ uv run ruff format .
```

The tests never touch a real Indico. They mock HTTP with [respx](https://lundberg.github.io/respx/) and call the tools through an in-memory MCP client, the same way an agent does. CI runs the same commands on Python 3.12 and 3.13.

## Try a change against a real Indico

The [MCP Inspector](https://github.com/modelcontextprotocol/inspector) lists the tools and lets you call them by hand:

```console
$ npx @modelcontextprotocol/inspector -e INDICO_URL=https://indico.cern.ch -e INDICO_READ_ONLY=true \
    uv --directory $PWD run indico-mcp
```

Or register your clone with your client:

```console
$ claude mcp add indico-dev -e INDICO_URL=https://indico.cern.ch -- uv --directory $PWD run indico-mcp
```

Test write tools on a throwaway event in a category you control.

## Add a tool

1. Write it in `src/indico_mcp/server.py`, inside `create_server`, in the right section (read, write or delete). Take `instance: InstanceName = None` as the last parameter and call `client(ctx, instance)`.
2. Write the docstring for the agent: say what the tool does, which ids it takes, and what it changes on Indico. The agent reads it to choose tools.
3. For HTML forms, use `IndicoClient.edit_form`, which loads the form and changes only the fields you pass. Posting a partial form resets fields Indico doesn't receive.
4. Add a test in `tests/test_tools.py` with the Indico responses mocked.
5. Regenerate the reference: `uv run python scripts/gen_tools_reference.py`. A test fails if you forget.
6. Add a line to `CHANGELOG.md`.

## Work on the documentation

```console
$ uv run --group docs mkdocs serve
```

opens the site at `http://127.0.0.1:8000`. Pages live in `docs/`, sorted by the [Divio system](https://docs.divio.com/documentation-system/): tutorials teach, how-to guides solve one task, reference describes, explanation discusses. Put a new page in the section that matches what the reader wants at that moment.

## Release

1. Update `version` in `pyproject.toml`, `codemeta.json` and `CITATION.cff` (a test checks they agree), and the `dateModified` in `codemeta.json`.
2. Move the `Unreleased` notes in `CHANGELOG.md` under the new version.
3. Commit, tag `vX.Y.Z`, push the tag, and create a GitHub release from it.
