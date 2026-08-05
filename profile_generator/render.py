"""Render the GitHub profile identity card and aggregate account statistics.

Layout: an authentic "neofetch"-style terminal readout — a titlebar with
traffic-light dots and a real window-title breadcrumb, a large ASCII
portrait on the left, and a single-column `label: value` readout on the
right grouped under comment-style section dividers (`# profile`,
`# github stats`). A small palette swatch strip and a blinking cursor
finish the terminal illusion. Row count (and therefore card height) is
driven entirely by content.
"""

from __future__ import annotations

import calendar
import datetime as dt
import html
from typing import Final

from .models import ProfileStats
from .portrait import ASCII_PORTRAIT

# ---------------------------------------------------------------------------
# Overall frame
# ---------------------------------------------------------------------------
CARD_WIDTH: Final[int] = 1500
OUTER_MARGIN: Final[int] = 24

CHROME_HEIGHT: Final[int] = 44
TITLE_TEXT: Final[str] = "akosimico@github:~/profile"

# Left pane — ASCII portrait
LEFT_WIDTH: Final[int] = 560
LEFT_X: Final[int] = OUTER_MARGIN
ASCII_X: Final[int] = LEFT_X + 26
ASCII_TOP_OFFSET: Final[int] = 54  # room under chrome for the prompt line
ASCII_BOTTOM_MARGIN: Final[int] = 46
ASCII_LINE_HEIGHT: Final[float] = 9.6
ASCII_FONT_SIZE: Final[float] = 7.6

# Right pane — neofetch-style readout
COLUMN_GAP: Final[int] = 44
RIGHT_X: Final[int] = LEFT_X + LEFT_WIDTH + COLUMN_GAP
RIGHT_WIDTH: Final[int] = CARD_WIDTH - RIGHT_X - OUTER_MARGIN
RIGHT_TOP: Final[int] = CHROME_HEIGHT + 46

ROW_HEIGHT: Final[int] = 30
ROW_HEIGHT_TALL: Final[int] = 52  # rows with a wrapped second line (Lines of Code)
GROUP_GAP_BEFORE: Final[int] = 28
GROUP_HEADER_HEIGHT: Final[int] = 26
LABEL_VALUE_GAP: Final[int] = 18
ROW_FONT_SIZE: Final[int] = 15
LABEL_CHAR_WIDTH: Final[float] = 8.7  # bold mono @ 15px
VALUE_CHAR_WIDTH: Final[float] = 8.3  # regular mono @ 15px

SWATCH_SIZE: Final[int] = 16
SWATCH_GAP: Final[int] = 6
SWATCH_ROW_HEIGHT: Final[int] = 40

BIRTH_DATE: Final[dt.date] = dt.date(2004, 6, 6)
PH_TIMEZONE: Final[dt.tzinfo] = dt.timezone(dt.timedelta(hours=8))

TRAFFIC_LIGHTS: Final[tuple[str, ...]] = ("#ff5f56", "#ffbd2e", "#27c93f")

THEMES: Final[dict[str, dict[str, str]]] = {
    "dark": {
        "background": "#050805",
        "chrome": "#0d160d",
        "border": "#14532d",
        "title": "#f0fdf4",
        "key": "#22c55e",
        "value": "#dcfce7",
        "muted": "#4ade80",
        "comment": "#3f7a4d",
        "ascii": "#16a34a",
        "positive": "#4ade80",
        "negative": "#f87171",
        "cursor": "#22c55e",
        "swatches": ("#22c55e", "#4ade80", "#16a34a", "#f0fdf4", "#f87171"),
    },
    "light": {
        "background": "#f0f4f1",
        "chrome": "#e2ece4",
        "border": "#cbd5e1",
        "title": "#064e3b",
        "key": "#047857",
        "value": "#0f172a",
        "muted": "#475569",
        "comment": "#7c9484",
        "ascii": "#115e59",
        "positive": "#0f766e",
        "negative": "#b91c1c",
        "cursor": "#047857",
        "swatches": ("#047857", "#0f766e", "#115e59", "#0f172a", "#b91c1c"),
    },
}


def render_all(stats: ProfileStats) -> dict[str, str]:
    """Render both GitHub color-scheme variants."""

    return {theme: render_svg(stats, theme) for theme in ("dark", "light")}


def render_svg(stats: ProfileStats, theme: str) -> str:
    stats.validate()
    if theme not in THEMES:
        raise ValueError(f"unsupported theme: {theme}")
    colors = THEMES[theme]

    profile_rows = (
        ("os", "Windows 11"),
        ("uptime", _display_uptime(stats.generated_at)),
        ("kernel", "Web / Python / Automation / Cloud"),
        ("languages.programming", "Python, JavaScript, C#, Java, PHP, HTML, CSS"),
        ("frameworks", "Laravel, Node.js, Express, Django, .NET"),
        ("databases", "PostgreSQL, MySQL, SQL, JSON, XML, YAML"),
        ("tools", "VS Code, Visual Studio, Git, Cursor, Claude, Codex"),
        ("languages.human", "English, Filipino"),
        ("hobbies", "Automation, Web Dev, AI Systems, Gaming"),
    )
    stats_rows = _stats_rows(stats)

    readout_svg, readout_bottom = _readout(profile_rows, stats_rows, stats, colors)

    ascii_start_y = CHROME_HEIGHT + ASCII_TOP_OFFSET
    ascii_min_height = (
        ascii_start_y
        + len(ASCII_PORTRAIT) * ASCII_LINE_HEIGHT
        + ASCII_BOTTOM_MARGIN
        + OUTER_MARGIN
    )
    total_height = round(max(readout_bottom + OUTER_MARGIN, ascii_min_height))

    ascii_render_width, ascii_line_height, ascii_font_size = _scaled_ascii_metrics(
        total_height, ascii_start_y
    )
    ascii_spans = "\n".join(
        f'      <tspan x="{ASCII_X}" y="{ascii_start_y + index * ascii_line_height:.2f}" '
        f'textLength="{ascii_render_width:.2f}" lengthAdjust="spacingAndGlyphs">'
        f"{_escape(line)}</tspan>"
        for index, line in enumerate(ASCII_PORTRAIT)
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_WIDTH}" height="{total_height}" viewBox="0 0 {CARD_WIDTH} {total_height}" role="img" aria-labelledby="title desc">
  <title id="title">Mico Helis GitHub profile identity and account statistics</title>
  <desc id="desc">Neofetch-style terminal readout with an ASCII portrait on the left and a labeled system/stats list on the right.</desc>
  <style>
    text {{ font-family: Consolas, "Liberation Mono", "DejaVu Sans Mono", monospace; white-space: pre; }}
    .ascii {{ fill: {colors['ascii']}; font-size: {ascii_font_size:.2f}px; font-weight: 500; }}
    .name {{ fill: {colors['title']}; font-size: 26px; font-weight: 700; }}
    .win-title {{ fill: {colors['muted']}; font-size: 13px; font-weight: 500; }}
    .group {{ fill: {colors['comment']}; font-size: 14px; font-weight: 600; }}
    .label {{ fill: {colors['key']}; font-size: {ROW_FONT_SIZE}px; font-weight: 700; }}
    .value {{ fill: {colors['value']}; font-size: {ROW_FONT_SIZE}px; font-weight: 400; }}
    .positive {{ fill: {colors['positive']}; font-weight: 700; }}
    .negative {{ fill: {colors['negative']}; font-weight: 700; }}
  </style>
  <rect width="{CARD_WIDTH}" height="{total_height}" rx="18" fill="{colors['background']}"/>
  <rect x="8" y="8" width="{CARD_WIDTH - 16}" height="{total_height - 16}" rx="14" fill="none" stroke="{colors['border']}" stroke-width="1.5"/>

  <!-- Titlebar -->
  <path d="M 8 22 A 14 14 0 0 1 22 8 H {CARD_WIDTH - 22} A 14 14 0 0 1 {CARD_WIDTH - 8} 22 V {CHROME_HEIGHT} H 8 Z" fill="{colors['chrome']}"/>
  <rect x="8" y="{CHROME_HEIGHT - 1}" width="{CARD_WIDTH - 16}" height="1" fill="{colors['border']}"/>
  <circle cx="40" cy="{CHROME_HEIGHT // 2}" r="6" fill="{TRAFFIC_LIGHTS[0]}"/>
  <circle cx="60" cy="{CHROME_HEIGHT // 2}" r="6" fill="{TRAFFIC_LIGHTS[1]}"/>
  <circle cx="80" cy="{CHROME_HEIGHT // 2}" r="6" fill="{TRAFFIC_LIGHTS[2]}"/>
  <text x="{CARD_WIDTH / 2:.0f}" y="{CHROME_HEIGHT / 2 + 4.5:.1f}" text-anchor="middle" class="win-title">{_escape(TITLE_TEXT)}</text>

  <!-- Left pane: ASCII portrait -->
  <text x="{ASCII_X}" y="{CHROME_HEIGHT + 30}" fill="{colors['muted']}" font-size="14" font-family="Consolas, monospace">$ whoami</text>
  <text class="ascii" aria-hidden="true" xml:space="preserve">
{ascii_spans}
  </text>
  <text class="name" x="{ASCII_X}" y="{total_height - OUTER_MARGIN - 14}">akosimico<tspan fill="{colors['cursor']}">_<animate attributeName="opacity" values="1;0;1" dur="1.2s" repeatCount="indefinite"/></tspan></text>

  <!-- Divider between panes -->
  <line x1="{LEFT_X + LEFT_WIDTH + COLUMN_GAP / 2:.0f}" y1="{CHROME_HEIGHT + 16}" x2="{LEFT_X + LEFT_WIDTH + COLUMN_GAP / 2:.0f}" y2="{total_height - OUTER_MARGIN}" stroke="{colors['border']}" stroke-width="1"/>

  <!-- Right pane: readout -->
{readout_svg}
</svg>
"""


# ---------------------------------------------------------------------------
# Readout: single-column `label: value` list, grouped, neofetch-style
# ---------------------------------------------------------------------------
def _readout(
    profile_rows: tuple[tuple[str, str], ...],
    stats_rows: list[tuple[str, str]],
    stats: ProfileStats,
    colors: dict[str, str],
) -> tuple[str, float]:
    label_width = (
        max(len(label) for label, _ in (*profile_rows, *stats_rows)) * LABEL_CHAR_WIDTH
    )
    value_x = RIGHT_X + label_width + LABEL_VALUE_GAP
    value_width = RIGHT_X + RIGHT_WIDTH - value_x

    y = float(RIGHT_TOP)
    parts: list[str] = []

    def group(title: str) -> None:
        nonlocal y
        y += GROUP_GAP_BEFORE if parts else 0
        dashes = "-" * 3
        parts.append(
            f'  <text x="{RIGHT_X}" y="{y:.2f}" class="group">{dashes} {_escape(title)} '
            f'{"-" * max(2, int((RIGHT_WIDTH - len(title) * 8.4 - 40) / 8.4))}</text>'
        )
        y += GROUP_HEADER_HEIGHT

    def row(label: str, value: str) -> None:
        nonlocal y
        parts.append(
            f'  <text x="{RIGHT_X}" y="{y:.2f}" class="label">{_escape(label)}</text>'
            f'  <text x="{value_x:.1f}" y="{y:.2f}" xml:space="preserve">{_value_span(value, value_width)}</text>'
        )
        y += ROW_HEIGHT

    def lines_row(stats: ProfileStats) -> None:
        nonlocal y
        details: list[str] = []
        if stats.lines_added:
            details.append(f'<tspan class="positive">{stats.lines_added:,}++</tspan>')
        if stats.lines_deleted:
            details.append(f'<tspan class="negative">{stats.lines_deleted:,}--</tspan>')
        joined = ", ".join(details)
        parts.append(
            f'  <text x="{RIGHT_X}" y="{y:.2f}" class="label">lines of code</text>'
            f'  <text x="{value_x:.1f}" y="{y:.2f}" xml:space="preserve">'
            f'{_value_span(f"{stats.total_lines:,} total", value_width)}</text>'
        )
        y += 22
        parts.append(
            f'  <text x="{value_x:.1f}" y="{y:.2f}" class="value" xml:space="preserve">({joined})</text>'
        )
        y += ROW_HEIGHT - 22 + 16

    group("profile")
    for label, value in profile_rows:
        row(label, value)

    group("github stats")
    for label, value in stats_rows:
        if label == "lines of code":
            lines_row(stats)
        else:
            row(label, value)

    # Palette swatch strip — a small decorative flourish, neofetch-style.
    y += GROUP_GAP_BEFORE - 12
    swatch_x = RIGHT_X
    for color in colors["swatches"]:
        parts.append(
            f'  <rect x="{swatch_x:.1f}" y="{y - SWATCH_SIZE:.1f}" width="{SWATCH_SIZE}" '
            f'height="{SWATCH_SIZE}" rx="3" fill="{color}"/>'
        )
        swatch_x += SWATCH_SIZE + SWATCH_GAP
    y += SWATCH_ROW_HEIGHT - SWATCH_SIZE

    return "\n".join(parts), y


def _value_span(value: str, available_width: float) -> str:
    estimated = len(value) * VALUE_CHAR_WIDTH
    if estimated <= available_width:
        return f'<tspan class="value">{_escape(value)}</tspan>'
    return (
        f'<tspan class="value" textLength="{available_width:.1f}" '
        f'lengthAdjust="spacingAndGlyphs">{_escape(value)}</tspan>'
    )


# ---------------------------------------------------------------------------
# ASCII scaling
# ---------------------------------------------------------------------------
def _scaled_ascii_metrics(
    total_height: int, ascii_start_y: int
) -> tuple[float, float, float]:
    line_count = len(ASCII_PORTRAIT)
    available_height = (
        total_height - OUTER_MARGIN - ASCII_BOTTOM_MARGIN
    ) - ascii_start_y
    line_height = max(available_height / line_count, ASCII_LINE_HEIGHT)
    font_size = line_height * (ASCII_FONT_SIZE / ASCII_LINE_HEIGHT)
    render_width = LEFT_WIDTH - (ASCII_X - LEFT_X) - 26
    return render_width, line_height, font_size


# ---------------------------------------------------------------------------
# Stats assembly (logic unchanged, carried over from the previous layout)
# ---------------------------------------------------------------------------
def _stats_rows(stats: ProfileStats) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    coverage = stats.coverage.upper()
    inventory_verified = coverage.startswith("COMPLETE") or coverage.startswith(
        "INVENTORY_COMPLETE"
    )
    activity_verified = coverage.startswith("COMPLETE")
    inventory = stats.inventory

    if inventory_verified and inventory.total:
        rows.append(("repositories", _repository_line(stats)))
        rows.append(("visibility", _visibility_line(stats)))
        if inventory.state_total:
            rows.append(("state", _state_line(stats)))
        if inventory.organizations:
            rows.append(
                (
                    "organizations",
                    f"{inventory.organizations:,} {_plural(inventory.organizations, 'organization')}",
                )
            )
        if activity_verified and stats.total_commits:
            rows.append(("commits", _commit_line(stats)))
        if activity_verified and stats.total_contributions:
            rows.append(("contributions", _contribution_line(stats)))
        if activity_verified and (stats.lines_added or stats.lines_deleted):
            rows.append(("lines of code", ""))
        if inventory.stars_owned or stats.followers:
            rows.append(("signals", _signal_line(stats)))

    rows.append(("last sync", _display_timestamp(stats.generated_at)))
    return rows


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
