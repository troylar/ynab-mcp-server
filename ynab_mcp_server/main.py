from __future__ import annotations

import argparse
import asyncio
import os
from typing import NoReturn

# Ensure new OpenAPI parser is enabled for FastMCP before any FastMCP import
os.environ.setdefault("FASTMCP_EXPERIMENTAL_ENABLE_NEW_OPENAPI_PARSER", "true")

from fastmcp import Client

from .server import create_server


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ynab-mcp-server",
        description="FastMCP-based MCP server for YNAB (auto-generated from OpenAPI)",
    )
    p.add_argument(
        "--token",
        help="YNAB Personal Access Token (or set YNAB_ACCESS_TOKEN)",
        default=os.environ.get("YNAB_ACCESS_TOKEN"),
    )
    p.add_argument(
        "--spec-url",
        help="Override OpenAPI spec URL (or set YNAB_OPENAPI_SPEC_URL)",
        default=os.environ.get("YNAB_OPENAPI_SPEC_URL"),
    )
    p.add_argument(
        "--base-url",
        help="Override YNAB API base URL (or set YNAB_BASE_URL)",
        default=os.environ.get("YNAB_BASE_URL"),
    )
    p.add_argument(
        "--timeout",
        help="HTTP timeout in seconds",
        type=float,
        default=30.0,
    )
    p.add_argument(
        "--list-tools",
        action="store_true",
        help="List all generated tools and exit",
    )
    p.add_argument(
        "--include-tags",
        help="Comma-separated list of OpenAPI tags to include (others excluded)",
        default=None,
    )
    p.add_argument(
        "--exclude-tags",
        help="Comma-separated list of OpenAPI tags to exclude",
        default=None,
    )
    p.add_argument(
        "--no-health-routes",
        action="store_true",
        help="Disable health tool and HTTP /health and /debug routes",
    )
    return p


def cli() -> NoReturn:
    parser = _build_parser()
    args = parser.parse_args()

    # Build the server outside any running event loop
    # Parse tag filters
    include_tags = set(filter(None, (args.include_tags or "").split(","))) or None
    exclude_tags = set(filter(None, (args.exclude_tags or "").split(","))) or None

    mcp = asyncio.run(
        create_server(
            token=args.token,
            spec_url=args.spec_url,
            base_url=args.base_url,
            timeout=args.timeout,
            include_tags=include_tags,
            exclude_tags=exclude_tags,
            enable_health_routes=not args.no_health_routes,
        )
    )

    if args.list_tools:
        async def _list():
            client = Client(mcp)
            async with client:
                tools = await client.list_tools()
                for t in tools:
                    print(t.name)
        asyncio.run(_list())
        raise SystemExit(0)

    # Run the server using default stdio transport (blocking)
    mcp.run()
    raise SystemExit(0)
