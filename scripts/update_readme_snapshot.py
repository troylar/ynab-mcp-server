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


import re

def _short_desc(tool) -> str:
    """Return a concise, one-line description.
    Prefer OpenAPI summary from FastMCP metadata; otherwise use the first sentence of description.
    """
    meta = getattr(tool, "meta", None) or {}
    fm = meta.get("_fastmcp", {})
    summary = (fm.get("summary") or "").strip()
    if summary:
        return summary
    desc = (tool.description or "").strip()
    # Remove code blocks and excessive markdown artifacts
    desc = re.sub(r"```[\s\S]*?```", " ", desc)
    # Take first line or sentence
    first = desc.split("\n", 1)[0]
    m = re.match(r"(.+?[.!?])\s", first + " ")
    out = (m.group(1) if m else first).strip()
    # Collapse whitespace and limit length
    out = re.sub(r"\s+", " ", out)
    if len(out) > 140:
        out = out[:137].rstrip() + "..."
    return out


def _render_markdown(tools) -> str:
    # tools: list[mcp.types.Tool]
    lines: list[str] = []
    lines.append("## Tools Inventory (Live Snapshot)\n")
    lines.append("This section is generated from your current environment. To refresh, run: `make snapshot-tools`.\n")
    lines.append("")
    # Simple table: Tool | Description
    lines.append("| Tool | Description |")
    lines.append("|------|-------------|")
    for t in sorted(tools, key=lambda x: x.name):
        name = t.name
        desc = _short_desc(t).replace("|", "\\|")
        lines.append(f"| `{name}` | {desc} |")
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
