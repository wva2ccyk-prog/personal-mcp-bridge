# Roadmap

This roadmap describes the direction for personal-mcp-bridge. The whole point of
this project is to be a small, auditable, read-only file bridge, so the roadmap
protects that: it stays read-only, fail-closed, and free of agent/automation
features. Anything that would turn it into a do-everything runtime is out of
scope by design.

Status legend: `planned`, `exploring`, `done`.

## Near term

- `done` Modernize packaging license metadata to SPDX.
- `planned` Add a short troubleshooting section for common setup mistakes
  (no roots configured, wrong alias, path outside an allowlisted root).
- `planned` Document the exact JSON shapes returned by `list_roots`,
  `read_file`, and `search` in one reference section.
- `planned` Add a small test that asserts public/tunnel mode refuses to start
  without a strong token, as living evidence of the fail-closed posture.

## Medium term

- `exploring` Optional read-only listing of a directory's entries (still
  alias-scoped, still no traversal) if a concrete operator need appears.
- `exploring` Configurable max file size and result limits surfaced as explicit
  settings rather than constants.

## Explicitly out of scope

- Writing, moving, or deleting files.
- Running shell commands, agents, or browser automation.
- Persisting any memory, audit, or cache database.
- Serving paths outside an allowlisted root, or emitting absolute local paths.

## How to influence the roadmap

Open a feature request issue describing the read-only access pattern you need.
Requests that keep the surface small and auditable are the best fit.
