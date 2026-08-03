import datetime as dt
import unittest

from profile_generator.collector import CollectionError, collect_profile_stats, year_windows


class FakeClient:
    def __init__(self, user, repositories, activities=None, contribution_result=(10, 0)):
        self.user = user
        self.repositories = repositories
        self.activities = activities or {}
        self.contribution_result = contribution_result
        self.contribution_calls = []
        self.activity_calls = []

    def get_authenticated_user(self):
        return dict(self.user)

    def list_repositories(self, affiliation):
        return list(self.repositories.get(affiliation, []))

    def contribution_counts(self, from_iso, to_iso):
        self.contribution_calls.append((from_iso, to_iso))
        return self.contribution_result

    def repository_activity(self, full_name, login):
        self.activity_calls.append((full_name, login))
        value = self.activities.get(full_name, (0, 0, 0))
        if isinstance(value, Exception):
            raise value
        return value


def repo(
    repo_id,
    owner,
    *,
    name=None,
    owner_type="User",
    visibility="public",
    private=False,
    archived=False,
    fork=False,
    disabled=False,
    stars=0,
):
    repo_name = name or f"repo-{repo_id}"
    return {
        "id": repo_id,
        "name": repo_name,
        "full_name": f"{owner}/{repo_name}",
        "owner": {"login": owner, "type": owner_type},
        "visibility": visibility,
        "private": private,
        "archived": archived,
        "fork": fork,
        "disabled": disabled,
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
            stars=99,
        )
        external_repo = repo(3, "external-user", visibility="internal", fork=True)
        return FakeClient(
            user={
                "login": "itsmfknlucy",
                "created_at": "2024-02-29T10:00:00Z",
                "followers": 42,
            },
            repositories={
                "owner": [repo(1, "itsmfknlucy", stars=5)],
                "organization_member": [organization_repo],
                "collaborator": [organization_repo, external_repo],
            },
            activities={
                "itsmfknlucy/repo-1": (10, 100, 20),
                "Org-One/repo-2": (20, 200, 30),
                "external-user/repo-3": (3, 50, 10),
            },
            contribution_result=(7, 5),
        )

    def test_collect_deduplicates_and_classifies_inventory_and_activity(self):
        client = self.make_client()
        stats = collect_profile_stats(
            [client],
            expected_login="itsmfknlucy",
            required_owners={"itsmfknlucy", "Org-One"},
            now=dt.datetime(2026, 3, 1, 12, 0, tzinfo=dt.timezone.utc),
        )

        inventory = stats.inventory
        self.assertEqual(inventory.total, 3)
        self.assertEqual((inventory.owned, inventory.organization_member, inventory.collaborator), (1, 1, 1))
        self.assertEqual((inventory.public, inventory.private, inventory.internal), (1, 1, 1))
        self.assertEqual((inventory.archived, inventory.forks, inventory.disabled), (1, 1, 0))
        self.assertEqual(inventory.organizations, 1)
        self.assertEqual(inventory.stars_owned, 5)
        self.assertEqual((stats.public_commits, stats.private_commits), (10, 20))
        self.assertEqual((stats.lines_added, stats.lines_deleted), (300, 50))
        self.assertEqual((stats.public_contributions, stats.restricted_contributions), (21, 15))
        self.assertEqual(stats.followers, 42)
        self.assertEqual(len(client.activity_calls), 2)
        self.assertEqual(len(client.contribution_calls), 3)

    def test_missing_required_owner_fails_before_activity_requests(self):
        client = self.make_client()
        with self.assertRaisesRegex(CollectionError, "required resource owner") as raised:
            collect_profile_stats(
                [client],
                expected_login="itsmfknlucy",
                required_owners={"itsmfknlucy", "Private-Missing-Org"},
                now=dt.datetime(2026, 3, 1, tzinfo=dt.timezone.utc),
            )
        self.assertNotIn("private-missing-org", str(raised.exception).casefold())
        self.assertEqual(client.activity_calls, [])
        self.assertEqual(client.contribution_calls, [])

    def test_repository_floor_rejects_partial_inventory_before_activity_requests(self):
        client = self.make_client()
        with self.assertRaisesRegex(CollectionError, "minimum required is 4"):
            collect_profile_stats(
                [client],
                expected_login="itsmfknlucy",
                required_owners={"itsmfknlucy", "Org-One"},
                minimum_repositories=4,
                now=dt.datetime(2026, 3, 1, tzinfo=dt.timezone.utc),
            )
        self.assertEqual(client.activity_calls, [])
        self.assertEqual(client.contribution_calls, [])

    def test_multiple_token_inventories_are_merged_without_double_counting(self):
        personal_repo = repo(1, "itsmfknlucy")
        org_repo = repo(2, "Org-Two", owner_type="Organization", visibility="private", private=True)
        user = {"login": "itsmfknlucy", "created_at": "2025-01-01T00:00:00Z", "followers": 42}
        personal = FakeClient(
            user=user,
            repositories={"owner": [personal_repo], "organization_member": [], "collaborator": []},
            activities={"itsmfknlucy/repo-1": (11, 100, 20)},
            contribution_result=(8, 2),
        )
        organization = FakeClient(
            user=user,
            repositories={"owner": [], "organization_member": [org_repo], "collaborator": []},
            activities={"Org-Two/repo-2": (9, 80, 10)},
            contribution_result=(999, 999),
        )

        stats = collect_profile_stats(
            [personal, organization],
            expected_login="itsmfknlucy",
            required_owners={"itsmfknlucy", "Org-Two"},
            now=dt.datetime(2025, 6, 1, tzinfo=dt.timezone.utc),
        )

        self.assertEqual((stats.public_commits, stats.private_commits), (11, 9))
        self.assertEqual((stats.lines_added, stats.lines_deleted), (180, 30))
        self.assertEqual((stats.public_contributions, stats.restricted_contributions), (8, 2))
        self.assertEqual(personal.activity_calls, [("itsmfknlucy/repo-1", "itsmfknlucy")])
        self.assertEqual(organization.activity_calls, [("Org-Two/repo-2", "itsmfknlucy")])
        self.assertEqual(len(personal.contribution_calls), 1)
        self.assertEqual(organization.contribution_calls, [])

    def test_activity_collection_tries_another_token_that_listed_the_repo(self):
        shared = repo(1, "Org-One", owner_type="Organization", visibility="private", private=True)
        user = {"login": "itsmfknlucy", "created_at": "2025-01-01T00:00:00Z", "followers": 1}
        first = FakeClient(
            user=user,
            repositories={"owner": [], "organization_member": [shared], "collaborator": []},
            activities={shared["full_name"]: RuntimeError("denied")},
        )
        second = FakeClient(
            user=user,
            repositories={"owner": [], "organization_member": [shared], "collaborator": []},
            activities={shared["full_name"]: (4, 20, 5)},
        )

        stats = collect_profile_stats(
            [first, second],
            expected_login="itsmfknlucy",
            required_owners={"Org-One"},
            now=dt.datetime(2025, 6, 1, tzinfo=dt.timezone.utc),
        )

        self.assertEqual(stats.private_commits, 4)
        self.assertEqual(len(first.activity_calls), 1)
        self.assertEqual(len(second.activity_calls), 1)

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
