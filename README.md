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
  <img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue" alt="Python 3.10 to 3.12">
  <img src="https://img.shields.io/badge/platform-Linux-lightgrey" alt="Linux">
  <a href="https://github.com/OSINTVerseHQ/OTinstaller/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="MIT license"></a>
</p>

<p align="center">
  <a href="https://github.com/OSINTVerseHQ/OTinstaller-Docs">Documentation</a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="#typed-inputs">Typed inputs</a> ·
  <a href="#command-reference">Commands</a> ·
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

The full install options, including Python 3.13+ systems, are below.

## Requirements

A Linux machine. Tested on Ubuntu 22.04 and 24.04, Debian 12, and Arch Linux. Kali Linux is checked by hand before a release.

Python 3.10 to 3.12, git, and the `venv` module. On Debian, Ubuntu and Kali, install that module with:

```bash
sudo apt install python3-venv git
```

### Ubuntu 26.04 LTS and other systems with Python 3.13+

Ubuntu 26.04 LTS ships Python 3.14 by default, and other distributions now ship Python 3.13+ too. otinstaller and some of its managed tools require Python 3.10–3.12, so on these systems install Python 3.12 explicitly and run otinstaller inside a virtualenv made with it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
uv venv --python 3.12 ~/.otinstaller-venv
source ~/.otinstaller-venv/bin/activate
uv pip install otinstaller
```

A uv-created virtualenv has no pip, so the install command is `uv pip install otinstaller`. Run `source ~/.otinstaller-venv/bin/activate` again in any new terminal before using otinstaller. `otinstaller doctor` prints the Python version it is running under and flags any registered tool that needs a different one.

The system Python on Ubuntu 22.04 and 24.04 already works. The uv method was tested on Ubuntu 26.04 only.

### Python version caveats

Some managed tools do not yet support Python 3.13+. The test matrix covers Python 3.10–3.12. Known affected tools:

- `auto-archiver`: requires Python <3.13 (dependency `pdqhash` needs a C++ compiler, no wheel for 3.13+)
- `telepathy`: requires Python <3.13 (dependency `googletrans`/`httpx` uses removed `cgi` module)

If you encounter install failures on Python 3.13+, run otinstaller in a Python 3.12 virtualenv.

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

`init` creates `~/.otinstaller/` and shows a responsible-use notice. It asks `Do you accept? [y/N]`. Type `y` and press Enter. Nothing can be installed until you do.

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

`--all` runs every installed tool that supports the given input type. Only `u`, `e`, `p`, `d` and `url` work with `--all`. Tools that need API keys or a login are skipped unless `--include-credentialed` is passed. Tools that monitor a target continuously (such as `instagram-monitor`) never run under `--all` or `auto`, because they do not exit on their own.

`otinstaller auto <target>` detects whether the target is an email, domain, IP, URL or username and runs the matching tools.

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
| `otinstaller update` / `--all` / `--check-only` | Update tools |
| `otinstaller check-updates` | Check for updates (read-only) |
| `otinstaller remove <tool>...` / `--all` | Remove tools |
| `otinstaller keys check` | Check API keys |
| `otinstaller resume` | Handle interrupted jobs |
| `otinstaller doctor` | Check the machine |
| `otinstaller about` | Show the banner, credits and contact |

### Scripts and AI agents

Every command supports `--json`. Commands never prompt when `--yes` or `-y` is given, or when stdin is not a terminal. otinstaller's own errors exit with 1 (error), 2 (invalid input) or 130 (interrupted). For a single-tool run, the tool's own exit code is returned and also recorded in the `.meta.json` file.

The startup banner is only shown in an interactive terminal. It is never printed with `--json` or when output is piped, and `OTINSTALLER_NO_BANNER=1` turns it off completely.

For AI agents, see [`llms.txt`](https://github.com/OSINTVerseHQ/OTinstaller/blob/main/llms.txt).

## Results

Results are saved to `./results/<tool>/<target>/` using the filename pattern `<YYYYmmdd-HHMMSS>_<tool>_<target>_<runid>.<ext>` plus a `.meta.json` sidecar. Results go to `./results/` in the folder where the command is run, so run it from the same folder each time, or set `OTINSTALLER_RESULTS_DIR` to a fixed path.

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


## Tools

The registry currently ships these tools. GitHub is the upstream project. Docs is the OTinstaller page for that tool.

| Name | GitHub | Docs |
| --- | --- | --- |
| Aliens Eye | [arxhr007/Aliens_eye](https://github.com/arxhr007/Aliens_eye) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/aliens-eye) |
| Auto Archiver | [bellingcat/auto-archiver](https://github.com/bellingcat/auto-archiver) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/auto-archiver) |
| Bbot | [blacklanternsecurity/bbot](https://github.com/blacklanternsecurity/bbot) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/bbot) |
| Blackbird | [p1ngul1n0/blackbird](https://github.com/p1ngul1n0/blackbird) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/blackbird) |
| Crosslinked | [m8sec/CrossLinked](https://github.com/m8sec/CrossLinked) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/crosslinked) |
| Ctfr | [UnaPibaGeek/ctfr](https://github.com/UnaPibaGeek/ctfr) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/ctfr) |
| Dnsgen | [AlephNullSK/dnsgen](https://github.com/AlephNullSK/dnsgen) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/dnsgen) |
| Dnstwist | [elceef/dnstwist](https://github.com/elceef/dnstwist) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/dnstwist) |
| EDGAR Tool | [bellingcat/edgar](https://github.com/bellingcat/edgar) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/edgar-tool) |
| Fierce | [mschwager/fierce](https://github.com/mschwager/fierce) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/fierce) |
| Finalrecon | [thewhiteh4t/FinalRecon](https://github.com/thewhiteh4t/FinalRecon) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/finalrecon) |
| Fsociety | [fsociety-team/fsociety](https://github.com/fsociety-team/fsociety) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/fsociety) |
| Ghunt | [mxrch/GHunt](https://github.com/mxrch/GHunt) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/ghunt) |
| H8Mail | [khast3x/h8mail](https://github.com/khast3x/h8mail) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/h8mail) |
| Holehe | [megadose/holehe](https://github.com/megadose/holehe) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/holehe) |
| Ignorant | [megadose/ignorant](https://github.com/megadose/ignorant) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/ignorant) |
| Instagram Location Search | [bellingcat/instagram-location-search](https://github.com/bellingcat/instagram-location-search) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/instagram-location-search) |
| Instagram Monitor | [misiektoja/instagram_monitor](https://github.com/misiektoja/instagram_monitor) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/instagram-monitor) |
| Instaloader | [instaloader/instaloader](https://github.com/instaloader/instaloader) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/instaloader) |
| Ivre | [ivre/ivre](https://github.com/ivre/ivre) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/ivre) |
| Linkook | [JackJuly/linkook](https://github.com/JackJuly/linkook) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/linkook) |
| Maigret | [soxoj/maigret](https://github.com/soxoj/maigret) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/maigret) |
| Mailaccess | [KatrielMoses/MailAccess](https://github.com/KatrielMoses/MailAccess) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/mailaccess) |
| NeutrOSINT | [Kr0wZ/NeutrOSINT](https://github.com/Kr0wZ/NeutrOSINT) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/neutrosint) |
| Nexfil | [thewhiteh4t/nexfil](https://github.com/thewhiteh4t/nexfil) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/nexfil) |
| Onionsearch | [megadose/OnionSearch](https://github.com/megadose/OnionSearch) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/onionsearch) |
| Openosint | [OpenOSINT/OpenOSINT](https://github.com/OpenOSINT/OpenOSINT) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/openosint) |
| Osint Brazuca Regex | [osintbrazuca/osint-brazuca-regex](https://github.com/osintbrazuca/osint-brazuca-regex) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/osint-brazuca-regex) |
| Paramspider | [devanshbatham/ParamSpider](https://github.com/devanshbatham/ParamSpider) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/paramspider) |
| Pywerview | [the-useless-one/pywerview](https://github.com/the-useless-one/pywerview) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/pywerview) |
| Secator | [freelabz/secator](https://github.com/freelabz/secator) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/secator) |
| Sherlock | [sherlock-project/sherlock](https://github.com/sherlock-project/sherlock) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/sherlock) |
| Sitedorks | [Zarcolio/sitedorks](https://github.com/Zarcolio/sitedorks) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/sitedorks) |
| Socialscan | [iojw/socialscan](https://github.com/iojw/socialscan) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/socialscan) |
| Socid Extractor | [soxoj/socid-extractor](https://github.com/soxoj/socid-extractor) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/socid-extractor) |
| Spiderfoot | [smicallef/spiderfoot](https://github.com/smicallef/spiderfoot) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/spiderfoot) |
| Sublist3r | [aboul3la/Sublist3r](https://github.com/aboul3la/Sublist3r) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/sublist3r) |
| Telegram Phone Number Checker | [bellingcat/telegram-phone-number-checker](https://github.com/bellingcat/telegram-phone-number-checker) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/telegram-phone-number-checker) |
| Telepathy | [jordanwildon/Telepathy](https://github.com/jordanwildon/Telepathy) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/telepathy) |
| The Big Brother | [chadi0x/TheBigBrother](https://github.com/chadi0x/TheBigBrother) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/thebigbrother) |
| theHarvester | [laramies/theHarvester](https://github.com/laramies/theHarvester) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/theharvester) |
| Torbot | [DedSecInside/TorBot](https://github.com/DedSecInside/TorBot) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/torbot) |
| Toutatis | [megadose/toutatis](https://github.com/megadose/toutatis) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/toutatis) |
| User Scanner | [kaifcodec/user-scanner](https://github.com/kaifcodec/user-scanner) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/user-scanner) |
| Whatsapp Osint | [jasperan/whatsapp-osint](https://github.com/jasperan/whatsapp-osint) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/whatsapp-osint) |
| Yark | [Owez/yark](https://github.com/Owez/yark) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/yark) |
| Zen | [s0md3v/Zen](https://github.com/s0md3v/Zen) | [Docs](https://osintverse.gitbook.io/otinstaller/tools/zen) |

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

[X](https://x.com/osintversehq) · [LinkedIn](https://www.linkedin.com/company/osintverse) · [YouTube](https://www.youtube.com/@osintversehq) · [Reddit](https://www.reddit.com/r/OSINTVerse/) · [GitHub](https://github.com/OSINTVerseHQ)

## License

MIT. See [LICENSE](https://github.com/OSINTVerseHQ/OTinstaller/blob/main/LICENSE).
