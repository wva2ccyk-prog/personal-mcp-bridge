"""personal-mcp-bridge: a minimal, read-only, allowlisted MCP bridge (alpha).

This is NOT a full personal automation layer. It exposes three read-only
capabilities over allowlisted local directories: list roots, read a file, and
search text. It is designed to fail closed and to never leak absolute local
paths or auth tokens in any web-facing response.
"""

__version__ = "0.1.0"
