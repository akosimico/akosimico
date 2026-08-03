"""Environment-only command line orchestration for profile generation."""

from __future__ import annotations

import json
import os
import pathlib
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Callable, Mapping

from .api import GitHubClient
from .collector import collect_profile_stats
from .models import ProfileStats
from .render import render_all


DEFAULT_REQUIRED_OWNERS = frozenset(
    {
        "itsmfknlucy",
        "Rodstark-Global-Solutions-Inc",
        "NexGen-LAVA-Inc",
        "FrostByte-Constructs-LLC",
    }
)


class ConfigurationError(RuntimeError):
    """Raised for missing or unsafe runtime configuration."""


@dataclass(frozen=True, slots=True)
class Config:
    tokens: tuple[str, ...] = field(repr=False)
    login: str
    required_owners: frozenset[str]
    root: pathlib.Path
    minimum_repositories: int = 0

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
        *,
        root: pathlib.Path | None = None,
    ) -> "Config":
        values = os.environ if env is None else env
        raw_tokens: list[str] = []
        single_token = values.get("PROFILE_STATS_TOKEN", "").strip()
        if single_token:
            raw_tokens.append(single_token)
        multi_token_value = values.get("PROFILE_STATS_TOKENS", "")
        raw_tokens.extend(line.strip() for line in multi_token_value.splitlines() if line.strip())
        tokens = tuple(dict.fromkeys(raw_tokens))
        if not tokens:
            raise ConfigurationError(
                "PROFILE_STATS_TOKEN or PROFILE_STATS_TOKENS encrypted repository secret is required"
            )
        login = values.get("PROFILE_LOGIN", "").strip()
        if not login:
            raise ConfigurationError("PROFILE_LOGIN is required")
        configured_owners = values.get("PROFILE_REQUIRED_OWNERS", "").strip()
        if configured_owners:
            required_owners = frozenset(
                owner.strip() for owner in configured_owners.split(",") if owner.strip()
            )
        else:
            required_owners = frozenset({*DEFAULT_REQUIRED_OWNERS, login})
        raw_minimum_repositories = values.get("PROFILE_MIN_REPOSITORIES", "0").strip() or "0"
        try:
            minimum_repositories = int(raw_minimum_repositories)
        except ValueError as exc:
            raise ConfigurationError(
                "PROFILE_MIN_REPOSITORIES must be a non-negative integer"
            ) from exc
        if minimum_repositories < 0:
            raise ConfigurationError("PROFILE_MIN_REPOSITORIES must be a non-negative integer")
        project_root = root or pathlib.Path(__file__).resolve().parents[1]
        return cls(
            tokens=tokens,
            login=login,
            required_owners=required_owners,
            root=project_root,
            minimum_repositories=minimum_repositories,
        )


def run_generation(
    config: Config,
    *,
    client_factory: Callable[[str], object] = GitHubClient,
) -> ProfileStats:
    """Collect, render, validate, and atomically publish aggregate outputs."""

    clients = [client_factory(token) for token in config.tokens]
    stats = collect_profile_stats(
        clients,
        expected_login=config.login,
        required_owners=config.required_owners,
        minimum_repositories=config.minimum_repositories,
    )
    rendered = render_all(stats)
    write_outputs(config.root, stats, rendered)
    return stats


def write_outputs(
    root: pathlib.Path,
    stats: ProfileStats,
    rendered: Mapping[str, str],
) -> None:
    """Validate all output in memory, then replace each destination atomically."""

    stats.validate()
    if set(rendered) != {"dark", "light"}:
        raise ValueError("rendered output must contain dark and light themes")
    for theme, svg in rendered.items():
        try:
            root_element = ET.fromstring(svg)
        except ET.ParseError as exc:
            raise ValueError(f"{theme} SVG is not valid XML") from exc
        if root_element.tag.rsplit("}", 1)[-1] != "svg":
            raise ValueError(f"{theme} output root is not SVG")

    payload = json.dumps(stats.to_public_dict(), indent=2, sort_keys=True) + "\n"
    destinations = {
        root / "assets/profile-dark.svg": rendered["dark"],
        root / "assets/profile-light.svg": rendered["light"],
        root / "generated/profile-stats.json": payload,
    }

    temporary_files: list[tuple[pathlib.Path, pathlib.Path]] = []
    try:
        for destination, content in destinations.items():
            destination.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary_name = tempfile.mkstemp(
                dir=destination.parent,
                prefix=f".{destination.name}.",
                suffix=".tmp",
                text=True,
            )
            temporary = pathlib.Path(temporary_name)
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            temporary_files.append((temporary, destination))

        for temporary, destination in temporary_files:
            os.replace(temporary, destination)
    finally:
        for temporary, _ in temporary_files:
            temporary.unlink(missing_ok=True)


def main() -> int:
    config = Config.from_env()
    stats = run_generation(config)
    inventory = stats.inventory
    print(
        "profile generation complete: "
        f"repositories={inventory.total} "
        f"owned={inventory.owned} "
        f"organization_member={inventory.organization_member} "
        f"collaborator={inventory.collaborator} "
        f"coverage={stats.coverage}"
    )
    return 0
