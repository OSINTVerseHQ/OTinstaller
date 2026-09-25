# Decisions

- The CLI does not apply the denylist at runtime; the registry pipeline applies it before publishing.
- Virtual environments are created in their final location (tools/<name>/venv/) because venv scripts embed absolute paths.
- The "commit" column in the state database was renamed to "commit_hash" to avoid SQLite reserved word conflicts.
- The notice acceptance file (accepted.json) stores the version and timestamp; changing the notice version requires re-acceptance.
- The .env file permissions are fixed to 600 on init if they are looser.
- The count line in list and search uses singular "tool" for 1, plural "tools" otherwise.
- Each tool gets its own virtualenv; no shared environments.
- Tools run on the same Python that runs otinstaller.
- otinstaller supports Linux only; install, remove, and run commands check sys.platform and exit with an error on other platforms.
- airecon passed verification but was deferred from launch because it requires Docker and Ollama, which otinstaller cannot check for yet; revisit once a `requires` field / dependency-check exists in the registry schema.
