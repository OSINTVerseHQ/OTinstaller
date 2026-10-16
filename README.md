<p align="center">
  <img src="https://raw.githubusercontent.com/OSINTVerseHQ/OTinstaller/main/docs/images/otinstaller-banner.png" alt="OTinstaller banner" width="900">
</p>

<p align="center">
  <b>Install, run, update and remove open-source tools by name.</b><br>
  One command interface for dozens of open-source intelligence (OSINT) tools, each in its own virtualenv.
</p>

<p align="center">
  <a href="https://github.com/OSINTVerseHQ/OTinstaller/actions/workflows/ci.yml"><img src="https://github.com/OSINTVerseHQ/OTinstaller/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/otinstaller/"><img src="https://img.shields.io/pypi/v/otinstaller" alt="PyPI"></a>
  <img src="https://img.shields.io/badge/python-3.10%20to%203.14-blue" alt="Python 3.10 to 3.14">
  <img src="https://img.shields.io/badge/platform-Linux-lightgrey" alt="Linux">
  <a href="https://github.com/OSINTVerseHQ/OTinstaller/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue" alt="Apache 2.0 license"></a>
  <a href="https://github.com/OSINTVerseHQ/OTinstaller/stargazers"><img src="https://img.shields.io/github/stars/OSINTVerseHQ/OTinstaller?style=flat" alt="GitHub stars"></a>
</p>

<p align="center">
  <a href="https://osintverse.gitbook.io/otinstaller">Documentation</a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="#typed-inputs">Typed inputs</a> ·
  <a href="#command-reference">Commands</a> ·
  <a href="#tool-catalogue">Tools</a> ·
  <a href="#faq">FAQ</a> ·
  <a href="#tools">Tools</a> ·
  <a href="#team">Team</a> ·
  <a href="#contact">Contact</a> ·
  <a href="https://youtu.be/_AfUGMFRaKA">Launch video</a>
</p>

<p align="center">
  <a href="https://youtu.be/_AfUGMFRaKA">
    <img src="https://i.ytimg.com/vi/_AfUGMFRaKA/maxresdefault.jpg" alt="Watch the OTinstaller launch video on YouTube" width="760">
  </a>
  <br>
  <a href="https://youtu.be/_AfUGMFRaKA"><b>Watch the launch video on YouTube (1:31)</b></a>
</p>


---

## What it does

Every open-source tool installs and runs a little differently. OTinstaller gives them one interface:

- **Install by name.** `ot install sherlock` creates an isolated virtualenv for the tool. Nothing touches your system Python.
- **Run with typed inputs.** `u:johndoe`, `e:john@example.com` or `d:example.com` are translated into each tool's own flags.
- **Run many tools at once.** `ot run --all u:johndoe` runs every installed tool that accepts a username, in parallel.
- **Keep every result.** Output is saved under `./results/<tool>/<target>/` with a `.meta.json` sidecar (command, timing, exit code, SHA-256).
- **Update and remove cleanly.** One command each, for one tool or all of them.
- **Script it.** Every command supports `--json`, and nothing prompts when `--yes` is given.

`ot` is a short alias for `otinstaller`. Both work everywhere.

## Why OTinstaller

Running one tool by hand, spiderfoot in this case:

```bash
git clone https://github.com/smicallef/spiderfoot
cd spiderfoot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 sf.py -u passive -s example.com
```

The same thing with OTinstaller:

```bash
ot install spiderfoot
ot run spiderfoot -- d:example.com
```

The same install-and-run pattern works for every tool in the catalogue. Each tool is pinned to a tested version, gets its own virtualenv, has its typed inputs turned into its own flags, and saves its output with a timestamp and a SHA-256.

## Quick start

```bash
pipx install otinstaller
ot init
ot install sherlock
ot run sherlock -- u:johndoe
```

<p align="center">
  <img src="https://raw.githubusercontent.com/OSINTVerseHQ/OTinstaller/main/docs/images/otinstaller-demo.png" alt="Installing and running a tool with OTinstaller" width="820">
</p>

The full install options are below.

## Requirements

A Linux machine. Tested on Ubuntu 22.04 and 24.04, Debian 12, Arch Linux and Kali Linux (rolling).

Python 3.10 to 3.14, git, and the `venv` module. On Debian, Ubuntu and Kali, install that module with:

```bash
sudo apt install python3-venv git
```

### Tools that need an older Python

Ubuntu 26.04 LTS and Kali ship Python 3.14, and otinstaller itself runs on it. A few managed tools only install on an older Python (listed below). To use them, run otinstaller inside a Python 3.12 virtualenv:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
uv venv --python 3.12 ~/.otinstaller-venv
source ~/.otinstaller-venv/bin/activate
uv pip install otinstaller
```

A uv-created virtualenv has no pip, so the install command is `uv pip install otinstaller`. Run `source ~/.otinstaller-venv/bin/activate` again in any new terminal before using otinstaller. `otinstaller doctor` prints the Python version it is running under and lists any registered tool that needs a different one.

### Python version caveats

Some managed tools only work on some Python versions. otinstaller checks before installing them and says which version to use, and `otinstaller doctor` lists the ones that won't install on your Python. Every tool was installed and run on Python 3.10, 3.12, 3.13 and 3.14 before 0.1.0. Known limits:

- `ghunt`: requires Python <3.14 (its dependency Pillow 10 has no wheels for 3.14 and needs the libjpeg headers to compile)
- `auto-archiver`: requires Python <3.13 (dependency `pdqhash` needs a C++ compiler, no wheel for 3.13+)
- `telepathy`: requires Python <3.13 (dependency `googletrans`/`httpx` uses removed `cgi` module)
- `spiderfoot`: requires Python <3.13 (its pinned `lxml` and `cryptography` have no wheels for 3.13+)
- `theharvester`: requires Python 3.12 or newer (its current release, 4.11.1, needs it)
- `whatsapp-osint`: requires Python 3.11 or newer (it imports `datetime.UTC`)


## Install OTinstaller

For system-wide installation, use `pipx install otinstaller`. This provides the `otinstaller` and `ot` commands on your PATH without a virtualenv.

Alternatively, create a virtualenv and install from PyPI:

```bash
python3 -m venv ~/.otinstaller-venv
source ~/.otinstaller-venv/bin/activate
pip install otinstaller
```

Run `source ~/.otinstaller-venv/bin/activate` again in any new terminal before using otinstaller.

### Install from source

To install from this repository (for development):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Run `source .venv/bin/activate` again from this folder in any new terminal if the next command says `otinstaller: command not found`.

Check the machine with:

```bash
otinstaller doctor
```

`doctor` prints `[ok]` or `[problem]` for Linux, Python, git, and venv. Fix any `[problem]` line before you continue. It often tells you the package to install.

## Run your first tool

`init` creates `~/.otinstaller/` and shows a responsible-use notice. It asks `Do you accept? [y/N]`. Type `y` and press Enter. Nothing can be installed until you do. If you go straight to `otinstaller install`, it shows the same notice and asks the first time. In scripts, run `otinstaller init --yes` first.

```bash
otinstaller init
```

Sherlock searches for a username. The install asks `Install? [y/N]`. The capital N means Enter alone means no, so type `y` to continue.

```bash
otinstaller install sherlock
otinstaller run sherlock -- someexampleuser123
```

The `--` marks where otinstaller's own options end. Everything after it is passed to Sherlock. When the run finishes, otinstaller prints a path under `results/` in the folder where you ran the command. That file is the tool's output.

To try a different tool, run `otinstaller list` and use its name in place of `sherlock`. Each tool has its own page in the [documentation](https://github.com/OSINTVerseHQ/OTinstaller-Docs).

## Typed inputs

Instead of remembering each tool's flags, use a typed input prefix:

| Prefix | Input | Example |
| --- | --- | --- |
| `u:` | username | `u:johndoe` |
| `e:` | email | `e:john@example.com` |
| `p:` | phone | `p:+15551234567` |
| `d:` | domain | `d:example.com` |
| `url:` | URL | `url:https://example.com` |
| `q:` | text query | `q:search terms` |
| `geo:` | coordinates | `geo:32.22,-110.97` |
| `tg:` | Telegram channel | `tg:channelname` |
| `lat:` | latitude | `lat:37.7749` |
| `lng:` | longitude | `lng:-122.4194` |

```bash
otinstaller run sherlock -- u:johndoe
otinstaller run holehe -- e:john@example.com
otinstaller run dnstwist -- d:example.com
```

Each tool declares which input types it supports. Run `otinstaller info <tool>` to see its mapping. Plain arguments after `--` are always passed to the tool unchanged, so every flag of the original tool still works.

## Run every matching tool

```bash
otinstaller run --all u:johndoe
otinstaller run --all --live e:john@example.com
```

`--all` runs every installed tool that supports the given input type. Only `u`, `e`, `p`, `d` and `url` work with `--all`. Tools that need API keys or a login are skipped unless `--include-credentialed` is passed, and tools that ask questions while they run (such as `ghunt login` or the fsociety menu) are always skipped; run those on their own. Tools that monitor a target continuously (such as `instagram-monitor`) never run under `--all` or `auto`, because they do not exit on their own.

`otinstaller auto <target>` detects whether the target is an email, domain, URL or username and runs every installed tool that takes that input, passing it with the tool's own flag, the same way as a typed input. It skips the same tools as `--all`, and `--include-credentialed` works the same way. `--type` overrides the detection, for example `--type phone`. IP addresses are detected, but no tool takes an IP as a typed input yet, so `auto` reports that none match.

`otinstaller playbook --list` shows the playbooks that ship with otinstaller (`domain-recon` and `username-investigation`). To add your own, put YAML files in a `playbooks` folder in the directory you run otinstaller from; a file with the same name as a bundled playbook replaces it.

## Command reference

| Command | What it does |
| --- | --- |
| `otinstaller init` | Create config and directories, accept the notice |
| `otinstaller list` / `--installed` | List tools |
| `otinstaller search <query>` | Search tools |
| `otinstaller info <tool>` or `otinstaller <tool>` | Show tool details |
| `otinstaller install <tool>...` / `--all` | Install tools |
| `otinstaller run <tool>... -- <args>` | Run tools |
| `otinstaller run --all u:...` | Run all matching tools |
| `otinstaller run --live` | Live status table for parallel runs |
| `otinstaller run --case <name>` | Group runs under a named case |
| `otinstaller auto <target>` | Detect the target type and run matching tools |
| `otinstaller playbook [name] [target]` / `--list` | Run or list playbooks |
| `otinstaller example <tool>` | Show example output |
| `otinstaller extract <target>` | Extract indicators from saved results |
| `otinstaller diff <tool> <target>` | Compare the two most recent runs |
| `otinstaller update` / `--all` / `--check-only` | Bring tools to the version this release of otinstaller pins and tested |
| `otinstaller check-updates` | Check for updates (read-only) |
| `otinstaller remove <tool>...` / `--all` | Remove tools |
| `otinstaller keys check` | Check API keys |
| `otinstaller crash-reports` / `on` / `off` | Show or change opt-in crash reports (off by default) |
| `otinstaller resume` | Handle interrupted jobs |
| `otinstaller doctor` | Check the machine |
| `otinstaller about` | Show the banner, credits and contact |

### Scripts and AI agents

Every command supports `--json`. Commands never prompt when `--yes` or `-y` is given, or when stdin is not a terminal. otinstaller's own errors exit with 1 (error), 2 (invalid input) or 130 (interrupted). For a single-tool run, the tool's own exit code is returned and also recorded in the `.meta.json` file.

The startup banner is only shown in an interactive terminal. It is never printed with `--json` or when output is piped, and `OTINSTALLER_NO_BANNER=1` turns it off completely.

For AI agents, see [`llms.txt`](https://github.com/OSINTVerseHQ/OTinstaller/blob/main/llms.txt).

## Results

Results are saved to `./results/<tool>/<target>/` using the filename pattern `<YYYYmmdd-HHMMSS>_<tool>_<target>_<runid>.<ext>` plus a `.meta.json` sidecar. Results go to `./results/` in the folder where the command is run, so run it from the same folder each time, or set `OTINSTALLER_RESULTS_DIR` to a fixed path.

Tools that ask for input, such as GHunt's login, setup wizards and menus, run on a pseudo-terminal when you are at one, so their prompts show up and the session is still saved. Values given to credential flags such as `--cookie`, `--token` or `--password` are written to `.meta.json` as `***`.

```
results/sherlock/testuser/20260929-123456_sherlock_testuser_abc123.txt
results/sherlock/testuser/20260929-123456_sherlock_testuser_abc123.meta.json
```

Results can contain personal data. Store and share them accordingly.

## API keys

One env file holds all API keys: `~/.otinstaller/.env`, permissions 600. From that file, each tool only receives the keys it declares in its registry entry. Tools also inherit your shell environment, so do not export secrets you do not want tools to see. Run `otinstaller keys check` to verify your keys.

## Resume

If a run or install is cut off by a crash, a kill or a power loss, otinstaller leaves a job marker in `~/.otinstaller/jobs/`. Run `otinstaller resume` to handle it:

- For installs: cleans up partial state and retries the install.
- For runs: reports the interrupted run and prints the command to rerun.

Pressing Ctrl+C stops cleanly and removes the marker, so there is nothing to resume. Use `otinstaller resume --dry-run` to preview, and `--json` for machine-readable output. Partial output from interrupted runs is always kept.

## Responsible use

OTinstaller installs and runs third-party open-source tools. It does not create, own or verify them. Many are dual-use: used for fraud investigations, journalism, security research and compliance, but capable of misuse.

Use them only on targets you are authorized to investigate, and follow the laws that apply to you and the terms of the services you query. Do not use them to harass, stalk or harm anyone.

Tools tagged `dual-use` in the registry print a notice and ask for confirmation before installing, unless `--yes` is given. The full notice is accepted on first `otinstaller init`, and `otinstaller init` shows it again any time.


## Tool catalogue

<!-- tool-catalogue:start -->
The registry ships **47 tools**. By what they accept: 24 username, 14 email, 4 phone, 18 domain, 7 ip address, 11 url, 5 name.
A tool that accepts several input types is listed under the first one.

<details>
<summary><b>Username</b> (15)</summary>

| Tool | What it does | Typed inputs | Notes |
| --- | --- | --- | --- |
| [Aliens Eye](https://github.com/arxhr007/Aliens_eye) ([docs](https://osintverse.gitbook.io/otinstaller/tools/aliens-eye)) | Hunt down 840+ social media accounts using AI | `u:` |  |
| [Blackbird](https://github.com/antoniaci/blackbird) ([docs](https://osintverse.gitbook.io/otinstaller/tools/blackbird)) | OSINT tool to search for accounts by username and email across social networks | `u:` `e:` |  |
| [Crosslinked](https://github.com/m8sec/CrossLinked) ([docs](https://osintverse.gitbook.io/otinstaller/tools/crosslinked)) | LinkedIn enumeration tool to extract valid employee names from an organization through search engine scraping | args after `--` |  |
| [Instagram Monitor](https://github.com/misiektoja/instagram_monitor) ([docs](https://osintverse.gitbook.io/otinstaller/tools/instagram-monitor)) | Track Instagram users' activities, profile changes and capture content with beautiful dashboards and... | `u:` | monitors continuously |
| [Instaloader](https://github.com/instaloader/instaloader) ([docs](https://osintverse.gitbook.io/otinstaller/tools/instaloader)) | Download pictures (or videos) along with their captions and other metadata from Instagram | `u:` |  |
| [Linkook](https://github.com/JackJuly/linkook) ([docs](https://osintverse.gitbook.io/otinstaller/tools/linkook)) | An OSINT tool for discovering linked social accounts and associated emails across multiple platforms using... | `u:` |  |
| [Maigret](https://github.com/soxoj/maigret) ([docs](https://osintverse.gitbook.io/otinstaller/tools/maigret)) | Collect a dossier on a person by username from 6K websites | `u:` |  |
| [Nexfil](https://github.com/thewhiteh4t/nexfil) ([docs](https://osintverse.gitbook.io/otinstaller/tools/nexfil)) | OSINT tool for finding profiles by username | `u:` |  |
| [Openosint](https://github.com/OpenOSINT/OpenOSINT) ([docs](https://osintverse.gitbook.io/otinstaller/tools/openosint)) | AI-powered OSINT agent with interactive REPL, MCP server, and direct CLI modes | args after `--` |  |
| [Sherlock](https://github.com/sherlock-project/sherlock) ([docs](https://osintverse.gitbook.io/otinstaller/tools/sherlock)) | Hunt down social media accounts by username across social networks | `u:` |  |
| [Socialscan](https://github.com/iojw/socialscan) ([docs](https://osintverse.gitbook.io/otinstaller/tools/socialscan)) | Python library for accurately querying username and email usage on online platforms | `q:` |  |
| [Telepathy](https://github.com/prose-intelligence-ltd/Telepathy-Community) ([docs](https://osintverse.gitbook.io/otinstaller/tools/telepathy)) | OSINT toolkit for investigating Telegram chats and accounts | `tg:` | needs a login or API key |
| [The Big Brother](https://github.com/chadi0x/TheBigBrother) ([docs](https://osintverse.gitbook.io/otinstaller/tools/thebigbrother)) | Find usernames across social networks | `u:` |  |
| [User Scanner](https://github.com/kaifcodec/user-scanner) ([docs](https://osintverse.gitbook.io/otinstaller/tools/user-scanner)) | (2-in-1) Email & Username OSINT suite featuring native MCP support for deep data extraction just from a... | `u:` `e:` |  |
| [Zen](https://github.com/s0md3v/Zen) ([docs](https://osintverse.gitbook.io/otinstaller/tools/zen)) | Find email addresses of GitHub users, repositories and organizations | `u:` `url:` |  |

</details>

<details>
<summary><b>Email</b> (5)</summary>

| Tool | What it does | Typed inputs | Notes |
| --- | --- | --- | --- |
| [Ghunt](https://github.com/mxrch/GHunt) ([docs](https://osintverse.gitbook.io/otinstaller/tools/ghunt)) | Offensive Google framework | `e:` | needs a login or API key |
| [H8Mail](https://github.com/khast3x/h8mail) ([docs](https://osintverse.gitbook.io/otinstaller/tools/h8mail)) | Email OSINT & Password breach hunting tool, locally or using premium services | `e:` |  |
| [Holehe](https://github.com/megadose/holehe) ([docs](https://osintverse.gitbook.io/otinstaller/tools/holehe)) | holehe allows you to check if the mail is used on different sites like twitter, instagram and will... | `e:` |  |
| [Mailaccess](https://github.com/KatrielMoses/MailAccess) ([docs](https://osintverse.gitbook.io/otinstaller/tools/mailaccess)) | Free email OSINT tool, 2500+ platforms, identity clustering, breach detection | `e:` |  |
| [NeutrOSINT](https://github.com/Kr0wZ/NeutrOSINT) ([docs](https://osintverse.gitbook.io/otinstaller/tools/neutrosint)) | Check if an email address or username exists on ProtonMail | `e:` |  |

</details>

<details>
<summary><b>Phone</b> (4)</summary>

| Tool | What it does | Typed inputs | Notes |
| --- | --- | --- | --- |
| [Ignorant](https://github.com/megadose/ignorant) ([docs](https://osintverse.gitbook.io/otinstaller/tools/ignorant)) | ignorant allows you to check if a phone number is used on different sites like snapchat, instagram | args after `--` |  |
| [Telegram Phone Number Checker](https://github.com/bellingcat/telegram-phone-number-checker) ([docs](https://osintverse.gitbook.io/otinstaller/tools/telegram-phone-number-checker)) | Check if phone numbers are connected to Telegram accounts | `p:` `u:` | needs a login or API key |
| [Toutatis](https://github.com/megadose/toutatis) ([docs](https://osintverse.gitbook.io/otinstaller/tools/toutatis)) | Toutatis is a tool that allows you to extract information from instagrams accounts such as e-mails, phone... | `u:` | needs a login or API key |
| [Whatsapp Osint](https://github.com/jasperan/whatsapp-osint) ([docs](https://osintverse.gitbook.io/otinstaller/tools/whatsapp-osint)) | WhatsApp spy - logs online/offline events from ANYONE in the world | args after `--` | needs a login or API key, monitors continuously |

</details>

<details>
<summary><b>Domain</b> (16)</summary>

| Tool | What it does | Typed inputs | Notes |
| --- | --- | --- | --- |
| [Bbot](https://github.com/blacklanternsecurity/bbot) ([docs](https://osintverse.gitbook.io/otinstaller/tools/bbot)) | The recursive internet scanner for hackers | `d:` |  |
| [Ctfr](https://github.com/UnaPibaGeek/ctfr) ([docs](https://osintverse.gitbook.io/otinstaller/tools/ctfr)) | Abusing Certificate Transparency logs for getting HTTPS websites subdomains | `d:` |  |
| [Dnsgen](https://github.com/AlephNullSK/dnsgen) ([docs](https://osintverse.gitbook.io/otinstaller/tools/dnsgen)) | DNSGen is a powerful and flexible DNS name permutation tool designed for security researchers and... | args after `--` |  |
| [Dnstwist](https://github.com/elceef/dnstwist) ([docs](https://osintverse.gitbook.io/otinstaller/tools/dnstwist)) | Domain name permutation engine for detecting homograph phishing attacks, typo squatting, and brand... | `d:` |  |
| [Fierce](https://github.com/mschwager/fierce) ([docs](https://osintverse.gitbook.io/otinstaller/tools/fierce)) | A DNS reconnaissance tool for locating non-contiguous IP space | `d:` |  |
| [Finalrecon](https://github.com/thewhiteh4t/FinalRecon) ([docs](https://osintverse.gitbook.io/otinstaller/tools/finalrecon)) | All In One Web Recon | `url:` |  |
| [Fsociety](https://github.com/fsociety-team/fsociety) ([docs](https://osintverse.gitbook.io/otinstaller/tools/fsociety)) | A Modular Penetration Testing Framework | args after `--` |  |
| [Ivre](https://github.com/ivre/ivre) ([docs](https://osintverse.gitbook.io/otinstaller/tools/ivre)) | Network recon framework | args after `--` |  |
| [Osint Brazuca Regex](https://github.com/osintbrazuca/osint-brazuca-regex) ([docs](https://osintverse.gitbook.io/otinstaller/tools/osint-brazuca-regex)) | Repositrio criado com intuito de reunir expresses regulares dentro do contexto Brasil | args after `--` |  |
| [Paramspider](https://github.com/devanshbatham/ParamSpider) ([docs](https://osintverse.gitbook.io/otinstaller/tools/paramspider)) | Mining URLs from dark corners of Web Archives for bug hunting/fuzzing/further probing | `d:` |  |
| [Pywerview](https://github.com/the-useless-one/pywerview) ([docs](https://osintverse.gitbook.io/otinstaller/tools/pywerview)) | A (partial) Python rewriting of PowerSploit's PowerView | args after `--` |  |
| [Secator](https://github.com/freelabz/secator) ([docs](https://osintverse.gitbook.io/otinstaller/tools/secator)) | secator - the pentester's swiss knife | args after `--` |  |
| [Sitedorks](https://github.com/Zarcolio/sitedorks) ([docs](https://osintverse.gitbook.io/otinstaller/tools/sitedorks)) | Search Google/Bing/Ecosia/DuckDuckGo/Yandex/Yahoo for a search term (dork) with a default set of websites,... | `q:` |  |
| [Spiderfoot](https://github.com/smicallef/spiderfoot) ([docs](https://osintverse.gitbook.io/otinstaller/tools/spiderfoot)) | SpiderFoot automates OSINT for threat intelligence and mapping your attack surface | `d:` |  |
| [Sublist3r](https://github.com/aboul3la/Sublist3r) ([docs](https://osintverse.gitbook.io/otinstaller/tools/sublist3r)) | Fast subdomain enumeration tool using multiple search engines and certificate transparency logs | `d:` |  |
| [theHarvester](https://github.com/laramies/theHarvester) ([docs](https://osintverse.gitbook.io/otinstaller/tools/theharvester)) | Find emails, subdomains and names for a domain | `d:` |  |

</details>

<details>
<summary><b>URL</b> (6)</summary>

| Tool | What it does | Typed inputs | Notes |
| --- | --- | --- | --- |
| [Auto Archiver](https://github.com/bellingcat/auto-archiver) ([docs](https://osintverse.gitbook.io/otinstaller/tools/auto-archiver)) | Automatically archive web content from various sources | `url:` | needs a login or API key |
| [Instagram Location Search](https://github.com/bellingcat/instagram-location-search) ([docs](https://osintverse.gitbook.io/otinstaller/tools/instagram-location-search)) | Find Instagram location IDs near specified coordinates | `lat:` `lng:` |  |
| [Onionsearch](https://github.com/megadose/OnionSearch) ([docs](https://osintverse.gitbook.io/otinstaller/tools/onionsearch)) | OnionSearch is a script that scrapes urls on different | `q:` |  |
| [Socid Extractor](https://github.com/soxoj/socid-extractor) ([docs](https://osintverse.gitbook.io/otinstaller/tools/socid-extractor)) | The extraction engine behind Maigret: turn any profile URL into a structured OSINT record across 150+ sites | `url:` |  |
| [Torbot](https://github.com/DedSecInside/TorBot) ([docs](https://osintverse.gitbook.io/otinstaller/tools/torbot)) | Dark Web OSINT Tool | `url:` |  |
| [Yark](https://github.com/Owez/yark) ([docs](https://osintverse.gitbook.io/otinstaller/tools/yark)) | OSINT for YouTube made simple | args after `--` |  |

</details>

<details>
<summary><b>Name</b> (1)</summary>

| Tool | What it does | Typed inputs | Notes |
| --- | --- | --- | --- |
| [EDGAR Tool](https://github.com/bellingcat/edgar) ([docs](https://osintverse.gitbook.io/otinstaller/tools/edgar-tool)) | Command line interface to search and retrieve corporate and financial data from the SEC EDGAR database | `q:` |  |

</details>

<!-- tool-catalogue:end -->

Every page linked as docs shows the tool's source, install method, credentials, typed inputs and example commands. Missing a tool? [Open an issue](https://github.com/OSINTVerseHQ/OTinstaller/issues) with its repository link. Each addition is installed, pinned to a commit and checked against its real flags before it ships.

## FAQ

**Does it work on Windows or macOS?**
On Windows, yes, inside WSL2 with Ubuntu. macOS is not tested yet, and most of the tools are built for Linux first.

**Do I need root?**
No. Root is only needed once, for `sudo apt install python3-venv git`. Everything else lives in your home directory under `~/.otinstaller/`.

**Does OTinstaller send my data anywhere?**
OTinstaller itself contacts GitHub and PyPI to install and update tools. It has no usage tracking. Crash reports are off unless you say yes: `otinstaller init` asks once, and Enter means no. If you turn them on, a report is sent only when otinstaller itself crashes, and it holds the error, where in otinstaller's code it happened, and the otinstaller, Python and OS versions, never your targets, command arguments, tool output, results, API keys, file paths or user name. Turn them on or off with `otinstaller crash-reports on` or `off`, and send a test report with `otinstaller crash-reports test`; `DO_NOT_TRACK=1` or `OTINSTALLER_CRASH_REPORTS=off` always turns them off. The tools you run contact the services they are built to query.

**How do I uninstall it?**
`ot remove --all` removes every tool, then `pipx uninstall otinstaller` removes OTinstaller itself. `rm -rf ~/.otinstaller` deletes the config, the API key file and the logs. Results stay wherever you ran your commands.

**Is it legal to use?**
The tools are legal to install. Whether a particular use is legal depends on where you are and what you are investigating. Read [Responsible use](#responsible-use) before running anything against a real person.

## Team

<table>
  <tr>
    <td align="center" width="200">
      <a href="https://github.com/Sushant-69x"><img src="https://github.com/Sushant-69x.png" width="100" alt="Sushant Koul"><br><b>Sushant Koul</b></a><br>
      Builder<br>
      <a href="https://github.com/Sushant-69x">GitHub</a> ·
      <a href="https://www.linkedin.com/in/sushantkoul07">LinkedIn</a>
    </td>
    <td align="center" width="200">
      <a href="https://github.com/dheerajydv19"><img src="https://github.com/dheerajydv19.png" width="100" alt="Dheeraj Yadav"><br><b>Dheeraj Yadav</b></a><br>
      OSINTverse<br>
      <a href="https://github.com/dheerajydv19">GitHub</a> ·
      <a href="https://x.com/dheerajydv19">X</a>
    </td>
  </tr>
</table>

Built by [OSINTverse](https://osintverse.com/).

## Contact

Email [hi@osintverse.com](mailto:hi@osintverse.com) for contributions, bug reports, new tool suggestions, or anything else. Bug reports can also go through [issues](https://github.com/OSINTVerseHQ/OTinstaller/issues).

If OTinstaller saves you time, a star on GitHub helps other investigators find it.

[X](https://x.com/osintversehq) · [LinkedIn](https://www.linkedin.com/company/osintverse) · [YouTube](https://www.youtube.com/@osintversehq) · [Reddit](https://www.reddit.com/r/OSINTVerse/) · [GitHub](https://github.com/OSINTVerseHQ)

## License

Apache License 2.0. See [LICENSE](https://github.com/OSINTVerseHQ/OTinstaller/blob/main/LICENSE) and [NOTICE](https://github.com/OSINTVerseHQ/OTinstaller/blob/main/NOTICE).

You can use, modify and redistribute OTinstaller, including in commercial work. If you redistribute it or ship something built on it, the license requires you to keep the NOTICE file with your copy. Please credit it as "OTinstaller by OSINTverse" with a link to this repository.
