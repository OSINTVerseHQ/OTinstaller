# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Contact email and OSINTverse social links in the README and `otinstaller about`

## [0.0.2] - 2026-10-11

### Added
- Startup banner for init, about, and a bare invocation
- `requires_python` on registry entries, with install failing early when the interpreter is too old
- `long_running` flag so whatsapp-osint and instagram-monitor are left out of `--all` and auto

### Changed
- README rewritten for the PyPI page, with absolute links and project URLs
- pyyaml pinned to 6.0.3 and ruff pinned to 0.16.10

### Fixed
- Registry input types and entrypoints for ghunt, theharvester, bbot, linkook, spiderfoot, ignorant, aliens-eye, telepathy, and neutrosint
- Git-installed tools pinned to full commit SHAs
- Removed the fabricated ghunt example output
- Interrupted runs print the real output path
- Result folders use the typed input value when no other target name is available

## [0.0.1] - 2026-09-29

### Added
- Initial release
- Basic tool management: install, remove, run, update, list, search, info
- Parallel tool execution with configurable concurrency
- Result storage with metadata and SHA256
- API key management via ~/.otinstaller/.env
- Responsible use notice on first run
- Auto-detect target type with the auto command
- Example output viewer
- Resume interrupted jobs
- Doctor diagnostics
- Typed input prefixes: u: (username), e: (email), p: (phone), d: (domain), url: (URL), q: (query), geo: (coordinates), tg: (Telegram channel)
- `--all` mode for the run command
- `--include-credentialed` flag for `--all`
- check-updates command
- `--tools` option for update and check-updates
- `--json` output and `--yes` / `-y` on commands
- Stable exit codes: 0 success, 1 error, 2 invalid input, 130 interrupted
- `ot` command alias
- Tools added for that release: Blackbird, Telegram Phone Number Checker, Auto Archiver, edgar-tool, instagram-location-search, Telepathy

### Fixed
- Tool name collision between a bare tool name and a subcommand
- Input type validation for `--all`
