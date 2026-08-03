import json
import pathlib
import tempfile
import unittest
from unittest import mock

from profile_generator.cli import Config, ConfigurationError, run_generation, write_outputs
from profile_generator.models import InventoryStats, ProfileStats


class CliTests(unittest.TestCase):
    def make_stats(self):
        return ProfileStats(
            schema_version=2,
            login="itsmfknlucy",
            generated_at="2026-08-03T04:17:00Z",
            account_created_at="2018-03-01T00:00:00Z",
            public_commits=1_234,
            private_commits=2_000,
            public_contributions=1_400,
            restricted_contributions=2_100,
            lines_added=10_000,
            lines_deleted=1_000,
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
                stars_owned=1,
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
        self.assertEqual(config.minimum_repositories, 0)

    def test_config_parses_repository_floor(self):
        config = Config.from_env(
            {
                "PROFILE_LOGIN": "itsmfknlucy",
                "PROFILE_STATS_TOKEN": "token-a",
                "PROFILE_MIN_REPOSITORIES": "18",
            },
            root=pathlib.Path("/tmp/profile-root"),
        )
        self.assertEqual(config.minimum_repositories, 18)

    def test_run_generation_passes_repository_floor_to_collector(self):
        config = Config(
            tokens=("not-a-real-token",),
            login="itsmfknlucy",
            required_owners=frozenset({"itsmfknlucy"}),
            root=pathlib.Path("/tmp/profile-root"),
            minimum_repositories=18,
        )
        stats = self.make_stats()
        with (
            mock.patch("profile_generator.cli.collect_profile_stats", return_value=stats) as collect,
            mock.patch("profile_generator.cli.render_all", return_value={"dark": "<svg/>", "light": "<svg/>"}),
            mock.patch("profile_generator.cli.write_outputs"),
        ):
            run_generation(config, client_factory=lambda token: object())
        collect.assert_called_once_with(
            [mock.ANY],
            expected_login="itsmfknlucy",
            required_owners=frozenset({"itsmfknlucy"}),
            minimum_repositories=18,
        )

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
            payload_text = (root / "generated/profile-stats.json").read_text(encoding="utf-8")
            payload = json.loads(payload_text)
            self.assertEqual(payload, stats.to_public_dict())
            self.assertEqual(payload_text, json.dumps(payload, indent=2, sort_keys=True) + "\n")
            self.assertEqual(list(root.rglob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
