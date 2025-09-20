from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Optional

from fastmcp import Client

from ynab_mcp_server.server import create_server


async def _run(tool_name: str) -> None:
    token = os.environ.get("YNAB_ACCESS_TOKEN")
    if not token:
        raise SystemExit("YNAB_ACCESS_TOKEN is required")

    include = set(filter(None, (os.environ.get("INCLUDE_TAGS") or "").split(","))) or None
    exclude = set(filter(None, (os.environ.get("EXCLUDE_TAGS") or "").split(","))) or None

    mcp = await create_server(token=token, include_tags=include, exclude_tags=exclude)

    client = Client(mcp)
    async with client:
        tools = await client.list_tools()
        by_name = {t.name: t for t in tools}
        tool = by_name.get(tool_name)
        if not tool:
            print(f"Tool not found: {tool_name}", file=sys.stderr)
            print("Available:", ", ".join(sorted(by_name.keys())), file=sys.stderr)
            raise SystemExit(2)
        schema = tool.inputSchema or {}
        print(json.dumps(schema, indent=2, sort_keys=True))


if __name__ == "__main__":
    name: Optional[str] = os.environ.get("NAME") or os.environ.get("TOOL")
    if not name and len(sys.argv) > 1:
        name = sys.argv[1]
    if not name:
        print("Usage: NAME=get_user uv run python scripts/tool_schema.py", file=sys.stderr)
        raise SystemExit(2)
    asyncio.run(_run(name))
