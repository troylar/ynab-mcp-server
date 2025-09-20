from __future__ import annotations

import asyncio
import os

from fastmcp import Client

from ynab_mcp_server.server import create_server


def _parse_tags(value: str | None) -> set[str] | None:
    if not value:
        return None
    parts = [p.strip() for p in value.split(",")]
    filtered = {p for p in parts if p}
    return filtered or None


async def _run() -> None:
    token = os.environ.get("YNAB_ACCESS_TOKEN")
    if not token:
        raise SystemExit("YNAB_ACCESS_TOKEN is required")

    include = _parse_tags(os.environ.get("INCLUDE_TAGS"))
    exclude = _parse_tags(os.environ.get("EXCLUDE_TAGS"))

    mcp = await create_server(token=token, include_tags=include, exclude_tags=exclude)

    client = Client(mcp)
    async with client:
        tools = await client.list_tools()
        tags: set[str] = set()
        for t in tools:
            meta = getattr(t, "meta", None) or {}
            fm = meta.get("_fastmcp", {})
            tags.update(fm.get("tags", []) or [])
        for tag in sorted(tags):
            print(tag)


if __name__ == "__main__":
    asyncio.run(_run())
