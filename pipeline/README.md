# Pipeline Documentation

This directory contains the tool discovery and verification pipeline.

## discover.py

Discovers candidate OSINT tools on GitHub using topic searches and writes them to `candidates.yaml`.

Usage:
```bash
python pipeline/discover.py [--limit N] [--output PATH]
```

- `--limit N`: Stop after finding N unique repos across all topic queries (default: no limit)
- `--output PATH`: Output file (default: `pipeline/candidates.yaml`)

## verify.py

Verifies candidate tools by installing each in an isolated sandbox, running a smoke test, and generating registry entries for those that pass.

Usage:
```bash
python pipeline/verify.py [--limit N] [--resume]
```

- `--limit N`: Only test the first N untested candidates (useful for trial runs)
- `--resume`: Skip candidates already recorded in `pipeline/verification_log.jsonl`

### Process

For each candidate with `likely_installable: true`:

1. Creates a fresh temporary sandbox directory
2. Creates a virtualenv inside it
3. Attempts installation based on `detected_install_method`:
   - `pip-repo` with `candidate_pip_package`: `pip install <package>`
   - `pip-repo` without package: `pip install git+https://github.com/<repo>.git`
   - `git-requirements`: `git clone` then `pip install -r requirements.txt`
4. Detects entrypoint (console script or root-level Python script)
5. Runs smoke test: `--help`, falling back to `--version` then `-h`
6. Records version (from `pip show` or git commit hash)
7. Deletes sandbox
8. Appends result to `pipeline/verification_log.jsonl` (JSON Lines format)

### Output Files

- `pipeline/verification_log.jsonl`: One JSON object per line, appended only. Contains:
  - `name`, `repo`, `outcome` (passed/failed/timeout/skipped)
  - `reason` (for failures), `entrypoint_command`/`entrypoint_script`, `version`, `smoke_output`, `tested_at`
- `registry/generated_registry.yaml`: Validated Tool entries for all passed candidates, ready for human review before merging into the bundled registry (`src/otinstaller/data/registry.yaml`)

### Resume Support

Run with `--resume` to skip already-tested candidates. The log file is append-only, so interrupted runs don't lose progress.

### Timing

A full run of ~100 candidates takes approximately 10-20 minutes depending on network speed and tool install times. The trial run of 5 candidates took ~60 seconds (2 passed, 3 failed). Typical per-tool time: 10-60 seconds for pip installs, 30-120 seconds for git-requirements installs.

## generated_registry.yaml

This file is NOT the bundled registry used by the CLI. It is a candidate output for human review. Each entry has been validated against the Tool schema but has not been manually reviewed for capabilities, topics, or API key requirements. A human should:

1. Review each entry for correctness
2. Add appropriate `capabilities` and `topics` tags
3. Add `api_keys` if the tool requires external APIs
4. Merge approved entries into `src/otinstaller/data/registry.yaml`

## Candidates File Format

`candidates.yaml` contains a list of candidates with:
- `name`: Sanitized tool name
- `repo`: GitHub repo (owner/name)
- `stars`: Star count
- `description`: Tool description
- `license`: SPDX license identifier
- `detected_install_method`: `pip-repo`, `git-requirements`, or `unknown`
- `likely_installable`: Boolean indicating if install is likely to succeed
- `candidate_pip_package`: PyPI package name (if known)
- `default_branch`: Default branch name
- `discovered_at`: ISO timestamp