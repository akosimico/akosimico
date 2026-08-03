from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "profile-stats.yml"


class RepositoryContractTests(unittest.TestCase):
    def test_readme_uses_light_and_dark_generated_svg_assets(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("assets/profile-dark.svg", readme)
        self.assertIn("assets/profile-light.svg", readme)
        self.assertIn("prefers-color-scheme: dark", readme)

    def test_readme_keeps_the_profile_theme_without_generator_notices(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        for expected in (
            "Lucifer Rodstark, Ph.D.",
            "## Systems",
            "## Engineering Surface",
            "## Current Build Axis",
        ):
            self.assertIn(expected, readme)
        for forbidden in (
            "## Account Telemetry",
            "generator documentation",
            "privacy-preserving",
            "Private repository names",
            "failure guarantees",
            "## Operating Principles",
        ):
            self.assertNotIn(forbidden, readme)

    def test_repository_has_no_internal_setup_or_process_documents(self) -> None:
        self.assertFalse((ROOT / "SECURITY.md").exists())
        self.assertFalse((ROOT / "COLLABORATION.md").exists())
        self.assertFalse((ROOT / "docs" / "profile-generator.md").exists())
        self.assertFalse((ROOT / "docs" / "superpowers").exists())
        self.assertFalse((ROOT / "assets" / "profile-banner.png").exists())
        self.assertFalse((ROOT / "assets" / "lucy.png").exists())

    def test_workflow_uses_current_official_actions_and_environment_only_secrets(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("actions/checkout@v6", workflow)
        self.assertIn("actions/setup-python@v6", workflow)
        self.assertIn('python-version: "3.13"', workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("schedule:", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("PROFILE_STATS_TOKENS: |", workflow)
        generation_step = workflow.index("- name: Generate authenticated profile statistics")
        token_environment = workflow.index("PROFILE_STATS_TOKENS: |")
        self.assertGreater(token_environment, generation_step)
        self.assertNotIn("PROFILE_STATS_TOKENS: |", workflow[:generation_step])
        self.assertIn("secrets.PROFILE_STATS_TOKENS", workflow)
        self.assertIn("secrets.PROFILE_STATS_TOKEN_RODSTARK", workflow)
        self.assertIn("secrets.PROFILE_STATS_TOKEN_NEXGEN_LAVA", workflow)
        self.assertIn("secrets.PROFILE_STATS_TOKEN_FROSTBYTE", workflow)
        self.assertIn("secrets.PROFILE_REQUIRED_OWNERS", workflow)
        self.assertIn("vars.PROFILE_REQUIRED_OWNERS", workflow)
        self.assertIn("PROFILE_MIN_REPOSITORIES:", workflow)
        self.assertIn("vars.PROFILE_MIN_REPOSITORIES", workflow)
        self.assertIn("'18'", workflow)
        self.assertNotIn("github_pat_", workflow)
        self.assertNotIn("pull_request_target", workflow)
        self.assertNotIn("docs/profile-generator.md", workflow)
        self.assertNotIn("SECURITY.md", workflow)

    def test_workflow_preserves_current_assets_until_credentials_exist(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn(
            "PROFILE_STATS_CONFIGURED: ${{ secrets.PROFILE_STATS_TOKEN != '' || secrets.PROFILE_STATS_TOKENS != '' }}",
            workflow,
        )
        self.assertIn("- name: Preserve current assets without profile credentials", workflow)
        self.assertIn("if: env.PROFILE_STATS_CONFIGURED != 'true'", workflow)

        authenticated_steps = (
            "Generate authenticated profile statistics",
            "Validate generated assets and repository hygiene",
            "Commit changed generated outputs",
        )
        for step_name in authenticated_steps:
            step_position = workflow.index(f"- name: {step_name}")
            following = workflow[step_position : step_position + 420]
            self.assertIn("if: env.PROFILE_STATS_CONFIGURED == 'true'", following)

        tests_position = workflow.index("python -m unittest discover -s tests -v")
        guard_position = workflow.index("PROFILE_STATS_CONFIGURED:")
        generation_position = workflow.index("python -m profile_generator")
        self.assertLess(guard_position, tests_position)
        self.assertLess(tests_position, generation_position)

    def test_workflow_runs_tests_before_generation_and_limits_committed_outputs(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        tests_position = workflow.index("python -m unittest discover -s tests -v")
        generation_position = workflow.index("python -m profile_generator")

        self.assertLess(tests_position, generation_position)
        self.assertIn("git diff --check", workflow)
        self.assertIn("xml.etree.ElementTree", workflow)
        self.assertIn("generated/profile-stats.json", workflow)
        self.assertIn('payload.get("repositories", {}).get("total", 0)', workflow)
        self.assertNotIn('payload.get("inventory", {})', workflow)
        self.assertIn(
            "git add assets/profile-dark.svg assets/profile-light.svg generated/profile-stats.json",
            workflow,
        )


if __name__ == "__main__":
    unittest.main()
