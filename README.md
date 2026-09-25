# Cell Broadcast Provider Info

This package contains Sailfish OS provider metadata for GSM/oFono Cell
Broadcast public-warning handling. It is data-only: consumers use it to resolve
Cell Broadcast topic subscriptions, public-warning categories, and private
attention-tone profiles without baking country/operator tables into runtime
packages.

## Installed Files

The generated catalog is installed as:

```
/usr/share/cell-broadcast-provider-info/channels.json
```

The generated Cell Broadcast attention-tone asset is installed as:

```
/usr/share/cell-broadcast-provider-info/attention-tones/cellbroadcast-attention-853-960.ogg
```

This Ogg Vorbis file is algorithmically generated from public-warning
requirements and is reserved for official Cell Broadcast emergency-alert
handling. It is intentionally not installed as a ringtone, ambience, alarm, or
generic notification sound.

The package also installs `cell-broadcast-provider-info.pc` for consumers that
need to find the data directory at build time.

## Catalog

`data/channels.json` is generated from AOSP CellBroadcastReceiver resources and
records the exact source commit in the JSON metadata. The catalog contains:

- PLMN/MCC entries.
- Mandatory and optional public-warning category topic ranges.
- Default enabled state for optional categories where available.
- Attention profile IDs for official public-warning categories.
- Named vibration profiles independently referenced by attention and national
  policy.
- Default and country-specific public-warning vibration patterns.

Optional national policies are installed by separate packages into
`/usr/share/cell-broadcast-provider-info/overrides.d/`. The base catalogue does
not embed those overlays or depend on private policy repositories. See
[Runtime overlays](#runtime-overlays) below.

`data/regulatory-vibration-policies.json` supplies independent national
vibration policy. An MCC policy is merged into the MCC entry and all of its
generated operator entries. The US MCCs select the `wea` vibration profile
under 47 CFR 10.530 without changing a category's sound event or Do Not
Disturb policy.

`data/regulatory-attention-policies.json` supplies national category-level
attention policy. It can promote a lower alert level to the `critical`
attention profile without changing the category's `alertLevel`. The UK policy
covers MCCs 234 and 235 because official guidance documents alerts sounding
even when a device is in Silent mode.

Catalog categories may add the following optional fields without changing the
base schema: `title`, `alertLevel`, `userConfigurable`,
`settingsVisible`, `display`, `attentionPolicy`, `sourceRef`,
`vibrationPattern`, and `vibrationRepeat`. Ranges add `languageRole` and may
override `vibrationPattern`; `overrideDnd` retains an explicit AOSP range
requirement. Entries may use `defaultVibrationPattern` for a country or
operator default, or `defaultVibrationProfile` plus
`vibrationSourceRef` for a named regulatory vibration policy.

3GPP TS 23.041 and TS 22.268 are used as normative cross-checks for Cell
Broadcast topic handling. National regulator sources should override AOSP
country-specific data when they conflict.

## Attention Profiles

The catalog currently exposes these public-warning attention profiles:

- `standard` for normal public-warning attention, including WEA and EU-Alert
  regions. WEA Extreme and EU-Alert Level 2 use this profile by default and
  therefore follow the device's normal ringtone and Silent-mode volume.
- `critical` for explicitly highest-severity public warnings. It uses the
  `cellbroadcast_critical_attention` event so device policy can bypass Silent
  and Do Not Disturb. A country configuration can also select it for a lower
  alert level without changing that alert's classification.

Both profiles point at the same private `853 Hz + 960 Hz` two-tone asset and
select different attention events. Their vibration is selected independently:
`standard` leaves vibration to the platform's existing attention haptic,
while `critical` references the repeating `sos` profile. The separate `wea`
profile is selected only by explicit national policy. Category policy can
select a different pattern independently of sound. Explicit attention vibration profiles
also carry resolved fields so consumers built for the earlier catalog remain
compatible.

AOSP inline `vibration=` values are retained on their exact channel ranges.
An AOSP `override_dnd=true` value is likewise retained as `overrideDnd`. On a
WEA Extreme or EU-Alert Level 2 range it promotes the category to critical
attention, because the standard ringtone event cannot remain audible when
Silent mode sets its volume to zero. FR-Alert Level 2 deliberately remains
standard.
Country or operator `default_vibration_pattern` arrays which differ from the
AOSP base are retained on the corresponding entry. Consumers resolve
vibration in this order: range, category, named regulatory entry profile,
numeric entry default, attention profile. A final generator pass discards
numeric category and range overrides when they are identical to the effective
inherited pattern. Regulatory policy can therefore override vibration without
changing sound or Do Not Disturb policy, while no-op arrays are not carried in
the generated catalog.

The generic `critical` profile is assigned to categories with explicit
highest-severity semantics: presidential/national alerts, extreme threats
outside WEA and EU-Alert Level 2, real ETWS warnings, and national regulatory
categories with critical attention policy. It may also be selected by explicit
country attention policy, including `override_dnd` on an otherwise standard
Extreme category. WEA Extreme, FR-Alert Level 2, and all
test/exercise categories retain normal profile-controlled attention. Critical
attention is not inferred from `mandatory`, because mandatory ranges also
include some test and lower-severity categories.

## Regenerating

Regenerate the catalog from a pinned AOSP CellBroadcastReceiver checkout:

```
tools/generate-cellbroadcast-catalog.py \
    --aosp-dir /path/to/packages/apps/CellBroadcastReceiver \
    --commit <aosp-commit-sha> \
    --output data/channels.json
```

No separately packaged national overlays are merged by default. For an explicit
combined catalogue, repeat `--regulatory-overrides PATH`. Do not use private
policy inputs when generating the public base package.
The `--regulatory-attention-policies` and `--regulatory-vibration-policies`
defaults remain `data/regulatory-attention-policies.json` and
`data/regulatory-vibration-policies.json`.

The attention-tone asset is generated during package installation. To generate
it manually:

```
tools/generate-cellbroadcast-attention-tones.py --output-dir attention-tones
```

The tone generator uses `ffmpeg` when available, falling back to
`gst-launch-1.0`.

## Presentation policy

Categories can specify these optional fields. Existing catalogues keep their
previous behaviour when the fields are absent.

| Field | Values / default | Meaning |
| --- | --- | --- |
| `attentionMode` | `warning` (default), `silent`, `sms` | Dedicated warning tone, no sound or haptic, or the user's SMS-tone profile. Explicit silence and SMS policy never fall back to critical attention. |
| `attentionDurationMs` | 0 (default), up to 600000 | Stop feedback after this interval without acknowledging or dismissing the alert. Zero leaves duration to the event. Completion is persisted as silence. |
| `attentionRepeat` | true (default) | Select repeating or single-play warning feedback. SMS follows SMS-tone behaviour. Haptic repetition remains independently controlled by `vibrationRepeat`. |
| `languageFilter` | `device` (default), `none` | Existing device-language selection for additional-language ranges, or presentation of each received language. With `none`, retransmissions still deduplicate, but different languages remain separate queued/history records. |
| `description` | empty | Settings explanation; empty retains the channel-number description. |
| `translations` | empty object | Language-tag keyed objects containing `name`, `title`, and/or `description`. Keys are lowercase BCP-47-style tags. The UI tries the full locale, then the language, then the base string. |

The mode, timing and translation metadata travel with persisted alerts, so
history and resumed presentation use the same policy. Language tags are not
truncated to two characters.


## Runtime overlays

Independent data packages may install JSON supplements in
`/usr/share/cell-broadcast-provider-info/overrides.d/`. The loader reads
`channels.json` first and then `*.json` supplements in filename order. It also
uses an adjacent `overrides.d` directory when given a custom catalogue path.
An absent or empty directory preserves the base catalogue.

Each supplement contains `"version": 1`, a `sources` object using the same
provenance format as the generator, and an `entries` object containing complete
MCC or PLMN entries. Shared attention and vibration profiles come from the base
catalogue. Supplements cannot replace those profiles or the default entry.
An MCC entry replaces its base entry and removes earlier carrier entries under
that MCC. Explicit PLMN entries in the same file are applied after the MCC.
Later files take precedence. Identical source definitions may be repeated;
conflicting provenance, invalid entries, unsupported versions and malformed
JSON cause catalogue loading to fail with the offending filename.

Policies using localized presentation and attention controls require
`cell-broadcast-presentation-policy >= 1`. This capability is provided by the
coordinated phone UI package.

Restart `voicecall-manager` after installing, updating or removing supplements;
the process caches its catalogue. Removing a supplement restores the base
policy after restart. Supplements are optional and maintained in independent
repositories so their publication and distribution can be controlled separately.
