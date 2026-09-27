"""MCP server for Indico."""

import argparse
import logging


def main() -> None:
    from indico_mcp.config import Settings
    from indico_mcp.server import create_server

    parser = argparse.ArgumentParser(description="MCP server for Indico (configured via INDICO_* env vars)")
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind address (default: localhost only)")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--path", default="/mcp", help="HTTP endpoint path")
    args = parser.parse_args()
    logging.getLogger("httpx").setLevel(logging.WARNING)

    server = create_server(Settings.from_env())
    if args.transport == "stdio":
        server.run("stdio")
    else:
        server.run("streamable-http", host=args.host, port=args.port, streamable_http_path=args.path)
