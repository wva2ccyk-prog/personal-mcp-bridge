## Summary

Describe what this change does and why.

## Boundary check

- [ ] Stays read-only (no write, move, delete, shell, agent, or browser behavior)
- [ ] Keeps alias-scoped, fail-closed, no-traversal path handling
- [ ] Does not add persistent memory, audit, or cache storage
- [ ] Public/tunnel mode still refuses weak tokens and never emits absolute paths

## Testing

- [ ] `python -m pytest -q` passes locally
- [ ] Added or updated tests for the changed behavior (or explained why not)

## Notes

Anything reviewers should know: tradeoffs, follow-ups, or open questions.
