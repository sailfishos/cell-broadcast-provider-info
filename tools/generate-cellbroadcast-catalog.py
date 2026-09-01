#!/usr/bin/env python3
#
# Generate the Sailfish oFono cell broadcast channel catalog from AOSP
# CellBroadcastReceiver resources.

import argparse
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
        "alertLevel": "geofencing",
        "attentionPolicy": "none",
        "display": "none",
        "userConfigurable": False,
        "settingsVisible": False,
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
WEA_VIBRATION_PATTERN = [
    0, 2000, 500, 1000, 500, 1000, 500,
    2000, 500, 1000, 500, 1000,
]
SOS_VIBRATION_PATTERN = [
    0, 500, 500, 500, 500, 500, 500,
    1000, 500, 1000, 500, 1000, 500,
    500, 500, 500, 500, 500, 500,
]
VIBRATION_PROFILES = {
    "wea": {
        "vibrationPattern": WEA_VIBRATION_PATTERN,
        "vibrationRepeat": False,
    },
    "sos": {
        "vibrationPattern": SOS_VIBRATION_PATTERN,
        "vibrationRepeat": True,
    },
}
ATTENTION_PROFILES = {
    "standard": {
        "soundFile": ATTENTION_TONE_FILE,
        "reservedUse": "official-cell-broadcast-public-warning",
        "event": "cellbroadcast_attention",
    },
    "critical": {
        "soundFile": ATTENTION_TONE_FILE,
        "reservedUse": "official-cell-broadcast-public-warning",
        "event": "cellbroadcast_critical_attention",
        "vibrationProfile": "sos",
        "vibrationPattern": VIBRATION_PROFILES["sos"]["vibrationPattern"],
        "vibrationRepeat": VIBRATION_PROFILES["sos"]["vibrationRepeat"],
    },
}

# FCC Part 10 WEA regions, including Puerto Rico, the US Virgin Islands, and
# American Samoa.
WEA_MCCS = {
    "310", "311", "312", "313", "314", "315", "316", "330", "332", "544",
}

# Countries where SailfishOS is officially sold at the time this catalog was
# added: EU, UK, Norway, and Switzerland. ETSI TS 102 900 requires a dedicated
# public-warning alerting indication. These MCCs use the standard profile until
# a national policy requires different attention behaviour.
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

# These category identifiers have explicit highest-severity semantics. Do not
# infer critical attention from a mandatory range: test and lower-severity
# categories may also be mandatory in national AOSP overlays.
CRITICAL_CATEGORY_IDS = {
    "presidential",
    "extreme",
    "etws",
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
    parser.add_argument(
        "--regulatory-overrides",
        default=os.path.join(os.path.dirname(__file__), "..", "data",
                             "ausalert-regulatory.json"),
        help="Regulatory override catalog applied after AOSP resources")
    parser.add_argument(
        "--regulatory-vibration-policies",
        default=os.path.join(os.path.dirname(__file__), "..", "data",
                             "regulatory-vibration-policies.json"),
        help="Regulatory vibration policies applied after AOSP resources")
    parser.add_argument(
        "--regulatory-attention-policies",
        default=os.path.join(os.path.dirname(__file__), "..", "data",
                             "regulatory-attention-policies.json"),
        help="Regulatory attention policies applied after AOSP resources")
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
        "integer_arrays": {},
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
            elif child.tag == "integer-array":
                try:
                    values["integer_arrays"][name] = [
                        int((item.text or "").strip())
                        for item in child.findall("item")
                    ]
                except ValueError:
                    continue
            elif child.tag == "bool":
                values["bools"][name] = (child.text or "").strip().lower() == "true"
    return values


def read_strings(path):
    values = {
        "arrays": {},
        "bools": {},
        "integer_arrays": {},
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
        "integer_arrays": dict(base["integer_arrays"]),
        "strings": dict(base["strings"]),
    }
    merged["arrays"].update(overlay["arrays"])
    merged["bools"].update(overlay["bools"])
    merged["integer_arrays"].update(overlay["integer_arrays"])
    merged["strings"].update(overlay["strings"])
    return merged


def parse_number(value):
    return int(value, 16) if value.lower().startswith("0x") else int(value)


def parse_vibration_pattern(value):
    try:
        pattern = [int(part) for part in value.split("|")]
    except ValueError:
        return []
    if len(pattern) < 2 or pattern[0] < 0 or any(duration <= 0 for duration in pattern[1:]):
        return []
    return pattern


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

    result = {
        "from": first,
        "to": last,
        "mandatory": category.get("mandatory", False) or attrs.get("always_on") == "true",
        "apply": category.get("apply", True),
    }
    if attrs.get("override_dnd") == "true":
        result["overrideDnd"] = True
    vibration_pattern = parse_vibration_pattern(attrs.get("vibration", ""))
    if vibration_pattern:
        result["vibrationPattern"] = vibration_pattern
    return result


def normalize_ranges(ranges):
    if not ranges:
        return []
    ranges = sorted(ranges, key=lambda r: (
        r["from"], r["to"], r["mandatory"], r["apply"],
        r.get("overrideDnd", False),
        tuple(r.get("vibrationPattern", []))))
    merged = []
    for item in ranges:
        if (merged and item["mandatory"] == merged[-1]["mandatory"]
                and item["apply"] == merged[-1]["apply"]
                and item.get("overrideDnd") == merged[-1].get("overrideDnd")
                and item.get("vibrationPattern") == merged[-1].get("vibrationPattern")
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
    if mcc in WEA_MCCS or mcc in EUALERT_MCCS:
        return "standard"
    return ""


def is_standard_extreme_attention(plmn, config, category_id):
    if category_id != "extreme":
        return False

    return (plmn[:3] in WEA_MCCS
            or plmn[:3] in EUALERT_MCCS
            or alert_system_name(config).upper() == "FR-ALERT")


def standard_extreme_requires_critical_attention(config, category_id, ranges):
    if category_id != "extreme":
        return False

    # FR-Alert Level 2 deliberately follows normal ringtone and Silent-mode
    # volume policy. Other WEA or EU-Alert country configurations can
    # explicitly request DND override; the critical event is the only attention
    # path which can also remain audible when ringtone volume is zero in Silent
    # mode.
    if alert_system_name(config).upper() == "FR-ALERT":
        return False
    return any(item.get("overrideDnd", False) for item in ranges)


def build_entry(plmn, config, default_names, base_vibration_pattern):
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
        for key in ("alertLevel", "attentionPolicy", "display",
                    "userConfigurable", "settingsVisible", "vibrationPattern",
                    "vibrationRepeat"):
            if key in category:
                category_entry[key] = category[key]
        standard_extreme = is_standard_extreme_attention(
            plmn, config, category["id"])
        critical_extreme = (
            standard_extreme
            and standard_extreme_requires_critical_attention(
                config, category["id"], ranges))
        if (category["id"] in CRITICAL_CATEGORY_IDS
                and not standard_extreme):
            category_entry["alertLevel"] = "critical"
            category_entry["attentionPolicy"] = "silent-dnd-override"
            category_entry["attentionProfile"] = "critical"
        elif category["id"] in ATTENTION_CATEGORY_IDS:
            if critical_extreme:
                category_entry["attentionPolicy"] = "silent-dnd-override"
                category_entry["attentionProfile"] = "critical"
            elif standard_extreme:
                category_entry["attentionProfile"] = "standard"
            elif attention_profile:
                category_entry["attentionProfile"] = attention_profile
        categories.append(category_entry)

    entry = {
        "plmn": plmn,
        "alertSystem": alert_system_name(config),
        "categories": categories,
    }
    if attention_profile:
        entry["defaultAttentionProfile"] = attention_profile
    vibration_pattern = config["integer_arrays"].get("default_vibration_pattern", [])
    if plmn and vibration_pattern and vibration_pattern != base_vibration_pattern:
        entry["defaultVibrationPattern"] = vibration_pattern
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


def read_regulatory_overrides(path):
    """Read separately maintained national regulatory policy data."""
    with open(path) as overrides_file:
        overrides = json.load(overrides_file)
    if not isinstance(overrides.get("entries"), dict):
        raise ValueError("Regulatory overrides must contain an entries object")
    if not isinstance(overrides.get("sources"), dict):
        raise ValueError("Regulatory overrides must contain a sources object")
    return overrides


def apply_regulatory_overrides(entries, overrides):
    """Apply MCC/PLMN regulatory policy after AOSP resource generation."""
    for plmn, entry in overrides["entries"].items():
        entry = dict(entry)
        entry["plmn"] = plmn
        entries[plmn] = entry
        if len(plmn) == 3:
            for generated_plmn in list(entries):
                if generated_plmn != plmn and generated_plmn.startswith(plmn):
                    del entries[generated_plmn]


def apply_regulatory_vibration_policies(entries, policies, vibration_profiles):
    """Merge regulatory vibration policy into matching MCC/PLMN entries."""
    for plmn, policy in policies["entries"].items():
        if not isinstance(policy, dict):
            raise ValueError("Vibration policy entries must be objects")
        unknown_fields = set(policy) - {
            "defaultVibrationProfile", "vibrationSourceRef",
        }
        if unknown_fields:
            raise ValueError("Unknown vibration policy fields for %s: %s"
                             % (plmn, ", ".join(sorted(unknown_fields))))
        profile_id = policy.get("defaultVibrationProfile", "")
        if profile_id not in vibration_profiles:
            raise ValueError("Unknown vibration profile %s for %s"
                             % (profile_id, plmn))
        source_ref = policy.get("vibrationSourceRef", "")
        if source_ref not in policies["sources"]:
            raise ValueError("Unknown vibration source %s for %s"
                             % (source_ref, plmn))

        matched = False
        for generated_plmn, entry in entries.items():
            if (generated_plmn == plmn
                    or (len(plmn) == 3 and generated_plmn.startswith(plmn))):
                entry.update(policy)
                matched = True
        if not matched:
            raise ValueError("Vibration policy %s matches no catalog entry" % plmn)


def apply_regulatory_attention_policies(entries, policies, attention_profiles):
    """Merge regulatory category attention policy into matching entries."""
    for plmn, policy in policies["entries"].items():
        if not isinstance(policy, dict):
            raise ValueError("Attention policy entries must be objects")
        unknown_fields = set(policy) - {"categories"}
        if unknown_fields:
            raise ValueError("Unknown attention policy fields for %s: %s"
                             % (plmn, ", ".join(sorted(unknown_fields))))
        category_policies = policy.get("categories")
        if not isinstance(category_policies, dict):
            raise ValueError("Attention policy %s must contain categories" % plmn)

        for category_id, category_policy in category_policies.items():
            if not isinstance(category_policy, dict):
                raise ValueError("Attention category policies must be objects")
            unknown_fields = set(category_policy) - {
                "attentionProfile", "attentionPolicy", "sourceRef",
            }
            if unknown_fields:
                raise ValueError("Unknown attention category fields for %s/%s: %s"
                                 % (plmn, category_id,
                                    ", ".join(sorted(unknown_fields))))
            profile_id = category_policy.get("attentionProfile", "")
            if profile_id not in attention_profiles:
                raise ValueError("Unknown attention profile %s for %s/%s"
                                 % (profile_id, plmn, category_id))
            source_ref = category_policy.get("sourceRef", "")
            if source_ref and source_ref not in policies["sources"]:
                raise ValueError("Unknown attention source %s for %s/%s"
                                 % (source_ref, plmn, category_id))

            matched = False
            for generated_plmn, entry in entries.items():
                if (generated_plmn != plmn
                        and not (len(plmn) == 3
                                 and generated_plmn.startswith(plmn))):
                    continue
                for category in entry.get("categories", []):
                    if category.get("id") == category_id:
                        category.update(category_policy)
                        matched = True
            if not matched:
                raise ValueError("Attention policy %s/%s matches no category"
                                 % (plmn, category_id))


def discard_redundant_vibration_overrides(entries, attention_profiles,
                                          vibration_profiles):
    """Drop vibration arrays which do not change the effective pattern."""
    for entry in entries.values():
        entry_pattern = entry.get("defaultVibrationPattern")
        vibration_profile = vibration_profiles.get(
            entry.get("defaultVibrationProfile"), {})
        vibration_profile_pattern = vibration_profile.get("vibrationPattern")

        # A named entry policy has higher precedence than an AOSP numeric
        # default. Once present, the numeric value can no longer affect any
        # category and should not be preserved as a misleading override.
        if vibration_profile_pattern and entry_pattern:
            del entry["defaultVibrationPattern"]
            entry_pattern = None

        for category in entry.get("categories", []):
            attention_profile = attention_profiles.get(
                category.get("attentionProfile"), {})
            effective_pattern = attention_profile.get("vibrationPattern")
            if not effective_pattern:
                attention_vibration_profile = vibration_profiles.get(
                    attention_profile.get("vibrationProfile"), {})
                effective_pattern = attention_vibration_profile.get(
                    "vibrationPattern")
            if entry_pattern:
                effective_pattern = entry_pattern
            if vibration_profile_pattern:
                effective_pattern = vibration_profile_pattern

            category_pattern = category.get("vibrationPattern")
            if category_pattern:
                if effective_pattern and category_pattern == effective_pattern:
                    del category["vibrationPattern"]
                else:
                    effective_pattern = category_pattern
            if not effective_pattern:
                continue

            for item in category.get("ranges", []):
                if item.get("vibrationPattern") == effective_pattern:
                    del item["vibrationPattern"]


def merge_regulatory_sources(*regulatory_data):
    sources = {}
    for data in regulatory_data:
        for source_id, source in data["sources"].items():
            if source_id in sources and sources[source_id] != source:
                raise ValueError("Conflicting regulatory source %s" % source_id)
            sources[source_id] = source
    return sources


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
        "default": build_entry("", base, default_names,
                               base["integer_arrays"].get("default_vibration_pattern", [])),
    }

    for mcc in sorted(mcc_configs):
        merged = merge_config(base, mcc_configs[mcc])
        entries[mcc] = build_entry(
            mcc, merged, default_names,
            base["integer_arrays"].get("default_vibration_pattern", []))

    for mcc in sorted(WEA_MCCS | EUALERT_MCCS):
        if mcc not in entries:
            entries[mcc] = build_entry(
                mcc, base, default_names,
                base["integer_arrays"].get("default_vibration_pattern", []))

    for mcc, mnc in sorted(mccmnc_configs):
        merged = merge_config(base, mcc_configs.get(mcc, {
            "arrays": {}, "bools": {}, "integer_arrays": {}, "strings": {}}))
        merged = merge_config(merged, mccmnc_configs[(mcc, mnc)])
        entries[mcc + mnc] = build_entry(
            mcc + mnc, merged, default_names,
            base["integer_arrays"].get("default_vibration_pattern", []))

    try:
        regulatory_overrides = read_regulatory_overrides(args.regulatory_overrides)
        attention_policies = read_regulatory_overrides(
            args.regulatory_attention_policies)
        vibration_policies = read_regulatory_overrides(
            args.regulatory_vibration_policies)
        regulatory_sources = merge_regulatory_sources(
            regulatory_overrides, attention_policies, vibration_policies)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        sys.stderr.write("Unable to read regulatory policy: %s\n" % error)
        return 1

    # Apply policy last. An MCC policy deliberately replaces every AOSP
    # PLMN-specific entry below it, because regulator requirements govern all
    # Australian operators rather than a selected carrier resource overlay.
    apply_regulatory_overrides(entries, regulatory_overrides)
    try:
        apply_regulatory_attention_policies(
            entries, attention_policies, ATTENTION_PROFILES)
        apply_regulatory_vibration_policies(
            entries, vibration_policies, VIBRATION_PROFILES)
    except ValueError as error:
        sys.stderr.write("Unable to apply regulatory policy: %s\n" % error)
        return 1
    discard_redundant_vibration_overrides(
        entries, ATTENTION_PROFILES, VIBRATION_PROFILES)

    catalog = {
        "version": 1,
        "attentionProfiles": ATTENTION_PROFILES,
        "vibrationProfiles": VIBRATION_PROFILES,
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
        "regulatorySources": regulatory_sources,
        "entries": entries,
    }

    with open(args.output, "w") as output:
        json.dump(catalog, output, indent=2, sort_keys=True)
        output.write("\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
