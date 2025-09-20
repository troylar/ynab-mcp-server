from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp import Client

from ynab_mcp_server import server as server_mod


@pytest.mark.asyncio
@respx.mock
async def test_post_body_is_json(monkeypatch: pytest.MonkeyPatch):
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test YNAB", "version": "0.0.1"},
        "servers": [{"url": "https://api.ynab.com/v1"}],
        "paths": {
            "/budgets/{budget_id}/accounts": {
                "post": {
                    "operationId": "createAccount",
                    "parameters": [
                        {
                            "name": "budget_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "account": {
                                            "type": "object",
                                            "properties": {
                                                "name": {"type": "string"},
                                                "type": {"type": "string"},
                                                "balance": {"type": "integer"},
                                            },
                                            "required": ["name", "type", "balance"],
                                        }
                                    },
                                    "required": ["account"],
                                }
                            }
                        },
                    },
                    "responses": {"201": {"description": "created"}},
                }
            }
        },
    }

    async def fake_fetch_openapi_spec(*_args, **_kwargs):  # type: ignore[no-redef]
        return spec

    monkeypatch.setattr(server_mod, "fetch_openapi_spec", fake_fetch_openapi_spec)

    captured: dict[str, httpx.Request | None] = {"req": None}

    def _recorder(request: httpx.Request) -> httpx.Response:
        captured["req"] = request
        return httpx.Response(201, json={"data": {"account": {"id": "acc1"}}})

    respx.post("https://api.ynab.com/v1/budgets/last-used/accounts").mock(side_effect=_recorder)

    mcp = await server_mod.create_server(token="TEST_TOKEN")
    client = Client(mcp)
    async with client:
        await client.call_tool(
            "create_account",
            {
                "budget_id": "last-used",
                "account": {
                    "name": "Test",
                    "type": "checking",
                    "balance": 0,
                },
            },
        )

    req = captured["req"]
    assert req is not None
    assert req.headers.get("content-type", "").startswith("application/json")
    import json as _json  # local import for test
    body = _json.loads(req.content.decode())
    assert body == {"account": {"name": "Test", "type": "checking", "balance": 0}}
