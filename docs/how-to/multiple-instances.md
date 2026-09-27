# Connect to several Indico servers

Many physicists use more than one Indico: CERN's for experiment meetings, their lab's for local seminars. You can serve all of them from one server process, or run one process per Indico. Pick one:

| | One server, several instances | One server per instance |
|---|---|---|
| Configuration | one entry with `INDICO_INSTANCES` | one entry per Indico |
| Tools the agent sees | one set, each with an `instance` argument | one set per server |
| Read-only on one Indico, writes on another | no, the settings apply to all instances | yes |

## One server for CERN, IN2P3 and Heidelberg

```console
$ claude mcp add indico \
    -e INDICO_INSTANCES=cern=https://indico.cern.ch,in2p3=https://indico.in2p3.fr,heidelberg=https://indico.physi.uni-heidelberg.de \
    -e INDICO_TOKEN_CERN=indp_... \
    -e INDICO_TOKEN_IN2P3=indp_... \
    -e INDICO_TOKEN_HEIDELBERG=indp_... \
    -- uvx --from git+https://github.com/vuillaut/indico-mcp indico-mcp
```

- `INDICO_INSTANCES` is a comma-separated list of `name=url`. Names use lowercase letters, digits and `_`.
- `INDICO_TOKEN_<NAME>` holds the token for that instance, with the name in upper case. Leave one out to read that Indico anonymously.

Each token is sent only to its own server.

Ask Claude "Which Indico servers can you reach?" to check. It calls `indico_list_instances`:

```json
{
  "instances": [
    {"name": "cern", "url": "https://indico.cern.ch", "token": true},
    {"name": "in2p3", "url": "https://indico.in2p3.fr", "token": true},
    {"name": "heidelberg", "url": "https://indico.physi.uni-heidelberg.de", "token": true}
  ],
  "default": null
}
```

The server never returns the tokens themselves.

## How the agent picks an instance

Every tool takes an `instance` argument. It accepts:

- a configured name: `cern`;
- the server address: `https://indico.cern.ch` or `indico.cern.ch`;
- any link on that server: `https://indico.cern.ch/event/1291157/timetable/`.

The last form means you can paste an event link and Claude will use the right server.

With several instances and no default, a call without `instance` fails with a message listing the names. This is on purpose: an agent that guesses could create an event on the wrong Indico.

## Set a default instance

If you mostly use one Indico, make it the default:

```console
-e INDICO_DEFAULT_INSTANCE=in2p3
```

Calls without `instance` then go to IN2P3. Other instances still work when named.

## Different rights per Indico

`INDICO_READ_ONLY`, `INDICO_ALLOW_DELETE` and `INDICO_UPLOAD_DIR` apply to every instance of a server. To read CERN but write to your lab's Indico, run two servers:

```console
$ claude mcp add indico-cern -e INDICO_URL=https://indico.cern.ch -e INDICO_READ_ONLY=true \
    -- uvx --from git+https://github.com/vuillaut/indico-mcp indico-mcp
$ claude mcp add indico-lab -e INDICO_URL=https://indico.in2p3.fr -e INDICO_TOKEN=indp_... \
    -- uvx --from git+https://github.com/vuillaut/indico-mcp indico-mcp
```

A server with one instance names it after its host (`indico.cern.ch`) and never needs the `instance` argument.
