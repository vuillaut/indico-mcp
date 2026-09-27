# Run the server over HTTP

By default the client starts the server as a child process. For a shared setup, or a client that only connects to remote servers, run it as an HTTP service instead.

## Start it

```console
$ INDICO_URL=https://indico.cern.ch uvx --from git+https://github.com/vuillaut/indico-mcp \
    indico-mcp --transport http --host 127.0.0.1 --port 8000
```

The MCP endpoint is `http://127.0.0.1:8000/mcp` (streamable HTTP). Change the path with `--path`.

## Send tokens per request

On a shared server, each user should send their own Indico token with each request, and the server should hold none.

With one instance, send either header:

```text
X-Indico-Token: indp_...
Authorization: Bearer indp_...
```

With several instances, send one header per instance: `X-Indico-Token-cern`, `X-Indico-Token-in2p3`. A `_` in an instance name becomes `-` in the header. The server ignores `X-Indico-Token` and `Authorization` when several instances are configured, so it never sends one Indico's token to another.

Requests without a token fall back to the token in the configuration, or to anonymous access.

In Claude Code:

```console
$ claude mcp add --transport http indico http://127.0.0.1:8000/mcp \
    --header "X-Indico-Token: indp_..."
```

## Expose it safely

The server has no login of its own. Anyone who reaches the port can use it with whatever token the configuration holds. So:

- keep the default `--host 127.0.0.1` unless a reverse proxy sits in front;
- leave `INDICO_TOKEN` unset on a shared server, so each user brings their own;
- put a reverse proxy with TLS and authentication in front before opening it to a network;
- consider `INDICO_READ_ONLY=true` for a service many people use.

## Run it as a container or service

There is no official image. The server is one command, so any process manager works. A minimal systemd unit:

```ini
[Service]
Environment=INDICO_URL=https://indico.cern.ch
Environment=INDICO_READ_ONLY=true
ExecStart=/usr/local/bin/uvx --from git+https://github.com/vuillaut/indico-mcp@v0.1.0 indico-mcp --transport http --host 127.0.0.1 --port 8000
Restart=on-failure
```
