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

`data/ausalert-regulatory.json` is a separately maintained Australian
regulatory policy source. The generator applies it after every AOSP MCC and
PLMN resource overlay, so its MCC `505` policy also wins over generated
`505xx` carrier entries. Its source, edition, and applicable AS/CA clause are
copied to `regulatorySources`, `sourceRef`, and `clause` in the generated
catalog. The original AOSP `source.commit` remains the pinned source commit.

Catalog categories may add the following optional fields without changing the
base schema: `title`, `alertLevel`, `userConfigurable`,
`settingsVisible`, `display`, `attentionPolicy`, and `sourceRef`. Ranges add
`languageRole`. DBGF channel 4400 is mandatory for all MCC 505 equipment.

3GPP TS 23.041 and TS 22.268 are used as normative cross-checks for Cell
Broadcast topic handling. National regulator sources should override AOSP
country-specific data when they conflict.

## Attention Profiles

The catalog currently exposes these public-warning attention profiles:

- `standard` for normal public-warning attention, including WEA and EU-Alert
  regions.
- `critical` for explicitly highest-severity public warnings. It uses the
  `cellbroadcast_critical_attention` event so device policy can bypass Silent
  and Do Not Disturb.

Both profiles currently point at the same private `853 Hz + 960 Hz` two-tone
asset and select different attention events.

The generic `critical` profile is assigned only to categories with explicit
highest-severity semantics: presidential/national alerts, extreme threats,
real ETWS warnings, and national regulatory categories such as Critical
AusAlert. It is not inferred from `mandatory`, because mandatory ranges also
include some test and lower-severity categories. Priority AusAlert and all
test/exercise categories retain normal profile-controlled attention.

## Regenerating

Regenerate the catalog from a pinned AOSP CellBroadcastReceiver checkout:

```
tools/generate-cellbroadcast-catalog.py \
    --aosp-dir /path/to/packages/apps/CellBroadcastReceiver \
    --commit <aosp-commit-sha> \
    --output data/channels.json
```

The default `--regulatory-overrides` value is
`data/ausalert-regulatory.json`; supply that option to use an alternate
regulatory source for review or testing.

The attention-tone asset is generated during package installation. To generate
it manually:

```
tools/generate-cellbroadcast-attention-tones.py --output-dir attention-tones
```

The tone generator uses `ffmpeg` when available, falling back to
`gst-launch-1.0`.
