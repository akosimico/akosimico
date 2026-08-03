import datetime as dt
import unittest

from profile_generator.collector import CollectionError, collect_profile_stats, year_windows


class FakeClient:
    def __init__(self, user, repositories, contribution_result=(10, 0)):
        self.user = user
        self.repositories = repositories
        self.contribution_result = contribution_result
        self.contribution_calls = []

    def get_authenticated_user(self):
        return dict(self.user)

    def list_repositories(self, affiliation):
        return list(self.repositories.get(affiliation, []))

    def commit_contributions(self, from_iso, to_iso):
        self.contribution_calls.append((from_iso, to_iso))
        return self.contribution_result


def repo(
    repo_id,
    owner,
    *,
    owner_type="User",
    visibility="public",
    private=False,
    archived=False,
    fork=False,
    disabled=False,
    size=0,
    stars=0,
):
    return {
        "id": repo_id,
        "owner": {"login": owner, "type": owner_type},
        "visibility": visibility,
        "private": private,
        "archived": archived,
        "fork": fork,
        "disabled": disabled,
        "size": size,
        "stargazers_count": stars,
    }


class CollectorTests(unittest.TestCase):
    def make_client(self):
        organization_repo = repo(
            2,
            "Org-One",
            owner_type="Organization",
            visibility="private",
            private=True,
            archived=True,
            size=200,
            stars=99,
        )
        return FakeClient(
            user={
                "login": "itsmfknlucy",
                "created_at": "2024-02-29T10:00:00Z",
                "followers": 42,
            },
            repositories={
                "owner": [repo(1, "itsmfknlucy", size=100, stars=5)],
                "organization_member": [organization_repo],
                "collaborator": [
                    organization_repo,
                    repo(
                        3,
                        "external-user",
                        visibility="internal",
                        fork=True,
                        size=300,
                    ),
                ],
            },
        )

    def test_collect_deduplicates_and_classifies_every_affiliation(self):
        client = self.make_client()
        now = dt.datetime(2026, 3, 1, 12, 0, tzinfo=dt.timezone.utc)

        stats = collect_profile_stats(
            [client],
            expected_login="itsmfknlucy",
            required_owners={"itsmfknlucy", "Org-One"},
            now=now,
        )

        inventory = stats.inventory
        self.assertEqual(inventory.total, 3)
        self.assertEqual((inventory.owned, inventory.organization_member, inventory.collaborator), (1, 1, 1))
        self.assertEqual((inventory.public, inventory.private, inventory.internal), (1, 1, 1))
        self.assertEqual(inventory.archived, 1)
        self.assertEqual(inventory.forks, 1)
        self.assertEqual(inventory.organizations, 1)
        self.assertEqual(inventory.resource_owners, 3)
        self.assertEqual(inventory.stars_owned, 5)
        self.assertEqual(inventory.size_kib, 600)
        self.assertEqual(stats.followers, 42)
        self.assertEqual(stats.commit_contributions, 30)
        self.assertEqual(len(client.contribution_calls), 3)

    def test_missing_required_owner_fails_instead_of_publishing_partial_totals(self):
        client = self.make_client()

        with self.assertRaisesRegex(CollectionError, "required resource owner"):
            collect_profile_stats(
                [client],
                expected_login="itsmfknlucy",
                required_owners={"itsmfknlucy", "Missing-Org"},
                now=dt.datetime(2026, 3, 1, tzinfo=dt.timezone.utc),
            )

    def test_authenticated_login_must_match_expected_login(self):
        client = self.make_client()
        client.user["login"] = "someone-else"

        with self.assertRaisesRegex(CollectionError, "authenticated login"):
            collect_profile_stats(
                [client],
                expected_login="itsmfknlucy",
                required_owners=set(),
                now=dt.datetime(2026, 3, 1, tzinfo=dt.timezone.utc),
            )

    def test_multiple_token_inventories_are_merged_without_double_counting_profile_contributions(self):
        personal = FakeClient(
            user={
                "login": "itsmfknlucy",
                "created_at": "2025-01-01T00:00:00Z",
                "followers": 42,
            },
            repositories={
                "owner": [repo(1, "itsmfknlucy", size=100, stars=2)],
                "organization_member": [],
                "collaborator": [],
            },
            contribution_result=(11, 0),
        )
        organization = FakeClient(
            user={
                "login": "itsmfknlucy",
                "created_at": "2025-01-01T00:00:00Z",
                "followers": 42,
            },
            repositories={
                "owner": [],
                "organization_member": [
                    repo(2, "Org-Two", owner_type="Organization", visibility="private", private=True)
                ],
                "collaborator": [],
            },
            contribution_result=(999, 999),
        )

        stats = collect_profile_stats(
            [personal, organization],
            expected_login="itsmfknlucy",
            required_owners={"itsmfknlucy", "Org-Two"},
            now=dt.datetime(2025, 6, 1, tzinfo=dt.timezone.utc),
        )

        self.assertEqual(stats.inventory.total, 2)
        self.assertEqual((stats.inventory.owned, stats.inventory.organization_member), (1, 1))
        self.assertEqual(stats.commit_contributions, 11)
        self.assertEqual(len(personal.contribution_calls), 1)
        self.assertEqual(organization.contribution_calls, [])

    def test_year_windows_are_contiguous_and_calendar_bounded(self):
        windows = year_windows(
            "2024-02-29T10:00:00Z",
            dt.datetime(2026, 3, 1, 12, 0, tzinfo=dt.timezone.utc),
        )

        self.assertEqual(
            windows,
            [
                ("2024-02-29T10:00:00Z", "2024-12-31T23:59:59Z"),
                ("2025-01-01T00:00:00Z", "2025-12-31T23:59:59Z"),
                ("2026-01-01T00:00:00Z", "2026-03-01T12:00:00Z"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
