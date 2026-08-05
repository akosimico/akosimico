"""Regenerate the profile SVG/JSON assets from your current render.py.

Run this after editing `profile_generator/render.py` (or portrait.py) to
rebuild the assets WITHOUT needing a GitHub token. It uses placeholder
stats so the README always renders.

    python regenerate_assets.py

If you want live GitHub numbers instead, run the GitHub Actions workflow
(which uses PROFILE_STATS_TOKEN) — it will overwrite these files with your
real statistics.

Safe to keep in the repo, or delete after use.
"""

from __future__ import annotations

import json
import pathlib

from profile_generator.models import InventoryStats, ProfileStats
from profile_generator.render import render_all

ROOT = pathlib.Path(__file__).resolve().parent

# Placeholder statistics. Replace with real data if you prefer, or let the
# GitHub Actions workflow fill in your actual numbers.
stats = ProfileStats(
    schema_version=2,
    login="akosimico",
    generated_at="2026-01-01T00:00:00Z",
    account_created_at="2024-01-01T00:00:00Z",
    public_commits=0,
    private_commits=0,
    public_contributions=0,
    restricted_contributions=0,
    lines_added=0,
    lines_deleted=0,
    followers=0,
    coverage="PENDING_AUTHENTICATED_SYNC",
    inventory=InventoryStats(
        total=0,
        owned=0,
        organization_member=0,
        collaborator=0,
        public=0,
        private=0,
        internal=0,
        archived=0,
        forks=0,
        disabled=0,
        organizations=0,
        stars_owned=0,
    ),
)

rendered = render_all(stats)

assets = ROOT / "assets"
generated = ROOT / "generated"
assets.mkdir(exist_ok=True)
generated.mkdir(exist_ok=True)

for theme, svg in rendered.items():
    (assets / f"profile-{theme}.svg").write_text(svg, encoding="utf-8", newline="\n")

payload = json.dumps(stats.to_public_dict(), indent=2, sort_keys=True) + "\n"
(generated / "profile-stats.json").write_text(payload, encoding="utf-8", newline="\n")

print("assets regenerated under assets/ and generated/")
