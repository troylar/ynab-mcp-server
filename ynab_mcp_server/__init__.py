"""YNAB MCP Server package."""

from importlib.metadata import version as _version

try:
    __version__ = _version("ynab-mcp-server")
except Exception:  # pragma: no cover
    __version__ = "0.0.0"

__all__ = ["__version__"]
