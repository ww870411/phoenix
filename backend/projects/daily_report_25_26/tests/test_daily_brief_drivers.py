"""经营差异归因的闭合、缺失及零基数验证。"""

import unittest
from datetime import date

from backend.projects.daily_report_25_26.services.daily_brief import BriefEvidence
from backend.projects.daily_report_25_26.services.daily_brief_drivers import build_cost_drivers


class DailyBriefDriversTest(unittest.TestCase):
    def setUp(self):
        self.day, self.peer = date(2026, 11, 1), date(2025, 11, 1)
        self.rows = {("Group", "eco_measurable_auxiliary_materials"):
                     {"value_biz_date": 0, "value_peer_date": 6}}
        self.raw = [{"company": "A", "item": "consumption_oil", "date": self.day, "value": 0},
                    {"company": "A", "item": "consumption_oil", "date": self.peer, "value": 10}]
        self.expected = [{"company": "A", "item": "consumption_oil", "period": period} for period in ("26-27", "25-26")]
        self.constants = [{"company": "A", "item": "price_oil", "period": period, "value": price}
                          for period, price in (("26-27", 8000), ("25-26", 6000))]

    def build(self):
        return build_cost_drivers(self.day, self.rows, BriefEvidence(self.raw, self.expected, self.constants), ["A"], {"A": "甲单位"})

    def test_decomposition_reconciles_and_preserves_zero(self):
        story = self.build()["stories"][0]
        driver = story["drivers"][0]
        self.assertEqual(driver["current"], 0)
        self.assertAlmostEqual(driver["quantity_effect"] + driver["price_effect"], -6)
        self.assertAlmostEqual(story["percent"], -100)

    def test_missing_quantity_does_not_become_zero(self):
        self.raw.pop(0)
        result = self.build()
        self.assertFalse(result["stories"])
        self.assertIn("可计量辅材成本", result["incomplete"])

    def test_unreconciled_total_is_not_explained(self):
        self.rows[("Group", "eco_measurable_auxiliary_materials")]["value_peer_date"] = 9
        self.assertFalse(self.build()["stories"])

    def test_missing_nonzero_price_is_not_explained(self):
        self.constants.pop()
        self.assertFalse(self.build()["stories"])


if __name__ == "__main__":
    unittest.main()
