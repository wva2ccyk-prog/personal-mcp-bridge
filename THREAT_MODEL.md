# Threat model (short)

## Assets

- The contents of allowlisted local directories.
- The bearer token, when one is configured.
- The fact and layout of the operator's local filesystem (path disclosure).

## Trust boundaries

- Loopback caller (the operator's own machine) is semi-trusted: in private
  mode with no token, loopback may call the read-only endpoints and the
  localhost-only `/call`.
- Remote/forwarded caller is untrusted: it can only reach the dedicated
  read-only endpoints, and only with a valid bearer token in public mode.

## Adversaries and mitigations

1. Remote attacker without a token.
   In public mode, all dedicated endpoints require a valid bearer token; the
   server refuses to start without a strong one. `/call` is refused outright
   for forwarded/remote requests.

2. Attacker trying path traversal or symlink escape.
   Paths are relative-only and validated; resolved paths must stay within the
   allowlisted root; symlinks are not followed out of the root.

3. Token leakage via URL.
   `?token=` persistent-token auth is refused in public mode and off by default
   locally, so tokens do not end up in logs, history, or referrers.

4. Path/topology disclosure.
   Responses use alias-relative refs. Absolute paths are emitted only with an
   explicit private-mode debug flag, never in public mode.

5. Resource exhaustion.
   Reads and searches are size- and match-bounded.

## Out of scope

- A malicious operator allowlisting a sensitive directory on purpose.
- Transport encryption (run behind your own TLS-terminating tunnel).
- Multi-tenant isolation: this is a single-operator tool.
