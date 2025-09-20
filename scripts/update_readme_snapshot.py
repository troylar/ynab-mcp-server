from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional, Set, Iterable

from fastmcp import Client

from ynab_mcp_server.server import create_server

README = Path(__file__).resolve().parents[1] / "README.md"
START_MARK = "<!-- TOOLS_SNAPSHOT_START -->"
END_MARK = "<!-- TOOLS_SNAPSHOT_END -->"


def _parse_tags(value: Optional[str]) -> Optional[Set[str]]:
    if not value:
        return None
    parts = [p.strip() for p in value.split(",")]
    tags = {p for p in parts if p}
    return tags or None


def _render_markdown(tools) -> str:
    # tools: list[mcp.types.Tool]
    lines: list[str] = []
    lines.append("## Tools Inventory (Live Snapshot)\n")
    lines.append("This section is generated from your current environment. To refresh, run: `make snapshot-tools`.\n")
    lines.append("")
    # Group by tags
    def get_tags(t) -> set[str]:
        meta = getattr(t, "meta", None) or {}
        fm = meta.get("_fastmcp", {})
        return set(fm.get("tags", []) or [])

    # Collect tag set
    all_tags: set[str] = set()
    for t in tools:
        all_tags |= get_tags(t)
    lines.append("### Tags\n")
    for tag in sorted(all_tags):
        lines.append(f"- {tag}")
    lines.append("")
    lines.append("### Tools\n")
    for t in sorted(tools, key=lambda x: x.name):
        desc = (t.description or "").strip()
        lines.append(f"- `{t.name}` — {desc}")
    lines.append("")
    return "\n".join(lines)


def _replace_between(text: str, start: str, end: str, replacement: str) -> str:
    sidx = text.find(start)
    eidx = text.find(end)
    block = f"\n{start}\n{replacement}\n{end}\n"
    if sidx == -1 or eidx == -1 or eidx < sidx:
        # Append at end with markers
        if not text.endswith("\n\n"):
            text += "\n"
        return text + block
    return text[:sidx] + block + text[eidx + len(end) + 1 :]


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
        markdown = _render_markdown(tools)

    content = README.read_text(encoding="utf-8") if README.exists() else ""
    new_content = _replace_between(content, START_MARK, END_MARK, markdown)
    README.write_text(new_content, encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(_run())
