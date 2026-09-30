# FI-Alert Cell Broadcast policy

The `cell-broadcast-provider-info-fi-alert` subpackage supplies the MCC 244
overlay from `data/overrides/fi-alert-regulatory.json`, derived from the V6
intake dated 2026-08-06. The data uses the repository's Apache 2.0 license.
It applies to all Finnish serving
networks, including inbound roaming, and replaces the inherited generic
category list. Existing identifiers are retained where the categories match,
so saved category preferences remain applicable.

The overlay selects WEA haptics, single 10.5-second standard warnings,
maximum-volume critical attention, visual-only silent severe alerts, and the
SMS profile for public authority announcements. Test and exercise categories
are disabled by default. Mandatory warning and geofencing channels stay
subscribed when optional alerts are disabled.

The explicit visual-only instruction takes precedence over the contradictory
generic vibration row. Geofencing triggers remain hidden protocol traffic;
the intake's display/audio cells for that channel need confirmation. Supplied
English, Finnish and Swedish text is retained, including the source wording;
unprovided translations fall back to English. No language filter is applied,
and each received language remains accessible as its own alert. These choices
need confirmation against the final compliance specification and device tests.

## Installation

The noarch RPM installs the overlay as
`/usr/share/cell-broadcast-provider-info/overrides.d/50-fi-alert.json`.
It requires the shared base catalogue and an overlay-capable Voicecall build.
The main provider package recommends this subpackage at the matching version
and release, so it is installed by default when weak dependencies are enabled.
It can be removed without removing the base catalogue.
Install the coordinated runtime/UI updates before testing the policy, then
restart `voicecall-manager` so it reloads the installed catalogue. Removal
restores the base policy after the same restart.

## Validation

Run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`.
The runtime repository tests overlay precedence and malformed-input handling
using synthetic policies; this repository tests the national requirements.

This subpackage is built from the main `cell-broadcast-provider-info` source
package alongside the base catalogue.
