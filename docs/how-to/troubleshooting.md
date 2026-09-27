# Troubleshoot

Tool errors come back to the agent as text, so the agent usually tells you what went wrong. This page explains the common messages.

## The server does not start

Run the command from your client configuration by hand. It prints the real error:

```console
$ INDICO_URL=https://indico.cern.ch uvx --from git+https://github.com/vuillaut/indico-mcp indico-mcp --help
```

| Message | Fix |
|---|---|
| `Set INDICO_URL (one instance) ... or INDICO_INSTANCES` | Neither setting is present. Check the `env` block of your client configuration. |
| `INDICO_INSTANCES: 'x': expected name=https://host` | Each entry needs a lowercase name, `=`, and a URL starting with `http://` or `https://`. |
| `uvx: command not found` in Claude Desktop | Put the full path of `uvx` in `command`. |

## Errors from Indico

| Message | Meaning |
|---|---|
| `Indico redirected to the login page` | No token, an invalid token, or a token without the scope this call needs. |
| `HTTP 401 (authentication failed...)` | The token is wrong or revoked. |
| `HTTP 403 (forbidden...)` | Your account lacks rights on this event, or the token lacks a scope. Management actions need **Everything (all methods)**; check-in needs **Registrants**. |
| `HTTP 404 (not found)` | Wrong id, or an id of the wrong kind. See [Ids](../reference/ids.md). |
| `event 123 not found or not visible to this user` | The event is protected and there is no token, or it does not exist. |

## Errors from the server

| Message | Meaning |
|---|---|
| `pass instance, one of [...]` | Several instances and no default. Name one, or set `INDICO_DEFAULT_INSTANCE`. |
| `unknown instance 'x'` | The name or host is not configured. The message lists what is. |
| `the form has no field(s) [...]` | The Indico page differs from what the server expects, usually after an Indico upgrade. Nothing was changed. Please [open an issue](https://github.com/vuillaut/indico-mcp/issues) with the Indico version. |
| `Indico rejected the form: field: message` | Indico refused the values, for example a talk longer than its session block. |
| `give the local time in the event's timezone, without an offset` | Pass `2026-10-05T14:30`, not `2026-10-05T14:30+02:00`. |
| `removing this ... deletes data, and deletes are disabled` | See [Limit what the agent can do](restrict.md#deletes). |

## Times look shifted

All times are in the event's timezone. Search results are the exception: Indico returns them in UTC, and the result says `"timezone": "UTC"`. Call `indico_get_event` for local times.

## A new talk got the wrong id

`indico_create_contribution` finds the new talk's id by title, because Indico does not return it. If two talks have the same title, it picks the newest. Check with `indico_list_contributions`.
