# Manage tokens

Without a token, the server sees what an anonymous visitor sees: public events and their timetables. Protected events, contribution lists and every write need a personal token.

## Create a token

1. Log in to your Indico server.
2. Open **My profile → Personal Tokens** and click **Create new token**.
3. Tick only the scopes you need:

    | Scope | Needed for |
    |---|---|
    | Classic API (read only) | reading protected events |
    | Everything (all methods) | every write tool, and `indico_list_contributions` |
    | Registrants | registration forms, registrations, check-in |
    | User information | `indico_whoami` |

4. Copy the token (`indp_...`). Indico shows it once.

Each Indico server has its own accounts and tokens. A CERN token does nothing on indico.in2p3.fr.

## What a token allows

A token acts as you. The agent can do anything your account can do within the token's scopes: if you manage a conference, so does the agent. Two consequences:

- Give a read-only token (**Classic API** only) to setups that only read. The server then fails on writes even if the write tools are registered.
- Also set `INDICO_READ_ONLY=true` so the write tools don't appear at all. See [Limit what the agent can do](restrict.md).

## Keep it out of files you share

Store the token in your client's user-level configuration (`~/.claude.json`, `claude_desktop_config.json`), or in an environment variable the configuration refers to. Never commit it. If a token leaks, revoke it in **Personal Tokens** and create a new one.

## Rotate a token

Create the new token, update the client configuration, restart the client, then revoke the old token in Indico.
