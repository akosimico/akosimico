import hashlib
import unittest
import xml.etree.ElementTree as ET

from profile_generator.models import InventoryStats, ProfileStats
from profile_generator.portrait import ASCII_PORTRAIT, portrait_bytes
from profile_generator.render import (
    ASCII_FONT_SIZE,
    ASCII_GUTTER,
    ASCII_LINE_HEIGHT,
    ASCII_RENDER_WIDTH,
    ASCII_START_Y,
    ASCII_X,
    CARD_HEIGHT,
    DIVIDER_X,
    render_all,
    render_svg,
)


class RenderTests(unittest.TestCase):
    def make_stats(self, **overrides):
        values = {
            "schema_version": 2,
            "login": "itsmfknlucy",
            "generated_at": "2026-08-03T04:17:00Z",
            "account_created_at": "2018-03-29T05:11:18Z",
            "public_commits": 1_234,
            "private_commits": 28_047,
            "public_contributions": 1_400,
            "restricted_contributions": 28_100,
            "lines_added": 99_000,
            "lines_deleted": 8_000,
            "followers": 42,
            "coverage": "COMPLETE",
            "inventory": InventoryStats(
                total=18,
                owned=6,
                organization_member=12,
                collaborator=0,
                public=1,
                private=17,
                internal=0,
                archived=0,
                forks=0,
                disabled=0,
                organizations=3,
                stars_owned=7,
            ),
        }
        values.update(overrides)
        return ProfileStats(**values)

    def test_both_themes_are_valid_svg_with_stable_ids(self):
        rendered = render_all(self.make_stats())
        self.assertEqual(set(rendered), {"dark", "light"})
        for svg in rendered.values():
            root = ET.fromstring(svg)
            ids = {element.attrib.get("id") for element in root.iter()}
            for expected_id in (
                "os_data",
                "uptime_data",
                "host_data",
                "kernel_data",
                "ide_data",
                "programming_data",
                "computer_data",
                "real_language_data",
                "software_hobby_data",
                "hardware_hobby_data",
                "repo_total",
                "visibility_data",
                "organization_data",
                "commit_data",
                "contribution_data",
                "lines_data",
                "signal_data",
                "generated_data",
            ):
                self.assertIn(expected_id, ids)
            tags = {element.tag.rsplit("}", 1)[-1] for element in root.iter()}
            self.assertNotIn("script", tags)
            self.assertNotIn("foreignObject", tags)
            self.assertNotIn("image", tags)

    def test_embedded_ascii_portrait_matches_the_approved_artwork(self):
        self.assertEqual(len(ASCII_PORTRAIT), 72)
        self.assertEqual({len(line) for line in ASCII_PORTRAIT}, {100})
        self.assertEqual(
            hashlib.sha256(portrait_bytes()).hexdigest(),
            "03a5d683e2d29b0a05bf62d76b567f21e620fe9585e607d5e403f92a13261f82",
        )

    def test_ascii_portrait_fits_the_terminal_panel(self):
        portrait_right_edge = ASCII_X + ASCII_RENDER_WIDTH
        portrait_bottom = ASCII_START_Y + (len(ASCII_PORTRAIT) - 1) * ASCII_LINE_HEIGHT
        self.assertEqual(DIVIDER_X - portrait_right_edge, ASCII_GUTTER)
        self.assertEqual(DIVIDER_X, 480)
        self.assertLessEqual(portrait_bottom, CARD_HEIGHT - 30)

    def test_svg_preserves_all_ascii_rows(self):
        root = ET.fromstring(render_svg(self.make_stats(), "dark"))
        ascii_text = next(element for element in root.iter() if element.attrib.get("class") == "ascii")
        lines = list(ascii_text)
        self.assertEqual(len(lines), 72)
        self.assertEqual(lines[0].text, ASCII_PORTRAIT[0])
        self.assertEqual(lines[-1].text, ASCII_PORTRAIT[-1])

    def test_statistics_use_requested_formats_and_zero_suppression(self):
        root = ET.fromstring(render_svg(self.make_stats(), "dark"))
        by_id = {element.attrib.get("id"): "".join(element.itertext()) for element in root.iter()}

        self.assertEqual(by_id["repo_total"], "18 (6 owned, 12 organization owned)")
        self.assertEqual(by_id["visibility_data"], "18 (1 public, 17 private)")
        self.assertNotIn("state_data", by_id)
        self.assertEqual(by_id["organization_data"], "3 organizations")
        self.assertEqual(by_id["commit_data"], "29,281 total commits (1,234 public, 28,047 private)")
        self.assertEqual(
            by_id["contribution_data"],
            "29,500 total contributions (1,400 public, 28,100 restricted)",
        )
        self.assertEqual(by_id["lines_data"], "91,000 total lines (99,000++, 8,000--)")
        self.assertEqual(by_id["signal_data"], "7 stars / 42 followers")
        self.assertEqual(by_id["generated_data"], "August 03, 2026 12:17 PM")

    def test_state_row_displays_only_nonzero_state_values(self):
        inventory = InventoryStats(
            total=18,
            owned=6,
            organization_member=12,
            collaborator=0,
            public=1,
            private=17,
            internal=0,
            archived=0,
            forks=1,
            disabled=0,
            organizations=3,
            stars_owned=7,
        )
        root = ET.fromstring(render_svg(self.make_stats(inventory=inventory), "dark"))
        by_id = {element.attrib.get("id"): "".join(element.itertext()) for element in root.iter()}
        self.assertEqual(by_id["state_data"], "1 (1 forked)")

    def test_zero_activity_rows_and_zero_components_are_omitted(self):
        inventory = InventoryStats(
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
            stars_owned=0,
        )
        stats = self.make_stats(
            inventory=inventory,
            public_commits=3,
            private_commits=0,
            public_contributions=0,
            restricted_contributions=0,
            lines_added=0,
            lines_deleted=0,
            followers=0,
        )
        root = ET.fromstring(render_svg(stats, "dark"))
        by_id = {element.attrib.get("id"): "".join(element.itertext()) for element in root.iter()}
        self.assertEqual(by_id["repo_total"], "1 (1 owned)")
        self.assertEqual(by_id["visibility_data"], "1 (1 public)")
        self.assertEqual(by_id["commit_data"], "3 total commits (3 public)")
        for absent in ("state_data", "organization_data", "contribution_data", "lines_data", "signal_data"):
            self.assertNotIn(absent, by_id)

    def test_lines_use_green_additions_and_red_deletions(self):
        svg = render_svg(self.make_stats(), "dark")
        self.assertIn('class="positive">99,000++</tspan>', svg)
        self.assertIn('class="negative">8,000--</tspan>', svg)
        self.assertIn("#3fb950", svg)
        self.assertIn("#f85149", svg)

    def test_equal_additions_and_deletions_keep_the_lines_row(self):
        root = ET.fromstring(
            render_svg(self.make_stats(lines_added=8_000, lines_deleted=8_000), "dark")
        )
        by_id = {
            element.attrib.get("id"): "".join(element.itertext()) for element in root.iter()
        }
        self.assertEqual(by_id["lines_data"], "0 total lines (8,000++, 8,000--)")

    def test_identity_header_and_removed_metrics_are_absent(self):
        svg = render_svg(self.make_stats(), "dark")
        for forbidden in (
            "lucifer@" + "rodstark",
            "LUCY-" + "ARCH-01",
            "Repo Size",
            "Coverage",
            "resource owners",
        ):
            self.assertNotIn(forbidden, svg)


    def test_inventory_complete_activity_pending_preserves_verified_inventory_only(self):
        stats = self.make_stats(
            public_commits=0,
            private_commits=0,
            public_contributions=0,
            restricted_contributions=0,
            lines_added=0,
            lines_deleted=0,
            coverage="INVENTORY_COMPLETE_ACTIVITY_PENDING",
        )
        root = ET.fromstring(render_svg(stats, "dark"))
        ids = {element.attrib.get("id") for element in root.iter()}
        for present in ("repo_total", "visibility_data", "organization_data", "signal_data"):
            self.assertIn(present, ids)
        for absent in ("commit_data", "contribution_data", "lines_data"):
            self.assertNotIn(absent, ids)

    def test_pending_state_does_not_present_unverified_metrics(self):
        inventory = InventoryStats(
            total=0,
            owned=0,
            organization_member=0,
            collaborator=0,
            public=0,
            private=0,
            internal=0,
            archived=0,
            forks=0,
            disabled=0,
            organizations=0,
            stars_owned=0,
        )
        stats = self.make_stats(
            inventory=inventory,
            public_commits=0,
            private_commits=0,
            public_contributions=0,
            restricted_contributions=0,
            lines_added=0,
            lines_deleted=0,
            followers=0,
            coverage="PENDING_AUTHENTICATED_SYNC",
        )
        root = ET.fromstring(render_svg(stats, "dark"))
        ids = {element.attrib.get("id") for element in root.iter()}
        self.assertNotIn("repo_total", ids)
        self.assertNotIn("commit_data", ids)
        self.assertIn("generated_data", ids)

    def test_profile_contains_requested_identity_details(self):
        root = ET.fromstring(render_svg(self.make_stats(), "dark"))
        by_id = {element.attrib.get("id"): element.text for element in root.iter()}
        self.assertEqual(by_id["os_data"], "Windows 11")
        self.assertEqual(by_id["uptime_data"], "27 years, 8 months, 11 days")
        self.assertEqual(by_id["host_data"], "Rodstark Global Solutions, Inc.")
        self.assertEqual(by_id["kernel_data"], "Enterprise Architecture / .NET / Cloud / AI")
        self.assertEqual(by_id["ide_data"], "VS Code / Codex / Visual Studio")

    def test_dynamic_text_is_xml_escaped(self):
        svg = render_svg(self.make_stats(coverage="COMPLETE & VERIFIED <SAFE>"), "dark")
        ET.fromstring(svg)
        self.assertNotIn("COMPLETE & VERIFIED", svg)


if __name__ == "__main__":
    unittest.main()
