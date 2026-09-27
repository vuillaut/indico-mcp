"""Write docs/reference/tools.md from the tools the server registers.

Run `uv run python scripts/gen_tools_reference.py` after changing a tool.
The test suite fails when the page is out of date.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import sys
from pathlib import Path
from typing import Any

from mcp.client.client import Client

from indico_mcp.config import Settings
from indico_mcp.server import create_server

OUTPUT = Path(__file__).resolve().parent.parent / "docs" / "reference" / "tools.md"

HEADER = """\
# Tools

This page is generated from the server code by `scripts/gen_tools_reference.py`. Do not edit it by hand.

Every tool also takes `instance`; see [Configuration](configuration.md#choosing-an-instance).
Times are local to the event's timezone, written like `2026-10-05T14:30`.

| Group | Registered when |
|---|---|
| Read | always |
| Write | `INDICO_READ_ONLY` is not set |
| Delete | `INDICO_ALLOW_DELETE=true` |

`indico_upload_file` also needs `INDICO_UPLOAD_DIR`.
"""


async def list_tools(**settings: Any) -> dict[str, Any]:
    async with Client(create_server(Settings.single("https://indico.example.org", **settings))) as client:
        return {t.name: t for t in (await client.list_tools()).tools}


def _type(schema: dict[str, Any]) -> str:
    if "anyOf" in schema:
        return " or ".join(_type(s) for s in schema["anyOf"] if s.get("type") != "null")
    if "enum" in schema:
        return " / ".join(f"`{v}`" for v in schema["enum"])
    if schema.get("type") == "array":
        return f"list of {_type(schema.get('items', {}))}"
    if "$ref" in schema:
        return schema["$ref"].rsplit("/", 1)[-1]
    return schema.get("type", "any")


def _cell(text: str) -> str:
    return text.replace("\n", " ").replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")


def _default(prop: dict[str, Any], required: bool) -> str:
    if required:
        return "required"
    return f"`{json.dumps(prop['default'])}`" if "default" in prop else ""


def _section(tool: Any) -> str:
    schema = tool.input_schema
    required = set(schema.get("required", []))
    description = inspect.cleandoc(tool.description or "").replace("<", "&lt;").replace(">", "&gt;")
    lines = [f"### `{tool.name}`", "", description, ""]
    params = {k: v for k, v in schema.get("properties", {}).items() if k != "instance"}
    if params:
        lines += ["| Parameter | Type | Default | Description |", "|---|---|---|---|"]
        for name, prop in params.items():
            default = _default(prop, name in required)
            text = prop.get("description", "")
            if "minimum" in prop and "maximum" in prop:
                text = f"{text} ({prop['minimum']} to {prop['maximum']})".strip()
            elif "minimum" in prop:
                text = f"{text} (at least {prop['minimum']})".strip()
            lines.append(f"| `{name}` | {_type(prop)} | {default} | {_cell(text)} |")
        lines.append("")
    return "\n".join(lines)


def _person(tools: dict[str, Any]) -> str:
    defs = tools["indico_create_contribution"].input_schema.get("$defs", {})
    person = defs.get("Person")
    if not person:
        return ""
    lines = ["## Person", "", person.get("description", ""), "", "| Field | Type | Default |", "|---|---|---|"]
    for name, prop in person["properties"].items():
        default = _default(prop, "default" not in prop)
        lines.append(f"| `{name}` | {_type(prop)} | {default} |")
    return "\n".join(lines) + "\n"


async def render() -> str:
    read = await list_tools(read_only=True)
    everything = await list_tools(allow_delete=True, upload_dir=Path("INDICO_UPLOAD_DIR"))
    write_and_read = await list_tools()
    groups = {
        "Read": list(read),
        "Write": [n for n in write_and_read if n not in read] + ["indico_upload_file"],
        "Delete": [n for n in everything if n not in write_and_read and n != "indico_upload_file"],
    }
    parts = [HEADER]
    for title, names in groups.items():
        parts.append(f"## {title}\n")
        parts += [_section(everything[n]) for n in names]
    parts.append(_person(everything))
    return "\n".join(parts).rstrip() + "\n"


def main() -> None:
    text = asyncio.run(render())
    if "--check" in sys.argv:
        if not OUTPUT.exists() or OUTPUT.read_text() != text:
            raise SystemExit(f"{OUTPUT} is out of date; run scripts/gen_tools_reference.py")
        return
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(text)
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
