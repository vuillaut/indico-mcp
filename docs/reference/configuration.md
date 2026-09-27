# Configuration

The server reads its settings from environment variables when it starts.

## Choosing an instance

Set exactly one of these groups.

### One Indico

| Variable | Default | Meaning |
|---|---|---|
| `INDICO_URL` | required | Base address, e.g. `https://indico.cern.ch`. A trailing `/` is dropped. |
| `INDICO_TOKEN` | none | Personal token (`indp_...`). Without one, access is anonymous. |

The instance is named after its host, e.g. `indico.cern.ch`.

### Several Indico servers

| Variable | Default | Meaning |
|---|---|---|
| `INDICO_INSTANCES` | required | Comma-separated `name=url` pairs: `cern=https://indico.cern.ch,in2p3=https://indico.in2p3.fr`. |
| `INDICO_TOKEN_<NAME>` | none | Token for instance `<name>`, upper-cased: `INDICO_TOKEN_CERN`. |
| `INDICO_DEFAULT_INSTANCE` | none | Instance used when a call has no `instance`. Without it, every call must name one. |

Names match `[a-z][a-z0-9_]*`; they are lower-cased on input. `INDICO_INSTANCES` wins over `INDICO_URL` when both are set.

### The `instance` argument

Every tool takes an optional `instance`. The server matches it, case-insensitively, against:

1. an instance name: `cern`;
2. an instance host: `indico.cern.ch`;
3. the host of any URL: `https://indico.cern.ch/event/1291157/`.

If `instance` is empty, the server uses the only instance, or the default. Otherwise the call fails and the message lists the configured instances.

## Behavior

These apply to every instance of a server.

| Variable | Default | Meaning |
|---|---|---|
| `INDICO_READ_ONLY` | `false` | Register only the read tools. |
| `INDICO_ALLOW_DELETE` | `false` | Register the delete tools, and let `indico_unschedule_timetable_entry` remove entries when that deletes data. |
| `INDICO_UPLOAD_DIR` | none | Register `indico_upload_file`, limited to files inside this folder. `~` is expanded. |
| `INDICO_TIMEOUT` | `30` | HTTP timeout in seconds for calls to Indico. |

Flags accept `1`, `true`, `yes` or `on`, in any case. Anything else means false.

## Command line

```text
indico-mcp [--transport {stdio,http}] [--host HOST] [--port PORT] [--path PATH]
```

| Option | Default | Meaning |
|---|---|---|
| `--transport` | `stdio` | `stdio` for clients that start the server, `http` for streamable HTTP. |
| `--host` | `127.0.0.1` | HTTP bind address. |
| `--port` | `8000` | HTTP port. |
| `--path` | `/mcp` | HTTP endpoint path. |

## HTTP headers

With `--transport http`, a request may carry its own token. It takes precedence over the configured token.

| Header | Used when |
|---|---|
| `X-Indico-Token-<name>` | always; `_` in the name becomes `-` |
| `X-Indico-Token` | only one instance is configured |
| `Authorization: Bearer <token>` | only one instance is configured |
