# personal-mcp-bridge

A minimal, read-only bridge that lets an MCP client (or any HTTP caller) browse
a few **allowlisted** local directories safely. It does three things:

- `list_roots` - list the directories you allowlisted, by public alias
- `read_file` - read one text file inside an allowlisted root
- `search` - search text files under an allowlisted root

That is the whole surface. It is intentionally small.

## What this is not

This is **not** a full personal automation layer. It does not run agents, write
files, run shell commands, drive a browser, or keep any memory, audit, or cache
database. It is an alpha, read-only file bridge with safe defaults. If you came
looking for a do-everything assistant runtime, this is the deliberately boring,
auditable subset.

## Safety model in one paragraph

Fail closed. With no roots configured, every request is blocked. Paths are
relative-only with no traversal, no drive letters, and no symlink escapes. In
public/tunnel mode the bridge refuses to start without a strong token, refuses
tokens passed in the URL, refuses the generic `/call` endpoint for any
forwarded/remote request, and never emits an absolute local path. See
[SECURITY.md](SECURITY.md) and [THREAT_MODEL.md](THREAT_MODEL.md).

## Install

Requires Python 3.10+.

```bash
python -m pip install -e .
# or, just install the runtime deps:
python -m pip install starlette uvicorn
```

## Run the demo (no real files touched)

The demo allowlists only the bundled synthetic `demo/mock_data` directory and
exercises all three tools in-process:

```bash
python demo/run_demo.py
```

You will see `list_roots`, a file read, a search hit on mock data, and a
traversal attempt being refused.

## Run the server against your own files

Allowlist one or more directories, then start the bridge on loopback:

```bash
export BRIDGE_ROOTS="notes=/path/to/notes;docs=/path/to/work/docs"
python -m personal_mcp_bridge
# serving on http://127.0.0.1:8787
```

Then:

```bash
curl http://127.0.0.1:8787/roots
curl "http://127.0.0.1:8787/read?root=notes&path=welcome.md"
curl "http://127.0.0.1:8787/search?root=notes&q=budget"
```

On loopback with no token set, local calls are allowed for convenience. To
require a token even locally, set `BRIDGE_TOKEN` and send
`Authorization: Bearer <token>`.

## Exposing it beyond localhost

Don't, unless you mean it. If you put this behind a tunnel, set
`BRIDGE_PUBLIC_MODE=1` and a strong `BRIDGE_TOKEN` (>=32 chars). The bridge will
refuse to start otherwise. Even then, only the dedicated read-only endpoints are
remote-reachable; the generic `/call` dispatch stays localhost-only.

## Status

Alpha. Read-only. Expect rough edges. Issues and PRs welcome.
