"""Aggregate repository inventory and account contribution collection."""

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

    def commit_contributions(self, from_iso: str, to_iso: str) -> tuple[int, int]: ...


@dataclass(slots=True)
class _RepositoryAggregate:
    payload: dict[str, Any]
    affiliations: set[str]


def collect_profile_stats(
    clients: Iterable[ProfileApi],
    *,
    expected_login: str,
    required_owners: Iterable[str],
    minimum_repositories: int = 0,
    now: dt.datetime | None = None,
) -> ProfileStats:
    """Collect complete aggregate statistics or fail before rendering."""

    current_time = _normalize_datetime(now or dt.datetime.now(dt.timezone.utc))
    client_list = tuple(clients)
    if not client_list:
        raise CollectionError("at least one authenticated token source is required")

    primary_user: dict[str, Any] | None = None
    authenticated_login = ""
    created_at = ""
    followers = 0
    merged: dict[int, _RepositoryAggregate] = {}

    for index, client in enumerate(client_list):
        user = client.get_authenticated_user()
        token_login = _required_text(user, "login", "authenticated user")
        if token_login.casefold() != expected_login.strip().casefold():
            raise CollectionError("authenticated login does not match PROFILE_LOGIN")
        token_created_at = _required_text(user, "created_at", "authenticated user")
        token_followers = _non_negative_int(user.get("followers"), "followers")
        if index == 0:
            primary_user = user
            authenticated_login = token_login
            created_at = token_created_at
            followers = token_followers
        else:
            if _format_iso(_parse_iso(token_created_at)) != _format_iso(_parse_iso(created_at)):
                raise CollectionError("token sources returned inconsistent account creation metadata")

        for affiliation in ("owner", "organization_member", "collaborator"):
            repositories = client.list_repositories(affiliation)
            for payload in repositories:
                repo_id = _positive_int(payload.get("id"), "repository id")
                _validate_repository_payload(payload)
                existing = merged.get(repo_id)
                if existing is None:
                    merged[repo_id] = _RepositoryAggregate(payload=dict(payload), affiliations={affiliation})
                    continue
                if _owner_login(existing.payload).casefold() != _owner_login(payload).casefold():
                    raise CollectionError("repository identity conflict detected during deduplication")
                existing.affiliations.add(affiliation)

    if primary_user is None:  # pragma: no cover - guarded by client_list
        raise CollectionError("primary token source was not available")

    inventory, observed_owners = _build_inventory(merged.values())
    required = {owner.strip().casefold() for owner in required_owners if owner and owner.strip()}
    missing_count = len(required - observed_owners)
    if missing_count:
        owner_label = "owner" if missing_count == 1 else "owners"
        verb = "was" if missing_count == 1 else "were"
        raise CollectionError(
            f"{missing_count} required resource {owner_label} {verb} not represented"
        )

    repository_floor = _non_negative_int(minimum_repositories, "minimum repository count")
    if inventory.total < repository_floor:
        raise CollectionError(
            f"repository inventory contains {inventory.total} repositories; "
            f"minimum required is {repository_floor}"
        )

    commit_contributions = 0
    restricted_contributions = 0
    primary_client = client_list[0]
    for from_iso, to_iso in year_windows(created_at, current_time):
        total, restricted = primary_client.commit_contributions(from_iso, to_iso)
        commit_contributions += _non_negative_int(total, "commit contributions")
        restricted_contributions += _non_negative_int(restricted, "restricted contributions")

    stats = ProfileStats(
        schema_version=1,
        login=authenticated_login,
        generated_at=_format_iso(current_time),
        account_created_at=_format_iso(_parse_iso(created_at)),
        commit_contributions=commit_contributions,
        restricted_contributions=restricted_contributions,
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
        cursor = dt.datetime(cursor.year + 1, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc)
    return windows


def _build_inventory(
    repositories: Iterable[_RepositoryAggregate],
) -> tuple[InventoryStats, set[str]]:
    total = owned = organization_member = collaborator = 0
    public = private = internal = 0
    archived = forks = disabled = 0
    stars_owned = size_kib = 0
    organization_owners: set[str] = set()
    resource_owners: set[str] = set()

    for repository in repositories:
        payload = repository.payload
        total += 1
        if "owner" in repository.affiliations:
            primary = "owner"
            owned += 1
        elif "organization_member" in repository.affiliations:
            primary = "organization_member"
            organization_member += 1
        elif "collaborator" in repository.affiliations:
            primary = "collaborator"
            collaborator += 1
        else:
            raise CollectionError("repository has no recognized affiliation")

        visibility = _repository_visibility(payload)
        if visibility == "public":
            public += 1
        elif visibility == "private":
            private += 1
        elif visibility == "internal":
            internal += 1
        else:  # pragma: no cover - guarded by validation
            raise CollectionError("repository has unsupported visibility")

        archived += int(_required_bool(payload, "archived"))
        forks += int(_required_bool(payload, "fork"))
        disabled += int(_required_bool(payload, "disabled"))
        size_kib += _non_negative_int(payload.get("size"), "repository size")
        if primary == "owner":
            stars_owned += _non_negative_int(payload.get("stargazers_count"), "stargazer count")

        owner = payload["owner"]
        owner_login = _required_text(owner, "login", "repository owner")
        owner_key = owner_login.casefold()
        resource_owners.add(owner_key)
        owner_type = _required_text(owner, "type", "repository owner")
        if owner_type.casefold() == "organization":
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
        resource_owners=len(resource_owners),
        stars_owned=stars_owned,
        size_kib=size_kib,
    )
    inventory.validate()
    return inventory, resource_owners


def _validate_repository_payload(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise CollectionError("repository inventory contained a non-object entry")
    owner = payload.get("owner")
    if not isinstance(owner, dict):
        raise CollectionError("repository inventory entry is missing owner metadata")
    _required_text(owner, "login", "repository owner")
    _required_text(owner, "type", "repository owner")
    _repository_visibility(payload)
    _required_bool(payload, "archived")
    _required_bool(payload, "fork")
    _required_bool(payload, "disabled")
    _non_negative_int(payload.get("size"), "repository size")
    _non_negative_int(payload.get("stargazers_count"), "stargazer count")


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
