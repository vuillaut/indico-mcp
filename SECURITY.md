# Security policy

indico-mcp handles Indico tokens that act with their owner's rights, so security reports are welcome.

## Reporting a vulnerability

Please do not open a public issue. Use GitHub's [private vulnerability reporting](https://github.com/vuillaut/indico-mcp/security/advisories/new) instead. Include the version or commit, your configuration (without tokens), and the steps to reproduce.

I aim to answer within a week.

## In scope

- A token sent to the wrong host, logged, or returned in a tool result.
- A tool running when its setting should hide it (read-only, deletes, uploads).
- `indico_upload_file` reading a file outside `INDICO_UPLOAD_DIR`.
- A write tool changing fields the caller did not ask to change.

## Out of scope

- What an agent does with the rights you gave its token. See the [safety model](https://vuillaut.github.io/indico-mcp/explanation/safety/).
- An HTTP deployment exposed without a reverse proxy and authentication.
- Vulnerabilities in Indico itself. Report those to the [Indico team](https://github.com/indico/indico/security).
