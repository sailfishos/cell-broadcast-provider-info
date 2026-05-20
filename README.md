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
- Roaming network hints from the source data.
- Attention profile IDs for official public-warning categories.

3GPP TS 23.041 and TS 22.268 are used as normative cross-checks for Cell
Broadcast topic handling. National regulator sources should override AOSP
country-specific data when they conflict.

## Attention Profiles

The catalog currently exposes these public-warning attention profiles:

- `wea` for US WEA MCCs `310`-`316`.
- `eualert` for EU-Alert regions where Sailfish OS is officially sold, namely
  EU MCCs plus UK `234,235`, Norway `242`, and Switzerland `228`.

Both profiles currently point at the same private `853 Hz + 960 Hz` two-tone
asset. They remain separate metadata profiles so runtime code can keep WEA and
EU-Alert policy selection separate, and so country-specific EU-Alert overrides
can be added later without changing WEA behavior.

## Regenerating

Regenerate the catalog from a pinned AOSP CellBroadcastReceiver checkout:

```
tools/generate-cellbroadcast-catalog.py \
    --aosp-dir /path/to/packages/apps/CellBroadcastReceiver \
    --commit <aosp-commit-sha> \
    --output data/channels.json
```

The attention-tone asset is generated during the qmake build. To generate it
manually:

```
tools/generate-cellbroadcast-attention-tones.py --output-dir attention-tones
```

The tone generator uses `ffmpeg` when available, falling back to
`gst-launch-1.0`.
