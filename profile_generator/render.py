"""Render aggregate profile statistics as GitHub-compatible SVG."""

from __future__ import annotations

import datetime as dt
import html
from typing import Final

from .models import ProfileStats


ASCII_PORTRAIT: Final[tuple[str, ...]] = (
    "                  *++",
    "               **+-----=*",
    "             +***+**##*+==",
    "            *#*+*#*####**+-",
    "           #*#####*+==+*##++",
    "           ###*=.........+#*",
    "           %%#:...........+*",
    "           *#-.............*",
    "           --..:::.....:...-",
    "           -:...-:.....-....",
    "            :..............-",
    "             :.............",
    "             +............-",
    "            #%+...:......:",
    "          #%%@%*:.......*+",
    "      *###%%%@%%%*-...-#%%###",
    "   #######%%%%@@%%%#+#%%%%#%###**",
    " ##########%%%%%%%*--=%%%%%%########",
    "  #######%%##%%%%%*..*%%%%%%%%###%%%",
    "   #######%%#%%%%%%-.%%%%%%%%%%%%%%%",
    "   %%%%####%%%%%%%*:.=%%%%%%%%%%%%%%",
    "    %%%%%%%%%%%%%%*:..#%%%%%%%%%%%%@%",
    "    %%%%%%%%%%%%%%*...*%%%%%%%%%%%@@%",
    "     %%%%%%%%%%%%%*:..+%%%%%%%%%%@@@%",
    "     @%%%%%%%%%%%%*:..=%%%%%%%@@@@@@%",
)

THEMES: Final[dict[str, dict[str, str]]] = {
    "dark": {
        "background": "#090b10",
        "panel": "#0e1118",
        "border": "#2b3140",
        "title": "#f0f3f6",
        "key": "#ff5d73",
        "value": "#c7b8ff",
        "muted": "#768390",
        "ascii": "#b7a7ff",
        "glow": "#6d28d9",
    },
    "light": {
        "background": "#f7f8fb",
        "panel": "#ffffff",
        "border": "#d8dee9",
        "title": "#1f2328",
        "key": "#9d174d",
        "value": "#5b21b6",
        "muted": "#6e7781",
        "ascii": "#4c1d95",
        "glow": "#c4b5fd",
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
    pending = stats.coverage.upper().startswith("PENDING")

    ascii_spans = "\n".join(
        f'      <tspan x="30" y="{48 + index * 18}">{_escape(line)}</tspan>'
        for index, line in enumerate(ASCII_PORTRAIT)
    )

    rows = [
        ("ID", "LUCY-ARCH-01", "id_data"),
        ("Alias", "Lucifer Rodstark, Ph.D.", "identity_data"),
        ("Class", "Enterprise Software Architect", "class_data"),
        ("Kernel", "Full Stack .NET / Cloud / AI", "kernel_data"),
        ("Runtime", "Enterprise · Agentic · Research", "runtime_data"),
        ("Protocol", "Plan → Design → Build → Verify", "protocol_data"),
        ("Repositories", "—" if pending else _repository_line(stats), "repo_total"),
        ("Visibility", "—" if pending else _visibility_line(stats), "visibility_data"),
        ("State", "—" if pending else _state_line(stats), "state_data"),
        ("Organizations", "—" if pending else f"{inventory.organizations:,} organization owners · {inventory.resource_owners:,} resource owners", "organization_data"),
        ("Repo size", "—" if pending else f"{_format_size_kib(inventory.size_kib)} GitHub-reported", "size_data"),
        ("Contributions", "—" if pending else f"{stats.commit_contributions:,} commit contributions", "commit_data"),
        ("Signals", "—" if pending else f"{inventory.stars_owned:,} owned stars · {stats.followers:,} followers", "signal_data"),
        ("Coverage", stats.coverage, "coverage_data"),
        ("Last sync", _display_timestamp(stats.generated_at), "generated_data"),
    ]

    row_spans = []
    y = 66
    for index, (label, value, element_id) in enumerate(rows):
        if index == 6:
            row_spans.append(
                f'      <tspan x="430" y="{y - 8}" class="section">— ACCOUNT COVERAGE —————————————————————————————</tspan>'
            )
            y += 22
        row_spans.append(
            f'      <tspan x="430" y="{y}" class="key">{_escape(label)}</tspan>'
            f'<tspan x="570" y="{y}" class="value" id="{element_id}">{_escape(value)}</tspan>'
        )
        y += 28

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="560" viewBox="0 0 1200 560" role="img" aria-labelledby="title desc">
  <title id="title">Lucifer Rodstark GitHub profile identity and aggregate account statistics</title>
  <desc id="desc">ASCII portrait, enterprise systems identity, and aggregate statistics for every repository accessible to the authenticated account.</desc>
  <defs>
    <linearGradient id="panel-gradient" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{colors['panel']}"/>
      <stop offset="1" stop-color="{colors['background']}"/>
    </linearGradient>
    <radialGradient id="accent-glow" cx="0.12" cy="0.2" r="0.75">
      <stop offset="0" stop-color="{colors['glow']}" stop-opacity="0.22"/>
      <stop offset="1" stop-color="{colors['glow']}" stop-opacity="0"/>
    </radialGradient>
    <style>
      text {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; white-space: pre; }}
      .ascii {{ fill: {colors['ascii']}; font-size: 15px; font-weight: 600; }}
      .header {{ fill: {colors['title']}; font-size: 19px; font-weight: 700; }}
      .section {{ fill: {colors['muted']}; font-size: 15px; font-weight: 600; }}
      .key {{ fill: {colors['key']}; font-size: 16px; font-weight: 700; }}
      .value {{ fill: {colors['value']}; font-size: 16px; font-weight: 500; }}
      .muted {{ fill: {colors['muted']}; font-size: 13px; }}
    </style>
  </defs>
  <rect width="1200" height="560" rx="22" fill="{colors['background']}"/>
  <rect x="10" y="10" width="1180" height="540" rx="18" fill="url(#panel-gradient)" stroke="{colors['border']}" stroke-width="2"/>
  <rect x="10" y="10" width="1180" height="540" rx="18" fill="url(#accent-glow)"/>
  <circle cx="34" cy="30" r="5" fill="{colors['key']}"/>
  <circle cx="52" cy="30" r="5" fill="{colors['value']}" opacity="0.78"/>
  <circle cx="70" cy="30" r="5" fill="{colors['muted']}" opacity="0.72"/>
  <text class="ascii" aria-hidden="true">
{ascii_spans}
  </text>
  <line x1="405" y1="30" x2="405" y2="528" stroke="{colors['border']}" stroke-width="1"/>
  <text>
    <tspan x="430" y="38" class="header">lucifer@rodstark :: LUCY-ID/ARCH-01</tspan>
    <tspan x="430" y="50" class="section">——————————————————————————————————————————————————</tspan>
{chr(10).join(row_spans)}
  </text>
  <text x="30" y="532" class="muted">ASCII source transformed locally · original portrait not stored</text>
</svg>
'''


def _repository_line(stats: ProfileStats) -> str:
    inventory = stats.inventory
    return (
        f"{inventory.total:,} total · {inventory.owned:,} owned · "
        f"{inventory.organization_member:,} org · {inventory.collaborator:,} collaborator"
    )


def _visibility_line(stats: ProfileStats) -> str:
    inventory = stats.inventory
    return f"{inventory.public:,} public · {inventory.private:,} private · {inventory.internal:,} internal"


def _state_line(stats: ProfileStats) -> str:
    inventory = stats.inventory
    return f"{inventory.archived:,} archived · {inventory.forks:,} forks · {inventory.disabled:,} disabled"


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


def _display_timestamp(value: str) -> str:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)
