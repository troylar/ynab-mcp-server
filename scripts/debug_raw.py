from __future__ import annotations

import argparse
import json
import os
from typing import Optional

import httpx

DEFAULT_BASE = os.environ.get("YNAB_BASE_URL", "https://api.ynab.com/v1")


def main() -> None:
    p = argparse.ArgumentParser(description="Raw HTTP debug against YNAB API")
    p.add_argument("path", help="API path starting with /, e.g. /budgets or /budgets/last-used/categories")
    p.add_argument("--method", default="GET", help="HTTP method (GET, POST, etc.)")
    p.add_argument("--base-url", default=DEFAULT_BASE, help="Base URL (default: %(default)s)")
    p.add_argument("--query", default=None, help="Query string (e.g. include_accounts=true)")
    p.add_argument("--json", dest="json_body", default=None, help="JSON body as a string")
    args = p.parse_args()

    token = os.environ.get("YNAB_ACCESS_TOKEN")
    if not token:
        raise SystemExit("YNAB_ACCESS_TOKEN is required")

    url = args.base_url.rstrip("/") + args.path
    if args.query:
        url += ("?" + args.query.lstrip("?"))

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "ynab-mcp-server/raw-debug",
    }

    kwargs = {}
    if args.json_body:
        try:
            kwargs["json"] = json.loads(args.json_body)
        except json.JSONDecodeError:
            raise SystemExit("--json must be valid JSON")

    method = (args.method or "GET").strip().upper()
    if not method:
        method = "GET"

    with httpx.Client(headers=headers, timeout=30.0) as client:
        resp = client.request(method, url, **kwargs)
        print("=== REQUEST ===")
        print(f"{method} {url}")
        print("Headers:")
        for k, v in headers.items():
            # do not print token value
            if k.lower() == "authorization":
                v = "Bearer ***"
            print(f"  {k}: {v}")
        if "json" in kwargs:
            print("Body (JSON):")
            print(json.dumps(kwargs["json"], indent=2))

        print("\n=== RESPONSE ===")
        print(f"Status: {resp.status_code}")
        print("Headers:")
        for k, v in resp.headers.items():
            print(f"  {k}: {v}")
        print("\nBody (raw):")
        print(resp.text)


if __name__ == "__main__":
    main()
