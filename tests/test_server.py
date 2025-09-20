from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import Client

from ynab_mcp_server import server as server_mod


@pytest.mark.asyncio
async def test_create_server_requires_token(monkeypatch: pytest.MonkeyPatch):
    # Ensure env token is not present
    monkeypatch.delenv("YNAB_ACCESS_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        await server_mod.create_server()


@pytest.mark.asyncio
@respx.mock
async def test_generated_get_user_tool_executes(monkeypatch: pytest.MonkeyPatch):
    # Minimal OpenAPI spec containing a GET /user endpoint with operationId getUser
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test YNAB", "version": "0.0.1"},
        "servers": [{"url": "https://api.ynab.com/v1"}],
        "paths": {
            "/user": {
                "get": {
                    "operationId": "getUser",
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {"schema": {"type": "object"}}
                            },
                        }
                    },
                }
            }
        },
    }

    async def fake_fetch_openapi_spec(*_args, **_kwargs):  # type: ignore[no-redef]
        return spec

    # Use our stubbed spec instead of hitting the network
    monkeypatch.setattr(server_mod, "fetch_openapi_spec", fake_fetch_openapi_spec)

    # Mock the GET /user API call
    route = respx.get("https://api.ynab.com/v1/user").mock(
        return_value=httpx.Response(200, json={"data": {"user": {"id": "abc"}}})
    )

    mcp = await server_mod.create_server(token="TEST_TOKEN")

    # Use in-memory client for FastMCP to list and call tools
    client = Client(mcp)
    async with client:
        tools = await client.list_tools()
        tool_names = {t.name for t in tools}
        assert "get_user" in tool_names

        result = await client.call_tool("get_user", {})
        assert result.data["data"]["user"]["id"] == "abc"

    # Verify auth header was applied
    assert route.called, "Expected /user route to be called"
    req = route.calls.last.request  # type: ignore[assignment]
    assert req.headers.get("Authorization") == "Bearer TEST_TOKEN"
