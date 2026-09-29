# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Typed input prefixes: u: (username), e: (email), p: (phone), d: (domain), url: (URL), q: (query), geo: (coordinates), 	g: (Telegram channel)
- --all mode for 
un command: run every installed tool supporting the given input types (-a short form)
- --include-credentialed flag for --all mode to include tools requiring API credentials
- check-updates command: read-only check for available updates
- --tools option for update and check-updates commands (comma-separated tool names)
- --json output support for all commands
- --yes / -y flag to skip confirmation prompts on all commands
- Stable exit codes: 0=success, 1=error, 2=invalid input, 130=interrupted
- Non-interactive mode detection (CI-friendly)
- ot command alias alongside otinstaller
- otinstaller <toolname> bare command shows tool info (same as info)
- New tools: Blackbird, Telegram Phone Number Checker, Auto Archiver, edgar-tool, instagram-location-search, Telepathy
- 
eeds_config field in registry for tools requiring configuration
- 
equires_credentials concept for tools with mandatory API keys

### Changed
- All commands now support --json output
- All commands respect --yes / -y and non-interactive stdin
- update command refactored to use shared check logic
- Registry schema extended with input_types, 
eeds_config

### Fixed
- Tool name collision handling (bare tool name vs subcommand)
- Input type validation for --all mode

## [0.0.1] - 2026-09-29

### Added
- Initial release
- Basic tool management: install, remove, run, update, list, search, info
- Parallel tool execution with configurable concurrency
- Result storage with metadata and SHA256
- API key management via ~/.otinstaller/.env
- Responsible use notice on first run
- Auto-detect target type with uto command
- Example output viewer
- Resume interrupted jobs
- Doctor diagnostics
