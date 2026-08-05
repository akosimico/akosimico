"""Render the GitHub profile identity card and aggregate account statistics.

Layout: a terminal-window "dashboard" — a title bar with traffic-light dots
and a decorative tab strip, a prominent ASCII portrait pane on the left (like
a terminal running `python profile.py`), and a right-hand column of stat
"cards" grouped under tab-styled section headers.
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
CARD_WIDTH: Final[int] = 1700
MIN_CARD_HEIGHT: Final[int] = 900
OUTER_MARGIN: Final[int] = 20

# Title bar (traffic lights + decorative tab strip)
CHROME_HEIGHT: Final[int] = 56
TAB_Y: Final[int] = 18
TAB_HEIGHT: Final[int] = 30
TAB_LABELS: Final[tuple[str, ...]] = ("portrait.ascii", "profile.json", "stats.log")

# Left "terminal" pane — home of the ASCII portrait
LEFT_PANEL_X: Final[int] = OUTER_MARGIN
LEFT_PANEL_WIDTH: Final[int] = 620
ASCII_X: Final[int] = LEFT_PANEL_X + 30
ASCII_PANEL_TOP_OFFSET: Final[int] = 58  # space under chrome for the prompt line
ASCII_BOTTOM_MARGIN: Final[int] = 100  # space reserved for the name label
ASCII_LINE_HEIGHT: Final[float] = 9.6
ASCII_FONT_SIZE: Final[float] = 7.6

# Right "dashboard" column — stat cards grouped under tab-chip section headers
PANEL_GAP: Final[int] = 30
RIGHT_PANEL_X: Final[int] = LEFT_PANEL_X + LEFT_PANEL_WIDTH + PANEL_GAP
RIGHT_PANEL_WIDTH: Final[int] = CARD_WIDTH - RIGHT_PANEL_X - OUTER_MARGIN

SECTION_CHIP_HEIGHT: Final[int] = 34
SECTION_GAP_AFTER: Final[int] = 18
SECTION_GAP_BEFORE: Final[int] = 26

CARD_GAP: Final[int] = 14
CARD_ROW_HEIGHT: Final[int] = 72
CARD_ROW_HEIGHT_TALL: Final[int] = 88  # rows whose value needs two tspans
CARD_PADDING_X: Final[int] = 24
CARD_LABEL_SIZE: Final[int] = 14
CARD_VALUE_SIZE: Final[int] = 23

BIRTH_DATE: Final[dt.date] = dt.date(2004, 6, 6)
PH_TIMEZONE: Final[dt.tzinfo] = dt.timezone(dt.timedelta(hours=8))

TRAFFIC_LIGHTS: Final[tuple[str, ...]] = ("#ff5f56", "#ffbd2e", "#27c93f")

THEMES: Final[dict[str, dict[str, str]]] = {
    "dark": {
        "background": "#050805",
        "panel": "#0a120a",
        "sidebar": "#081008",
        "chrome": "#0d160d",
        "card": "#0a140a",
        "border": "#14532d",
        "title": "#f0fdf4",
        "key": "#22c55e",
        "value": "#dcfce7",
        "muted": "#4ade80",
        "ascii": "#16a34a",
        "glow": "#22c55e",
        "positive": "#4ade80",
        "negative": "#f87171",
        "tab_inactive": "#0d160d",
        "tab_inactive_text": "#3f6b47",
    },
    "light": {
        "background": "#f0f4f1",
        "panel": "#ffffff",
        "sidebar": "#e8f0ea",
        "chrome": "#e2ece4",
        "card": "#ffffff",
        "border": "#cbd5e1",
        "title": "#064e3b",
        "key": "#047857",
        "value": "#0f172a",
        "muted": "#475569",
        "ascii": "#115e59",
        "glow": "#ccfbf1",
        "positive": "#0f766e",
        "negative": "#b91c1c",
        "tab_inactive": "#dbe6de",
        "tab_inactive_text": "#7c8c82",
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
        ("OS", "Windows 11", "os_data"),
        ("Uptime", _display_uptime(stats.generated_at), "uptime_data"),
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
        ("Languages.Human", "English, Filipino", "real_language_data"),
        (
            "Hobbies.Software",
            "Automation, Web Dev, AI Systems, Gaming",
            "software_hobby_data",
        ),
    )

    stats_rows = _stats_rows(stats)

    # --- Lay out the right-hand dashboard column top-to-bottom -----------
    cards: list[tuple[int, int, str]] = []  # (y, height, svg_group)
    cursor_y = CHROME_HEIGHT + SECTION_GAP_BEFORE

    chip, cursor_y = _section_chip("PROFILE", cursor_y, colors)
    cards.append(
        (cursor_y - SECTION_CHIP_HEIGHT - SECTION_GAP_AFTER, SECTION_CHIP_HEIGHT, chip)
    )
    for label, value, element_id in profile_rows:
        height = CARD_ROW_HEIGHT
        card = _card(label, value, element_id, cursor_y, height, colors)
        cards.append((cursor_y, height, card))
        cursor_y += height + CARD_GAP

    cursor_y += SECTION_GAP_BEFORE - CARD_GAP
    chip, cursor_y = _section_chip("GITHUB STATS", cursor_y, colors)
    cards.append(
        (cursor_y - SECTION_CHIP_HEIGHT - SECTION_GAP_AFTER, SECTION_CHIP_HEIGHT, chip)
    )
    for row in stats_rows:
        if row[2] == "lines_data":
            height = CARD_ROW_HEIGHT_TALL
            card = _lines_card(stats, cursor_y, height, colors)
        else:
            height = CARD_ROW_HEIGHT
            card = _card(*row, cursor_y, height, colors)
        cards.append((cursor_y, height, card))
        cursor_y += height + CARD_GAP

    right_panel_bottom = cursor_y - CARD_GAP + OUTER_MARGIN
    total_height = max(right_panel_bottom, MIN_CARD_HEIGHT)

    dashboard_svg = "\n".join(svg for _, _, svg in cards)

    # --- Scale the ASCII portrait to fill the left terminal pane ---------
    ascii_start_y = CHROME_HEIGHT + ASCII_PANEL_TOP_OFFSET
    ascii_render_width, ascii_line_height, ascii_font_size = _scaled_ascii_metrics(
        total_height, ascii_start_y
    )
    ascii_spans = "\n".join(
        f'      <tspan x="{ASCII_X}" y="{ascii_start_y + index * ascii_line_height:.2f}" '
        f'textLength="{ascii_render_width:.2f}" lengthAdjust="spacingAndGlyphs">'
        f"{_escape(line)}</tspan>"
        for index, line in enumerate(ASCII_PORTRAIT)
    )

    tab_strip = _tab_strip(colors)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_WIDTH}" height="{total_height}" viewBox="0 0 {CARD_WIDTH} {total_height}" role="img" aria-labelledby="title desc">
<title id="title">Mico Helis GitHub profile identity and account statistics</title>
  <desc id="desc">Terminal-window dashboard with a tabbed title bar, a prominent ASCII portrait pane, and a right-hand column of stat cards grouped under tab-styled section headers.</desc>
  <defs>
    <linearGradient id="panel-gradient" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{colors['panel']}"/>
      <stop offset="1" stop-color="{colors['background']}"/>
    </linearGradient>
    <linearGradient id="sidebar-gradient" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{colors['sidebar']}"/>
      <stop offset="1" stop-color="{colors['background']}"/>
    </linearGradient>
    <radialGradient id="accent-glow" cx="0.15" cy="0.05" r="0.7">
      <stop offset="0" stop-color="{colors['glow']}" stop-opacity="0.22"/>
      <stop offset="1" stop-color="{colors['glow']}" stop-opacity="0"/>
    </radialGradient>
    <style>
      text {{ font-family: Consolas, "Liberation Mono", "DejaVu Sans Mono", monospace; white-space: pre; }}
      .ascii {{ fill: {colors['ascii']}; font-size: {ascii_font_size:.2f}px; font-weight: 500; }}
      .name {{ fill: {colors['title']}; font-size: 30px; font-weight: 700; }}
      .chip {{ fill: {colors['key']}; font-size: 15px; font-weight: 700; letter-spacing: 2px; }}
      .tab-active {{ fill: {colors['title']}; font-size: 14px; font-weight: 600; }}
      .tab-inactive {{ fill: {colors['tab_inactive_text']}; font-size: 14px; font-weight: 500; }}
      .label {{ fill: {colors['muted']}; font-size: {CARD_LABEL_SIZE}px; font-weight: 600; letter-spacing: 1.5px; }}
      .value {{ fill: {colors['value']}; font-size: {CARD_VALUE_SIZE}px; font-weight: 700; }}
      .positive {{ fill: {colors['positive']}; font-weight: 700; }}
      .negative {{ fill: {colors['negative']}; font-weight: 700; }}
    </style>
  </defs>
  <rect width="{CARD_WIDTH}" height="{total_height}" rx="22" fill="{colors['background']}"/>
  <rect x="10" y="10" width="{CARD_WIDTH - 20}" height="{total_height - 20}" rx="18" fill="url(#panel-gradient)" stroke="{colors['border']}" stroke-width="2"/>

  <!-- Title bar: traffic lights + decorative tab strip -->
  <path d="M 10 28 A 18 18 0 0 1 28 10 H {CARD_WIDTH - 28} A 18 18 0 0 1 {CARD_WIDTH - 10} 28 V {CHROME_HEIGHT} H 10 Z" fill="{colors['chrome']}"/>
  <rect x="10" y="{CHROME_HEIGHT - 1}" width="{CARD_WIDTH - 20}" height="1" fill="{colors['border']}"/>
  <circle cx="46" cy="{CHROME_HEIGHT // 2}" r="7" fill="{TRAFFIC_LIGHTS[0]}"/>
  <circle cx="70" cy="{CHROME_HEIGHT // 2}" r="7" fill="{TRAFFIC_LIGHTS[1]}"/>
  <circle cx="94" cy="{CHROME_HEIGHT // 2}" r="7" fill="{TRAFFIC_LIGHTS[2]}"/>
{tab_strip}

  <!-- Left terminal pane: ASCII portrait -->
  <rect x="{LEFT_PANEL_X}" y="{CHROME_HEIGHT}" width="{LEFT_PANEL_WIDTH}" height="{total_height - CHROME_HEIGHT - OUTER_MARGIN}" rx="14" fill="url(#sidebar-gradient)" stroke="{colors['border']}" stroke-width="1.5"/>
  <rect x="{LEFT_PANEL_X}" y="{CHROME_HEIGHT}" width="{LEFT_PANEL_WIDTH}" height="{total_height - CHROME_HEIGHT - OUTER_MARGIN}" rx="14" fill="url(#accent-glow)"/>

  <text x="{ASCII_X}" y="{CHROME_HEIGHT + 34}" fill="{colors['muted']}" font-size="17" font-family="Consolas, monospace">$ python profile.py</text>

  <text class="ascii" aria-hidden="true" xml:space="preserve">
{ascii_spans}
  </text>

  <text class="name" x="{ASCII_X}" y="{total_height - OUTER_MARGIN - 44}">akosimico</text>

  <!-- Right dashboard column: stat cards -->
{dashboard_svg}
</svg>
"""


# ---------------------------------------------------------------------------
# Chrome / tabs
# ---------------------------------------------------------------------------
def _tab_strip(colors: dict[str, str]) -> str:
    x = 130
    parts: list[str] = []
    for index, label in enumerate(TAB_LABELS):
        width = 26 + len(label) * 8
        active = index == 0
        fill = colors["panel"] if active else colors["tab_inactive"]
        text_class = "tab-active" if active else "tab-inactive"
        parts.append(
            f'  <rect x="{x}" y="{TAB_Y}" width="{width}" height="{TAB_HEIGHT}" rx="8" '
            f'fill="{fill}" stroke="{colors["border"]}" stroke-width="1"/>\n'
            f'  <text x="{x + width / 2:.1f}" y="{TAB_Y + TAB_HEIGHT / 2 + 5:.1f}" '
            f'text-anchor="middle" class="{text_class}">{_escape(label)}</text>'
        )
        if active:
            parts.append(
                f'  <rect x="{x + 6}" y="{TAB_Y + TAB_HEIGHT - 2}" width="{width - 12}" height="2.5" '
                f'fill="{colors["glow"]}"/>'
            )
        x += width + 10
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Dashboard cards
# ---------------------------------------------------------------------------
def _section_chip(title: str, y: int, colors: dict[str, str]) -> tuple[str, int]:
    width = 34 + len(title) * 10
    svg = (
        f'  <rect x="{RIGHT_PANEL_X}" y="{y}" width="{width}" height="{SECTION_CHIP_HEIGHT}" rx="8" '
        f'fill="none" stroke="{colors["key"]}" stroke-width="1.5"/>\n'
        f'  <text x="{RIGHT_PANEL_X + width / 2:.1f}" y="{y + SECTION_CHIP_HEIGHT / 2 + 5:.1f}" '
        f'text-anchor="middle" class="chip">{_escape(title)}</text>'
    )
    return svg, y + SECTION_CHIP_HEIGHT + SECTION_GAP_AFTER


def _card(
    label: str, value: str, element_id: str, y: int, height: int, colors: dict[str, str]
) -> str:
    value_span = f'<tspan class="value" id="{element_id}">{_escape(value)}</tspan>'
    return _card_shell(label, value_span, y, height, colors)


def _lines_card(
    stats: "ProfileStats", y: int, height: int, colors: dict[str, str]
) -> str:
    details: list[str] = []
    if stats.lines_added:
        details.append(f'<tspan class="positive">{stats.lines_added:,}++</tspan>')
    if stats.lines_deleted:
        details.append(f'<tspan class="negative">{stats.lines_deleted:,}--</tspan>')
    joined = ", ".join(details)
    value_span = (
        f'<tspan class="value" id="lines_data">{stats.total_lines:,} total</tspan>'
        f'<tspan x="{RIGHT_PANEL_X + CARD_PADDING_X}" dy="26" class="value" '
        f'style="font-size:{CARD_VALUE_SIZE - 4}px">({joined})</tspan>'
    )
    return _card_shell("Lines of Code", value_span, y, height, colors)


def _card_shell(
    label: str, value_markup: str, y: int, height: int, colors: dict[str, str]
) -> str:
    label_y = y + 24
    value_y = label_y + 30
    return (
        f'  <rect x="{RIGHT_PANEL_X}" y="{y}" width="{RIGHT_PANEL_WIDTH}" height="{height}" rx="10" '
        f'fill="{colors["card"]}" stroke="{colors["border"]}" stroke-width="1"/>\n'
        f'  <rect x="{RIGHT_PANEL_X}" y="{y}" width="4" height="{height}" rx="2" fill="{colors["key"]}"/>\n'
        f'  <text x="{RIGHT_PANEL_X + CARD_PADDING_X}" y="{label_y}" class="label">'
        f"{_escape(label.upper())}</text>\n"
        f'  <text x="{RIGHT_PANEL_X + CARD_PADDING_X}" y="{value_y}" xml:space="preserve">'
        f"{value_markup}</text>"
    )


# ---------------------------------------------------------------------------
# ASCII scaling
# ---------------------------------------------------------------------------
def _scaled_ascii_metrics(
    total_height: int, ascii_start_y: int
) -> tuple[float, float, float]:
    """Scale the ASCII portrait so its 72 lines fill the terminal pane's vertical space.

    Never scales *below* the original density (min() would be wrong here — we
    want to grow to fill blank space, not shrink on short cards), and keeps the
    font-to-line-height ratio identical to the original design.
    """
    line_count = len(ASCII_PORTRAIT)
    available_height = (
        total_height - OUTER_MARGIN - ASCII_BOTTOM_MARGIN
    ) - ascii_start_y
    line_height = max(available_height / line_count, ASCII_LINE_HEIGHT)
    font_size = line_height * (ASCII_FONT_SIZE / ASCII_LINE_HEIGHT)
    render_width = LEFT_PANEL_WIDTH - (ASCII_X - LEFT_PANEL_X) - 30
    return render_width, line_height, font_size


# ---------------------------------------------------------------------------
# Stats assembly (unchanged logic, carried over from the previous layout)
# ---------------------------------------------------------------------------
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
