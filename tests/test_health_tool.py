from __future__ import annotations

import pytest
from fastmcp import Client

from ynab_mcp_server import server as server_mod


@pytest.mark.asyncio
async def test_health_tool_available_and_returns_ok(monkeypatch: pytest.MonkeyPatch):
    # Provide a minimal spec to avoid network calls
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "0.0.1"},
        "servers": [{"url": "https://api.ynab.com/v1"}],
        "paths": {},
    }

    async def fake_fetch_openapi_spec(*_args, **_kwargs):  # type: ignore[no-redef]
        return spec

    monkeypatch.setattr(server_mod, "fetch_openapi_spec", fake_fetch_openapi_spec)

    mcp = await server_mod.create_server(token="TEST_TOKEN")
    client = Client(mcp)
    async with client:
        tools = await client.list_tools()
        names = {t.name for t in tools}
        assert "health" in names
        res = await client.call_tool("health", {})
        assert res.data == {"status": "ok"}
