"""Render the GitHub profile identity card and aggregate account statistics."""

from __future__ import annotations

import calendar
import datetime as dt
import html
from pathlib import Path
from typing import Final

from .models import ProfileStats


CARD_WIDTH: Final[int] = 1500
CARD_HEIGHT: Final[int] = 690
ASCII_X: Final[int] = 20
DIVIDER_X: Final[int] = 550
ASCII_FONT_SIZE: Final[int] = 8
ASCII_RENDER_WIDTH: Final[int] = 500
ASCII_GUTTER: Final[int] = 20
ASCII_LINE_HEIGHT: Final[int] = 11
ASCII_START_Y: Final[int] = 50
BIRTH_DATE: Final[dt.date] = dt.date(1998, 11, 23)
ASCII_SOURCE_PATH: Final[Path] = Path(__file__).resolve().parents[1] / "assets" / "ascii-portrait.txt"


def _load_ascii_portrait(path: Path = ASCII_SOURCE_PATH) -> tuple[str, ...]:
    lines = tuple(path.read_text(encoding="utf-8").splitlines())
    if len(lines) != 55 or any(len(line) != 100 for line in lines):
        raise ValueError("ASCII portrait must contain exactly 55 lines of 100 characters")
    return lines


ASCII_PORTRAIT: Final[tuple[str, ...]] = _load_ascii_portrait()

THEMES: Final[dict[str, dict[str, str]]] = {
    "dark": {
        "background": "#090909",
        "panel": "#160b0b",
        "border": "#4a1d1d",
        "title": "#fff5f5",
        "key": "#ff5c5c",
        "value": "#fff0f0",
        "muted": "#9b7777",
        "ascii": "#ff8d8d",
        "glow": "#b42318",
    },
    "light": {
        "background": "#fffafa",
        "panel": "#ffffff",
        "border": "#e7b5b0",
        "title": "#2b0b0b",
        "key": "#b42318",
        "value": "#7a271a",
        "muted": "#7f5a55",
        "ascii": "#b42318",
        "glow": "#fecdca",
    },
}


def render_all(stats: ProfileStats) -> dict[str, str]:
    """Render both GitHub color-scheme variants."""

    return {theme: render_svg(stats, theme) for theme in ("dark", "light")}


def render_svg(stats: ProfileStats, theme: str) -> str:
    """Return one deterministic SVG document with stable metric IDs."""

    stats.validate()
    if theme not in THEMES:
        raise ValueError(f"unsupported theme: {theme}")
    colors = THEMES[theme]
    inventory = stats.inventory
    inventory_pending = stats.coverage.upper().startswith("PENDING")
    signals_complete = stats.coverage.upper().startswith("COMPLETE")

    ascii_spans = "\n".join(
        f'      <tspan x="{ASCII_X}" y="{ASCII_START_Y + index * ASCII_LINE_HEIGHT}" textLength="{ASCII_RENDER_WIDTH}" lengthAdjust="spacingAndGlyphs">{_escape(line)}</tspan>'
        for index, line in enumerate(ASCII_PORTRAIT)
    )

    profile_rows = (
        ("OS", "Windows 11", "os_data"),
        ("Uptime", _display_uptime(stats.generated_at), "uptime_data"),
        ("Host", "Rodstark Global Solutions, Inc.", "host_data"),
        ("Kernel", "Enterprise Architecture / .NET / Cloud / AI", "kernel_data"),
        ("IDE", "VS Code / Codex / Visual Studio", "ide_data"),
        (
            "Languages.Programming",
            "C#, VB.NET, C++, Python, Java, PHP, JavaScript, TS",
            "programming_data",
        ),
        (
            "Languages.Computer",
            "HTML, CSS, SASS, SQL, JSON, XML, YAML",
            "computer_data",
        ),
        (
            "Languages.Real",
            "English, Filipino, German, Japanese",
            "real_language_data",
        ),
        (
            "Hobbies.Software",
            "Modding, SaaS, Gaming, AI Systems, Automation",
            "software_hobby_data",
        ),
        (
            "Hobbies.Hardware",
            "PC Building, Performance Tuning, Undervolting",
            "hardware_hobby_data",
        ),
    )

    repository_value = "—" if inventory_pending else _repository_line(stats)
    visibility_value = "—" if inventory_pending else _visibility_line(stats)
    state_value = "—" if inventory_pending else _state_line(stats)
    organization_value = (
        "—"
        if inventory_pending
        else f"{inventory.organizations:,} organizations / {inventory.resource_owners:,} resource owners"
    )
    size_value = "—" if inventory_pending else _format_size_kib(inventory.size_kib)
    commit_value = (
        f"{stats.commit_contributions:,} commit contributions / "
        f"{stats.restricted_contributions:,} restricted"
        if signals_complete
        else "—"
    )
    signal_value = (
        f"{inventory.stars_owned:,} stars / {stats.followers:,} followers"
        if signals_complete
        else "—"
    )

    stats_rows = (
        ("Repositories", repository_value, "repo_total"),
        ("Visibility", visibility_value, "visibility_data"),
        ("State", state_value, "state_data"),
        ("Organizations", organization_value, "organization_data"),
        ("Repo Size", size_value, "size_data"),
        ("Commits", commit_value, "commit_data"),
        ("Signals", signal_value, "signal_data"),
        ("Coverage", stats.coverage, "coverage_data"),
        ("Last Sync", _display_timestamp(stats.generated_at), "generated_data"),
    )

    profile_y = (90, 116, 142, 168, 194, 238, 264, 290, 334, 360)
    profile_spans = "\n".join(
        _row(label, value, element_id, y)
        for (label, value, element_id), y in zip(profile_rows, profile_y, strict=True)
    )
    stats_spans = "\n".join(
        _row(label, value, element_id, 440 + index * 25)
        for index, (label, value, element_id) in enumerate(stats_rows)
    )

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_WIDTH}" height="{CARD_HEIGHT}" viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}" role="img" aria-labelledby="title desc">
  <title id="title">Lucifer Rodstark, Ph.D. GitHub profile identity and account statistics</title>
  <desc id="desc">Terminal-style identity card with an ASCII portrait and aggregate GitHub account statistics.</desc>
  <defs>
    <linearGradient id="panel-gradient" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{colors['panel']}"/>
      <stop offset="1" stop-color="{colors['background']}"/>
    </linearGradient>
    <radialGradient id="accent-glow" cx="0.12" cy="0.2" r="0.75">
      <stop offset="0" stop-color="{colors['glow']}" stop-opacity="0.24"/>
      <stop offset="1" stop-color="{colors['glow']}" stop-opacity="0"/>
    </radialGradient>
    <style>
      text {{ font-family: Consolas, "Liberation Mono", "DejaVu Sans Mono", monospace; white-space: pre; }}
      .ascii {{ fill: {colors['ascii']}; font-size: {ASCII_FONT_SIZE}px; font-weight: 500; }}
      .header {{ fill: {colors['title']}; font-size: 19px; font-weight: 700; }}
      .section {{ fill: {colors['muted']}; font-size: 15px; font-weight: 700; }}
      .key {{ fill: {colors['key']}; font-size: 15px; font-weight: 700; }}
      .value {{ fill: {colors['value']}; font-size: 15px; font-weight: 500; }}
    </style>
  </defs>
  <rect width="{CARD_WIDTH}" height="{CARD_HEIGHT}" rx="22" fill="{colors['background']}"/>
  <rect x="10" y="10" width="{CARD_WIDTH - 20}" height="{CARD_HEIGHT - 20}" rx="18" fill="url(#panel-gradient)" stroke="{colors['border']}" stroke-width="2"/>
  <rect x="10" y="10" width="{CARD_WIDTH - 20}" height="{CARD_HEIGHT - 20}" rx="18" fill="url(#accent-glow)"/>
  <circle cx="34" cy="30" r="5" fill="{colors['key']}"/>
  <circle cx="52" cy="30" r="5" fill="{colors['ascii']}" opacity="0.78"/>
  <circle cx="70" cy="30" r="5" fill="{colors['muted']}" opacity="0.72"/>
  <text class="ascii" aria-hidden="true" xml:space="preserve">
{ascii_spans}
  </text>
  <line x1="{DIVIDER_X}" y1="30" x2="{DIVIDER_X}" y2="660" stroke="{colors['border']}" stroke-width="1"/>
  <text>
    <tspan x="580" y="38" class="header">lucifer@rodstark :: LUCY-ARCH-01</tspan>
    <tspan x="580" y="54" class="section">— PROFILE / LUCIFER RODSTARK, PH.D. —————————————————————————</tspan>
{profile_spans}
    <tspan x="580" y="410" class="section">— GITHUB STATS —————————————————————————————————————————————</tspan>
{stats_spans}
  </text>
</svg>
'''


def _row(label: str, value: str, element_id: str, y: int) -> str:
    return (
        f'      <tspan x="580" y="{y}" class="key">{_escape(label)}</tspan>'
        f'<tspan x="920" y="{y}" class="value" id="{element_id}">{_escape(value)}</tspan>'
    )


def _repository_line(stats: ProfileStats) -> str:
    inventory = stats.inventory
    return (
        f"{inventory.total:,} total / {inventory.owned:,} owned / "
        f"{inventory.organization_member:,} org / {inventory.collaborator:,} collaborator"
    )


def _visibility_line(stats: ProfileStats) -> str:
    inventory = stats.inventory
    return (
        f"{inventory.public:,} public / {inventory.private:,} private / "
        f"{inventory.internal:,} internal"
    )


def _state_line(stats: ProfileStats) -> str:
    inventory = stats.inventory
    return (
        f"{inventory.archived:,} archived / {inventory.forks:,} forks / "
        f"{inventory.disabled:,} disabled"
    )


def _format_size_kib(size_kib: int) -> str:
    value = float(size_kib)
    units = ("KiB", "MiB", "GiB", "TiB", "PiB")
    unit = units[0]
    for candidate in units:
        unit = candidate
        if value < 1024 or candidate == units[-1]:
            break
        value /= 1024
    if unit == "KiB":
        return f"{int(value):,} {unit}"
    return f"{value:,.1f} {unit}"


def _display_uptime(value: str) -> str:
    current = _parse_timestamp(value).date()
    years = current.year - BIRTH_DATE.year
    months = current.month - BIRTH_DATE.month
    days = current.day - BIRTH_DATE.day
    if days < 0:
        previous_month = current.month - 1 or 12
        previous_year = current.year if current.month > 1 else current.year - 1
        days += calendar.monthrange(previous_year, previous_month)[1]
        months -= 1
    if months < 0:
        months += 12
        years -= 1
    return f"{years} years, {months} months, {days} days"


def _display_timestamp(value: str) -> str:
    return _parse_timestamp(value).strftime("%Y-%m-%d %H:%M UTC")


def _parse_timestamp(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(dt.timezone.utc)


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)
