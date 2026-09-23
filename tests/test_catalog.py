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


class CatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(CATALOG_PATH) as catalog_file:
            cls.catalog = json.load(catalog_file)

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

    def test_attention_profiles_and_provenance(self):
        profiles = self.catalog["attentionProfiles"]
        vibration_profiles = self.catalog["vibrationProfiles"]
        self.assertEqual({"standard", "critical"}, set(profiles))
        self.assertEqual({"wea", "sos"}, set(vibration_profiles))
        self.assertEqual("cellbroadcast_attention", profiles["standard"]["event"])
        self.assertEqual("cellbroadcast_critical_attention",
                         profiles["critical"]["event"])
        self.assertNotIn("vibrationProfile", profiles["standard"])
        self.assertEqual("sos", profiles["critical"]["vibrationProfile"])
        self.assertNotIn("vibrationPattern", profiles["standard"])
        self.assertNotIn("vibrationRepeat", profiles["standard"])
        self.assertEqual(
            [0, 2000, 500, 1000, 500, 1000, 500,
             2000, 500, 1000, 500, 1000],
            vibration_profiles["wea"]["vibrationPattern"])
        self.assertFalse(vibration_profiles["wea"]["vibrationRepeat"])
        self.assertEqual(
            [0, 500, 500, 500, 500, 500, 500,
             1000, 500, 1000, 500, 1000, 500,
             500, 500, 500, 500, 500, 500],
            vibration_profiles["sos"]["vibrationPattern"])
        self.assertTrue(vibration_profiles["sos"]["vibrationRepeat"])
        self.assertEqual(vibration_profiles["sos"]["vibrationPattern"],
                         profiles["critical"]["vibrationPattern"])
        self.assertEqual(vibration_profiles["sos"]["vibrationRepeat"],
                         profiles["critical"]["vibrationRepeat"])
        for plmn in ("262", "310"):
            entry = self.catalog["entries"][plmn]
            self.assertEqual("standard", entry["defaultAttentionProfile"])
            for category in entry["categories"]:
                if (category["id"] not in {"presidential", "extreme", "etws"}
                        and "attentionProfile" in category):
                    self.assertEqual("standard", category["attentionProfile"])

    def test_aosp_vibration_overrides(self):
        inline_patterns = {
            tuple(item["vibrationPattern"])
            for entry in self.catalog["entries"].values()
            for category in entry["categories"]
            for item in category["ranges"]
            if "vibrationPattern" in item
        }
        self.assertEqual({
            (0, 1000, 500, 1000, 500, 1000, 500,
             2000, 500, 2000, 500, 2000, 500,
             1000, 500, 1000, 500, 1000, 500),
            (0, 500, 500, 500, 500, 500, 500,
             1000, 500, 1000, 500, 1000, 500,
             500, 500, 500, 500, 500, 500),
            (0, 350, 250, 350),
        }, inline_patterns)

        pulse_pattern = [0] + [500] * 16
        self.assertEqual(pulse_pattern,
                         self.catalog["entries"]["302"]["defaultVibrationPattern"])
        self.assertEqual(pulse_pattern,
                         self.catalog["entries"]["334"]["defaultVibrationPattern"])

    def test_wea_vibration_policy_and_provenance(self):
        wea_mccs = {"310", "311", "312", "313", "314", "315", "316",
                    "330", "332", "544"}
        for plmn, entry in self.catalog["entries"].items():
            if plmn[:3] in wea_mccs:
                self.assertEqual("wea", entry["defaultVibrationProfile"])
                self.assertEqual("47-cfr-10-530", entry["vibrationSourceRef"])

        for plmn in ("310", "310260", "311", "316", "330", "332", "544"):
            categories = self.catalog["entries"][plmn]["categories"]
            extreme = next(category for category in categories
                           if category["id"] == "extreme")
            self.assertEqual("standard", extreme["attentionProfile"])
            self.assertNotEqual("critical", extreme.get("alertLevel"))
            self.assertNotEqual("silent-dnd-override",
                                extreme.get("attentionPolicy"))

            critical_categories = [category for category in categories
                                   if category["id"] in {"presidential", "etws"}]
            self.assertTrue(critical_categories)
            self.assertTrue(all(category["attentionProfile"] == "critical"
                                for category in critical_categories))

        source = self.catalog["regulatorySources"]["47-cfr-10-530"]
        self.assertEqual("47 CFR 10.530", source["source"])
        self.assertEqual("Common vibration cadence", source["title"])
        self.assertEqual(["10.530(a)"], source["clauses"])

    def test_eualert_level_two_uses_configured_attention(self):
        for plmn in ("204", "214", "234", "235", "238", "270", "284"):
            extreme = next(
                category for category in self.catalog["entries"][plmn]["categories"]
                if category["id"] == "extreme")
            self.assertEqual("critical", extreme["attentionProfile"])
            self.assertEqual("silent-dnd-override",
                             extreme["attentionPolicy"])
            self.assertNotEqual("critical", extreme.get("alertLevel"))
            if plmn != "235":
                self.assertTrue(all(item["overrideDnd"]
                                    for item in extreme["ranges"]))

        for plmn in ("234", "235"):
            extreme = next(
                category for category in self.catalog["entries"][plmn]["categories"]
                if category["id"] == "extreme")
            self.assertEqual("gov-uk-emergency-alerts", extreme["sourceRef"])

        for plmn in ("208", "262"):
            extreme = next(
                category for category in self.catalog["entries"][plmn]["categories"]
                if category["id"] == "extreme")
            self.assertEqual("standard", extreme["attentionProfile"])
            self.assertNotEqual("critical", extreme.get("alertLevel"))
            self.assertNotEqual("silent-dnd-override",
                                extreme.get("attentionPolicy"))

        french_extreme = next(
            category for category in self.catalog["entries"]["208"]["categories"]
            if category["id"] == "extreme")
        self.assertTrue(all(item["overrideDnd"]
                            for item in french_extreme["ranges"]))

        source = self.catalog["regulatorySources"]["gov-uk-emergency-alerts"]
        self.assertEqual("GOV.UK", source["source"])

    def test_regulatory_attention_policy_updates_category_only(self):
        generator = load_generator()
        entries = {
            "234": {
                "categories": [{
                    "id": "extreme",
                    "alertLevel": "extreme",
                    "attentionProfile": "standard",
                }],
            },
            "23410": {
                "categories": [{
                    "id": "extreme",
                    "alertLevel": "extreme",
                    "attentionProfile": "standard",
                }],
            },
        }
        policies = {
            "sources": {"source": {}},
            "entries": {
                "234": {
                    "categories": {
                        "extreme": {
                            "attentionProfile": "critical",
                            "attentionPolicy": "silent-dnd-override",
                            "sourceRef": "source",
                        },
                    },
                },
            },
        }

        generator.apply_regulatory_attention_policies(
            entries, policies, generator.ATTENTION_PROFILES)

        for entry in entries.values():
            extreme = entry["categories"][0]
            self.assertEqual("extreme", extreme["alertLevel"])
            self.assertEqual("critical", extreme["attentionProfile"])
            self.assertEqual("silent-dnd-override",
                             extreme["attentionPolicy"])

    def test_redundant_vibration_overrides_are_discarded(self):
        generator = load_generator()
        standard = generator.VIBRATION_PROFILES["wea"]["vibrationPattern"]
        critical = generator.VIBRATION_PROFILES["sos"]["vibrationPattern"]
        different = [0, 350, 250, 350]
        entries = {
            "232": {
                "categories": [{
                    "attentionProfile": "critical",
                    "vibrationPattern": list(critical),
                    "ranges": [
                        {"vibrationPattern": list(critical)},
                        {"vibrationPattern": different},
                    ],
                }],
            },
            "310": {
                "defaultVibrationProfile": "wea",
                "defaultVibrationPattern": different,
                "categories": [{
                    "attentionProfile": "critical",
                    "ranges": [{"vibrationPattern": list(standard)}],
                }],
            },
            "999": {
                "defaultVibrationPattern": different,
                "categories": [{
                    "attentionProfile": "standard",
                    "ranges": [{"vibrationPattern": list(different)}],
                }],
            },
            "998": {
                "categories": [{
                    "attentionProfile": "standard",
                    "vibrationPattern": different,
                    "ranges": [{"vibrationPattern": list(different)}],
                }],
            },
        }

        generator.discard_redundant_vibration_overrides(
            entries, generator.ATTENTION_PROFILES,
            generator.VIBRATION_PROFILES)

        category = entries["232"]["categories"][0]
        self.assertNotIn("vibrationPattern", category)
        self.assertNotIn("vibrationPattern", category["ranges"][0])
        self.assertEqual(different, category["ranges"][1]["vibrationPattern"])
        self.assertNotIn("defaultVibrationPattern", entries["310"])
        self.assertNotIn(
            "vibrationPattern", entries["310"]["categories"][0]["ranges"][0])
        self.assertNotIn(
            "vibrationPattern", entries["999"]["categories"][0]["ranges"][0])
        self.assertEqual(
            different, entries["998"]["categories"][0]["vibrationPattern"])
        self.assertNotIn(
            "vibrationPattern", entries["998"]["categories"][0]["ranges"][0])

        for plmn in ("232", "262"):
            extreme = next(
                category for category in self.catalog["entries"][plmn]["categories"]
                if category["id"] == "extreme")
            self.assertEqual("standard", extreme["attentionProfile"])
            patterns = [item["vibrationPattern"] for item in extreme["ranges"]
                        if "vibrationPattern" in item]
            self.assertTrue(patterns)
            self.assertTrue(all(pattern == critical for pattern in patterns))

    def test_mcc_override_sets_plmn_and_removes_aosp_plmn_entries(self):
        generator = load_generator()
        entries = {"99901": {"plmn": "99901"}, "99902": {"plmn": "99902"}}
        overrides = {"entries": {"999": {"categories": []}}}
        generator.apply_regulatory_overrides(entries, overrides)
        self.assertEqual({"999"}, set(entries))
        self.assertEqual("999", entries["999"]["plmn"])

    def test_same_overlay_keeps_explicit_carrier_exception(self):
        generator = load_generator()
        entries = {"99901": {"plmn": "99901"}}
        overrides = {"entries": {
            "99902": {"categories": []},
            "999": {"categories": []},
        }}
        generator.apply_regulatory_overrides(entries, overrides)
        self.assertEqual({"999", "99902"}, set(entries))
        self.assertEqual("99902", entries["99902"]["plmn"])

    def test_generic_critical_attention_policy(self):
        generator = load_generator()
        critical_ids = {"presidential", "extreme", "etws"}
        mandatory_noncritical = 0

        for plmn, entry in self.catalog["entries"].items():
            for category in entry["categories"]:
                category_id = category["id"]
                standard_extreme = (
                    category_id == "extreme"
                    and (plmn[:3] in (generator.WEA_MCCS
                                      | generator.EUALERT_MCCS)
                         or entry.get("alertSystem", "").upper() == "FR-ALERT"))
                configured_critical_extreme = (
                    standard_extreme
                    and entry.get("alertSystem", "").upper() != "FR-ALERT"
                    and (category.get("sourceRef")
                         == "gov-uk-emergency-alerts"
                         or any(item.get("overrideDnd", False)
                                for item in category["ranges"])))
                if ((category_id in critical_ids and not standard_extreme)
                        or configured_critical_extreme):
                    self.assertEqual("critical", category["attentionProfile"])
                    self.assertEqual("silent-dnd-override",
                                     category["attentionPolicy"])
                    if configured_critical_extreme:
                        self.assertNotEqual("critical", category.get("alertLevel"))
                    else:
                        self.assertEqual("critical", category["alertLevel"])
                else:
                    self.assertNotEqual("critical", category.get("attentionProfile"))
                    if any(item["mandatory"] for item in category["ranges"]):
                        mandatory_noncritical += 1

        self.assertGreater(mandatory_noncritical, 0)


if __name__ == "__main__":
    unittest.main()
