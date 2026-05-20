#!/usr/bin/env python3
#
# Generate the Sailfish oFono cell broadcast channel catalog from AOSP
# CellBroadcastReceiver resources.

import argparse
import datetime
import json
import os
import re
import sys
import xml.etree.ElementTree as ET


CATEGORIES = [
    {
        "id": "presidential",
        "name": "Presidential alerts",
        "array": "cmas_presidential_alerts_channels_range_strings",
        "title_string": "cmas_presidential_level_alert",
        "default": True,
    },
    {
        "id": "extreme",
        "name": "Extreme alerts",
        "array": "cmas_alert_extreme_channels_range_strings",
        "title_string": "enable_cmas_extreme_threat_alerts_title",
        "default_bool": "extreme_threat_alerts_enabled_default",
    },
    {
        "id": "severe",
        "name": "Severe alerts",
        "array": "cmas_alerts_severe_range_strings",
        "title_string": "enable_cmas_severe_threat_alerts_title",
        "default_bool": "severe_threat_alerts_enabled_default",
    },
    {
        "id": "amber",
        "name": "Amber alerts",
        "array": "cmas_amber_alerts_channels_range_strings",
        "title_string": "enable_cmas_amber_alerts_title",
        "default_bool": "amber_alerts_enabled_default",
    },
    {
        "id": "monthly_test",
        "name": "Monthly test alerts",
        "array": "required_monthly_test_range_strings",
        "title_string": "enable_cmas_test_alerts_title",
        "default_bool": "test_alerts_enabled_default",
    },
    {
        "id": "exercise",
        "name": "Exercise alerts",
        "array": "exercise_alert_range_strings",
        "title_string": "enable_exercise_test_alerts_title",
        "default_bool": "test_exercise_alerts_enabled_default",
    },
    {
        "id": "operator_defined",
        "name": "Operator defined test alerts",
        "array": "operator_defined_alert_range_strings",
        "title_string": "enable_operator_defined_test_alerts_title",
        "default_bool": "test_operator_defined_alerts_enabled_default",
    },
    {
        "id": "etws",
        "name": "ETWS alerts",
        "array": "etws_alerts_range_strings",
        "title_string": "enable_etws_alerts_title",
        "default": True,
        "mandatory": True,
        "apply": False,
    },
    {
        "id": "etws_test",
        "name": "ETWS test alerts",
        "array": "etws_test_alerts_range_strings",
        "title_string": "enable_etws_test_alerts_title",
        "default": True,
        "mandatory": True,
        "apply": False,
    },
    {
        "id": "public_safety",
        "name": "Public safety alerts",
        "array": "public_safety_messages_channels_range_strings",
        "title_string": "enable_public_safety_messages_title",
        "default_bool": "public_safety_messages_enabled_default",
    },
    {
        "id": "state_local_test",
        "name": "State/local test alerts",
        "array": "state_local_test_alert_range_strings",
        "title_string": "enable_state_local_test_alerts_title",
        "default_bool": "state_local_test_alerts_enabled_default",
    },
    {
        "id": "emergency",
        "name": "Emergency alerts",
        "array": "emergency_alerts_channels_range_strings",
        "title_string": "enable_emergency_alerts_title",
        "default_bool": "emergency_alerts_enabled_default",
    },
    {
        "id": "geo_fencing",
        "name": "Geo-fencing trigger messages",
        "array": "geo_fencing_trigger_messages_range_strings",
        "default": True,
    },
    {
        "id": "additional",
        "name": "Additional emergency alerts",
        "array": "additional_cbs_channels_strings",
        "default": True,
    },
]

# These Cell Broadcast attention indications are internal assets reserved for
# official public-warning handling. They must not be installed in ringtone,
# ambience, alarm, or generic notification sound locations.
ATTENTION_TONE_DIR = "/usr/share/cell-broadcast-provider-info/attention-tones"
ATTENTION_TONE_FILE = ATTENTION_TONE_DIR + "/cellbroadcast-attention-853-960.ogg"
ATTENTION_PROFILES = {
    "eualert": {
        "soundFile": ATTENTION_TONE_FILE,
        "reservedUse": "official-cell-broadcast-public-warning",
    },
    "wea": {
        "soundFile": ATTENTION_TONE_FILE,
        "reservedUse": "official-cell-broadcast-public-warning",
    },
}

WEA_MCCS = {"310", "311", "312", "313", "314", "315", "316"}

# Countries where SailfishOS is officially sold at the time this catalog was
# added: EU, UK, Norway, and Switzerland. ETSI TS 102 900 requires a dedicated
# public-warning alerting indication, but does not define one universal EU
# waveform, so this profile is an MCC-selectable default with room for later
# country-specific overrides.
EUALERT_MCCS = {
    "202", "204", "206", "208", "214", "216", "219", "222", "226",
    "230", "231", "232", "234", "235", "238", "240", "242", "244",
    "246", "247", "248", "260", "262", "268", "270", "272", "278",
    "280", "284", "293", "228",
}

ATTENTION_CATEGORY_IDS = {
    "presidential",
    "extreme",
    "severe",
    "amber",
    "monthly_test",
    "exercise",
    "operator_defined",
    "etws",
    "etws_test",
    "public_safety",
    "state_local_test",
    "emergency",
    "additional",
}


QUALIFIER_RE = re.compile(r"^values(?:-(.*))?$")
MCC_RE = re.compile(r"^mcc(\d{3})$")
MNC_RE = re.compile(r"^mnc(\d{2,3})$")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--aosp-dir", required=True,
                        help="AOSP CellBroadcastReceiver checkout or archive extraction")
    parser.add_argument("--commit", required=True,
                        help="Pinned AOSP commit SHA")
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def parse_qualifiers(dirname):
    match = QUALIFIER_RE.match(dirname)
    if not match:
        return None
    if not match.group(1):
        return ("", "")

    mcc = ""
    mnc = ""
    for qualifier in match.group(1).split("-"):
        mcc_match = MCC_RE.match(qualifier)
        if mcc_match:
            mcc = mcc_match.group(1)
            continue
        mnc_match = MNC_RE.match(qualifier)
        if mnc_match:
            mnc = mnc_match.group(1)
            continue

        # Locale, API level, and other resource qualifiers do not affect the
        # generated oFono channel catalog.
        return None

    if not mcc and mnc:
        return None
    return (mcc, mnc)


def read_config(path):
    values = {
        "arrays": {},
        "bools": {},
        "strings": {},
    }
    if os.path.exists(path):
        tree = ET.parse(path)
        root = tree.getroot()
        for child in root:
            name = child.attrib.get("name")
            if not name:
                continue
            if child.tag == "string-array":
                values["arrays"][name] = [
                    (item.text or "").strip()
                    for item in child.findall("item")
                    if (item.text or "").strip()
                ]
            elif child.tag == "bool":
                values["bools"][name] = (child.text or "").strip().lower() == "true"
    return values


def read_strings(path):
    values = {
        "arrays": {},
        "bools": {},
        "strings": {},
    }
    if not os.path.exists(path):
        return values

    tree = ET.parse(path)
    root = tree.getroot()
    for child in root:
        name = child.attrib.get("name")
        if name and child.tag == "string":
            text = "".join(child.itertext()).strip()
            if text:
                values["strings"][name] = text
    return values


def merge_config(base, overlay):
    merged = {
        "arrays": dict(base["arrays"]),
        "bools": dict(base["bools"]),
        "strings": dict(base["strings"]),
    }
    merged["arrays"].update(overlay["arrays"])
    merged["bools"].update(overlay["bools"])
    merged["strings"].update(overlay["strings"])
    return merged


def parse_number(value):
    return int(value, 16) if value.lower().startswith("0x") else int(value)


def parse_range_item(item, category):
    parts = item.split(":", 1)
    range_text = parts[0].strip()
    attrs = {}
    if len(parts) == 2:
        for attr in parts[1].split(","):
            if "=" not in attr:
                continue
            key, value = attr.split("=", 1)
            attrs[key.strip()] = value.strip()

    rat = attrs.get("rat")
    if rat and rat != "gsm":
        return None
    if attrs.get("debug_build") == "true":
        return None
    if attrs.get("emergency") == "false":
        return None

    if "-" in range_text:
        first, last = [parse_number(part.strip()) for part in range_text.split("-", 1)]
    else:
        first = last = parse_number(range_text)

    return {
        "from": first,
        "to": last,
        "mandatory": category.get("mandatory", False) or attrs.get("always_on") == "true",
        "apply": category.get("apply", True),
    }


def normalize_ranges(ranges):
    if not ranges:
        return []
    ranges = sorted(ranges, key=lambda r: (r["from"], r["to"], r["mandatory"], r["apply"]))
    merged = []
    for item in ranges:
        if (merged and item["mandatory"] == merged[-1]["mandatory"]
                and item["apply"] == merged[-1]["apply"]
                and item["from"] <= merged[-1]["to"] + 1):
            merged[-1]["to"] = max(merged[-1]["to"], item["to"])
        else:
            merged.append(dict(item))
    return merged


def category_default(config, category):
    if "default_bool" in category:
        return config["bools"].get(category["default_bool"], True)
    return category.get("default", True)


def resolve_string(strings, name, seen=None):
    if seen is None:
        seen = set()
    if not name or name in seen:
        return ""
    seen.add(name)

    value = strings.get(name, "").strip()
    if value.startswith("@string/"):
        return resolve_string(strings, value[len("@string/"):], seen)
    return value


def category_name(config, category):
    title = resolve_string(config["strings"], category.get("title_string"))
    return title or category["name"]


def alert_system_name(config):
    strings = config["strings"]
    for category in CATEGORIES:
        value = resolve_string(strings, category.get("title_string"))
        match = re.search(r"\b[A-Za-z]{2,}-[Aa][Ll][Ee][Rr][Tt]\b", value)
        if match:
            return match.group(0)
    return ""


def attention_profile_for_plmn(plmn):
    mcc = plmn[:3]
    if mcc in WEA_MCCS:
        return "wea"
    if mcc in EUALERT_MCCS:
        return "eualert"
    return ""


def build_entry(plmn, config, default_names):
    attention_profile = attention_profile_for_plmn(plmn)
    categories = []
    for category in CATEGORIES:
        ranges = []
        for item in config["arrays"].get(category["array"], []):
            parsed = parse_range_item(item, category)
            if parsed:
                ranges.append(parsed)
        ranges = normalize_ranges(ranges)
        if not ranges:
            continue
        name = category_name(config, category)
        default_name = default_names.get(category["id"], "")
        category_entry = {
            "id": category["id"],
            "name": name,
            "customName": name.lower() != default_name.lower(),
            "defaultEnabled": category_default(config, category),
            "ranges": ranges,
        }
        if attention_profile and category["id"] in ATTENTION_CATEGORY_IDS:
            category_entry["attentionProfile"] = attention_profile
        categories.append(category_entry)

    entry = {
        "plmn": plmn,
        "alertSystem": alert_system_name(config),
        "categories": categories,
        "roamingNetworks": config["arrays"].get("cmas_roaming_network_strings", []),
    }
    if attention_profile:
        entry["defaultAttentionProfile"] = attention_profile
    return entry


def collect_configs(res_dir):
    configs = {}
    for dirname in sorted(os.listdir(res_dir)):
        config_path = os.path.join(res_dir, dirname, "config.xml")
        strings_path = os.path.join(res_dir, dirname, "strings.xml")
        if not os.path.exists(config_path) and not os.path.exists(strings_path):
            continue
        qualifiers = parse_qualifiers(dirname)
        if qualifiers is None:
            continue
        configs[qualifiers] = merge_config(read_config(config_path),
                                           read_strings(strings_path))
    return configs


def main():
    args = parse_args()
    res_dir = os.path.join(args.aosp_dir, "res")
    configs = collect_configs(res_dir)
    base = configs.get(("", ""))
    if not base:
        sys.stderr.write("No default res/values/config.xml found\n")
        return 1

    mcc_configs = {}
    mccmnc_configs = {}
    for (mcc, mnc), config in configs.items():
        if not mcc:
            continue
        if mnc:
            mccmnc_configs[(mcc, mnc)] = config
        else:
            mcc_configs[mcc] = config

    default_names = {
        category["id"]: category_name(base, category)
        for category in CATEGORIES
    }

    entries = {
        "default": build_entry("", base, default_names),
    }

    for mcc in sorted(mcc_configs):
        merged = merge_config(base, mcc_configs[mcc])
        entries[mcc] = build_entry(mcc, merged, default_names)

    for mcc in sorted(WEA_MCCS | EUALERT_MCCS):
        if mcc not in entries:
            entries[mcc] = build_entry(mcc, base, default_names)

    for mcc, mnc in sorted(mccmnc_configs):
        merged = merge_config(base, mcc_configs.get(mcc, {"arrays": {}, "bools": {}, "strings": {}}))
        merged = merge_config(merged, mccmnc_configs[(mcc, mnc)])
        entries[mcc + mnc] = build_entry(mcc + mnc, merged, default_names)

    catalog = {
        "version": 1,
        "attentionProfiles": ATTENTION_PROFILES,
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {
            "name": "AOSP CellBroadcastReceiver",
            "url": "https://android.googlesource.com/platform/packages/apps/CellBroadcastReceiver/+/main/",
            "commit": args.commit,
            "specReferences": [
                "3GPP TS 23.041",
                "3GPP TS 22.268",
                "ETSI TS 102 900",
                "47 CFR 10.520",
                "47 CFR 10.530",
            ],
        },
        "entries": entries,
    }

    with open(args.output, "w") as output:
        json.dump(catalog, output, indent=2, sort_keys=True)
        output.write("\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
