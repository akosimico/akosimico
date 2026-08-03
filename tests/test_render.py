import hashlib
import unittest
import xml.etree.ElementTree as ET

from profile_generator.models import InventoryStats, ProfileStats
from profile_generator.render import (
    ASCII_FONT_SIZE,
    ASCII_GUTTER,
    ASCII_LINE_HEIGHT,
    ASCII_PORTRAIT,
    ASCII_SOURCE_PATH,
    ASCII_START_Y,
    ASCII_X,
    CARD_HEIGHT,
    DIVIDER_X,
    render_all,
    render_svg,
)


class RenderTests(unittest.TestCase):
    def make_stats(self, coverage: str = "COMPLETE") -> ProfileStats:
        return ProfileStats(
            schema_version=1,
            login="itsmfknlucy",
            generated_at="2026-08-03T04:17:00Z",
            account_created_at="2018-03-29T05:11:18Z",
            commit_contributions=1_234,
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
                size_kib=815_911,
            ),
        )

    def test_both_themes_are_valid_svg_with_stable_ids(self) -> None:
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
                "signal_data",
                "coverage_data",
                "generated_data",
            ):
                self.assertIn(expected_id, ids)
            tags = {element.tag.rsplit("}", 1)[-1] for element in root.iter()}
            self.assertNotIn("script", tags)
            self.assertNotIn("foreignObject", tags)
            self.assertNotIn("image", tags)

    def test_uploaded_ascii_portrait_is_used_exactly(self) -> None:
        raw = ASCII_SOURCE_PATH.read_text(encoding="utf-8")

        self.assertEqual(len(ASCII_PORTRAIT), 55)
        self.assertEqual({len(line) for line in ASCII_PORTRAIT}, {100})
        self.assertEqual(tuple(raw.splitlines()), ASCII_PORTRAIT)
        self.assertEqual(
            hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            "81f21b4f2ec1a214548fed974a258a15431e7bca0b19f30290dc72bedc956d41",
        )

    def test_uploaded_ascii_portrait_fits_the_terminal_panel(self) -> None:
        estimated_right_edge = (
            ASCII_X + max(map(len, ASCII_PORTRAIT)) * ASCII_FONT_SIZE * 0.62
        )
        estimated_bottom = (
            ASCII_START_Y + (len(ASCII_PORTRAIT) - 1) * ASCII_LINE_HEIGHT
        )

        self.assertLessEqual(estimated_right_edge, DIVIDER_X - ASCII_GUTTER)
        self.assertLessEqual(estimated_bottom, CARD_HEIGHT - 30)

    def test_svg_preserves_all_uploaded_ascii_rows(self) -> None:
        root = ET.fromstring(render_svg(self.make_stats(), "dark"))
        ascii_text = next(
            element for element in root.iter() if element.attrib.get("class") == "ascii"
        )
        lines = list(ascii_text)

        self.assertEqual(len(lines), 55)
        self.assertEqual(lines[0].text, ASCII_PORTRAIT[0])
        self.assertEqual(lines[-1].text, ASCII_PORTRAIT[-1])

    def test_profile_contains_requested_identity_details_and_no_contact_section(self) -> None:
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

    def test_complete_statistics_include_private_contribution_signal(self) -> None:
        root = ET.fromstring(render_svg(self.make_stats(), "dark"))
        by_id = {element.attrib.get("id"): element.text for element in root.iter()}

        self.assertEqual(
            by_id["commit_data"],
            "1,234 commit contributions / 28,047 restricted",
        )
        self.assertEqual(by_id["signal_data"], "7 stars / 42 followers")
        self.assertEqual(by_id["coverage_data"], "COMPLETE")

    def test_dark_theme_is_red_and_black_without_purple(self) -> None:
        svg = render_svg(self.make_stats(), "dark").casefold()

        for expected in ("#090909", "#160b0b", "#ff5c5c", "#ff8d8d"):
            self.assertIn(expected, svg)
        for forbidden in ("#6d28d9", "#c7b8ff", "#b7a7ff", "#5b21b6"):
            self.assertNotIn(forbidden, svg)

    def test_light_theme_is_red_and_white_without_purple(self) -> None:
        svg = render_svg(self.make_stats(), "light").casefold()

        for expected in ("#fffafa", "#ffffff", "#b42318", "#7a271a"):
            self.assertIn(expected, svg)
        for forbidden in ("#c4b5fd", "#5b21b6", "#4c1d95", "#9d174d"):
            self.assertNotIn(forbidden, svg)

    def test_svg_uses_portable_monospace_font_and_preserves_spaces(self) -> None:
        svg = render_svg(self.make_stats(), "dark")

        self.assertIn(
            'font-family: Consolas, "Liberation Mono", "DejaVu Sans Mono", monospace;',
            svg,
        )
        self.assertIn('xml:space="preserve"', svg)
        self.assertNotIn("ui-monospace", svg)

    def test_dynamic_text_is_xml_escaped(self) -> None:
        svg = render_svg(self.make_stats("COMPLETE & VERIFIED <SAFE>"), "dark")
        root = ET.fromstring(svg)
        coverage = next(
            element for element in root.iter() if element.attrib.get("id") == "coverage_data"
        )

        self.assertEqual(coverage.text, "COMPLETE & VERIFIED <SAFE>")
        self.assertIn("COMPLETE &amp; VERIFIED &lt;SAFE&gt;", svg)

    def test_pending_state_does_not_present_zeroes_as_verified_metrics(self) -> None:
        stats = ProfileStats(
            schema_version=1,
            login="itsmfknlucy",
            generated_at="2026-08-03T04:17:00Z",
            account_created_at="2018-03-29T05:11:18Z",
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

    def test_card_has_no_footer_disclaimer_or_external_asset(self) -> None:
        svg = render_svg(self.make_stats(), "dark")

        for forbidden in (
            "original portrait not stored",
            "transformed locally",
            "source-portrait.png",
            "private-email@example.invalid",
            ".png",
        ):
            self.assertNotIn(forbidden, svg)
        self.assertIn("Lucifer Rodstark, Ph.D.", svg)
        self.assertIn("LUCY-ARCH-01", svg)


if __name__ == "__main__":
    unittest.main()
