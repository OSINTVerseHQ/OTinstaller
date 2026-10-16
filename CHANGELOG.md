# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-10-15

### Added
- Opt-in crash reports through Sentry. Off unless you say yes: `otinstaller init` (or the first `install` on a terminal) asks once and Enter means no; `--yes`, scripts and pipes never turn them on. A report is sent only when otinstaller itself crashes, never for a tool's own failure, and holds the error type, a cleaned message, where in otinstaller's code it happened and the otinstaller, Python and OS versions. Targets, arguments, tool output, results, API keys, file paths, host and user names are never sent. `otinstaller crash-reports on|off` changes it, `DO_NOT_TRACK=1` or `OTINSTALLER_CRASH_REPORTS=off` always turns it off, and `doctor` shows the setting
- `debian/` packaging, for Kali and other Debian-based distributions
- Python 3.13 and 3.14 support. Every tool was installed and run on 3.10, 3.12, 3.13 and 3.14; the few that need another Python say so before installing. `doctor` now lists those tools as a note instead of a problem
- `otinstaller crash-reports test` sends a test report, to check the setup
- MailAccess harvests a domain's email addresses: `otinstaller run mailaccess d:company.com` runs its `harvest-emails --domain company.com`. `e:` still runs an investigation
- Registry: `playwright_browsers` downloads a tool's Playwright browser into the tool's own folder, and `input_types` can map a typed input to several words, such as a subcommand and its flag

### Changed
- License changed from MIT to Apache License 2.0, with a NOTICE file that redistributions and derived works must keep, crediting OSINTverse. Releases up to and including 0.0.4 stay under MIT.
- `otinstaller install` (and `playbook`) on a terminal now shows the responsible-use notice and asks, the same as `init`, instead of stopping with "run 'otinstaller init' first". Scripts, pipes and `--json` runs still need `otinstaller init --yes`; the notice is never accepted for you
- `update` and `check-updates` follow the versions this registry pins and tested. Before, they compared pinned PyPI tools with PyPI's newest release, offered an "update", and then reinstalled the same pinned version. A tool whose pin or install method changed in the registry is now offered for update
- Sublist3r installs from its author's GitHub repository (pinned commit) instead of the PyPI upload, which isn't published by the author. `otinstaller update sublist3r` switches an existing install over
- New tool virtualenvs upgrade pip before installing anything. If that fails (an offline mirror, say), the bundled pip is used as before
- Playbooks ship with the package. A `playbooks` folder in the current directory still works and overrides a bundled playbook with the same name
- `auto` gained `--include-credentialed` and `--type phone`
- MailAccess 0.18.7 (was 0.18.6), installed with its `browser` extra and Chromium's headless shell, so its browser checks run. Without them MailAccess skipped those checks. The install now downloads about 150 MB more and takes about 450 MB more disk
- MailAccess no longer adds `investigate` to every run, so `otinstaller run mailaccess -- harvest-emails ...` and its other commands work. Plain arguments now need the command: `otinstaller run mailaccess -- investigate you@example.com`
- Dependencies: typer `>=0.20,<1` instead of exactly 0.27.2, click `>=8.1`, and sentry-sdk `>=2.0,<3`, so the versions Debian and Kali ship work

### Fixed
- telegram-phone-number-checker: keys from `~/.otinstaller/.env` now reach the tool. It reads `API_ID`, `API_HASH` and `PHONE_NUMBER`, but the registry declared `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`, so the values were never passed. The keys are optional, because the tool asks for them when they are not set
- telepathy no longer lists `TELEGRAM_API_ID` and `TELEGRAM_API_HASH` as required. It never read them: it asks for its credentials on the first run and stores them itself, so it is now marked `interactive`
- telepathy's typed inputs `u:` and `p:` mapped to `--username` and `--phone`, which telepathy doesn't have. It now takes `tg:` (a chat or user), passed as `-t`
- `run --all` leaves out interactive tools, which would wait for input that a captured run can't give, and tools marked `needs_config` unless `--include-credentialed` is passed
- `auto` and playbooks gave the target to every tool as a bare argument, so tools that need a flag (theHarvester `--domain`, h8mail `-t`, ctfr `--domain` and others) failed, and `default_args` were dropped. They now pass it the same way as a typed input, choose tools by their typed inputs, and skip the same tools as `run --all`
- `otinstaller playbook` found no playbooks when otinstaller was installed from PyPI, because the playbooks were only in the git checkout
- `install --verbose` reported a tool as installed even when a step failed (spiderfoot's requirements on Python 3.13, for example). A failed step now stops the install, as it does without `--verbose`
- On Python 3.10 with the pip that venv bundles, packages without a `pyproject.toml` (ivre) were installed with a `#!python` first line, so their command couldn't start. Upgrading pip first fixes it
- `run` crashed with a traceback when a tool's command was missing. It now exits 127 and says to reinstall with `--force`
- Python version limits for tools that can't install or start outside them: GHunt needs 3.13 or older (its pinned Pillow 10 has no wheels for 3.14), theHarvester needs 3.12+ (its current release requires it), whatsapp-osint needs 3.11+ (it imports `datetime.UTC`), spiderfoot needs 3.12 or older (its pinned lxml and cryptography have no wheels for 3.13). otinstaller now says so before installing, instead of failing in pip
- dnsgen no longer claims a `d:` input. It reads a file of domains, so `d:example.com` failed; run it as `otinstaller run dnsgen -- domains.txt`
- edgar-tool's `d:` input passed the domain as a subcommand name, which edgar rejects. `q:` (a text search) is unchanged
- sitedorks asks a question before opening browser tabs, which was invisible in a captured run. It is now marked `interactive`, so it runs on a terminal
- The installed-tool contract test never ran a tool: it looked for commands in the wrong folder and treated "not found" as a pass. It now builds each command the way `otinstaller run` does
- Yes/no prompts showed the default twice (`[y/N] [n]`)

## [0.0.4] - 2026-10-13

### Added
- `interactive` registry flag: single runs on a terminal use a pseudo-terminal, so login prompts, menus and setup wizards are visible and answerable. `--verbose` on a terminal does the same for any tool. Output is still saved and hashed
- `run_from_source` registry flag for git scripts that read data files by relative path

### Changed
- instaloader 4.15.4 and mailaccess 0.18.6, re-verified on Ubuntu 24.04 with Python 3.12
- The results folder is named after the typed input when there is one, otherwise the first argument that is not a flag, so `-- url:https://example.com --headers` no longer saves under `headers/`

### Fixed
- ghunt: `ot run ghunt -- login` runs `ghunt login` again; `e:` maps to the `email` subcommand instead of a default argument that was added to every run
- blackbird runs from its checkout, so it finds `data/wmn-data.json` from any directory
- dnstwist installs with its `[full]` extras (DNS, WHOIS, GeoIP, fuzzy hashing)
- osint-brazuca-regex requires Python 3.12+, so install stops early on 3.10 and 3.11 instead of failing at run time
- auto-archiver no longer warns that Google keys are required; they are optional
- Values of credential flags such as `--cookie`, `--token`, `--password` and `--api-hash` are written as `***` in `.meta.json` and never used to name the results folder
- `extra_packages` accepts `==`, `>=`, `<=`, `!=` and `~=` version operators

## [0.0.3] - 2026-10-12

### Added
- Contact email and OSINTverse social links in the README and `otinstaller about`
- README tool catalogue, generated from the registry, plus a why section, FAQ, docs link and launch video

### Changed
- user-scanner 1.5.2.2, linkook 1.1.3, aliens-eye 2.7.0 and mailaccess 0.18.5, each re-verified on Ubuntu 24.04 with Python 3.12
- blackbird now installs from its new home, antoniaci/blackbird; Telepathy points to prose-intelligence-ltd/Telepathy-Community

### Fixed
- mailaccess runs `mailaccess --no-banner investigate <email>`; the old `--email` flag no longer exists, and 0.18.5 fixes the missing greenlet dependency

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
