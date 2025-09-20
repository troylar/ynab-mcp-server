from __future__ import annotations

import asyncio
import os

from ynab_mcp_server.server import create_server


def _parse_tags(value: str | None) -> set[str] | None:
    if not value:
        return None
    parts = [p.strip() for p in value.split(",")]
    tags = {p for p in parts if p}
    return tags or None


def main() -> None:
    token = os.environ.get("YNAB_ACCESS_TOKEN")
    if not token:
        raise SystemExit("YNAB_ACCESS_TOKEN is required")

    include = _parse_tags(os.environ.get("INCLUDE_TAGS"))
    exclude = _parse_tags(os.environ.get("EXCLUDE_TAGS"))

    mcp = asyncio.run(create_server(token=token, include_tags=include, exclude_tags=exclude))
    # Default host/port with env overrides
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    mcp.run(transport="http", host=host, port=port)


if __name__ == "__main__":
    main()
