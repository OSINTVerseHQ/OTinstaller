# Registry format

The registry is a YAML file with a top-level `tools` list. Each entry describes a command-line tool that otinstaller can install and run.

The bundled registry ships with 40 verified tools. See docs/TAGGING.md for how capability, topic, and accepts tags were assigned.

## Tool fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | yes | Unique identifier, lowercase with hyphens/underscore, max 40 chars. Regex: `^[a-z0-9][a-z0-9_-]{0,39}$` |
| display_name | string | yes | Human-readable name |
| description | string | yes | One-line description |
| repo | string | no | GitHub repository as "owner/name" |
| license | string | no | SPDX license identifier |
| stars | integer | no | GitHub stars count, non-negative |
| tier | string | no | Either "verified" or "community" (default: "community") |
| install | object | yes | Installation method, see below |
| entrypoint | object | yes | How to run the tool, see below |
| smoke_args | list[string] | no | Args for smoke test (default: `["--help"]`) |
| capabilities | list[string] | no | Tool capabilities, lowercase with hyphens |
| topics | list[string] | no | Tool topics, lowercase with hyphens |
| api_keys | object | no | Required and optional API key names |
| needs_config | boolean | no | Whether tool needs extra config (default: false) |
| resume_flag | string | no | Flag to pass for resume support |
| example | string | no | Relative path to sample output file |
| verified | object | no | Verification info, see below |
| accepts | list[string] | no | Target types this tool accepts (see below) |

## Accepts field

The `accepts` field specifies what types of targets this tool can operate on. This enables future auto-mode features where otinstaller can suggest or filter tools based on the target type.

Allowed values:
- `username` - Username or handle (e.g., sherlock, maigret)
- `email` - Email address
- `domain` - Domain name (e.g., theharvester)
- `ip` - IP address
- `phone` - Phone number
- `url` - URL
- `name` - Person's name

Each value must be one of the above. Unknown values raise a validation error.

## Install object

### Pip method
```yaml
install:
  method: pip
  package: sherlock-project      # required, PyPI package name
  version: "0.14.0"              # optional, pinned version
```

Validation:
- `package` required, regex `^[A-Za-z0-9][A-Za-z0-9._-]*$`
- `version` optional, regex `^[0-9A-Za-z.!+-]+$`
- `url`, `ref`, `requirements`, `as_package` must not be set

### Git method
```yaml
install:
  method: git
  url: https://github.com/owner/repo.git
  ref: main                      # optional, branch/tag/commit
  requirements: requirements.txt # exactly one of this or as_package
  as_package: true               # or install the cloned repo as a package
```

Validation:
- `url` required, must be `https://github.com/...` URL
- `ref` optional, regex `^[A-Za-z0-9._/-]+$`, must not start with `-`
- Exactly one of `requirements` or `as_package: true` required
- `requirements` must be relative path, no `..`
- `package` and `version` must not be set

## Entrypoint object

Exactly one of:
```yaml
entrypoint:
  command: sherlock              # console script name in the venv
```

```yaml
entrypoint:
  script: run.py                 # relative path to Python file (git only)
```

Validation:
- `command` regex `^[A-Za-z0-9][A-Za-z0-9._-]*$`
- `script` relative path, no `..`, only allowed for git method

## API keys object

```yaml
api_keys:
  required: [SHODAN_API_KEY]
  optional: [HUNTER_API_KEY]
```

Key names must match `^[A-Z][A-Z0-9_]*$`.

## Verification object

```yaml
verified:
  date: "2024-01-15"
  version: "0.14.0"
  os: "ubuntu-24.04"
  python: "3.12"
```

## Denylist

The denylist lives in `registry/denylist.yaml` with four lists:

- `capabilities`: capabilities that cause denial (e.g., `phishing`, `bruteforce`)
- `topics`: topics that cause denial
- `keywords`: case-insensitive substrings matched against name and description
- `repos`: GitHub repos (owner/name) that cause denial

A tool is denied if any of its capabilities, topics, or repo match, or if any keyword appears in its name or description. The registry pipeline applies the denylist before publishing; the CLI does not apply it at runtime.

## Example: pip tool

```yaml
- name: sherlock
  display_name: "Sherlock"
  description: "Search for a username across many social networks"
  repo: "sherlock-project/sherlock"
  license: "MIT"
  tier: "community"
  install:
    method: pip
    package: sherlock-project
  entrypoint:
    command: sherlock
  smoke_args: ["--help"]
  capabilities: ["username-search"]
```

## Example: git tool

```yaml
- name: theharvester
  display_name: "theHarvester"
  description: "Find emails, subdomains and names for a domain"
  repo: "laramies/theHarvester"
  tier: "community"
  install:
    method: git
    url: https://github.com/laramies/theHarvester.git
    as_package: true
  entrypoint:
    command: theHarvester
  capabilities: ["domain-recon", "email-search"]
  api_keys:
    optional: ["SHODAN_API_KEY", "HUNTER_API_KEY"]
```