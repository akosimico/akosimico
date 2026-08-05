"""Render the GitHub profile identity card and aggregate account statistics."""

from __future__ import annotations

import calendar
import datetime as dt
import html
from typing import Final

from .models import ProfileStats
from .portrait import ASCII_PORTRAIT

CARD_WIDTH: Final[int] = 1500
CARD_HEIGHT: Final[int] = 690
ASCII_X: Final[int] = 20
DIVIDER_X: Final[int] = 480
CONTENT_X: Final[int] = DIVIDER_X + 30
VALUE_X: Final[int] = 850
CONTENT_FONT_SIZE: Final[int] = 18
VALUE_FONT_WEIGHT: Final[int] = 600
ASCII_FONT_SIZE: Final[float] = 6.5
ASCII_RENDER_WIDTH: Final[int] = 440
ASCII_GUTTER: Final[int] = 20
ASCII_LINE_HEIGHT: Final[float] = 8.3
ASCII_START_Y: Final[int] = 45
BIRTH_DATE: Final[dt.date] = dt.date(2004, 6, 6)
PH_TIMEZONE: Final[dt.tzinfo] = dt.timezone(dt.timedelta(hours=8))

THEMES: Final[dict[str, dict[str, str]]] = {
    "dark": {
        "background": "#050805",
        "panel": "#0a120a",
        "border": "#14532d",
        "title": "#f0fdf4",
        "key": "#22c55e",
        "value": "#dcfce7",
        "muted": "#4ade80",
        "ascii": "#16a34a",
        "glow": "#22c55e",
        "positive": "#4ade80",
        "negative": "#f87171",
    },
    "light": {
        "background": "#f0f4f1",  # Soft, washed-out mint white (lowers background tint)
        "panel": "#ffffff",  # Pure white panel to give the ASCII breathing room
        "border": "#cbd5e1",  # Muted gray border to avoid neon distractions
        "title": "#064e3b",
        "key": "#047857",
        "value": "#0f172a",
        "muted": "#475569",
        "ascii": "#115e59",  # Deep teal-green that sharply defines fine text dots
        "glow": "#ccfbf1",
        "positive": "#0f766e",
        "negative": "#b91c1c",
    },
}


def render_all(stats: ProfileStats) -> dict[str, str]:
    """Render both GitHub color-scheme variants."""

    return {theme: render_svg(stats, theme) for theme in ("dark", "light")}


def render_svg(stats: ProfileStats, theme: str) -> str:
    """Return one deterministic SVG document with stable aggregate metric IDs."""

    stats.validate()
    if theme not in THEMES:
        raise ValueError(f"unsupported theme: {theme}")
    colors = THEMES[theme]

    ascii_spans = "\n".join(
        f'      <tspan x="{ASCII_X}" y="{ASCII_START_Y + index * ASCII_LINE_HEIGHT}" '
        f'textLength="{ASCII_RENDER_WIDTH}" lengthAdjust="spacingAndGlyphs">'
        f"{_escape(line)}</tspan>"
        for index, line in enumerate(ASCII_PORTRAIT)
    )

    profile_rows = (
        ("OS", "Windows 11", "os_data"),
        ("Uptime", _display_uptime(stats.generated_at), "uptime_data"),
        ("Host", "akosimico", "host_data"),
        ("Kernel", "Web / Python / Automation / Cloud", "kernel_data"),
        (
            "Languages.Programming",
            "Python, JavaScript, C#, Java, PHP, HTML, CSS",
            "programming_data",
        ),
        (
            "Frameworks & Libraries",
            "Laravel, Node.js, Express, Django, .NET",
            "frameworks_data",
        ),
        (
            "Databases & Formats",
            "PostgreSQL, MySQL, SQL, JSON, XML, YAML",
            "databases_data",
        ),
        (
            "Developer & AI Tools",
            "VS Code, Visual Studio, Git, Cursor, Claude, Codex",
            "tools_data",
        ),
        (
            "Languages.Human",
            "English, Filipino",
            "real_language_data",
        ),
        (
            "Hobbies.Software",
            "Automation, Web Dev, AI Systems, Gaming",
            "software_hobby_data",
        ),
    )
    profile_y = (75, 101, 127, 153, 179, 205, 231, 257, 283, 309)
    profile_spans = "\n".join(
        _row(label, value, element_id, y)
        for (label, value, element_id), y in zip(profile_rows, profile_y, strict=True)
    )

    stats_rows = _stats_rows(stats)
    rendered_stats: list[str] = []
    for index, row in enumerate(stats_rows):
        y = 425 + index * 25
        if row[2] == "lines_data":
            rendered_stats.append(_lines_row(stats, y))
        else:
            rendered_stats.append(_row(*row, y))
    stats_spans = "\n".join(rendered_stats)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_WIDTH}" height="{CARD_HEIGHT}" viewBox="0 0 {CARD_WIDTH} {CARD_HEIGHT}" role="img" aria-labelledby="title desc">
<title id="title">Mico Helis GitHub profile identity and account statistics</title>
  <desc id="desc">Terminal-style identity card with an embedded ASCII portrait and aggregate GitHub statistics.</desc>
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
      .section {{ fill: {colors['muted']}; font-size: {CONTENT_FONT_SIZE}px; font-weight: 700; }}
      .key {{ fill: {colors['key']}; font-size: {CONTENT_FONT_SIZE}px; font-weight: 700; }}
      .value {{ fill: {colors['value']}; font-size: {CONTENT_FONT_SIZE}px; font-weight: {VALUE_FONT_WEIGHT}; }}
      .positive {{ fill: {colors['positive']}; font-weight: 700; }}
      .negative {{ fill: {colors['negative']}; font-weight: 700; }}
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
<tspan x="{CONTENT_X}" y="38" class="section">— PROFILE  —————————————————————————————————————————</tspan>
{profile_spans}
    <tspan x="{CONTENT_X}" y="395" class="section">— GITHUB STATS —————————————————————————————————————————————</tspan>
{stats_spans}
  </text>
</svg>
"""


def _stats_rows(stats: ProfileStats) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    coverage = stats.coverage.upper()
    inventory_verified = coverage.startswith("COMPLETE") or coverage.startswith(
        "INVENTORY_COMPLETE"
    )
    activity_verified = coverage.startswith("COMPLETE")
    inventory = stats.inventory

    if inventory_verified and inventory.total:
        rows.append(("Repositories", _repository_line(stats), "repo_total"))
        rows.append(("Visibility", _visibility_line(stats), "visibility_data"))
        if inventory.state_total:
            rows.append(("State", _state_line(stats), "state_data"))
        if inventory.organizations:
            rows.append(
                (
                    "Organizations",
                    f"{inventory.organizations:,} {_plural(inventory.organizations, 'organization')}",
                    "organization_data",
                )
            )
        if activity_verified and stats.total_commits:
            rows.append(("Commits", _commit_line(stats), "commit_data"))
        if activity_verified and stats.total_contributions:
            rows.append(
                ("Contributions", _contribution_line(stats), "contribution_data")
            )
        if activity_verified and (stats.lines_added or stats.lines_deleted):
            rows.append(("Lines of Code", "", "lines_data"))
        if inventory.stars_owned or stats.followers:
            rows.append(("Signals", _signal_line(stats), "signal_data"))

    rows.append(("Last Sync", _display_timestamp(stats.generated_at), "generated_data"))
    return rows


def _row(label: str, value: str, element_id: str, y: int) -> str:
    return (
        f'      <tspan x="{CONTENT_X}" y="{y}" class="key">{_escape(label)}</tspan>'
        f'<tspan x="{VALUE_X}" y="{y}" class="value" id="{element_id}">{_escape(value)}</tspan>'
    )


def _lines_row(stats: ProfileStats, y: int) -> str:
    details: list[str] = []
    if stats.lines_added:
        details.append(f'<tspan class="positive">{stats.lines_added:,}++</tspan>')
    if stats.lines_deleted:
        details.append(f'<tspan class="negative">{stats.lines_deleted:,}--</tspan>')
    joined = ", ".join(details)
    return (
        f'      <tspan x="{CONTENT_X}" y="{y}" class="key">Lines of Code</tspan>'
        f'<tspan x="{VALUE_X}" y="{y}" class="value" id="lines_data">'
        f"{stats.total_lines:,} total lines ({joined})</tspan>"
    )


def _repository_line(stats: ProfileStats) -> str:
    inventory = stats.inventory
    details = _nonzero_details(
        (inventory.owned, "owned"),
        (inventory.organization_member, "organization owned"),
        (inventory.collaborator, "collaborator"),
    )
    return _grouped_total(inventory.total, details)


def _visibility_line(stats: ProfileStats) -> str:
    inventory = stats.inventory
    details = _nonzero_details(
        (inventory.public, "public"),
        (inventory.private, "private"),
        (inventory.internal, "internal"),
    )
    return _grouped_total(inventory.total, details)


def _state_line(stats: ProfileStats) -> str:
    inventory = stats.inventory
    details = _nonzero_details(
        (inventory.archived, "archived"),
        (inventory.forks, "forked"),
        (inventory.disabled, "disabled"),
    )
    return _grouped_total(inventory.state_total, details)


def _commit_line(stats: ProfileStats) -> str:
    details = _nonzero_details(
        (stats.public_commits, "public"),
        (stats.private_commits, "private"),
    )
    return f"{stats.total_commits:,} total commits ({', '.join(details)})"


def _contribution_line(stats: ProfileStats) -> str:
    details = _nonzero_details(
        (stats.public_contributions, "public"),
        (stats.restricted_contributions, "restricted"),
    )
    return f"{stats.total_contributions:,} total contributions ({', '.join(details)})"


def _signal_line(stats: ProfileStats) -> str:
    parts: list[str] = []
    if stats.inventory.stars_owned:
        parts.append(
            f"{stats.inventory.stars_owned:,} {_plural(stats.inventory.stars_owned, 'star')}"
        )
    if stats.followers:
        parts.append(f"{stats.followers:,} {_plural(stats.followers, 'follower')}")
    return " / ".join(parts)


def _nonzero_details(*items: tuple[int, str]) -> list[str]:
    return [f"{value:,} {label}" for value, label in items if value]


def _grouped_total(total: int, details: list[str]) -> str:
    return f"{total:,} ({', '.join(details)})" if details else f"{total:,}"


def _plural(value: int, singular: str) -> str:
    return singular if value == 1 else f"{singular}s"


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
    return (
        _parse_timestamp(value).astimezone(PH_TIMEZONE).strftime("%B %d, %Y %I:%M %p")
    )


def _parse_timestamp(value: str) -> dt.datetime:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)
