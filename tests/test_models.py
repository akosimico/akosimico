import json
import unittest

from profile_generator.models import InventoryStats, ProfileStats


class InventoryStatsTests(unittest.TestCase):
    def make_inventory(self, **overrides):
        values = {
            "total": 3,
            "owned": 1,
            "organization_member": 1,
            "collaborator": 1,
            "public": 1,
            "private": 1,
            "internal": 1,
            "archived": 1,
            "forks": 1,
            "disabled": 0,
            "organizations": 1,
            "stars_owned": 7,
        }
        values.update(overrides)
        return InventoryStats(**values)

    def test_validate_accepts_consistent_aggregate(self):
        inventory = self.make_inventory()
        inventory.validate()
        self.assertEqual(inventory.state_total, 2)

    def test_validate_rejects_affiliation_total_mismatch(self):
        with self.assertRaisesRegex(ValueError, "affiliation"):
            self.make_inventory(collaborator=0).validate()

    def test_validate_rejects_visibility_total_mismatch(self):
        with self.assertRaisesRegex(ValueError, "visibility"):
            self.make_inventory(internal=0).validate()

    def test_validate_rejects_negative_values(self):
        with self.assertRaisesRegex(ValueError, "non-negative"):
            self.make_inventory(stars_owned=-1).validate()


class ProfileStatsTests(unittest.TestCase):
    def make_stats(self, **overrides):
        values = {
            "schema_version": 2,
            "login": "itsmfknlucy",
            "generated_at": "2026-08-03T04:17:00Z",
            "account_created_at": "2018-03-01T00:00:00Z",
            "public_commits": 1_234,
            "private_commits": 28_047,
            "public_contributions": 1_400,
            "restricted_contributions": 28_100,
            "lines_added": 99_000,
            "lines_deleted": 8_000,
            "followers": 42,
            "coverage": "COMPLETE",
            "inventory": InventoryStats(
                total=3,
                owned=1,
                organization_member=1,
                collaborator=1,
                public=1,
                private=1,
                internal=1,
                archived=1,
                forks=1,
                disabled=0,
                organizations=1,
                stars_owned=7,
            ),
        }
        values.update(overrides)
        return ProfileStats(**values)

    def test_totals_are_derived_from_public_components(self):
        stats = self.make_stats()
        self.assertEqual(stats.total_commits, 29_281)
        self.assertEqual(stats.total_contributions, 29_500)
        self.assertEqual(stats.total_lines, 91_000)

    def test_public_dict_contains_aggregate_data_only(self):
        stats = self.make_stats()
        payload = stats.to_public_dict()
        serialized = json.dumps(payload, sort_keys=True)

        self.assertEqual(payload["repositories"]["total"], 3)
        self.assertEqual(payload["owners"], {"organizations": 1})
        self.assertEqual(payload["activity"]["commits"], {
            "private": 28_047,
            "public": 1_234,
            "total": 29_281,
        })
        self.assertEqual(payload["activity"]["lines"]["total"], 91_000)
        self.assertNotIn("resource_owners", serialized)
        self.assertNotIn("repository_size", serialized)
        for forbidden in ("repository_name", "full_name", "repo_id", "owner_login", "url"):
            self.assertNotIn(forbidden, serialized)

    def test_validate_rejects_invalid_activity_values(self):
        with self.assertRaisesRegex(ValueError, "public_commits"):
            self.make_stats(public_commits=-1).validate()


if __name__ == "__main__":
    unittest.main()
