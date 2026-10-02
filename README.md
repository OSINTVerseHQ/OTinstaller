# OTinstaller

Install, run, update, and remove open-source command line tools by name.

You pick a tool from a list. OTinstaller downloads it into its own folder, runs it, and saves the output. You do not learn a different install method for each tool.

Status: early development. Not published to PyPI yet.

## What you need

A Linux machine. Tested on Ubuntu 22.04 and 24.04, Debian 12, and Arch Linux. Kali Linux is checked by hand before a release.

Python 3.10 or newer, git, and the `venv` module. On Debian, Ubuntu and Kali, install that module with:

```bash
sudo apt install python3-venv git
```

Note: Some managed tools do not yet support Python 3.13+. The test matrix covers Python 3.10–3.12. If you encounter install failures on newer Python versions, try running otinstaller in a Python 3.12 virtualenv.

## Install otinstaller

These commands install otinstaller itself. Run them in this repository's folder. A virtualenv is a private Python folder, so this install does not change the Python that came with the system.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

`otinstaller` should now be on your path. A new terminal does not keep that. Run `source .venv/bin/activate` again from this folder if the next command says `otinstaller: command not found`.

For system-wide installation, use `pipx install otinstaller` (or `pipx install .` from this directory). This provides the `otinstaller` and `ot` commands on your PATH without a virtualenv.

Check the machine with:

```bash
otinstaller doctor
```

`doctor` prints `[ok]` or `[problem]` for Linux, Python, git, and venv. Fix any `[problem]` line before you continue. It often tells you the package to install.

## Run your first tool

`init` creates `~/.otinstaller/` and shows a responsible-use notice. It asks `Do you accept? [y/N]`. Type `y` and press Enter. Nothing can be installed until you do.

```bash
otinstaller init
```

Sherlock searches for a username. This install asks `Install? [y/N]`. The capital N means Enter alone means no. Type `y` to continue.

```bash
otinstaller install sherlock
otinstaller run sherlock -- someexampleuser123
```

The `--` marks where otinstaller's own options end. Everything after it is passed to Sherlock. When the run finishes, otinstaller prints a path under `results/` in the folder where you ran the command. That file is the tool's output.

To try a different tool, use its name from the guide in place of `sherlock`.

## Typed inputs

Instead of remembering each tool's flags, you can use typed input prefixes:

- `u:` username (e.g., `u:johndoe`)
- `e:` email (e.g., `e:john@example.com`)
- `p:` phone (e.g., `p:+15551234567`)
- `d:` domain (e.g., `d:example.com`)
- `url:` URL (e.g., `url:https://example.com`)
- `q:` text query (e.g., `q:search terms`)
- `geo:` coordinates (e.g., `geo:32.22,-110.97`)
- `tg:` Telegram channel (e.g., `tg:channelname`)
- `lat:` latitude (e.g., `lat:37.7749`)
- `lng:` longitude (e.g., `lng:-122.4194`)

Example:

```bash
otinstaller run sherlock -- u:johndoe
otinstaller run ghunt -- u:johndoe e:john@example.com
```

Each tool declares which input types it supports. Use `otinstaller info <tool>` to see the mapping.

## All mode

Run every installed tool that supports a given input type:

```bash
otinstaller run --all u:johndoe
otinstaller run -a u:johndoe e:john@example.com
```

Only `u`, `e`, `p`, `d`, and `url` work with `--all`. Tools requiring API credentials are skipped unless `--include-credentialed` is passed.

## Agent-friendly usage

Every command supports `--json` for machine-readable output. Commands never prompt when `--yes` or `-y` is given, or when stdin is not a terminal (CI mode). Exit codes are stable: 0 = success, 1 = error, 2 = invalid input, 130 = interrupted.

Command reference:

- `otinstaller init` — Initialize config and directories
- `otinstaller install <tool>...` — Install tools
- `otinstaller remove <tool>...` / `--all` — Remove tools
- `otinstaller run <tool>... -- <args>` — Run tools
- `otinstaller run --all u:...` — Run all matching tools
- `otinstaller info <tool>` — Show tool details
- `otinstaller list` / `--installed` — List tools
- `otinstaller search <query>` — Search tools
- `otinstaller update` / `--all` / `--check-only` — Update tools
- `otinstaller check-updates` — Check for updates (read-only)
- `otinstaller auto <target>` — Auto-detect type and run tools
- `otinstaller example <tool>` — Show example output
- `otinstaller keys check` — Check API keys
- `otinstaller resume` — Resume interrupted jobs
- `otinstaller doctor` — Run diagnostics

For AI agents: see `llms.txt` at the repository root.

## Results

Results are saved automatically to `./results/<tool>/<target>/` using the filename pattern `<YYYYmmdd-HHMMSS>_<tool>_<target>_<runid>.<ext>` plus a `.meta.json` sidecar. The results directory can be overridden with `--output` or `OTINSTALLER_RESULTS_DIR`.

Example:

```
results/sherlock/testuser/20260929-123456_sherlock_testuser_abc123.txt
results/sherlock/testuser/20260929-123456_sherlock_testuser_abc123.meta.json
```

## API keys

One env file holds all API keys: `~/.otinstaller/.env`, permissions 600. Each tool only receives the keys it declares in its registry entry. Use `otinstaller keys check` to verify.

## Resume

If a run or install is interrupted (crash, Ctrl+C, kill), otinstaller keeps a job marker in `~/.otinstaller/jobs/`. Run `otinstaller resume` to detect and handle interrupted jobs:

- For installs: cleans up partial state and retries the install.
- For runs: reports the interrupted run and prints the command to rerun manually.

Use `otinstaller resume --dry-run` to see what would happen without making changes. Use `--json` for machine-readable output.

Finished jobs are skipped on resume (their marker is removed on completion). Partial output from interrupted runs is always kept in the results directory.

## Dual-use tools and responsible use

Some tools are tagged `dual-use` in the registry. They can be used for legitimate research but also for misuse. Installing a dual-use tool prints a notice and requires confirmation unless `--yes` is given.

The global responsible-use notice is accepted on first `otinstaller init`. You can re-read it with `otinstaller init` any time.

## Python version caveats

Some managed tools do not yet support Python 3.13+. The test matrix covers Python 3.10–3.12. Known affected tools:

- `auto-archiver`: requires Python <3.13 (dependency `pdqhash` needs a C++ compiler, no wheel for 3.13+)
- `telepathy`: requires Python <3.13 (dependency `googletrans`/`httpx` uses removed `cgi` module)

If you encounter install failures on Python 3.13+, run otinstaller in a Python 3.12 virtualenv.

## License

MIT. See [LICENSE](LICENSE).