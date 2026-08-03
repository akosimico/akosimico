from __future__ import annotations

import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "profile-stats.yml"


class RepositoryContractTests(unittest.TestCase):
    def test_readme_uses_generated_identity_card_and_footer_banner(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("assets/profile-dark.svg", readme)
        self.assertIn("assets/profile-light.svg", readme)
        self.assertIn("prefers-color-scheme: dark", readme)
        self.assertIn("assets/profile-banner.png", readme)
        self.assertIn('alt="Identification Card"', readme)

    def test_readme_contains_requested_sections_and_removes_old_sections(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for expected in (
            "Lucifer Rodstark, Ph.D.",
            "Cloud & AI Solutions Engineer",
            "## Current Direction",
            "## The Stack",
            "## What I Build",
            "## Operating Philosophy",
            "## Organizations",
            "Architecture before acceleration.",
        ):
            self.assertIn(expected, readme)
        for forbidden in (
            "## Engineering Surface",
            "## Controlled Execution",
            "## Current Build Axis",
            "Agentics</a>",
        ):
            self.assertNotIn(forbidden, readme)

    def test_repository_uses_embedded_portrait_and_contains_banner_asset(self):
        self.assertFalse((ROOT / "assets" / ("ascii-" + "portrait.txt")).exists())
        self.assertTrue((ROOT / "profile_generator" / "portrait.py").is_file())
        banner = ROOT / "assets" / "profile-banner.png"
        self.assertTrue(banner.is_file())
        raw = banner.read_bytes()
        self.assertEqual(raw[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", raw[16:24])
        self.assertEqual((width, height), (917, 512))

    def test_repository_has_no_temporary_update_payload_or_workflow(self):
        self.assertFalse((ROOT / ".profile-update").exists())
        self.assertFalse((ROOT / ".profile-finalize").exists())
        self.assertFalse((ROOT / ".github" / "workflows" / "apply-profile-v2.yml").exists())
        self.assertFalse((ROOT / ".github" / "workflows" / "apply-profile-final.yml").exists())
        self.assertFalse((ROOT / "docs" / "superpowers").exists())

    def test_workflow_uses_current_actions_and_embedded_portrait_source(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("actions/checkout@v6", workflow)
        self.assertIn("actions/setup-python@v6", workflow)
        self.assertIn('python-version: "3.13"', workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("schedule:", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn('"profile_generator/**"', workflow)
        self.assertIn('"assets/profile-banner.png"', workflow)
        self.assertNotIn("ascii-" + "portrait.txt", workflow)
        self.assertIn("PROFILE_STATS_TOKENS: |", workflow)
        self.assertIn("secrets.PROFILE_STATS_TOKEN_EXTERNAL_1", workflow)
        self.assertIn("secrets.PROFILE_STATS_TOKEN_EXTERNAL_2", workflow)
        self.assertIn("python -m unittest discover -s tests -v", workflow)
        self.assertIn("python -m profile_generator", workflow)
        self.assertIn("git diff --check", workflow)
        self.assertIn("generated/profile-stats.json", workflow)
        self.assertIn(
            "git add assets/profile-dark.svg assets/profile-light.svg generated/profile-stats.json",
            workflow,
        )
        self.assertNotIn("pull_request_target", workflow)


if __name__ == "__main__":
    unittest.main()
