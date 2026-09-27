# Install the server

The server is a Python package. It needs Python 3.12 or later. The commands below use [uv](https://docs.astral.sh/uv/), which fetches the right Python for you.

## Run it without installing

```console
$ uvx --from git+https://github.com/vuillaut/indico-mcp indico-mcp --help
```

uv builds the package in its cache and runs it. Use this same command in your MCP client configuration. To pin a version, add a tag or commit:

```console
$ uvx --from git+https://github.com/vuillaut/indico-mcp@v0.1.0 indico-mcp --help
```

Pinning is a good idea: the write tools depend on Indico internals, so you want to upgrade on purpose, not whenever the cache refreshes.

## Install it as a command

```console
$ uv tool install git+https://github.com/vuillaut/indico-mcp
$ indico-mcp --help
```

This puts `indico-mcp` on your `PATH`. Upgrade with `uv tool upgrade indico-mcp`.

## Install from a clone

Use this to change the code or run an unreleased version:

```console
$ git clone https://github.com/vuillaut/indico-mcp.git
$ cd indico-mcp
$ uv sync
$ uv run indico-mcp --help
```

In client configurations, run it with `uv --directory /path/to/indico-mcp run indico-mcp`.

## With pip

```console
$ python -m pip install git+https://github.com/vuillaut/indico-mcp
```

## Next

[Connect an MCP client](connect-clients.md).
