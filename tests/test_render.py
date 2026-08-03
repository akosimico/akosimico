import unittest
import xml.etree.ElementTree as ET

from profile_generator.models import InventoryStats, ProfileStats
from profile_generator.render import (
    ASCII_FONT_SIZE,
    ASCII_GUTTER,
    ASCII_PORTRAIT,
    ASCII_X,
    DIVIDER_X,
    render_all,
    render_svg,
)


class RenderTests(unittest.TestCase):
    def make_stats(self, coverage="COMPLETE"):
        return ProfileStats(
            schema_version=1,
            login="itsmfknlucy",
            generated_at="2026-08-03T04:17:00Z",
            account_created_at="2018-03-01T00:00:00Z",
            commit_contributions=1234,
            restricted_contributions=28_047,
            followers=42,
            coverage=coverage,
            inventory=InventoryStats(
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
                resource_owners=4,
                stars_owned=7,
                size_kib=815_829,
            ),
        )

    def test_both_themes_are_valid_svg_with_stable_ids(self):
        rendered = render_all(self.make_stats())

        self.assertEqual(set(rendered), {"dark", "light"})
        for svg in rendered.values():
            root = ET.fromstring(svg)
            self.assertTrue(root.tag.endswith("svg"))
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
                "commit_data",
                "coverage_data",
                "generated_data",
            ):
                self.assertIn(expected_id, ids)
            tags = {element.tag.rsplit("}", 1)[-1] for element in root.iter()}
            self.assertNotIn("script", tags)
            self.assertNotIn("foreignObject", tags)
            self.assertNotIn("image", tags)

    def test_profile_contains_requested_identity_details_and_no_contact_section(self):
        svg = render_svg(self.make_stats(), "dark")
        root = ET.fromstring(svg)
        by_id = {element.attrib.get("id"): element.text for element in root.iter()}

        self.assertEqual(by_id["os_data"], "Windows 11")
        self.assertEqual(by_id["uptime_data"], "27 years, 8 months, 11 days")
        self.assertEqual(by_id["host_data"], "Rodstark Global Solutions, Inc.")
        self.assertEqual(
            by_id["kernel_data"],
            "Enterprise Architecture / .NET / Cloud / AI",
        )
        self.assertEqual(by_id["ide_data"], "VS Code / Codex / Visual Studio")
        self.assertEqual(
            by_id["programming_data"],
            "C#, VB.NET, C++, Python, Java, PHP, JavaScript, TS",
        )
        self.assertEqual(
            by_id["computer_data"],
            "HTML, CSS, SASS, SQL, JSON, XML, YAML",
        )
        self.assertEqual(
            by_id["real_language_data"],
            "English, Filipino, German, Japanese",
        )
        self.assertEqual(
            by_id["software_hobby_data"],
            "Modding, SaaS, Gaming, AI Systems, Automation",
        )
        self.assertEqual(
            by_id["hardware_hobby_data"],
            "PC Building, Performance Tuning, Undervolting",
        )
        self.assertNotIn("Contact", svg)
        self.assertNotIn("Email", svg)
        self.assertNotIn("LinkedIn", svg)
        self.assertNotIn("Discord", svg)
        self.assertEqual(
            by_id["commit_data"],
            "1,234 commits / 28,047 private contributions",
        )

    def test_dark_theme_is_red_and_black_without_purple_palette(self):
        svg = render_svg(self.make_stats(), "dark").casefold()

        for expected in ("#090909", "#160b0b", "#ff5c5c", "#ffb0b0"):
            self.assertIn(expected, svg)
        for forbidden in ("#6d28d9", "#c7b8ff", "#b7a7ff", "#5b21b6"):
            self.assertNotIn(forbidden, svg)

    def test_light_theme_is_red_and_white_without_purple_palette(self):
        svg = render_svg(self.make_stats(), "light").casefold()

        for expected in ("#fffafa", "#ffffff", "#b42318", "#7a271a"):
            self.assertIn(expected, svg)
        for forbidden in ("#c4b5fd", "#5b21b6", "#4c1d95", "#9d174d"):
            self.assertNotIn(forbidden, svg)

    def test_ascii_portrait_respects_the_left_panel_gutter(self):
        estimated_right_edge = (
            ASCII_X + max(map(len, ASCII_PORTRAIT)) * ASCII_FONT_SIZE * 0.62
        )

        self.assertLessEqual(estimated_right_edge, DIVIDER_X - ASCII_GUTTER)

    def test_svg_forces_a_portable_monospace_font_before_generic_fallbacks(self):
        svg = render_svg(self.make_stats(), "dark")

        self.assertIn(
            'font-family: Consolas, "Liberation Mono", "DejaVu Sans Mono", monospace;',
            svg,
        )
        self.assertNotIn("ui-monospace", svg)

    def test_dynamic_text_is_xml_escaped(self):
        svg = render_svg(self.make_stats("COMPLETE & VERIFIED <SAFE>"), "dark")
        root = ET.fromstring(svg)
        coverage = next(element for element in root.iter() if element.attrib.get("id") == "coverage_data")

        self.assertEqual(coverage.text, "COMPLETE & VERIFIED <SAFE>")
        self.assertIn("COMPLETE &amp; VERIFIED &lt;SAFE&gt;", svg)

    def test_inventory_bootstrap_shows_verified_repository_counts_but_not_unknown_signals(self):
        stats = self.make_stats("INVENTORY_COMPLETE")
        stats = ProfileStats(
            schema_version=stats.schema_version,
            login=stats.login,
            generated_at=stats.generated_at,
            account_created_at=stats.account_created_at,
            commit_contributions=0,
            restricted_contributions=0,
            followers=0,
            coverage=stats.coverage,
            inventory=stats.inventory,
        )

        root = ET.fromstring(render_svg(stats, "dark"))
        by_id = {element.attrib.get("id"): element for element in root.iter()}

        self.assertIn("18 total", by_id["repo_total"].text)
        self.assertEqual(by_id["commit_data"].text, "—")
        self.assertEqual(by_id["signal_data"].text, "—")
        self.assertEqual(by_id["coverage_data"].text, "INVENTORY_COMPLETE")

    def test_pending_bootstrap_does_not_present_zeroes_as_verified_metrics(self):
        stats = ProfileStats(
            schema_version=1,
            login="itsmfknlucy",
            generated_at="2026-08-03T04:17:00Z",
            account_created_at="2018-03-01T00:00:00Z",
            commit_contributions=0,
            restricted_contributions=0,
            followers=0,
            coverage="PENDING_AUTHENTICATED_SYNC",
            inventory=InventoryStats(
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
                resource_owners=0,
                stars_owned=0,
                size_kib=0,
            ),
        )

        root = ET.fromstring(render_svg(stats, "dark"))
        by_id = {element.attrib.get("id"): element for element in root.iter()}

        self.assertEqual(by_id["repo_total"].text, "—")
        self.assertEqual(by_id["commit_data"].text, "—")
        self.assertEqual(by_id["coverage_data"].text, "PENDING_AUTHENTICATED_SYNC")

    def test_card_has_no_extra_footer_or_source_asset_reference(self):
        svg = render_svg(self.make_stats(), "dark")

        for forbidden in (
            "source-portrait.png",
            "original portrait not stored",
            "transformed locally",
            "legal-identity-placeholder",
            "private-email@example.invalid",
            ".png",
        ):
            self.assertNotIn(forbidden, svg)
        self.assertIn("Lucifer Rodstark, Ph.D.", svg)
        self.assertIn("LUCY-ARCH-01", svg)


if __name__ == "__main__":
    unittest.main()
