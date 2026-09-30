#!/usr/bin/env python3
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class PolicyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(
            (ROOT / "data" / "overrides" / "fi-alert-regulatory.json").read_text())

    def test_fi_alert_policy(self):
        entry = self.catalog["entries"]["244"]
        self.assertEqual("FI-Alert", entry["alertSystem"])
        self.assertEqual("wea", entry["defaultVibrationProfile"])
        self.assertFalse(any(key.startswith("244") and key != "244"
                             for key in self.catalog["entries"]))
        categories = {item["id"]: item for item in entry["categories"]}
        expected = {
            "presidential": ([4370, 4383], True, True, "warning"),
            "severe": (list(range(4373, 4379)) + list(range(4386, 4392)), True, False, "silent"),
            "public_safety": ([4396, 4397], True, False, "sms"),
            "monthly_test": ([4380, 4393], False, False, "warning"),
            "exercise": ([4381, 4394], False, False, "warning"),
            "geo_fencing": ([4400], True, True, "silent"),
        }
        self.assertEqual(set(expected), set(categories))
        for category_id, (channels, enabled, mandatory, mode) in expected.items():
            category = categories[category_id]
            self.assertEqual(channels, [channel for item in category["ranges"]
                                        for channel in range(item["from"], item["to"] + 1)])
            self.assertEqual(enabled, category["defaultEnabled"])
            self.assertTrue(all(item["mandatory"] == mandatory for item in category["ranges"]))
            self.assertEqual(not mandatory, category["userConfigurable"])
            self.assertEqual(mode, category["attentionMode"])
            self.assertEqual("none", category["languageFilter"])
            self.assertFalse(category["attentionRepeat"])
            self.assertFalse(category["vibrationRepeat"])
            for language in ("fi", "sv"):
                self.assertEqual({"name", "title", "description"},
                                 set(category["translations"][language]))
                self.assertTrue(all(category["translations"][language].values()))
            if mode == "warning":
                self.assertEqual(10500, category["attentionDurationMs"])
            if mode == "silent":
                self.assertNotIn("attentionProfile", category)
        self.assertEqual("critical", categories["presidential"]["attentionProfile"])
        self.assertEqual("none", categories["geo_fencing"]["display"])
        self.assertFalse(categories["geo_fencing"]["settingsVisible"])


if __name__ == "__main__":
    unittest.main()
