# Australian Cell Broadcast policy

The `cell-broadcast-provider-info-ausalert` subpackage supplies the AusAlert
MCC 505 overlay. Its regulatory source and clauses are recorded in
`data/overrides/ausalert-regulatory.json`.

The policy preserves mandatory Critical alerts and hidden channel 4400,
optional Priority alerts, and the national exercise/test defaults. Critical
attention uses the shared critical profile; Priority uses standard attention
with one SOS vibration cycle. All other applicable categories retain standard
profile-controlled attention.

The main provider package recommends this subpackage at the matching version
and release, so it is installed by default when weak dependencies are enabled.
It can be removed without removing the base catalogue.

## Installation

The noarch RPM installs the overlay as
`/usr/share/cell-broadcast-provider-info/overrides.d/50-ausalert.json`.
It requires the shared base catalogue and an overlay-capable Voicecall build.
Install the coordinated runtime/UI updates before testing the policy, then
restart `voicecall-manager` so it reloads the installed catalogue. Removal
restores the base policy after the same restart.

## Validation

Run `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`.
The runtime repository tests overlay precedence and malformed-input handling
using synthetic policies; this repository tests the national requirements.

This subpackage is built from the main `cell-broadcast-provider-info` source
package alongside the base catalogue.
