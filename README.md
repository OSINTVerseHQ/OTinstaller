# otinstaller

Install, run, update and remove open-source command line tools by name.

You pick a tool from a list. otinstaller downloads it into its own folder, runs it, and saves the output. You do not learn a different install method for each tool.

It is for people doing open-source intelligence (OSINT) work. otinstaller does not write the tools. It installs other people's software. You are responsible for how you use it.

Status: early development. Not published to PyPI yet. The tool list, a longer walkthrough, and the responsible-use notice are at [osintverse.com/otinstaller](https://osintverse.com/otinstaller).

## What you need

A Linux machine. Tested on Ubuntu 22.04 and 24.04, Debian 12, and Arch Linux. Kali Linux is checked by hand before a release.

Python 3.10 or newer, git, and the `venv` module. On Debian, Ubuntu and Kali, install that module with:

```bash
sudo apt install python3-venv git
```

## Install otinstaller

These commands install otinstaller itself. Run them in this repository's folder. A virtualenv is a private Python folder, so this install does not change the Python that came with the system.

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
pip install -e .
```

`otinstaller` should now be on your path. A new terminal does not keep that. Run `source .venv/bin/activate` again from this folder if the next command says `otinstaller: command not found`.

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
```

```bash
otinstaller run sherlock -- someexampleuser123
```

The `--` marks where otinstaller's own options end. Everything after it is passed to Sherlock. When the run finishes, otinstaller prints a path under `results/` in the folder where you ran the command. That file is the tool's output.

To try a different tool, use its name from the guide in place of `sherlock`.

## License

MIT. See [LICENSE](LICENSE).
