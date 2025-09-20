# Makefile for YNAB MCP Server (uv-based)
# Usage: make [target]

# --- Config ----
UV ?= uv
APP := ynab-mcp-server

# Optional filters (comma-separated)
INCLUDE_TAGS ?=
EXCLUDE_TAGS ?=

# Colors
RESET=\033[0m
BOLD=\033[1m
BLUE=\033[34m
GREEN=\033[32m
YELLOW=\033[33m

.DEFAULT_GOAL := help

## Create uv virtualenv and install dev deps
venv:
	@printf "$(BLUE)▶ Creating uv venv & installing dev deps...$(RESET)\n"
	@$(UV) venv
	@$(UV) pip install -U pip
	@$(UV) pip install -e '.[dev]'
	@printf "$(GREEN)✓ uv venv ready$(RESET)\n"

## Install project (editable) + dev deps (idempotent)
install: venv
	@:

## Lint with Ruff (auto-fix)
lint:
	@$(UV) run ruff check . --fix

## Type-check with MyPy
typecheck:
	@$(UV) run mypy ynab_mcp_server

## Run tests with Pytest
test:
	@$(UV) run pytest -q

## Run tests in verbose mode
testv:
	@$(UV) run pytest -vv

## List generated tools with descriptions (respects INCLUDE_TAGS/EXCLUDE_TAGS; requires YNAB_ACCESS_TOKEN)
list-tools:
	@INCLUDE_TAGS="$(INCLUDE_TAGS)" EXCLUDE_TAGS="$(EXCLUDE_TAGS)" YNAB_ACCESS_TOKEN="$$YNAB_ACCESS_TOKEN" \
		$(UV) run python scripts/list_tools_describe.py

## List generated tools (names only)
list-tools-names:
	@INCLUDE_FLAG=""; EXCLUDE_FLAG=""; \
	if [ -n "$(INCLUDE_TAGS)" ]; then INCLUDE_FLAG="--include-tags $(INCLUDE_TAGS)"; fi; \
	if [ -n "$(EXCLUDE_TAGS)" ]; then EXCLUDE_FLAG="--exclude-tags $(EXCLUDE_TAGS)"; fi; \
	YNAB_ACCESS_TOKEN=$$YNAB_ACCESS_TOKEN $(UV) run $(APP) $$INCLUDE_FLAG $$EXCLUDE_FLAG --list-tools

## Show a tool's input schema (set NAME or pass as arg); respects filters
tool-schema:
	@NAME="$(NAME)" INCLUDE_TAGS="$(INCLUDE_TAGS)" EXCLUDE_TAGS="$(EXCLUDE_TAGS)" YNAB_ACCESS_TOKEN="$$YNAB_ACCESS_TOKEN" \
		$(UV) run python scripts/tool_schema.py $$NAME

## List unique OpenAPI tags across generated tools (respects filters; requires YNAB_ACCESS_TOKEN)
list-tags:
	@echo "Listing tags (filters: INCLUDE=$(INCLUDE_TAGS) EXCLUDE=$(EXCLUDE_TAGS))"
	@INCLUDE_TAGS="$(INCLUDE_TAGS)" EXCLUDE_TAGS="$(EXCLUDE_TAGS)" YNAB_ACCESS_TOKEN="$$YNAB_ACCESS_TOKEN" \
		$(UV) run python scripts/list_tags.py

## List tools with descriptions (respects filters; requires YNAB_ACCESS_TOKEN)
list-tools-describe:
	@INCLUDE_TAGS="$(INCLUDE_TAGS)" EXCLUDE_TAGS="$(EXCLUDE_TAGS)" YNAB_ACCESS_TOKEN="$$YNAB_ACCESS_TOKEN" \
		$(UV) run python scripts/list_tools_describe.py

## Run MCP server (STDIO) (respects filters; requires YNAB_ACCESS_TOKEN)
run:
	@INCLUDE_FLAG=""; EXCLUDE_FLAG=""; \
	if [ -n "$(INCLUDE_TAGS)" ]; then INCLUDE_FLAG="--include-tags $(INCLUDE_TAGS)"; fi; \
	if [ -n "$(EXCLUDE_TAGS)" ]; then EXCLUDE_FLAG="--exclude-tags $(EXCLUDE_TAGS)"; fi; \
	YNAB_ACCESS_TOKEN=$$YNAB_ACCESS_TOKEN $(UV) run $(APP) $$INCLUDE_FLAG $$EXCLUDE_FLAG

## Run MCP server over HTTP (respects filters; requires YNAB_ACCESS_TOKEN)
run-http:
	@HOST="$(HOST)" PORT="$(PORT)" INCLUDE_TAGS="$(INCLUDE_TAGS)" EXCLUDE_TAGS="$(EXCLUDE_TAGS)" YNAB_ACCESS_TOKEN="$$YNAB_ACCESS_TOKEN" \
		$(UV) run python scripts/run_http.py

## Lint, typecheck, and test (CI parity)
ci: lint typecheck test
	@printf "$(GREEN)All checks passed$(RESET)\n"

## Format with Ruff (imports/order only)
format:
	@$(UV) run ruff check . --fix

## Generate or update uv lockfile (uv.lock)
lock:
	@$(UV) lock

## Sync environment strictly to lockfile
sync:
	@$(UV) sync --frozen

## Update README with a live snapshot of current tools (requires YNAB_ACCESS_TOKEN)
snapshot-tools:
	@INCLUDE_TAGS="$(INCLUDE_TAGS)" EXCLUDE_TAGS="$(EXCLUDE_TAGS)" YNAB_ACCESS_TOKEN="$$YNAB_ACCESS_TOKEN" \
		$(UV) run python scripts/update_readme_snapshot.py
	@printf "$(GREEN)✓ README tools snapshot updated$(RESET)\n"

## Clean caches and build artifacts
clean:
	@printf "$(YELLOW)Cleaning build and cache artifacts...$(RESET)\n"
	@rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage* dist build *.egg-info
	@find . -name '__pycache__' -type d -prune -exec rm -rf {} +
	@printf "$(GREEN)✓ Clean complete$(RESET)\n"

## Show this help
help:
	@printf "\n$(BOLD)YNAB MCP Server — Developer Commands (uv)$(RESET)\n\n"
	@printf "$(BLUE)Environment$(RESET)\n"
	@printf "  - Export your token:  export YNAB_ACCESS_TOKEN=ynab_pat_...\n\n"
	@printf "$(BLUE)Common Tasks$(RESET)\n"
	@awk 'BEGIN {FS = ":.*##"; printf "  %-18s %s\n", "Target", "Description"} /^[a-zA-Z0-9_\-]+:.*##/ { printf "  %-18s %s\n", $$1, $$2 }' $(MAKEFILE_LIST) | sort
	@printf "\n$(BLUE)Filters$(RESET)\n"
	@printf "  - INCLUDE_TAGS=User,Budgets  (comma-separated)\n"
	@printf "  - EXCLUDE_TAGS=internal,deprecated\n\n"
	@printf "$(BLUE)Examples$(RESET)\n"
	@printf "  make install       # create uv venv and install dev deps\n"
	@printf "  make ci            # lint + typecheck + tests\n"
	@printf "  make coverage      # run tests with coverage → htmlcov/index.html\n"
	@printf "  make lock          # generate/update uv.lock\n"
	@printf "  make sync          # sync environment strictly to uv.lock\n"
	@printf "  make list-tags     # show all OpenAPI tags available\n"
	@printf "  make list-tools    # list generated tools (respects filters)\n"
	@printf "  make run           # run STDIO MCP server\n"
	@printf "  make run-http      # run HTTP server (HOST, PORT env vars supported)\n"
	@printf "     e.g., HOST=0.0.0.0 PORT=9000 make run-http\n\n"
	@printf "$(BLUE)Notes$(RESET)\n"
	@printf "  - Uses uv for all commands; no manual venv activation needed.\n"
	@printf "  - Consider committing uv.lock for reproducible installs.\n"
	@printf "  - See README.md for more details.\n\n"

.PHONY: venv install lint typecheck test testv list-tools list-tags run run-http ci format clean help