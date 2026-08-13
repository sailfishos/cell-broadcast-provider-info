#!/usr/bin/env python3

import importlib.util
import json
import os
import unittest


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG_PATH = os.path.join(ROOT, "data", "channels.json")
GENERATOR_PATH = os.path.join(ROOT, "tools", "generate-cellbroadcast-catalog.py")


def load_generator():
    spec = importlib.util.spec_from_file_location("catalog_generator", GENERATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AusAlertCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(CATALOG_PATH) as catalog_file:
            cls.catalog = json.load(catalog_file)

    def category(self, category_id):
        return next(category for category in self.catalog["entries"]["505"]["categories"]
                    if category["id"] == category_id)

    def test_ausalert_regulatory_policy(self):
        self.assertEqual("505", self.catalog["entries"]["505"]["plmn"])
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

    def test_geo_fencing_is_hidden_control_traffic(self):
        geo_fencing_categories = [
            category
            for entry in self.catalog["entries"].values()
            for category in entry["categories"]
            if category["id"] == "geo_fencing"
        ]
        self.assertTrue(geo_fencing_categories)
        for category in geo_fencing_categories:
            self.assertEqual("geofencing", category["alertLevel"])
            self.assertEqual("none", category["attentionPolicy"])
            self.assertEqual("none", category["display"])
            self.assertFalse(category["userConfigurable"])
            self.assertFalse(category["settingsVisible"])

        channel_4400_categories = [
            category for category in geo_fencing_categories
            if any(item["from"] <= 4400 <= item["to"]
                   for item in category["ranges"])
        ]
        self.assertTrue(channel_4400_categories)
        self.assertTrue(all(category["display"] == "none"
                            and not category["userConfigurable"]
                            and not category["settingsVisible"]
                            for category in channel_4400_categories))

        dbgf = self.category("ausalert_dbgf")
        self.assertEqual([4400], [item["from"] for item in dbgf["ranges"]])
        self.assertTrue(all(item["mandatory"] for item in dbgf["ranges"]))

    def test_attention_profiles_and_provenance(self):
        profiles = self.catalog["attentionProfiles"]
        self.assertEqual({"standard", "critical"}, set(profiles))
        self.assertEqual("cellbroadcast_attention", profiles["standard"]["event"])
        self.assertEqual("cellbroadcast_critical_attention",
                         profiles["critical"]["event"])
        self.assertEqual("critical",
                         self.category("ausalert_critical")["attentionProfile"])
        for category in self.catalog["entries"]["505"]["categories"]:
            if (category["id"] != "ausalert_critical"
                    and "attentionProfile" in category):
                self.assertEqual("standard", category["attentionProfile"])
        for plmn in ("262", "310"):
            entry = self.catalog["entries"][plmn]
            self.assertEqual("standard", entry["defaultAttentionProfile"])
            for category in entry["categories"]:
                if (category["id"] not in {"presidential", "extreme", "etws"}
                        and "attentionProfile" in category):
                    self.assertEqual("standard", category["attentionProfile"])
        source = self.catalog["regulatorySources"]["as-ca-s042-1-2025-a1-2026"]
        self.assertEqual("AS/CA S042.1", source["source"])
        self.assertEqual("2025 + Amendment No. 1/2026", source["edition"])
        self.assertEqual(
            "Requirements for connection to an air interface of a "
            "Telecommunications Network— Part 1: General", source["title"])
        self.assertIn("5.2.3.2", source["clauses"])
        self.assertIn("5.2.3.5", source["clauses"])
        self.assertIn("5.2.3.15", source["clauses"])

    def test_mcc_override_sets_plmn_and_removes_aosp_plmn_entries(self):
        generator = load_generator()
        entries = {"50501": {"plmn": "50501"}, "50502": {"plmn": "50502"}}
        overrides = {"entries": {"505": {"categories": []}}}
        generator.apply_regulatory_overrides(entries, overrides)
        self.assertEqual({"505"}, set(entries))
        self.assertEqual("505", entries["505"]["plmn"])

    def test_generic_critical_attention_policy(self):
        critical_ids = {"presidential", "extreme", "etws", "ausalert_critical"}
        mandatory_noncritical = 0

        for entry in self.catalog["entries"].values():
            for category in entry["categories"]:
                category_id = category["id"]
                if category_id in critical_ids:
                    self.assertEqual("critical", category["attentionProfile"])
                    self.assertEqual("critical", category["alertLevel"])
                    self.assertEqual("silent-dnd-override",
                                     category["attentionPolicy"])
                else:
                    self.assertNotEqual("critical", category.get("attentionProfile"))
                    if any(item["mandatory"] for item in category["ranges"]):
                        mandatory_noncritical += 1

        self.assertGreater(mandatory_noncritical, 0)


if __name__ == "__main__":
    unittest.main()
