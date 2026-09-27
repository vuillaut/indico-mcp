# Connect an MCP client

The server speaks MCP over standard input and output by default. Every client needs the same three things:

- the command: `uvx`, with arguments `--from git+https://github.com/vuillaut/indico-mcp indico-mcp`;
- the environment variables: at least `INDICO_URL` (or `INDICO_INSTANCES`) and usually a token;
- a name for the server, such as `indico-cern`.

The examples connect to indico.cern.ch. All settings are listed in [Configuration](../reference/configuration.md).

## Claude Code

```console
$ claude mcp add indico-cern \
    -e INDICO_URL=https://indico.cern.ch \
    -e INDICO_TOKEN=indp_... \
    -- uvx --from git+https://github.com/vuillaut/indico-mcp indico-mcp
```

Add `--scope user` to use the server in every project, or `--scope project` to share it with a team through `.mcp.json`. Don't put a token in a shared `.mcp.json`; reference an environment variable instead:

```json
{
  "mcpServers": {
    "indico-cern": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/vuillaut/indico-mcp", "indico-mcp"],
      "env": {"INDICO_URL": "https://indico.cern.ch", "INDICO_TOKEN": "${INDICO_CERN_TOKEN}"}
    }
  }
}
```

Check with `claude mcp list`, or `/mcp` inside Claude Code.

## Claude Desktop

Edit `claude_desktop_config.json`:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "indico-cern": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/vuillaut/indico-mcp", "indico-mcp"],
      "env": {"INDICO_URL": "https://indico.cern.ch", "INDICO_TOKEN": "indp_..."}
    }
  }
}
```

Restart Claude Desktop. If the server fails to start, Claude Desktop may not find `uvx` on its `PATH`: put the full path in `command` (run `which uvx` to get it).

## Cursor

Use the same `mcpServers` block in `~/.cursor/mcp.json` (all projects) or `.cursor/mcp.json` (one project).

## VS Code

Create `.vscode/mcp.json`. VS Code uses `servers` instead of `mcpServers`, and can prompt for the token so it stays out of the file:

```json
{
  "inputs": [
    {"id": "indico-token", "type": "promptString", "description": "Indico token", "password": true}
  ],
  "servers": {
    "indico-cern": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "git+https://github.com/vuillaut/indico-mcp", "indico-mcp"],
      "env": {"INDICO_URL": "https://indico.cern.ch", "INDICO_TOKEN": "${input:indico-token}"}
    }
  }
}
```

## Any other client

Clients that start local servers take the same command, arguments and environment. Clients that only connect to remote servers need the HTTP transport: see [Run the server over HTTP](http-server.md).
