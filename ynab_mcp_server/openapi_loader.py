from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx
import yaml

DEFAULT_SPEC_URL = "https://api.ynab.com/papi/open_api_spec.yaml"
CACHE_ENV = "YNAB_MCP_SPEC_CACHE"


def _default_cache_path() -> Path:
    base = os.environ.get("XDG_CACHE_HOME", os.path.join(Path.home(), ".cache"))
    return Path(base) / "ynab-mcp-server" / "open_api_spec.yaml"


async def fetch_openapi_spec(
    spec_url: str = DEFAULT_SPEC_URL,
    *,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Fetch the OpenAPI spec from a URL (YAML or JSON) and return it as a dict.

    Falls back to cached file if available and network fetch fails.
    You can override the cache location by setting YNAB_MCP_SPEC_CACHE.
    """
    cache_path = Path(os.environ.get(CACHE_ENV, str(_default_cache_path())))
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(spec_url)
            resp.raise_for_status()
            text = resp.text
    except Exception:
        if cache_path.exists():
            # Fallback to cache
            return _parse_spec(cache_path.read_text(encoding="utf-8"))
        raise

    # Write-through cache
    try:
        cache_path.write_text(text, encoding="utf-8")
    except Exception:
        # Cache failures are non-fatal
        pass

    return _parse_spec(text)


def _parse_spec(text: str) -> dict[str, Any]:
    # Try JSON first, then YAML
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("OpenAPI spec content is not a mapping")
    return data
