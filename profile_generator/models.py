"""Immutable aggregate models used by the profile generator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class InventoryStats:
    """Aggregate repository inventory with no repository-level identifiers."""

    total: int
    owned: int
    organization_member: int
    collaborator: int
    public: int
    private: int
    internal: int
    archived: int
    forks: int
    disabled: int
    organizations: int
    resource_owners: int
    stars_owned: int
    size_kib: int

    def validate(self) -> None:
        values = {
            "total": self.total,
            "owned": self.owned,
            "organization_member": self.organization_member,
            "collaborator": self.collaborator,
            "public": self.public,
            "private": self.private,
            "internal": self.internal,
            "archived": self.archived,
            "forks": self.forks,
            "disabled": self.disabled,
            "organizations": self.organizations,
            "resource_owners": self.resource_owners,
            "stars_owned": self.stars_owned,
            "size_kib": self.size_kib,
        }
        if any(not isinstance(value, int) or isinstance(value, bool) for value in values.values()):
            raise ValueError("inventory values must be integers")
        if any(value < 0 for value in values.values()):
            raise ValueError("inventory values must be non-negative")
        if self.owned + self.organization_member + self.collaborator != self.total:
            raise ValueError("affiliation totals must equal the repository total")
        if self.public + self.private + self.internal != self.total:
            raise ValueError("visibility totals must equal the repository total")
        for label, count in (
            ("archived", self.archived),
            ("forks", self.forks),
            ("disabled", self.disabled),
        ):
            if count > self.total:
                raise ValueError(f"{label} count cannot exceed repository total")
        if self.organizations > self.resource_owners:
            raise ValueError("organization count cannot exceed resource owner count")
        if self.total == 0 and (self.resource_owners or self.organizations or self.stars_owned or self.size_kib):
            raise ValueError("empty inventory cannot contain repository-derived aggregates")


@dataclass(frozen=True, slots=True)
class ProfileStats:
    """Public aggregate profile state rendered into JSON and SVG."""

    schema_version: int
    login: str
    generated_at: str
    account_created_at: str
    commit_contributions: int
    restricted_contributions: int
    followers: int
    coverage: str
    inventory: InventoryStats

    def validate(self) -> None:
        self.inventory.validate()
        if self.schema_version < 1:
            raise ValueError("schema_version must be at least 1")
        if not self.login.strip():
            raise ValueError("login must not be empty")
        if not self.generated_at.strip() or not self.account_created_at.strip():
            raise ValueError("timestamps must not be empty")
        if not self.coverage.strip():
            raise ValueError("coverage must not be empty")
        for label, value in (
            ("commit_contributions", self.commit_contributions),
            ("restricted_contributions", self.restricted_contributions),
            ("followers", self.followers),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{label} must be a non-negative integer")

    def to_public_dict(self) -> dict[str, Any]:
        """Return a stable aggregate-only document suitable for a public repository."""

        self.validate()
        inventory = self.inventory
        return {
            "account_created_at": self.account_created_at,
            "coverage": self.coverage,
            "generated_at": self.generated_at,
            "login": self.login,
            "owners": {
                "organizations": inventory.organizations,
                "resource_owners": inventory.resource_owners,
            },
            "repositories": {
                "collaborator": inventory.collaborator,
                "organization_member": inventory.organization_member,
                "owned": inventory.owned,
                "total": inventory.total,
            },
            "schema_version": self.schema_version,
            "signals": {
                "commit_contributions": self.commit_contributions,
                "followers": self.followers,
                "repository_size_kib": inventory.size_kib,
                "restricted_contributions": self.restricted_contributions,
                "stars_owned": inventory.stars_owned,
            },
            "state": {
                "archived": inventory.archived,
                "disabled": inventory.disabled,
                "forks": inventory.forks,
            },
            "visibility": {
                "internal": inventory.internal,
                "private": inventory.private,
                "public": inventory.public,
            },
        }
