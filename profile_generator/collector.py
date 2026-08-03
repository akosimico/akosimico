"""Aggregate repository inventory, activity, and account contribution statistics."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Any, Iterable, Protocol

from .models import InventoryStats, ProfileStats


class CollectionError(RuntimeError):
    """Raised when account coverage cannot be verified as complete."""


class ProfileApi(Protocol):
    def get_authenticated_user(self) -> dict[str, Any]: ...

    def list_repositories(self, affiliation: str) -> list[dict[str, Any]]: ...

    def contribution_counts(self, from_iso: str, to_iso: str) -> tuple[int, int]: ...

    def repository_activity(self, full_name: str, login: str) -> tuple[int, int, int]: ...


@dataclass(slots=True)
class _RepositoryAggregate:
    payload: dict[str, Any]
    affiliations: set[str]
    client_indexes: set[int]


def collect_profile_stats(
    clients: Iterable[ProfileApi],
    *,
    expected_login: str,
    required_owners: Iterable[str],
    minimum_repositories: int = 0,
    now: dt.datetime | None = None,
) -> ProfileStats:
    """Collect complete aggregate statistics or fail before publishing output."""

    current_time = _normalize_datetime(now or dt.datetime.now(dt.timezone.utc))
    client_list = tuple(clients)
    if not client_list:
        raise CollectionError("at least one authenticated token source is required")

    expected = expected_login.strip()
    if not expected:
        raise CollectionError("expected login must not be empty")

    authenticated_login = ""
    created_at = ""
    followers = 0
    merged: dict[int, _RepositoryAggregate] = {}

    for index, client in enumerate(client_list):
        user = client.get_authenticated_user()
        token_login = _required_text(user, "login", "authenticated user")
        if token_login.casefold() != expected.casefold():
            raise CollectionError("authenticated login does not match PROFILE_LOGIN")
        token_created_at = _required_text(user, "created_at", "authenticated user")
        token_followers = _non_negative_int(user.get("followers"), "followers")
        if index == 0:
            authenticated_login = token_login
            created_at = token_created_at
            followers = token_followers
        elif _format_iso(_parse_iso(token_created_at)) != _format_iso(_parse_iso(created_at)):
            raise CollectionError("token sources returned inconsistent account creation metadata")

        for affiliation in ("owner", "organization_member", "collaborator"):
            repositories = client.list_repositories(affiliation)
            for payload in repositories:
                _validate_repository_payload(payload)
                repo_id = _positive_int(payload.get("id"), "repository id")
                existing = merged.get(repo_id)
                if existing is None:
                    merged[repo_id] = _RepositoryAggregate(
                        payload=dict(payload),
                        affiliations={affiliation},
                        client_indexes={index},
                    )
                    continue
                if _repository_identity(existing.payload) != _repository_identity(payload):
                    raise CollectionError("repository identity conflict detected during deduplication")
                existing.affiliations.add(affiliation)
                existing.client_indexes.add(index)

    inventory, observed_owners = _build_inventory(merged.values())
    required = {owner.strip().casefold() for owner in required_owners if owner and owner.strip()}
    missing_count = len(required - observed_owners)
    if missing_count:
        owner_label = "owner" if missing_count == 1 else "owners"
        verb = "was" if missing_count == 1 else "were"
        raise CollectionError(f"{missing_count} required resource {owner_label} {verb} not represented")

    repository_floor = _non_negative_int(minimum_repositories, "minimum repository count")
    if inventory.total < repository_floor:
        raise CollectionError(
            f"repository inventory contains {inventory.total} repositories; "
            f"minimum required is {repository_floor}"
        )

    public_commits = 0
    private_commits = 0
    lines_added = 0
    lines_deleted = 0

    for repository in merged.values():
        primary_affiliation = _primary_affiliation(repository.affiliations)
        if primary_affiliation == "collaborator":
            continue

        activity: tuple[int, int, int] | None = None
        for client_index in sorted(repository.client_indexes):
            try:
                result = client_list[client_index].repository_activity(
                    _required_text(repository.payload, "full_name", "repository"),
                    authenticated_login,
                )
                activity = (
                    _non_negative_int(result[0], "repository commit count"),
                    _non_negative_int(result[1], "repository additions"),
                    _non_negative_int(result[2], "repository deletions"),
                )
                break
            except (CollectionError, RuntimeError, TypeError, IndexError, ValueError):
                continue
        if activity is None:
            raise CollectionError(
                "repository activity could not be collected from available credentials"
            )

        commits, additions, deletions = activity
        if _repository_visibility(repository.payload) == "public":
            public_commits += commits
        else:
            private_commits += commits
        lines_added += additions
        lines_deleted += deletions

    public_contributions = 0
    restricted_contributions = 0
    primary_client = client_list[0]
    for from_iso, to_iso in year_windows(created_at, current_time):
        visible, restricted = primary_client.contribution_counts(from_iso, to_iso)
        public_contributions += _non_negative_int(visible, "public contributions")
        restricted_contributions += _non_negative_int(
            restricted, "restricted contributions"
        )

    stats = ProfileStats(
        schema_version=2,
        login=authenticated_login,
        generated_at=_format_iso(current_time),
        account_created_at=_format_iso(_parse_iso(created_at)),
        public_commits=public_commits,
        private_commits=private_commits,
        public_contributions=public_contributions,
        restricted_contributions=restricted_contributions,
        lines_added=lines_added,
        lines_deleted=lines_deleted,
        followers=followers,
        coverage="COMPLETE",
        inventory=inventory,
    )
    stats.validate()
    return stats


def year_windows(created_at: str, now: dt.datetime) -> list[tuple[str, str]]:
    """Split an account lifetime into GraphQL-safe calendar-year windows."""

    start = _parse_iso(created_at)
    end = _normalize_datetime(now)
    if start > end:
        raise CollectionError("account creation time is later than generation time")

    windows: list[tuple[str, str]] = []
    cursor = start
    while cursor <= end:
        year_end = dt.datetime(cursor.year, 12, 31, 23, 59, 59, tzinfo=dt.timezone.utc)
        window_end = min(year_end, end)
        windows.append((_format_iso(cursor), _format_iso(window_end)))
        cursor = dt.datetime(cursor.year + 1, 1, 1, tzinfo=dt.timezone.utc)
    return windows


def _build_inventory(
    repositories: Iterable[_RepositoryAggregate],
) -> tuple[InventoryStats, set[str]]:
    total = owned = organization_member = collaborator = 0
    public = private = internal = 0
    archived = forks = disabled = 0
    stars_owned = 0
    organization_owners: set[str] = set()
    observed_owners: set[str] = set()

    for repository in repositories:
        payload = repository.payload
        total += 1
        primary = _primary_affiliation(repository.affiliations)
        if primary == "owner":
            owned += 1
        elif primary == "organization_member":
            organization_member += 1
        else:
            collaborator += 1

        visibility = _repository_visibility(payload)
        if visibility == "public":
            public += 1
        elif visibility == "private":
            private += 1
        else:
            internal += 1

        archived += int(_required_bool(payload, "archived"))
        forks += int(_required_bool(payload, "fork"))
        disabled += int(_required_bool(payload, "disabled"))
        if primary == "owner":
            stars_owned += _non_negative_int(payload.get("stargazers_count"), "stargazer count")

        owner = payload["owner"]
        owner_login = _required_text(owner, "login", "repository owner")
        owner_key = owner_login.casefold()
        observed_owners.add(owner_key)
        if _required_text(owner, "type", "repository owner").casefold() == "organization":
            organization_owners.add(owner_key)

    inventory = InventoryStats(
        total=total,
        owned=owned,
        organization_member=organization_member,
        collaborator=collaborator,
        public=public,
        private=private,
        internal=internal,
        archived=archived,
        forks=forks,
        disabled=disabled,
        organizations=len(organization_owners),
        stars_owned=stars_owned,
    )
    inventory.validate()
    return inventory, observed_owners


def _primary_affiliation(affiliations: set[str]) -> str:
    if "owner" in affiliations:
        return "owner"
    if "organization_member" in affiliations:
        return "organization_member"
    if "collaborator" in affiliations:
        return "collaborator"
    raise CollectionError("repository has no recognized affiliation")


def _validate_repository_payload(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise CollectionError("repository inventory contained a non-object entry")
    _positive_int(payload.get("id"), "repository id")
    _required_text(payload, "name", "repository")
    _required_text(payload, "full_name", "repository")
    owner = payload.get("owner")
    if not isinstance(owner, dict):
        raise CollectionError("repository inventory entry is missing owner metadata")
    _required_text(owner, "login", "repository owner")
    _required_text(owner, "type", "repository owner")
    _repository_visibility(payload)
    _required_bool(payload, "archived")
    _required_bool(payload, "fork")
    _required_bool(payload, "disabled")
    _non_negative_int(payload.get("stargazers_count"), "stargazer count")


def _repository_identity(payload: dict[str, Any]) -> tuple[str, str]:
    return (
        _required_text(payload, "full_name", "repository").casefold(),
        _owner_login(payload).casefold(),
    )


def _repository_visibility(payload: dict[str, Any]) -> str:
    visibility = payload.get("visibility")
    if isinstance(visibility, str) and visibility.casefold() in {"public", "private", "internal"}:
        return visibility.casefold()
    private = payload.get("private")
    if isinstance(private, bool):
        return "private" if private else "public"
    raise CollectionError("repository inventory entry has invalid visibility metadata")


def _owner_login(payload: dict[str, Any]) -> str:
    owner = payload.get("owner")
    if not isinstance(owner, dict):
        raise CollectionError("repository inventory entry is missing owner metadata")
    return _required_text(owner, "login", "repository owner")


def _required_text(payload: dict[str, Any], key: str, context: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CollectionError(f"{context} is missing required {key}")
    return value.strip()


def _required_bool(payload: dict[str, Any], key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise CollectionError(f"repository inventory entry has invalid {key} metadata")
    return value


def _positive_int(value: Any, label: str) -> int:
    parsed = _non_negative_int(value, label)
    if parsed == 0:
        raise CollectionError(f"{label} must be positive")
    return parsed


def _non_negative_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise CollectionError(f"{label} must be a non-negative integer")
    return value


def _parse_iso(value: str) -> dt.datetime:
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CollectionError("invalid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise CollectionError("timestamp must include a timezone")
    return _normalize_datetime(parsed)


def _normalize_datetime(value: dt.datetime) -> dt.datetime:
    if value.tzinfo is None:
        raise CollectionError("generation time must include a timezone")
    return value.astimezone(dt.timezone.utc).replace(microsecond=0)


def _format_iso(value: dt.datetime) -> str:
    return _normalize_datetime(value).isoformat().replace("+00:00", "Z")
