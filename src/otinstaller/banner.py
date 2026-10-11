"""Startup banner shown by init, about and a bare invocation."""

from __future__ import annotations

import os
import sys

from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

from otinstaller import __version__

WIDE_ART = r"""
 ██████╗ ████████╗██╗███╗   ██╗███████╗████████╗ █████╗ ██╗     ██╗     ███████╗██████╗
██╔═══██╗╚══██╔══╝██║████╗  ██║██╔════╝╚══██╔══╝██╔══██╗██║     ██║     ██╔════╝██╔══██╗
██║   ██║   ██║   ██║██╔██╗ ██║███████╗   ██║   ███████║██║     ██║     █████╗  ██████╔╝
██║   ██║   ██║   ██║██║╚██╗██║╚════██║   ██║   ██╔══██║██║     ██║     ██╔══╝  ██╔══██╗
╚██████╔╝   ██║   ██║██║ ╚████║███████║   ██║   ██║  ██║███████╗███████╗███████╗██║  ██║
 ╚═════╝    ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝
""".strip("\n")

NARROW_ART = r"""
   ____  _______            __        ____
  / __ \/_  __(_)___  _____/ /_____ _/ / /__  _____
 / / / / / / / / __ \/ ___/ __/ __ `/ / / _ \/ ___/
/ /_/ / / / / / / / (__  ) /_/ /_/ / / /  __/ /
\____/ /_/ /_/_/ /_/____/\__/\__,_/_/_/\___/_/
""".strip("\n")

# Top-to-bottom gradient, one color per art row.
GRADIENT = ["#00e5ff", "#00b8ff", "#4d8bff", "#8a5cff", "#c03cff", "#ff2bd6"]

TAGLINE = "Install, run, update and remove open-source tools by name"
CREDITS = [
    ("Sushant Koul", "https://www.linkedin.com/in/sushantkoul07"),
    ("Dheeraj Yadav", "https://x.com/dheerajydv19"),
]
ORG = ("OSINTverse", "https://osintverse.com/")

WIDE_MIN_COLUMNS = len(WIDE_ART.splitlines()[0]) + 4
NARROW_MIN_COLUMNS = max(len(line) for line in NARROW_ART.splitlines()) + 4


def banner_enabled(json_output: bool = False) -> bool:
    """The banner is for people at a terminal, never for pipes, scripts or --json."""
    if json_output or os.environ.get("OTINSTALLER_NO_BANNER"):
        return False
    return sys.stdout.isatty()


def pick_art(columns: int) -> str | None:
    if columns >= WIDE_MIN_COLUMNS:
        return WIDE_ART
    if columns >= NARROW_MIN_COLUMNS:
        return NARROW_ART
    return None


def _gradient_art(art: str, color: bool) -> Text:
    text = Text()
    lines = art.splitlines()
    for i, line in enumerate(lines):
        # Spread the palette evenly whatever the number of rows.
        shade = GRADIENT[round(i * (len(GRADIENT) - 1) / max(len(lines) - 1, 1))]
        text.append(line + "\n", style=f"bold {shade}" if color else "")
    text.rstrip()
    return text


def _info_line(color: bool) -> Text:
    return Text(TAGLINE, style="italic" if color else "", justify="center")


def _credits_line(color: bool) -> Text:
    line = Text(justify="center")
    line.append(f"v{__version__}", style="bold #00e5ff" if color else "")
    line.append("  ·  ", style="dim" if color else "")
    for name, url in CREDITS:
        line.append(name, style=f"bold link {url}" if color else "")
        line.append("  ·  ", style="dim" if color else "")
    line.append(ORG[0], style=f"bold #ff2bd6 link {ORG[1]}" if color else "")
    return line


def render_banner(console: Console, *, color: bool = True) -> None:
    """Print the banner, choosing an art size that fits the terminal."""
    color = color and not os.environ.get("NO_COLOR") and console.color_system is not None
    art = pick_art(console.width)

    parts: list = []
    if art:
        parts.append(Align.center(_gradient_art(art, color)))
        parts.append(Text(""))
    else:
        parts.append(Text("OTinstaller", style="bold" if color else "", justify="center"))
    parts.append(_info_line(color))
    parts.append(_credits_line(color))

    console.print()
    console.print(
        Panel(
            Group(*parts),
            border_style="#8a5cff" if color else "",
            padding=(1, 2),
            expand=art is not WIDE_ART,
        )
    )
