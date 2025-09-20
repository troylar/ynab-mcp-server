# YNAB MCP Server (FastMCP)

FastMCP-based MCP server for the YNAB API. It generates MCP tools for all YNAB endpoints directly from YNAB's OpenAPI specification and authenticates via Bearer token.

- Tools are auto-generated from OpenAPI and named in snake_case (e.g., `get_user`, `get_budgets`, `get_budget_by_id`).
- OpenAPI tags (e.g., `User`, `Budgets`) are propagated to tool metadata for discovery and tag-based filtering.
- Health tool and optional HTTP routes are included for easy monitoring.

---

## Quickstart

Prereqs: Python 3.11+, uv package manager, and a YNAB Personal Access Token.

1. Install uv (if needed)

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Install dependencies (editable) and dev tools

```bash
make install
# or directly with uv
# uv venv && uv pip install -U pip && uv pip install -e '.[dev]'
```

3. Set your token

```bash
export YNAB_ACCESS_TOKEN=ynab_pat_...
```

4. Explore tools (names + descriptions)

```bash
# Lists every generated tool with its description
make list-tools

# Tag-filtered lists (comma-separated)
INCLUDE_TAGS=User make list-tools
EXCLUDE_TAGS=internal make list-tools
```

5. Run the server

```bash
# STDIO transport (local tools)
make run

# HTTP transport (enables HTTP routes below)
make run-http  # defaults to http://127.0.0.1:8000
# Override host/port
HOST=0.0.0.0 PORT=9000 make run-http
```

6. Health and debug routes (HTTP only)

```bash
# After `make run-http`
curl http://127.0.0.1:8000/health   # → OK
curl http://127.0.0.1:8000/debug    # → {"name": "...", "base_url": ..., "spec_url": ...}
```

7. CI parity and coverage

```bash
# Lint + typecheck + test
make ci

# HTML coverage report at htmlcov/index.html
make coverage
```

---

## Install in Claude Desktop, Cursor, and Windsurf (MCP)

Below are working examples for wiring this server into popular MCP-capable apps. All examples assume `uv` is on your PATH and `ynab-mcp-server` is installed (Quickstart above). The server uses STDIO by default.

Environment that all configs need:

- `YNAB_ACCESS_TOKEN`: required. Your YNAB Personal Access Token.
- Optional filters: `INCLUDE_TAGS`, `EXCLUDE_TAGS` (comma-separated)
- Optional overrides: `YNAB_OPENAPI_SPEC_URL`, `YNAB_BASE_URL`

### Claude Desktop (mcpServers)

Add to your Claude Desktop MCP config (e.g., `claude_desktop_config.json` or equivalent):

```json
{
  "mcpServers": {
    "ynab": {
      "command": "uv",
      "args": ["run", "ynab-mcp-server"],
      "env": {
        "YNAB_ACCESS_TOKEN": "ynab_pat_xxx",
        "INCLUDE_TAGS": "",
        "EXCLUDE_TAGS": ""
      }
    }
  }
}
```

Notes:

- Uses STDIO transport; Claude will launch the server on demand.
- Set `INCLUDE_TAGS`/`EXCLUDE_TAGS` as needed.

### Cursor (MCP)

Cursor supports MCP servers with the same `command`/`args` pattern. Add to your Cursor MCP configuration (for example, in your Cursor settings file if available):

```json
{
  "mcpServers": {
    "ynab": {
      "command": "uv",
      "args": ["run", "ynab-mcp-server"],
      "env": {
        "YNAB_ACCESS_TOKEN": "ynab_pat_xxx",
        "INCLUDE_TAGS": "",
        "EXCLUDE_TAGS": ""
      }
    }
  }
}
```

Notes:

- The exact file location/name can vary by Cursor version. The structure above matches common MCP conventions.

### Windsurf

Windsurf can launch MCP servers with an MCP tool configuration. Example JSON snippet:

```json
{
  "tools": [
    {
      "type": "mcp",
      "name": "ynab",
      "command": "uv",
      "args": ["run", "ynab-mcp-server"],
      "env": {
        "YNAB_ACCESS_TOKEN": "ynab_pat_xxx",
        "INCLUDE_TAGS": "",
        "EXCLUDE_TAGS": ""
      }
    }
  ]
}
```

Notes:

- This launches the MCP server via STDIO. If you prefer HTTP, see below.

### HTTP transport alternative

You can run the server via HTTP and point your client to it. Start the server:

```bash
HOST=127.0.0.1 PORT=8000 YNAB_ACCESS_TOKEN=ynab_pat_xxx make run-http
```

Then your MCP-capable app can be configured to connect over HTTP if it supports MCP-over-HTTP, or you can mount the FastMCP app into a Starlette/FastAPI app as needed.

---

## Advanced Topics

- **Tag-based filtering**

  - Include only certain OpenAPI-tagged operations:
    - `INCLUDE_TAGS=User,Budgets make list-tools`
  - Exclude certain tags:
    - `EXCLUDE_TAGS=internal,deprecated make list-tools`
  - Combine include & exclude. Precedence: exclude > include.

- **Custom Route Mapping**
  The server uses FastMCP’s OpenAPI integration with `RouteMap` support via `_build_route_maps()` in `ynab_mcp_server/server.py`. You can alter behavior by providing `route_maps` or `route_map_fn` to `create_server()`.

  Examples (see FastMCP docs for more):

  - Convert specific path prefixes to tools
  - Exclude `admin` endpoints
  - Map GET-with-path-params to resource templates

- **Tool naming normalization**

  - OpenAPI `operationId` values are normalized to snake_case (e.g., `getUser` → `get_user`) via the `mcp_names` mapping passed to `FastMCP.from_openapi()`.

- **OpenAPI tags in tool metadata**

  - OpenAPI tags are available on each tool in `tool.meta['_fastmcp']['tags']` for client-side discovery.

- **Spec fetching and caching** (`ynab_mcp_server/openapi_loader.py`)

  - Fetches YAML or JSON from `https://api.ynab.com/papi/open_api_spec.yaml`.
  - Writes through to cache; on fetch failure, falls back to cached file if present.
  - Override cache path with `YNAB_MCP_SPEC_CACHE`.

- **Configuration**

  - `YNAB_ACCESS_TOKEN`: Required; Bearer token for YNAB API.
  - `YNAB_OPENAPI_SPEC_URL`: Override OpenAPI spec URL (default YNAB spec URL).
  - `YNAB_BASE_URL`: Override API base URL (default `https://api.ynab.com/v1`).
  - `INCLUDE_TAGS`, `EXCLUDE_TAGS`: Filters for tool exposure (comma-separated).

- **uv lockfile**
  - Generate/update lockfile: `make lock` → creates `uv.lock`
  - Strict sync from lockfile: `make sync`
  - Recommended to commit `uv.lock` for reproducible installs.

---

## Tools Inventory

The full set of tools is generated from the YNAB OpenAPI spec and may evolve with YNAB updates. Tools are named in snake_case and grouped by OpenAPI tags. Use these commands to view the live inventory on your machine:

```bash
# List all tags discovered
make list-tags

# List all tools with descriptions (optionally filtered by tags)
make list-tools
INCLUDE_TAGS=User make list-tools
EXCLUDE_TAGS=internal make list-tools
```

### Current tags (example output)

From a recent run:

- Accounts
- Budgets
- Categories
- Months
- Payee Locations
- Payees
- Scheduled Transactions
- Transactions
- User
- system

### Example tools (subset)

- `health` — Server health check (local tool)
- `get_user` — Retrieve user information
- `get_budgets` — List budgets
- `get_budget_by_id` — Get a budget by ID (e.g., `last-used`)
- `get_categories` — List categories (per budget)
- `get_accounts` — List accounts (per budget)
- `get_transactions` — List transactions (per budget)
- `create_account` — Create an account (per budget)

Run `make list-tools` to see the full, live list with descriptions from your current spec.

---

## Development

- **Repository tasks** (uv-based): see `Makefile` for:
  - `install`, `lint`, `typecheck`, `test`, `ci`, `coverage`
  - `run`, `run-http`, `list-tools`, `list-tags`
- **Tests**: Pytest + Respx stubs; see `tests/` directory.
- **CI**: GitHub Actions runs Ruff, MyPy, and Pytest using uv.

Contributions welcome! Open an issue or PR if you’d like additional helpers or custom mappings.

<!-- TOOLS_SNAPSHOT_START -->

## Tools Inventory (Live Snapshot)

This section is generated from your current environment. To refresh, run: `make snapshot-tools`.

| Tool                              | Description                                                                          |
| --------------------------------- | ------------------------------------------------------------------------------------ |
| `create_account`                  | Creates a new account                                                                |
| `create_scheduled_transaction`    | Creates a single scheduled transaction (a transaction with a future date).           |
| `create_transaction`              | Creates a single transaction or multiple transactions.                               |
| `delete_scheduled_transaction`    | Deletes a scheduled transaction                                                      |
| `delete_transaction`              | Deletes a transaction                                                                |
| `get_account_by_id`               | Returns a single account                                                             |
| `get_accounts`                    | Returns all accounts                                                                 |
| `get_budget_by_id`                | Returns a single budget with all related entities.                                   |
| `get_budget_month`                | Returns a single budget month                                                        |
| `get_budget_months`               | Returns all budget months                                                            |
| `get_budget_settings_by_id`       | Returns settings for a budget                                                        |
| `get_budgets`                     | Returns budgets list with summary information                                        |
| `get_categories`                  | Returns all categories grouped by category group.                                    |
| `get_category_by_id`              | Returns a single category.                                                           |
| `get_month_category_by_id`        | Returns a single category for a specific budget month.                               |
| `get_payee_by_id`                 | Returns a single payee                                                               |
| `get_payee_location_by_id`        | Returns a single payee location                                                      |
| `get_payee_locations`             | Returns all payee locations                                                          |
| `get_payee_locations_by_payee`    | Returns all payee locations for a specified payee                                    |
| `get_payees`                      | Returns all payees                                                                   |
| `get_scheduled_transaction_by_id` | Returns a single scheduled transaction                                               |
| `get_scheduled_transactions`      | Returns all scheduled transactions                                                   |
| `get_transaction_by_id`           | Returns a single transaction                                                         |
| `get_transactions`                | Returns budget transactions, excluding any pending transactions                      |
| `get_transactions_by_account`     | Returns all transactions for a specified account, excluding any pending transactions |
| `get_transactions_by_category`    | Returns all transactions for a specified category                                    |
| `get_transactions_by_month`       | Returns all transactions for a specified month                                       |
| `get_transactions_by_payee`       | Returns all transactions for a specified payee                                       |
| `get_user`                        | Returns authenticated user information                                               |
| `health`                          | Server health check.                                                                 |
| `import_transactions`             | Imports available transactions on all linked accounts for the given budget.          |
| `update_category`                 | Update a category                                                                    |
| `update_month_category`           | Update a category for a specific month.                                              |
| `update_payee`                    | Update a payee                                                                       |
| `update_scheduled_transaction`    | Updates a single scheduled transaction                                               |
| `update_transaction`              | Updates a single transaction                                                         |
| `update_transactions`             | Updates multiple transactions, by `id` or `import_id`.                               |

<!-- TOOLS_SNAPSHOT_END -->
