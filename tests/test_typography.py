import unittest

from profile_generator.models import InventoryStats, ProfileStats
from profile_generator.render import ASCII_FONT_SIZE, render_svg


class TypographyTests(unittest.TestCase):
    def make_stats(self) -> ProfileStats:
        return ProfileStats(
            schema_version=2,
            login="itsmfknlucy",
            generated_at="2026-08-03T15:52:11Z",
            account_created_at="2018-03-29T05:11:18Z",
            public_commits=49,
            private_commits=17_881,
            public_contributions=42,
            restricted_contributions=28_047,
            lines_added=3_838_506,
            lines_deleted=375_863,
            followers=5,
            coverage="COMPLETE",
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
                stars_owned=14,
            ),
        )

    def test_content_text_is_larger_and_values_are_semibold(self):
        for theme in ("dark", "light"):
            with self.subTest(theme=theme):
                svg = render_svg(self.make_stats(), theme)
                self.assertEqual(
                    svg.count("font-size: 18px; font-weight: 700;"),
                    2,
                )
                self.assertEqual(
                    svg.count("font-size: 18px; font-weight: 600;"),
                    1,
                )
                self.assertIn(
                    f"font-size: {ASCII_FONT_SIZE}px; font-weight: 500;",
                    svg,
                )


if __name__ == "__main__":
    unittest.main()
