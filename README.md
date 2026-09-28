# otinstaller

Install, run, update and remove open-source command line tools by name.

People doing open-source intelligence (OSINT) work collect a pile of unrelated command line tools, each with its own install method. otinstaller gives those tools one interface. You install a tool by name, run it with the same command shape every time, and every run is saved to disk with a metadata file.

otinstaller does not write the tools. It installs third-party software from PyPI or GitHub into an isolated virtualenv, runs it, and stores the output. You are responsible for how you use what it installs.

Status: early development. Not published to PyPI yet.

Linux only. Python 3.10 or newer, git, and a working `venv` module are required. The distributions and versions that are tested are listed under [Supported Linux](#supported-linux).

## Install from a checkout

Each block is one command. On GitHub, use the copy button on the block.

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
pip install -e .
```

For tests and the registry pipeline:

```bash
pip install -e ".[dev,pipeline]"
```

The published install, once it exists, will be:

```bash
pip install otinstaller
```

## Usage

`init` creates `~/.otinstaller/`, writes an env file for API keys (mode 600), and asks you to accept the responsible use notice. Install is refused until you accept. `install` prints what it will fetch and asks for confirmation. Pass `--yes` (or `-y`) when there is no terminal. A non-interactive install without `--yes` exits with an error rather than guessing.

Each block is one command. On GitHub, use the copy button on the block. Replace `<tool>` with a name from the [covered tools](#covered-tools) table.

### Check the machine, then install and run one tool

```bash
otinstaller doctor
```

```bash
otinstaller init
```

```bash
otinstaller search username
```

```bash
otinstaller info sherlock
```

```bash
otinstaller install sherlock
```

```bash
otinstaller run sherlock -- someexampleuser123
```

A successful run prints the exit code, the output path, and a SHA-256 of the file:

```text
tool exited 0
saved to results/sherlock/someexampleuser123/20260922-143000_sherlock_someexampleuser123_a1b2c3d4.txt
sha256  3b1c...
```

Add `--verbose` on `run` to stream the tool's output to the terminal while it is also written to disk.

### Pass a tool its own flags

Arguments after `--` go to the tool unchanged.

```bash
otinstaller run theharvester -- -d example.com -b bing
```

### Run several tools on the same target

They share the same arguments and run together, up to four at a time. `--parallel` changes that limit.

```bash
otinstaller run sherlock maigret -- someexampleuser123
```

```bash
otinstaller run sherlock maigret --parallel 2 -- someexampleuser123
```

If the target happens to be a registered tool name, pass it with `--target` so it is not read as another tool to run.

```bash
otinstaller run sherlock --target holehe -- holehe
```

### Keep related runs in one case

`--case` groups output under one folder. The same flag works on `run`, `auto`, `extract` and `diff`.

```bash
otinstaller run sherlock --case demo-run -- someexampleuser123
```

```bash
otinstaller extract sherlock --case demo-run
```

```bash
otinstaller diff sherlock someexampleuser123 --case demo-run
```

### Let otinstaller choose the tools

`auto` classifies the target as an email, domain, IP address, URL or username, then runs every installed tool whose registry entry accepts that type. It does not install missing tools. It lists them and skips them. `--dry-run` prints the plan. `--type` overrides detection when the guess is wrong.

```bash
otinstaller auto --dry-run example.com
```

```bash
otinstaller auto --type domain example.com
```

### Keys, updates and a failed install

```bash
otinstaller keys check
```

```bash
otinstaller update sherlock --check-only
```

```bash
otinstaller resume
```

The otinstaller process exit code follows the tool: a non-zero tool exit is a non-zero otinstaller exit. With several tools, any failure exits 1 after the summary line. A missing required API key is a warning on stderr. The tool still runs.

## Commands

| Command | What it does |
| --- | --- |
| `otinstaller list` | List tools in the registry. `--installed` lists what is on this machine. `--json` prints JSON. |
| `otinstaller search <words>` | Search names, descriptions and capabilities. |
| `otinstaller info <tool>` | Show install method, entrypoint, capabilities, API keys and verification. |
| `otinstaller install <tool> [tool...]` | Install one or more tools. `--force` reinstalls. `--yes` skips the prompt. |
| `otinstaller remove <tool>` | Remove an installed tool. `--all` removes every installed tool. |
| `otinstaller run <tool> [tool...] -- <args>` | Run installed tools. Arguments after `--` are passed through. |
| `otinstaller auto <target>` | Detect the target type and run every matching installed tool. |
| `otinstaller update <tool>` | Update to the latest version. `--all` updates everything installed. `--check-only` reports without installing. |
| `otinstaller extract <tool>` | Pull emails, domains, IP addresses and URLs out of saved results. |
| `otinstaller diff <tool> <target>` | Compare the two most recent runs of one tool against one target. |
| `otinstaller keys check` | Show which declared API keys are set, and which tools are missing a required key. |
| `otinstaller resume` | Retry an install that was interrupted. Report an interrupted run so you can start it again. |
| `otinstaller doctor` | Check platform, Python, git, venv and that the home directory is writable. |
| `otinstaller --version` | Print the version. |

`list`, `search`, `info`, `extract`, `diff`, `update --check-only`, `keys check` and `resume` accept `--json`.

Unknown tool names exit with an error and, when possible, a short "did you mean" suggestion.

## Where output goes

Results are written under `./results` in the current directory. Set `OTINSTALLER_RESULTS_DIR` to put them somewhere else. There is no `--output` flag.

```text
results/<tool>/<target>/
  <YYYYmmdd-HHMMSS>_<tool>_<target>_<runid>.txt
  <YYYYmmdd-HHMMSS>_<tool>_<target>_<runid>.meta.json
```

With `--case`:

```text
results/cases/<case>/<tool>/<target>/
  <YYYYmmdd-HHMMSS>_<tool>_<target>_<runid>.txt
  <YYYYmmdd-HHMMSS>_<tool>_<target>_<runid>.meta.json
```

The timestamp is UTC. The run id is eight hex characters. The target and case are lowercased, characters outside `[a-z0-9._-]` become `_`, and the result is cut at 80 characters. An empty name becomes `target`.

The `.meta.json` file records the command, tool version, target, case, start and end time, duration, exit code, status (`complete`, `failed` or `interrupted`), output path, byte size and SHA-256. API key values are replaced with `***` if they appear in the command. Environment values are never written. See [docs/RESULTS.md](docs/RESULTS.md) for the full field list.

`extract` reads the `.txt` files for one installed tool, one case, or a path you pass. `diff` prints lines added and removed between the two newest runs of the same tool and target.

Partial output is kept if a run is interrupted. `resume` does not replay it. It retries a half-finished install, and for a half-finished run it prints the command to start again. `--dry-run` reports that plan without changing anything. Finished work is left alone.

## API keys

One file holds every key: `~/.otinstaller/.env`, mode 600. `init` creates it if it is missing and tightens the mode if it is looser.

```text
SHODAN_API_KEY=your-key-here
```

Each tool receives only the keys named in its registry entry. `otinstaller info <tool>` lists required and optional names. `otinstaller keys check` shows which of those names are set, which registry tools are missing a required key, and which single missing key would satisfy the most tools. Key values are not printed.

## Updates and removal

`update` asks PyPI for the latest release, or GitHub for the latest commit, and reinstalls when the installed version differs. A git tool pinned to a ref in the registry is skipped. `--check-only` prints the comparison and does not install. `--json` works with `--check-only`.

`remove` deletes that tool's directory and its row in the state database. It will not delete anything outside `~/.otinstaller/tools/`.

Install failures are logged to `~/.otinstaller/logs/install-<tool>.log`. The failed tool directory is removed, so a later install starts clean.

## Covered tools

The bundled registry ships these 38 tools. A tool is listed after it installs in a clean virtualenv and a smoke test (`--help`, then `--version`, then `-h`) exits cleanly. Entries are reviewed before a release.

Install and run any of them with the same commands. Replace `<tool>` with a name from the table. Pass `--yes` on install to skip the confirmation prompt.

```bash
otinstaller install <tool>
```

```bash
otinstaller run <tool> -- <args>
```

| Tool | Description | Input type | GitHub |
| --- | --- | --- | --- |
| `aliens-eye` | Search for a username across social networks. | username | [arxhr007/Aliens_eye](https://github.com/arxhr007/Aliens_eye) |
| `bbot` | Recursively scan a domain or IP. | domain, ip | [blacklanternsecurity/bbot](https://github.com/blacklanternsecurity/bbot) |
| `cloud-enum` | Find public cloud resources for a domain or IP. | domain, ip | [initstring/cloud_enum](https://github.com/initstring/cloud_enum) |
| `crosslinked` | Find employee names for an organization. | username, email, name | [m8sec/CrossLinked](https://github.com/m8sec/CrossLinked) |
| `ctfr` | List subdomains from certificate transparency logs. | domain | [UnaPibaGeek/ctfr](https://github.com/UnaPibaGeek/ctfr) |
| `dnsgen` | Generate DNS name permutations. | domain | [AlephNullSK/dnsgen](https://github.com/AlephNullSK/dnsgen) |
| `dnstwist` | Generate lookalike domain names. | domain, ip | [elceef/dnstwist](https://github.com/elceef/dnstwist) |
| `fierce` | DNS reconnaissance for a domain. | domain, ip | [mschwager/fierce](https://github.com/mschwager/fierce) |
| `finalrecon` | Collect public information about a website. | domain, ip | [thewhiteh4t/FinalRecon](https://github.com/thewhiteh4t/FinalRecon) |
| `fsociety` | Modular security testing framework. | domain, username, email | [fsociety-team/fsociety](https://github.com/fsociety-team/fsociety) |
| `ghunt` | Look up a Google account from a username or email. | username, email | [mxrch/GHunt](https://github.com/mxrch/GHunt) |
| `h8mail` | Search breach data for an email address. | email | [khast3x/h8mail](https://github.com/khast3x/h8mail) |
| `holehe` | Check whether an email is registered on other sites. | email, username | [megadose/holehe](https://github.com/megadose/holehe) |
| `ignorant` | Check whether a phone number is registered on other sites. | phone | [megadose/ignorant](https://github.com/megadose/ignorant) |
| `instagram-monitor` | Record changes to a public Instagram profile. | username | [misiektoja/instagram_monitor](https://github.com/misiektoja/instagram_monitor) |
| `instaloader` | Download public Instagram posts and metadata. | username, url | [instaloader/instaloader](https://github.com/instaloader/instaloader) |
| `ivre` | Network reconnaissance framework. | domain, ip | [ivre/ivre](https://github.com/ivre/ivre) |
| `linkook` | Find social accounts linked to a username. | username, email | [JackJuly/linkook](https://github.com/JackJuly/linkook) |
| `maigret` | Search for a username across many sites. | username | [soxoj/maigret](https://github.com/soxoj/maigret) |
| `mailaccess` | Look up an email address across many sites. | email | [KatrielMoses/MailAccess](https://github.com/KatrielMoses/MailAccess) |
| `nexfil` | Find profiles for a username. | username | [thewhiteh4t/nexfil](https://github.com/thewhiteh4t/nexfil) |
| `onionsearch` | Search onion sites. | url | [megadose/OnionSearch](https://github.com/megadose/OnionSearch) |
| `openosint` | Command line agent for public-information lookups. | username, email, domain | [OpenOSINT/OpenOSINT](https://github.com/OpenOSINT/OpenOSINT) |
| `osint-brazuca-regex` | Regular expressions for Brazilian identifiers. | domain, name | [osintbrazuca/osint-brazuca-regex](https://github.com/osintbrazuca/osint-brazuca-regex) |
| `paramspider` | Collect archived URLs for a domain. | domain, url | [devanshbatham/ParamSpider](https://github.com/devanshbatham/ParamSpider) |
| `pywerview` | Collect information from a Windows domain. | domain, username | [the-useless-one/pywerview](https://github.com/the-useless-one/pywerview) |
| `secator` | Run security tasks from one command line. | domain, ip, username, email | [freelabz/secator](https://github.com/freelabz/secator) |
| `sherlock` | Search for a username across social networks. | username | [sherlock-project/sherlock](https://github.com/sherlock-project/sherlock) |
| `sitedorks` | Build search-engine queries for a site. | domain, url | [Zarcolio/sitedorks](https://github.com/Zarcolio/sitedorks) |
| `socialscan` | Check username or email use on social sites. | username, email | [iojw/socialscan](https://github.com/iojw/socialscan) |
| `socid-extractor` | Extract identifiers from a profile URL. | url, username | [soxoj/socid-extractor](https://github.com/soxoj/socid-extractor) |
| `spiderfoot` | Collect public information for a domain, IP, username, or email. | domain, ip, username, email | [smicallef/spiderfoot](https://github.com/smicallef/spiderfoot) |
| `theharvester` | Find emails, subdomains, and names for a domain. | domain | [laramies/theHarvester](https://github.com/laramies/theHarvester) |
| `torbot` | Collect links from onion sites. | url, domain | [DedSecInside/TorBot](https://github.com/DedSecInside/TorBot) |
| `toutatis` | Read public Instagram details from a phone number. | phone | [megadose/toutatis](https://github.com/megadose/toutatis) |
| `user-scanner` | Look up an email address or a username. | username, email | [kaifcodec/user-scanner](https://github.com/kaifcodec/user-scanner) |
| `whatsapp-osint` | Record WhatsApp presence changes for a phone number. | phone, name | [jasperan/whatsapp-osint](https://github.com/jasperan/whatsapp-osint) |
| `yark` | Collect public information from YouTube. | url, username, name | [Owez/yark](https://github.com/Owez/yark) |

## The registry

The registry file is chosen in this order:

1. `OTINSTALLER_REGISTRY`, if set.
2. `~/.otinstaller/registry.yaml`, if that file exists.
3. The registry bundled with the package.

The denylist in [registry/denylist.yaml](registry/denylist.yaml) is applied when the registry is built, not when you run the CLI. It excludes tools by capability: phishing kits, IP grabbers, message or call bombers, credential brute-forcers, private-account bypass, dox-dump hosting, and active scanners that are not OSINT tools. Tools tagged `dual-use` can still be installed. `install` prints a short reminder, and `info` points at the notice below.

Format, install methods and tag meanings are in [docs/REGISTRY.md](docs/REGISTRY.md) and [docs/TAGGING.md](docs/TAGGING.md).

## Configuration

| Variable | Default | Effect |
| --- | --- | --- |
| `OTINSTALLER_HOME` | `~/.otinstaller` | Tools, logs, state database, acceptance record and `.env`. |
| `OTINSTALLER_RESULTS_DIR` | `./results` | Where run output is written. |
| `OTINSTALLER_REGISTRY` | bundled registry | Registry file to load. |

Home layout, including `state.db` and per-tool virtualenvs, is described in [docs/LAYOUT.md](docs/LAYOUT.md).

otinstaller itself installs from PyPI and GitHub. It does not send telemetry. A tool you run may contact whatever services that tool contacts.

## Responsible use

This is the notice `otinstaller init` asks you to accept.

```text
RESPONSIBLE USE NOTICE
otinstaller installs and runs third-party open-source tools. It does not create,
own, endorse or verify them. Many are dual-use: used for fraud investigations,
journalism, security research and compliance, but capable of misuse.

You are solely responsible for how you use these tools and for complying with all
applicable laws, including privacy, data-protection and computer-misuse laws in your
jurisdiction, and the terms of any service you query. Use them only on targets you
are authorized to investigate. Do not use them to harass, stalk or harm anyone.

Tools are provided as-is, without warranty. Their authors and the otinstaller
contributors accept no liability for misuse.
```

Acceptance is stored in `~/.otinstaller/accepted.json` with the notice version. A newer notice version requires acceptance again.

## Supported Linux

| Distribution | Version | How it is tested |
| --- | --- | --- |
| Ubuntu | 22.04 LTS | CI, on every push and pull request |
| Ubuntu | 24.04 LTS | CI, on every push and pull request |
| Debian | 12 (bookworm) | CI, in a Debian 12 container |
| Arch Linux | current rolling release | CI, in the `archlinux:latest` image |
| Kali Linux | current release | Checked by hand before a release |

Ubuntu CI runs on Python 3.10, 3.11 and 3.12. Debian and Arch use the Python that ships with that image. Kali is Debian-based, so the Debian 12 job covers the same package family. `otinstaller doctor` checks the machine you are on and names the package to install when git or `venv` is missing.

On Debian, Ubuntu and Kali the venv package is `python3-venv`.

Managed tools are installed with pip or git only. Each tool gets its own virtualenv under `~/.otinstaller/tools/<name>/`. Nothing is installed into system Python. Tools that need Go, Rust, Node or Docker are not supported.

## Authors

otinstaller is written and maintained by otinstaller contributors. See [LICENSE](LICENSE).

The tools in the covered tools table are separate projects. Their authors are the people named on each GitHub repository. otinstaller does not write those tools and does not claim them.

## Contributing

Install the development and pipeline extras, then run the same checks CI runs:

```bash
pip install -e ".[dev,pipeline]"
```

```bash
ruff check .
```

```bash
ruff format --check .
```

```bash
pytest
```

The CLI in `src/otinstaller/cli.py` is a thin layer. Install, run, results and state live in importable modules under `src/otinstaller/`. Tests are in `tests/`. A behavior change needs a test, including the failure case.

To propose a new tool, run the pipeline in [pipeline/](pipeline/README.md). It discovers candidate repositories, installs each in a sandbox, smoke-tests it, and writes entries for review. Generated output is not what the CLI loads until a person reviews it and it is merged into `src/otinstaller/data/registry.yaml`. Tag meanings are in [docs/TAGGING.md](docs/TAGGING.md). The denylist in [registry/denylist.yaml](registry/denylist.yaml) can be edited without a code change.

Design notes that are easy to trip over are collected in [docs/DECISIONS.md](docs/DECISIONS.md).

Open a pull request against this repository. Keep commit messages short and in the imperative mood, for example `add config module`.

## License

MIT. See [LICENSE](LICENSE).
