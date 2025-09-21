from __future__ import annotations

import os
# Ensure new OpenAPI parser is enabled before FastMCP is imported
os.environ["FASTMCP_EXPERIMENTAL_ENABLE_NEW_OPENAPI_PARSER"] = os.environ.get(
    "FASTMCP_EXPERIMENTAL_ENABLE_NEW_OPENAPI_PARSER", "true"
)
import re
import json
from collections.abc import Iterable
from typing import Any

import httpx
from fastmcp import FastMCP
from fastmcp.server.openapi import MCPType, RouteMap

from .openapi_loader import DEFAULT_SPEC_URL, fetch_openapi_spec


def _snake_case(name: str) -> str:
    """Convert camelCase/PascalCase/mixed to snake_case and collapse multiple underscores."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
    s3 = re.sub(r"[^a-zA-Z0-9_]+", "_", s2)
    return re.sub(r"__+", "_", s3).strip("_").lower()


def _build_mcp_names_from_spec(spec: dict[str, Any]) -> dict[str, str]:
    """Build a mapping of original operationIds to normalized snake_case tool names.

    FastMCP uses operationId (slugified) as the default name. We remap to
    snake_case for consistency with MCP naming best practices.
    """
    names: dict[str, str] = {}
    paths = spec.get("paths", {}) or {}
    for _path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            if not isinstance(op, dict):
                continue
            op_id = op.get("operationId")
            if not op_id or not isinstance(op_id, str):
                continue
            snake = _snake_case(op_id)
            if snake and snake != op_id:
                names[op_id] = snake
    return names

YNAB_BASE_URL = "https://api.ynab.com/v1"
ENV_TOKEN = "YNAB_ACCESS_TOKEN"
ENV_SPEC_URL = "YNAB_OPENAPI_SPEC_URL"
ENV_BASE_URL = "YNAB_BASE_URL"


def _get_env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name, default)
    return value


def _build_route_maps(
    include_tags: set[str] | None,
    exclude_tags: set[str] | None,
    user_maps: Iterable[RouteMap] | None,
) -> list[RouteMap] | None:
    """Construct RouteMap list for OpenAPI integration.

    Precedence: Exclusions are evaluated before inclusions.
    If user_maps is provided, those are used as-is.
    """
    if user_maps:
        return list(user_maps)

    maps: list[RouteMap] = []

    # Exclusions first
    if exclude_tags:
        for tag in sorted(exclude_tags):
            maps.append(RouteMap(tags={tag}, mcp_type=MCPType.EXCLUDE))

    if include_tags is not None:
        # Only include specified tags, exclude everything else by default
        for tag in sorted(include_tags):
            maps.append(RouteMap(tags={tag}, mcp_type=MCPType.TOOL))
        maps.append(RouteMap(mcp_type=MCPType.EXCLUDE))
        return maps

    # Default: include all as tools (FastMCP default)
    if maps:
        # We added exclusions; include everything else as tools
        maps.append(RouteMap(mcp_type=MCPType.TOOL))
        return maps

    return None


async def create_server(
    *,
    token: str | None = None,
    spec_url: str | None = None,
    base_url: str | None = None,
    timeout: float = 30.0,
    include_tags: set[str] | None = None,
    exclude_tags: set[str] | None = None,
    route_maps: Iterable[RouteMap] | None = None,
    route_map_fn: Any | None = None,
    enable_health_routes: bool = True,
) -> FastMCP:
    """Create a FastMCP server from the YNAB OpenAPI spec.

    - Loads the OpenAPI spec from YNAB (YAML) and parses it.
    - Configures an httpx AsyncClient with Bearer token auth.
    - Generates MCP tools/resources from OpenAPI with optional tag filtering.

    Environment variables (optional):
    - YNAB_ACCESS_TOKEN: Bearer token for API access
    - YNAB_OPENAPI_SPEC_URL: Override the OpenAPI spec URL
    - YNAB_BASE_URL: Override API base URL (default https://api.ynab.com/v1)
    """
    token = token or _get_env(ENV_TOKEN)
    if not token:
        raise RuntimeError(
            "YNAB access token is required. Set YNAB_ACCESS_TOKEN or pass token explicitly."
        )

    spec_url = spec_url or _get_env(ENV_SPEC_URL, DEFAULT_SPEC_URL) or DEFAULT_SPEC_URL
    base_url = base_url or _get_env(ENV_BASE_URL, YNAB_BASE_URL) or YNAB_BASE_URL

    spec: dict[str, Any] = await fetch_openapi_spec(spec_url, timeout=timeout)

    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "ynab-mcp-server/0.1 (+https://github.com/troylar/ynab-mcp-server)",
        "Accept": "application/json",
    }

    def _deep_clean_nulls(obj: Any) -> Any:
        """Recursively remove keys with value None from mappings and
        filter None items from lists. Leaves other values intact.

        This is a defensive normalization for YNAB endpoints that sometimes
        return `null` for optional objects (e.g., `default_budget: null`),
        while the OpenAPI schema describes those as object types without
        explicit `nullable: true`. Removing nulls allows output validation
        to pass while preserving all real data.
        """
        if isinstance(obj, dict):
            cleaned: dict[str, Any] = {}
            for k, v in obj.items():
                if v is None:
                    # Drop null keys entirely
                    continue
                cleaned[k] = _deep_clean_nulls(v)
            return cleaned
        if isinstance(obj, list):
            return [
                _deep_clean_nulls(v)
                for v in obj
                if v is not None
            ]
        return obj

    async def _response_hook(response: httpx.Response) -> None:
        """Normalize successful empty/None JSON payloads and surface YNAB errors clearly.

        IMPORTANT: This hook runs before the response body is accessed. We MUST
        fully read the content before touching response.content/response.json().

        - If 2xx and body is empty, JSON null, or 204 → coerce to '{}' so schemas expecting
          an object won't fail client-side validation.
        - If 2xx and JSON has top-level data: null → coerce to {"data": {}}.
        - If non-2xx and JSON body has an 'error' field → raise with that context.
        """
        try:
            # Ensure body is fully read (prevents streaming access errors)
            if hasattr(response, "aread"):
                await response.aread()  # type: ignore[attr-defined]

            if 200 <= response.status_code < 300:
                # Normalize empty body / null / 204
                content = (response.content or b"")
                if response.status_code == 204 or not content.strip():
                    response._content = b"{}"  # type: ignore[attr-defined]
                    response.headers["Content-Length"] = str(len(response._content))
                else:
                    try:
                        data = response.json()
                        if data is None:
                            # Entire payload null → {}
                            response._content = b"{}"  # type: ignore[attr-defined]
                            response.headers["Content-Length"] = str(len(response._content))
                        elif isinstance(data, dict) and data.get("data", ... ) is None:
                            # Coerce {"data": null} → {"data": {}}
                            data = {**data, "data": {}}
                            new = json.dumps(data).encode("utf-8")
                            response._content = new  # type: ignore[attr-defined]
                            response.headers["Content-Length"] = str(len(new))
                        elif isinstance(data, (dict, list)):
                            # Drop null-valued fields recursively to satisfy schemas
                            cleaned = _deep_clean_nulls(data)
                            if cleaned is not data:
                                new = json.dumps(cleaned).encode("utf-8")
                                response._content = new  # type: ignore[attr-defined]
                                response.headers["Content-Length"] = str(len(new))
                    except Exception:
                        # Non-JSON success bodies pass through as-is
                        pass
            else:
                # Surface YNAB error details when available, and shape a uniform error payload
                err = {
                    "status": response.status_code,
                    "id": None,
                    "name": None,
                    "detail": None,
                    "request_id": response.headers.get("x-request-id"),
                }
                try:
                    j = response.json()
                    if isinstance(j, dict):
                        # YNAB typically returns { error: { id, name, detail } } or similar
                        e = j.get("error")
                        if isinstance(e, dict):
                            err["id"] = e.get("id")
                            err["name"] = e.get("name")
                            err["detail"] = e.get("detail") or e.get("message")
                        elif e is not None:
                            err["detail"] = str(e)
                except Exception:
                    # Not JSON; keep defaults
                    pass

                # Attach a uniform error JSON body for clients/inspectors
                try:
                    payload = {"error": {k: v for k, v in err.items() if v is not None}}
                    response._content = json.dumps(payload).encode("utf-8")  # type: ignore[attr-defined]
                    response.headers["Content-Length"] = str(len(response._content))
                    response.headers["Content-Type"] = "application/json"
                except Exception:
                    pass

                # 429-specific hint when rate limited
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    hint = f" Rate limited. Retry-After={retry_after}" if retry_after else " Rate limited."
                else:
                    hint = ""

                # Raise with a rich message (FastMCP surfaces this to MCP clients)
                msg = f"YNAB API error {response.status_code}:{hint}"
                if err["detail"]:
                    msg += f" {err['detail']}"
                elif err["name"]:
                    msg += f" {err['name']}"

                raise httpx.HTTPStatusError(
                    msg,
                    request=response.request,
                    response=response,
                )
        except httpx.HTTPError:
            raise
        except Exception as ex:
            # Never crash in hook; surface as HTTPError with context
            raise httpx.HTTPError(f"Response handling failed: {ex}")

    api_client = httpx.AsyncClient(
        base_url=base_url,
        headers=headers,
        timeout=timeout,
        event_hooks={"response": [_response_hook]},
    )

    maps = _build_route_maps(include_tags, exclude_tags, route_maps)

    # Force-enable the new OpenAPI parser so users don't need to set an env var
    os.environ.setdefault("FASTMCP_EXPERIMENTAL_ENABLE_NEW_OPENAPI_PARSER", "true")

    # Create the MCP server directly from the OpenAPI specification
    # Normalize tool names to snake_case via mcp_names mapping
    mcp_names = _build_mcp_names_from_spec(spec)

    mcp = FastMCP.from_openapi(
        openapi_spec=spec,
        client=api_client,
        name="YNAB MCP Server",
        timeout=timeout,
        route_maps=maps,
        route_map_fn=route_map_fn,
        mcp_names=mcp_names,
    )

    if enable_health_routes:
        # Health tool
        @mcp.tool(name="health", tags={"system"})
        def health() -> dict[str, str]:
            """Server health check."""
            return {"status": "ok"}

        # Optional HTTP health and debug endpoints (when transport is HTTP)
        try:
            from starlette.requests import Request
            from starlette.responses import JSONResponse, PlainTextResponse

            @mcp.custom_route("/health", methods=["GET"]) 
            async def health_route(_request: Request) -> PlainTextResponse:
                return PlainTextResponse("OK")

            @mcp.custom_route("/debug", methods=["GET"]) 
            async def debug_route(_request: Request) -> JSONResponse:
                info = {
                    "name": "YNAB MCP Server",
                    "base_url": base_url,
                    "spec_url": spec_url,
                }
                return JSONResponse(info)
        except Exception:
            # If Starlette is not available, just skip HTTP routes
            pass

    return mcp
