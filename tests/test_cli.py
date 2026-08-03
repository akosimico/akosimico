import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from profile_generator.cli import Config, ConfigurationError, run_generation, write_outputs
from profile_generator.models import InventoryStats, ProfileStats


class CliTests(unittest.TestCase):
    def make_stats(self):
        return ProfileStats(
            schema_version=1,
            login="itsmfknlucy",
            generated_at="2026-08-03T04:17:00Z",
            account_created_at="2018-03-01T00:00:00Z",
            commit_contributions=1234,
            restricted_contributions=0,
            followers=42,
            coverage="COMPLETE",
            inventory=InventoryStats(
                total=1,
                owned=1,
                organization_member=0,
                collaborator=0,
                public=1,
                private=0,
                internal=0,
                archived=0,
                forks=0,
                disabled=0,
                organizations=0,
                resource_owners=1,
                stars_owned=1,
                size_kib=1,
            ),
        )

    def test_config_requires_encrypted_secret_value(self):
        with self.assertRaisesRegex(ConfigurationError, "PROFILE_STATS_TOKEN"):
            Config.from_env({"PROFILE_LOGIN": "itsmfknlucy"})

    def test_config_accepts_multiple_tokens_and_deduplicates_them(self):
        config = Config.from_env(
            {
                "PROFILE_LOGIN": "itsmfknlucy",
                "PROFILE_STATS_TOKENS": "token-a\n\ntoken-b\ntoken-a\n",
                "PROFILE_REQUIRED_OWNERS": "itsmfknlucy,Org-One",
            },
            root=pathlib.Path("/tmp/profile-root"),
        )

        self.assertEqual(config.tokens, ("token-a", "token-b"))
        self.assertEqual(config.required_owners, frozenset({"itsmfknlucy", "Org-One"}))

    def test_config_representation_redacts_tokens(self):
        config = Config(
            tokens=("sensitive-token-value",),
            login="itsmfknlucy",
            required_owners=frozenset(),
            root=pathlib.Path("/tmp/profile-root"),
        )

        self.assertNotIn("sensitive-token-value", repr(config))

    def test_collection_failure_preserves_existing_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / "assets").mkdir()
            (root / "generated").mkdir()
            paths = [
                root / "assets/profile-dark.svg",
                root / "assets/profile-light.svg",
                root / "generated/profile-stats.json",
            ]
            for path in paths:
                path.write_text("verified-old-content", encoding="utf-8")
            config = Config(
                tokens=("not-a-real-token",),
                login="itsmfknlucy",
                required_owners=frozenset(),
                root=root,
            )

            with mock.patch("profile_generator.cli.collect_profile_stats", side_effect=RuntimeError("collection failed")):
                with self.assertRaisesRegex(RuntimeError, "collection failed"):
                    run_generation(config, client_factory=lambda token: object())

            for path in paths:
                self.assertEqual(path.read_text(encoding="utf-8"), "verified-old-content")

    def test_write_outputs_is_atomic_and_json_is_deterministic(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            stats = self.make_stats()
            rendered = {
                "dark": '<svg xmlns="http://www.w3.org/2000/svg"><text>dark</text></svg>',
                "light": '<svg xmlns="http://www.w3.org/2000/svg"><text>light</text></svg>',
            }

            write_outputs(root, stats, rendered)

            dark = (root / "assets/profile-dark.svg").read_text(encoding="utf-8")
            light = (root / "assets/profile-light.svg").read_text(encoding="utf-8")
            payload_text = (root / "generated/profile-stats.json").read_text(encoding="utf-8")
            payload = json.loads(payload_text)

            self.assertEqual(dark, rendered["dark"])
            self.assertEqual(light, rendered["light"])
            self.assertTrue(payload_text.endswith("\n"))
            self.assertEqual(payload, stats.to_public_dict())
            self.assertEqual(payload_text, json.dumps(payload, indent=2, sort_keys=True) + "\n")
            self.assertEqual(list(root.rglob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
