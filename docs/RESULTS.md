# Results layout

Every run of a tool with `otinstaller run` saves its raw output to disk automatically,
with a sidecar `.meta.json` file recording exactly what happened. Runs can optionally
be grouped into a named case folder.

If a target argument after `--` happens to match a registered tool name, it will be
interpreted as an additional tool to run. Use `--target` explicitly to disambiguate.

## Without --case

```
results/<tool>/<sanitized-target>/
  <YYYYmmdd-HHMMSS>_<tool>_<sanitized-target>_<runid>.txt
  <YYYYmmdd-HHMMSS>_<tool>_<sanitized-target>_<runid>.meta.json
```

## With --case NAME

```
results/cases/<sanitized-case>/<tool>/<sanitized-target>/
  <YYYYmmdd-HHMMSS>_<tool>_<sanitized-target>_<runid>.txt
  <YYYYmmdd-HHMMSS>_<tool>_<sanitized-target>_<runid>.meta.json
```

## Naming rules

- `sanitized-target`: the target string (username, domain, etc.) is lowercased,
  non-alphanumeric characters except `._-` become `_`, repeated `_` are collapsed,
  leading/trailing `_` and `.` are stripped, truncated to 80 chars. Empty becomes
  `target`.
- `runid`: 8 lowercase hex characters from `os.urandom`.
- `timestamp`: `YYYYmmdd-HHMMSS` (UTC).

## The .meta.json file

The sidecar file contains:

```json
{
  "command": ["tool", "arg1", "arg2"],
  "tool": "sherlock",
  "tool_version": "0.16.2",
  "target": "someuser",
  "case": null,
  "started_at": "2026-09-22T14:30:00+00:00",
  "ended_at": "2026-09-22T14:30:05+00:00",
  "duration_seconds": 5.2,
  "exit_code": 0,
  "status": "complete",
  "output_path": "results/sherlock/someuser/20260922-143000_sherlock_someuser_a1b2c3d4.txt",
  "sha256": "3b1c...",
  "bytes": 12345
}
```

- `command`: the full command line, with any API key values redacted to `***`.
- `status`: `complete` (exit 0), `failed` (non-zero exit), or `interrupted` (killed by signal).
- `sha256`: streaming SHA-256 of the output file, for integrity verification.
- Environment variable values are never written; only variable names appear.

## Worked example

```bash
$ otinstaller run sherlock someexampleuser123
running sherlock...
tool exited 0
saved to results/sherlock/someexampleuser123/20260922-143000_sherlock_someexampleuser123_a1b2c3d4.txt
sha256  3b1c...

$ cat results/sherlock/someexampleuser123/20260922-143000_sherlock_someexampleuser123_a1b2c3d4.meta.json
{
  "command": ["sherlock", "someexampleuser123"],
  "tool": "sherlock",
  "tool_version": "0.16.2",
  "target": "someexampleuser123",
  "case": null,
  "started_at": "2026-09-22T14:30:00+00:00",
  "ended_at": "2026-09-22T14:30:05+00:00",
  "duration_seconds": 5.2,
  "exit_code": 0,
  "status": "complete",
  "output_path": "results/sherlock/someexampleuser123/20260922-143000_sherlock_someexampleuser123_a1b2c3d4.txt",
  "sha256": "3b1c...",
  "bytes": 12345
}
```

With a case:

```bash
$ otinstaller run sherlock --case demo-run -- someexampleuser123
running sherlock...
tool exited 0
saved to results/cases/demo-run/sherlock/someexampleuser123/20260922-143100_sherlock_someexampleuser123_e5f6a7b8.txt
sha256  7f2d...

$ find results/cases -type f
results/cases/demo-run/sherlock/someexampleuser123/20260922-143100_sherlock_someexampleuser123_e5f6a7b8.txt
results/cases/demo-run/sherlock/someexampleuser123/20260922-143100_sherlock_someexampleuser123_e5f6a7b8.meta.json
```