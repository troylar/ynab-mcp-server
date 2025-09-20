# YNAB MCP Server (FastMCP)

FastMCP-based MCP server for the YNAB API. It generates MCP tools for all YNAB endpoints directly from YNAB's OpenAPI specification and authenticates via Bearer token.

- Tools are auto-generated from OpenAPI and named in snake_case (e.g., `get_user`, `get_budgets`, `get_budget_by_id`).
- OpenAPI tags (e.g., `User`, `Budgets`) are propagated to tool metadata for discovery and tag-based filtering.
- Health tool and optional HTTP routes are included for easy monitoring.

---

## Quickstart

Prereqs: Python 3.11+, uv package manager, and a YNAB Personal Access Token.

1) Install uv (if needed)

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2) Install dependencies (editable) and dev tools

```bash
make install
# or directly with uv
# uv venv && uv pip install -U pip && uv pip install -e '.[dev]'
```

3) Set your token

```bash
export YNAB_ACCESS_TOKEN=ynab_pat_...
```

4) Explore tools (names + descriptions)

```bash
# Lists every generated tool with its description
make list-tools

# Tag-filtered lists (comma-separated)
INCLUDE_TAGS=User make list-tools
EXCLUDE_TAGS=internal make list-tools
```

5) Run the server

```bash
# STDIO transport (local tools)
make run

# HTTP transport (enables HTTP routes below)
make run-http  # defaults to http://127.0.0.1:8000
# Override host/port
HOST=0.0.0.0 PORT=9000 make run-http
```

6) Health and debug routes (HTTP only)

```bash
# After `make run-http`
curl http://127.0.0.1:8000/health   # → OK
curl http://127.0.0.1:8000/debug    # → {"name": "...", "base_url": ..., "spec_url": ...}
```

7) CI parity and coverage

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


### Tags

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

### Tools

- `create_account` — Creates a new account


**Path Parameters:**

- **budget_id** (Required): The id of the budget ("last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget)


**Request Body:**

The account to create. (Required)


**Request Properties:**


**Responses:**

- **201** (Success): The account was successfully created
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "account": "unknown_type"
  }
}
```

- **400**: The request could not be understood due to malformed syntax or validation error(s).
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `create_scheduled_transaction` — Creates a single scheduled transaction (a transaction with a future date).


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).


**Request Body:**

The scheduled transaction to create (Required)


**Request Properties:**


**Responses:**

- **201** (Success): The scheduled transaction was successfully created
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "scheduled_transaction": "unknown_type"
  }
}
```

- **400**: The request could not be understood due to malformed syntax or validation error(s).
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `create_transaction` — Creates a single transaction or multiple transactions.  If you provide a body containing a `transaction` object, a single transaction will be created and if you provide a body containing a `transactions` array, multiple transactions will be created.  Scheduled transactions (transactions with a future date) cannot be created on this endpoint.


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).


**Request Body:**

The transaction or transactions to create.  To create a single transaction you can specify a value for the `transaction` object and to create multiple transactions you can specify an array of `transactions`.  It is expected that you will only provide a value for one of these objects. (Required)


**Request Properties:**


**Responses:**

- **201** (Success): The transaction or transactions were successfully created
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "transaction_ids": [
      "string"
    ],
    "transaction": "unknown_type",
    "transactions": [
      "unknown_type"
    ],
    "server_knowledge": 1
  }
}
```

- **400**: The request could not be understood due to malformed syntax or validation error(s).
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **409**: A transaction on the same account with the same `import_id` already exists.
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `delete_scheduled_transaction` — Deletes a scheduled transaction


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).

- **scheduled_transaction_id** (Required): The id of the scheduled transaction


**Responses:**

- **200** (Success): The scheduled transaction was successfully deleted
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "scheduled_transaction": "unknown_type"
  }
}
```

- **404**: The scheduled transaction was not found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `delete_transaction` — Deletes a transaction


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).

- **transaction_id** (Required): The id of the transaction


**Responses:**

- **200** (Success): The transaction was successfully deleted
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "transaction": "unknown_type",
    "server_knowledge": 1
  }
}
```

- **404**: The transaction was not found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_account_by_id` — Returns a single account


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).

- **account_id** (Required): The id of the account


**Responses:**

- **200** (Success): The requested account
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "account": "unknown_type"
  }
}
```

- **404**: The requested account was not found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **default**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_accounts` — Returns all accounts


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).


**Query Parameters:**

- **last_knowledge_of_server**: The starting server knowledge.  If provided, only entities that have changed since `last_knowledge_of_server` will be included.


**Responses:**

- **200** (Success): The list of requested accounts
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "accounts": [
      "unknown_type"
    ],
    "server_knowledge": 1
  }
}
```

- **404**: No accounts were found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **default**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_budget_by_id` — Returns a single budget with all related entities.  This resource is effectively a full budget export.


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).


**Query Parameters:**

- **last_knowledge_of_server**: The starting server knowledge.  If provided, only entities that have changed since `last_knowledge_of_server` will be included.


**Responses:**

- **200** (Success): The requested budget
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "budget": "unknown_type",
    "server_knowledge": 1
  }
}
```

- **404**: The specified budget was not found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **default**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_budget_month` — Returns a single budget month


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).

- **month** (Required): The budget month in ISO format (e.g. 2016-12-01) ("current" can also be used to specify the current calendar month (UTC))


**Responses:**

- **200** (Success): The budget month detail
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "month": "unknown_type"
  }
}
```

- **404**: The budget month was not found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **default**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_budget_months` — Returns all budget months


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).


**Query Parameters:**

- **last_knowledge_of_server**: The starting server knowledge.  If provided, only entities that have changed since `last_knowledge_of_server` will be included.


**Responses:**

- **200** (Success): The list of budget months
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "months": [
      "unknown_type"
    ],
    "server_knowledge": 1
  }
}
```

- **404**: No budget months were found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **default**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_budget_settings_by_id` — Returns settings for a budget


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).


**Responses:**

- **200** (Success): The requested budget settings
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "settings": "unknown_type"
  }
}
```

- **404**: The specified Budget was not found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **default**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_budgets` — Returns budgets list with summary information


**Query Parameters:**

- **include_accounts**: Whether to include the list of budget accounts


**Responses:**

- **200** (Success): The list of budgets
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "budgets": [
      "unknown_type"
    ],
    "default_budget": "unknown_type"
  }
}
```

- **404**: No budgets were found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **default**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_categories` — Returns all categories grouped by category group.  Amounts (budgeted, activity, balance, etc.) are specific to the current budget month (UTC).


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).


**Query Parameters:**

- **last_knowledge_of_server**: The starting server knowledge.  If provided, only entities that have changed since `last_knowledge_of_server` will be included.


**Responses:**

- **200** (Success): The categories grouped by category group
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "category_groups": [
      "unknown_type"
    ],
    "server_knowledge": 1
  }
}
```

- **404**: No categories were found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **default**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_category_by_id` — Returns a single category.  Amounts (budgeted, activity, balance, etc.) are specific to the current budget month (UTC).


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).

- **category_id** (Required): The id of the category


**Responses:**

- **200** (Success): The requested category
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "category": "unknown_type"
  }
}
```

- **404**: The category not was found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **default**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_month_category_by_id` — Returns a single category for a specific budget month.  Amounts (budgeted, activity, balance, etc.) are specific to the current budget month (UTC).


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).

- **month** (Required): The budget month in ISO format (e.g. 2016-12-01) ("current" can also be used to specify the current calendar month (UTC))

- **category_id** (Required): The id of the category


**Responses:**

- **200** (Success): The requested month category
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "category": "unknown_type"
  }
}
```

- **404**: The month category was not was found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **default**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_payee_by_id` — Returns a single payee


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).

- **payee_id** (Required): The id of the payee


**Responses:**

- **200** (Success): The requested payee
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "payee": "unknown_type"
  }
}
```

- **404**: The payee was not found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **default**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_payee_location_by_id` — Returns a single payee location


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).

- **payee_location_id** (Required): id of payee location


**Responses:**

- **200** (Success): The payee location
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "payee_location": "unknown_type"
  }
}
```

- **404**: The payee location was not found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **default**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_payee_locations` — Returns all payee locations


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).


**Responses:**

- **200** (Success): The list of payee locations
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "payee_locations": [
      "unknown_type"
    ]
  }
}
```

- **404**: No payees locations were found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **default**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_payee_locations_by_payee` — Returns all payee locations for a specified payee


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).

- **payee_id** (Required): id of payee


**Responses:**

- **200** (Success): The list of requested payee locations
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "payee_locations": [
      "unknown_type"
    ]
  }
}
```

- **404**: No payees locations were found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **default**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_payees` — Returns all payees


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).


**Query Parameters:**

- **last_knowledge_of_server**: The starting server knowledge.  If provided, only entities that have changed since `last_knowledge_of_server` will be included.


**Responses:**

- **200** (Success): The requested list of payees
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "payees": [
      "unknown_type"
    ],
    "server_knowledge": 1
  }
}
```

- **404**: No payees were found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **default**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_scheduled_transaction_by_id` — Returns a single scheduled transaction


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).

- **scheduled_transaction_id** (Required): The id of the scheduled transaction


**Responses:**

- **200** (Success): The requested Scheduled Transaction
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "scheduled_transaction": "unknown_type"
  }
}
```

- **404**: The scheduled transaction was not found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **default**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_scheduled_transactions` — Returns all scheduled transactions


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).


**Query Parameters:**

- **last_knowledge_of_server**: The starting server knowledge.  If provided, only entities that have changed since `last_knowledge_of_server` will be included.


**Responses:**

- **200** (Success): The list of requested scheduled transactions
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "scheduled_transactions": [
      "unknown_type"
    ],
    "server_knowledge": 1
  }
}
```

- **404**: No scheduled transactions were found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **default**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_transaction_by_id` — Returns a single transaction


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).

- **transaction_id** (Required): The id of the transaction


**Responses:**

- **200** (Success): The requested transaction
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "transaction": "unknown_type",
    "server_knowledge": 1
  }
}
```

- **404**: The transaction was not found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **default**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_transactions` — Returns budget transactions, excluding any pending transactions


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).


**Query Parameters:**

- **since_date**: If specified, only transactions on or after this date will be included.  The date should be ISO formatted (e.g. 2016-12-30).

- **type**: If specified, only transactions of the specified type will be included. "uncategorized" and "unapproved" are currently supported.

- **last_knowledge_of_server**: The starting server knowledge.  If provided, only entities that have changed since `last_knowledge_of_server` will be included.


**Responses:**

- **200** (Success): The list of requested transactions
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "transactions": [
      "unknown_type"
    ],
    "server_knowledge": 1
  }
}
```

- **400**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **404**: No transactions were found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_transactions_by_account` — Returns all transactions for a specified account, excluding any pending transactions


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).

- **account_id** (Required): The id of the account


**Query Parameters:**

- **since_date**: If specified, only transactions on or after this date will be included.  The date should be ISO formatted (e.g. 2016-12-30).

- **type**: If specified, only transactions of the specified type will be included. "uncategorized" and "unapproved" are currently supported.

- **last_knowledge_of_server**: The starting server knowledge.  If provided, only entities that have changed since `last_knowledge_of_server` will be included.


**Responses:**

- **200** (Success): The list of requested transactions
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "transactions": [
      "unknown_type"
    ],
    "server_knowledge": 1
  }
}
```

- **404**: No transactions were found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **default**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_transactions_by_category` — Returns all transactions for a specified category


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).

- **category_id** (Required): The id of the category


**Query Parameters:**

- **since_date**: If specified, only transactions on or after this date will be included.  The date should be ISO formatted (e.g. 2016-12-30).

- **type**: If specified, only transactions of the specified type will be included. "uncategorized" and "unapproved" are currently supported.

- **last_knowledge_of_server**: The starting server knowledge.  If provided, only entities that have changed since `last_knowledge_of_server` will be included.


**Responses:**

- **200** (Success): The list of requested transactions
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "transactions": [
      "unknown_type"
    ],
    "server_knowledge": 1
  }
}
```

- **404**: No transactions were found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **default**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_transactions_by_month` — Returns all transactions for a specified month


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).

- **month** (Required): The budget month in ISO format (e.g. 2016-12-01) ("current" can also be used to specify the current calendar month (UTC))


**Query Parameters:**

- **since_date**: If specified, only transactions on or after this date will be included.  The date should be ISO formatted (e.g. 2016-12-30).

- **type**: If specified, only transactions of the specified type will be included. "uncategorized" and "unapproved" are currently supported.

- **last_knowledge_of_server**: The starting server knowledge.  If provided, only entities that have changed since `last_knowledge_of_server` will be included.


**Responses:**

- **200** (Success): The list of requested transactions
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "transactions": [
      "unknown_type"
    ],
    "server_knowledge": 1
  }
}
```

- **404**: No transactions were found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **default**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_transactions_by_payee` — Returns all transactions for a specified payee


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).

- **payee_id** (Required): The id of the payee


**Query Parameters:**

- **since_date**: If specified, only transactions on or after this date will be included.  The date should be ISO formatted (e.g. 2016-12-30).

- **type**: If specified, only transactions of the specified type will be included. "uncategorized" and "unapproved" are currently supported.

- **last_knowledge_of_server**: The starting server knowledge.  If provided, only entities that have changed since `last_knowledge_of_server` will be included.


**Responses:**

- **200** (Success): The list of requested transactions
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "transactions": [
      "unknown_type"
    ],
    "server_knowledge": 1
  }
}
```

- **404**: No transactions were found
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

- **default**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `get_user` — Returns authenticated user information


**Responses:**

- **200** (Success): The user info
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "user": "unknown_type"
  }
}
```

- **default**: An error occurred
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `health` — Server health check.
- `import_transactions` — Imports available transactions on all linked accounts for the given budget.  Linked accounts allow transactions to be imported directly from a specified financial institution and this endpoint initiates that import.  Sending a request to this endpoint is the equivalent of clicking "Import" on each account in the web application or tapping the "New Transactions" banner in the mobile applications.  The response for this endpoint contains the transaction ids that have been imported.


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).


**Responses:**

- **200**: The request was successful but there were no transactions to import
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "transaction_ids": [
      "string"
    ]
  }
}
```

- **201** (Success): One or more transactions were imported successfully
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "transaction_ids": [
      "string"
    ]
  }
}
```

- **400**: The request could not be understood due to malformed syntax or validation error(s)
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `update_category` — Update a category


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).

- **category_id** (Required): The id of the category


**Request Body:**

The category to update (Required)


**Request Properties:**


**Responses:**

- **200** (Success): The category was successfully updated
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "category": "unknown_type",
    "server_knowledge": 1
  }
}
```

- **400**: The request could not be understood due to malformed syntax or validation error(s)
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `update_month_category` — Update a category for a specific month.  Only `budgeted` amount can be updated.


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).

- **month** (Required): The budget month in ISO format (e.g. 2016-12-01) ("current" can also be used to specify the current calendar month (UTC))

- **category_id** (Required): The id of the category


**Request Body:**

The category to update.  Only `budgeted` amount can be updated and any other fields specified will be ignored. (Required)


**Request Properties:**


**Responses:**

- **200** (Success): The month category was successfully updated
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "category": "unknown_type",
    "server_knowledge": 1
  }
}
```

- **400**: The request could not be understood due to malformed syntax or validation error(s)
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `update_payee` — Update a payee


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).

- **payee_id** (Required): The id of the payee


**Request Body:**

The payee to update (Required)


**Request Properties:**


**Responses:**

- **200** (Success): The payee was successfully updated
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "payee": "unknown_type",
    "server_knowledge": 1
  }
}
```

- **400**: The request could not be understood due to malformed syntax or validation error(s)
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `update_scheduled_transaction` — Updates a single scheduled transaction


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).

- **scheduled_transaction_id** (Required): The id of the scheduled transaction


**Request Body:**

The scheduled transaction to update (Required)


**Request Properties:**


**Responses:**

- **200** (Success): The scheduled transaction was successfully updated
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "scheduled_transaction": "unknown_type"
  }
}
```

- **400**: The request could not be understood due to malformed syntax or validation error(s)
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `update_transaction` — Updates a single transaction


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).

- **transaction_id** (Required): The id of the transaction


**Request Body:**

The transaction to update (Required)


**Request Properties:**


**Responses:**

- **200** (Success): The transaction was successfully updated
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "transaction": "unknown_type",
    "server_knowledge": 1
  }
}
```

- **400**: The request could not be understood due to malformed syntax or validation error(s)
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```
- `update_transactions` — Updates multiple transactions, by `id` or `import_id`.


**Path Parameters:**

- **budget_id** (Required): The id of the budget. "last-used" can be used to specify the last used budget and "default" can be used if default budget selection is enabled (see: https://api.ynab.com/#oauth-default-budget).


**Request Body:**

The transactions to update. Each transaction must have either an `id` or `import_id` specified. If `id` is specified as null an `import_id` value can be provided which will allow transaction(s) to be updated by its `import_id`. If an `id` is specified, it will always be used for lookup.  You should not specify both `id` and `import_id`.  Updating an `import_id` on an existing transaction is not allowed; if an `import_id` is specified, it will only be used to lookup the transaction. (Required)


**Request Properties:**


**Responses:**

- **209**: The transactions were successfully updated
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "data": {
    "transaction_ids": [
      "string"
    ],
    "transaction": "unknown_type",
    "transactions": [
      "unknown_type"
    ],
    "server_knowledge": 1
  }
}
```

- **400**: The request could not be understood due to malformed syntax or validation error(s).
  - Content-Type: `application/json`

  - **Response Properties:**

  - **Example:**
```json
{
  "error": "unknown_type"
}
```

<!-- TOOLS_SNAPSHOT_END -->
