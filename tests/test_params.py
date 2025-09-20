from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import Client

from ynab_mcp_server import server as server_mod


@pytest.mark.asyncio
@respx.mock
async def test_query_param_boolean_encoded(monkeypatch: pytest.MonkeyPatch):
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test YNAB", "version": "0.0.1"},
        "servers": [{"url": "https://api.ynab.com/v1"}],
        "paths": {
            "/budgets": {
                "get": {
                    "operationId": "getBudgets",
                    "parameters": [
                        {
                            "name": "include_accounts",
                            "in": "query",
                            "schema": {"type": "boolean"},
                        }
                    ],
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
    }

    async def fake_fetch_openapi_spec(*_args, **_kwargs):  # type: ignore[no-redef]
        return spec

    monkeypatch.setattr(server_mod, "fetch_openapi_spec", fake_fetch_openapi_spec)

    called = {
        "request": None,
    }

    def _recorder(request: httpx.Request) -> httpx.Response:
        called["request"] = request
        return httpx.Response(200, json={"data": {"budgets": []}})

    respx.get("https://api.ynab.com/v1/budgets").mock(side_effect=_recorder)

    mcp = await server_mod.create_server(token="TEST_TOKEN")
    client = Client(mcp)
    async with client:
        await client.call_tool("get_budgets", {"include_accounts": True})

    req = called["request"]
    assert req is not None, "Expected request to be captured"
    # Accept common encodings for booleans
    val = req.url.params.get("include_accounts")
    assert val is not None
    assert str(val).lower() in {"true", "1"}


@pytest.mark.asyncio
@respx.mock
async def test_path_param_substitution(monkeypatch: pytest.MonkeyPatch):
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test YNAB", "version": "0.0.1"},
        "servers": [{"url": "https://api.ynab.com/v1"}],
        "paths": {
            "/budgets/{budget_id}": {
                "get": {
                    "operationId": "getBudgetById",
                    "parameters": [
                        {
                            "name": "budget_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
    }

    async def fake_fetch_openapi_spec(*_args, **_kwargs):  # type: ignore[no-redef]
        return spec

    monkeypatch.setattr(server_mod, "fetch_openapi_spec", fake_fetch_openapi_spec)

    seen = {"called": False}

    def _recorder(request: httpx.Request) -> httpx.Response:
        seen["called"] = True
        assert request.url == httpx.URL("https://api.ynab.com/v1/budgets/last-used")
        return httpx.Response(200, json={"data": {"budget": {}}})

    respx.get("https://api.ynab.com/v1/budgets/last-used").mock(side_effect=_recorder)

    mcp = await server_mod.create_server(token="TEST_TOKEN")
    client = Client(mcp)
    async with client:
        await client.call_tool("get_budget_by_id", {"budget_id": "last-used"})

    assert seen["called"], "Expected path-substituted request to be called"
