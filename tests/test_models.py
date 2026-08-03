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
            "resource_owners": 3,
            "stars_owned": 7,
            "size_kib": 2048,
        }
        values.update(overrides)
        return InventoryStats(**values)

    def test_validate_accepts_consistent_aggregate(self):
        inventory = self.make_inventory()
        inventory.validate()

    def test_validate_rejects_affiliation_total_mismatch(self):
        inventory = self.make_inventory(collaborator=0)
        with self.assertRaisesRegex(ValueError, "affiliation"):
            inventory.validate()

    def test_validate_rejects_visibility_total_mismatch(self):
        inventory = self.make_inventory(internal=0)
        with self.assertRaisesRegex(ValueError, "visibility"):
            inventory.validate()

    def test_validate_rejects_negative_values(self):
        inventory = self.make_inventory(size_kib=-1)
        with self.assertRaisesRegex(ValueError, "non-negative"):
            inventory.validate()


class ProfileStatsTests(unittest.TestCase):
    def test_public_dict_contains_aggregate_data_only(self):
        stats = ProfileStats(
            schema_version=1,
            login="itsmfknlucy",
            generated_at="2026-08-03T04:17:00Z",
            account_created_at="2018-03-01T00:00:00Z",
            commit_contributions=1234,
            restricted_contributions=0,
            followers=42,
            coverage="COMPLETE",
            inventory=InventoryStats(
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
                resource_owners=3,
                stars_owned=7,
                size_kib=2048,
            ),
        )

        payload = stats.to_public_dict()
        serialized = json.dumps(payload, sort_keys=True)

        self.assertEqual(payload["repositories"]["total"], 3)
        self.assertEqual(payload["signals"]["commit_contributions"], 1234)
        for forbidden in ("repository_name", "full_name", "repo_id", "owner_login", "url"):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
