#!/usr/bin/env python3
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class PolicyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(
            (ROOT / "data" / "overrides" / "ausalert-regulatory.json").read_text())

    def category(self, category_id):
        return next(category for category in self.catalog["entries"]["505"]["categories"]
                    if category["id"] == category_id)

    def test_attention_and_provenance(self):
        self.assertEqual("critical", self.category("ausalert_critical")["attentionProfile"])
        self.assertEqual(
            [0, 500, 500, 500, 500, 500, 500,
             1000, 500, 1000, 500, 1000, 500,
             500, 500, 500, 500, 500, 500],
            self.category("ausalert_priority")["vibrationPattern"])
        self.assertFalse(self.category("ausalert_priority").get("vibrationRepeat", False))
        for category in self.catalog["entries"]["505"]["categories"]:
            if category["id"] != "ausalert_critical" and "attentionProfile" in category:
                self.assertEqual("standard", category["attentionProfile"])
        source = self.catalog["sources"]["as-ca-s042-1-2025-a1-2026"]
        self.assertEqual("AS/CA S042.1", source["source"])
        self.assertEqual("2025 + Amendment No. 1/2026", source["edition"])
        self.assertEqual(
            "Requirements for connection to an air interface of a "
            "Telecommunications Network— Part 1: General", source["title"])
        for clause in ("5.2.3.2", "5.2.3.5", "5.2.3.15"):
            self.assertIn(clause, source["clauses"])

    def test_ausalert_regulatory_policy(self):
        self.assertEqual({"505"}, set(self.catalog["entries"]))
        critical = self.category("ausalert_critical")
        self.assertEqual("Critical AusAlert", critical["title"])
        self.assertTrue(critical["defaultEnabled"])
        self.assertFalse(critical["userConfigurable"])
        self.assertEqual("silent-dnd-override", critical["attentionPolicy"])
        self.assertEqual([4370, 4383], [item["from"] for item in critical["ranges"]])
        self.assertEqual(["local", "additional"],
                         [item["languageRole"] for item in critical["ranges"]])
        self.assertTrue(all(item["mandatory"] for item in critical["ranges"]))

        expected = {
            "ausalert_priority": ("Priority AusAlert", [4371, 4384], True),
            "ausalert_exercise": ("Exercise", [4381, 4394], True),
            "ausalert_monthly_test": ("Test", [4380, 4393], False),
            "ausalert_operator_test": ("Operator Test", [4382, 4395], False),
            "ausalert_state_local_test": ("State/Local Test", [4398, 4399], True),
        }
        for category_id, (title, channels, enabled) in expected.items():
            category = self.category(category_id)
            self.assertEqual(title, category["title"])
            self.assertEqual(enabled, category["defaultEnabled"])
            self.assertTrue(category["userConfigurable"])
            self.assertEqual(channels, [item["from"] for item in category["ranges"]])

        dbgf = self.category("ausalert_dbgf")
        self.assertTrue(dbgf["defaultEnabled"])
        self.assertFalse(dbgf["userConfigurable"])
        self.assertFalse(dbgf["settingsVisible"])
        self.assertEqual("none", dbgf["display"])
        self.assertEqual(4400, dbgf["ranges"][0]["from"])
        self.assertTrue(dbgf["ranges"][0]["mandatory"])
        self.assertEqual("geofencing", dbgf["alertLevel"])
        self.assertEqual("none", dbgf["attentionPolicy"])


if __name__ == "__main__":
    unittest.main()
