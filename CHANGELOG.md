# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project aims
to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html) once it
leaves alpha.

## [Unreleased]

### Changed
- Modernized packaging license metadata to the SPDX `license = "MIT"` string
  plus `license-files`, removing the deprecated setuptools license table.

### Documentation
- Added this changelog, a public `ROADMAP.md`, and GitHub issue/pull-request
  templates to make maintenance and contribution expectations explicit.

## [0.1.0] - 2026-06-30

### Added
- Initial public alpha release of the minimal, read-only, allowlisted MCP file
  bridge: `list_roots`, `read_file`, and `search` over public aliases.
- Bundled in-process demo against synthetic `demo/mock_data` showing the three
  tools and a refused traversal attempt.
- GitHub Actions CI running the test suite on each push.

### Security
- Fail-closed defaults: no roots configured means every request is blocked.
- Relative-only paths with no traversal, drive letters, or symlink escapes.
- Hardened public/tunnel mode: refuses to start without a strong token, refuses
  tokens in the URL, refuses the generic `/call` endpoint for forwarded
  requests, and never emits absolute local paths. See `SECURITY.md` and
  `THREAT_MODEL.md`.

[Unreleased]: https://github.com/wva2ccyk-prog/personal-mcp-bridge/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/wva2ccyk-prog/personal-mcp-bridge/releases/tag/v0.1.0
