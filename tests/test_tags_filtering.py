from __future__ import annotations

import pytest
from fastmcp import Client

from ynab_mcp_server import server as server_mod


@pytest.mark.asyncio
async def test_include_tags_filters_tools(monkeypatch: pytest.MonkeyPatch):
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "0.0.1"},
        "servers": [{"url": "https://api.ynab.com/v1"}],
        "paths": {
            "/user": {
                "get": {
                    "operationId": "getUser",
                    "tags": ["User"],
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            },
                        }
                    },
                }
            },
            "/budgets": {
                "get": {
                    "operationId": "getBudgets",
                    "tags": ["Budgets"],
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {"schema": {"type": "object"}}
                            },
                        }
                    },
                }
            },
        },
    }

    async def fake_fetch_openapi_spec(*_args, **_kwargs):  # type: ignore[no-redef]
        return spec

    monkeypatch.setattr(server_mod, "fetch_openapi_spec", fake_fetch_openapi_spec)

    mcp = await server_mod.create_server(token="T", include_tags={"User"})
    client = Client(mcp)
    async with client:
        tools = await client.list_tools()
        names = {t.name for t in tools}
        # health tool is always present by default
        assert "health" in names
        assert "get_user" in names
        assert "get_budgets" not in names


@pytest.mark.asyncio
async def test_exclude_tags_filters_tools(monkeypatch: pytest.MonkeyPatch):
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "0.0.1"},
        "servers": [{"url": "https://api.ynab.com/v1"}],
        "paths": {
            "/user": {
                "get": {
                    "operationId": "getUser",
                    "tags": ["User", "internal"],
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            },
                        }
                    },
                }
            },
            "/budgets": {
                "get": {
                    "operationId": "getBudgets",
                    "tags": ["Budgets"],
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {"schema": {"type": "object"}}
                            },
                        }
                    },
                }
            },
        },
    }

    async def fake_fetch_openapi_spec(*_args, **_kwargs):  # type: ignore[no-redef]
        return spec

    monkeypatch.setattr(server_mod, "fetch_openapi_spec", fake_fetch_openapi_spec)

    mcp = await server_mod.create_server(token="T", exclude_tags={"internal"})
    client = Client(mcp)
    async with client:
        tools = await client.list_tools()
        names = {t.name for t in tools}
        assert "get_user" not in names  # excluded
        assert "get_budgets" in names


@pytest.mark.asyncio
async def test_openapi_tags_exposed_in_meta(monkeypatch: pytest.MonkeyPatch):
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "0.0.1"},
        "servers": [{"url": "https://api.ynab.com/v1"}],
        "paths": {
            "/user": {
                "get": {
                    "operationId": "getUser",
                    "tags": ["User", "public"],
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {"application/json": {"schema": {"type": "object"}}},
                        }
                    },
                }
            }
        },
    }

    async def fake_fetch_openapi_spec(*_args, **_kwargs):  # type: ignore[no-redef]
        return spec

    monkeypatch.setattr(server_mod, "fetch_openapi_spec", fake_fetch_openapi_spec)

    mcp = await server_mod.create_server(token="T")
    client = Client(mcp)
    async with client:
        tools = await client.list_tools()
        by_name = {t.name: t for t in tools}
        tool = by_name.get("get_user")
        assert tool is not None
        if hasattr(tool, "meta") and tool.meta:
            fm = tool.meta.get("_fastmcp", {})
            tags = set(fm.get("tags", []))
            assert {"User", "public"}.issubset(tags)
