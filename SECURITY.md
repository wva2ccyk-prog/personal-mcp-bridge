# Security

This is alpha software. It is read-only by design, but read access to your
files is still access. Treat the allowlist as the boundary that matters.

## Reporting

Please open a private security advisory or contact the maintainers before
filing a public issue for anything that could expose a user's files or token.

## Design guarantees

The bridge enforces these properties:

1. Fail closed. No allowlisted roots means every request is refused. There is
   no implicit "serve my home directory" default.
2. No traversal. Caller paths are POSIX-relative only. Absolute paths, `..`,
   drive letters, backslashes, and NUL bytes are rejected. Resolved paths must
   stay within the allowlisted root, and symlinks are not followed out of it.
3. Read-only. There is no write, delete, move, or execute path anywhere in the
   public surface.
4. No URL tokens in public mode. A persistent token passed via `?token=` is
   refused whenever public/tunnel mode is on, because URL tokens leak through
   logs, proxies, history, and referrers.
5. Localhost-only dispatch. The generic `/call` endpoint refuses any request
   that is forwarded (`X-Forwarded-For`/`Forwarded`) or from a non-loopback
   client. Remote callers can only reach the dedicated read-only endpoints.
6. No path leakage. Web-facing responses reference files as
   `alias/relative/path`. Absolute local paths are emitted only when
   `INCLUDE_LOCAL_PATHS=1` in private mode, and never in public mode.
7. Bounded reads. File reads and searches are size-capped so a caller cannot
   exhaust memory.

## Public/tunnel mode

Set `BRIDGE_PUBLIC_MODE=1` (or `BRIDGE_TUNNEL_MODE=1`) when the process may be
reachable off-localhost. The bridge then refuses to start unless:

- `BRIDGE_TOKEN` is set and at least 32 characters,
- `ALLOW_QUERY_TOKEN_AUTH` is not set,
- `INCLUDE_LOCAL_PATHS` is not set.

## What is intentionally absent

No agent runner, no shell execution, no file writes, no persistent browser
profile, no memory/audit/cache databases, no admin connector that could return
a raw token or a `?token=` URL. These were excluded from the public bridge on
purpose.
