# Two-bone playback: source contract and next bounded recipe

No GSC has been deployed or compiled for this rig. This document binds a future
experiment to real retail references. Hashes are retained in
[validation-2026-10-12.json](validation-2026-10-12.json). A native-table name is
not proof of its argument types, event semantics or custom preload behavior.

## Observed retail route

Retained retail dump pin `1dd48a78e55ef9c99519fc5221a206168ce2e98a`:

| File and lines | Observed behavior | Scope |
| --- | --- | --- |
| `scripts/mp/animatedmodels.gsc:16-19,37-38` | `precachempanim` consumes names, then `scriptmodelplayanim` plays the selected animation | Existing string-based prop route; no custom rig proof |
| `scripts/cp/maps/cp_zmb/cp_zmb_ufo.gsc:215,218` | `scriptmodelplayanim` plays UFO breakaway then idle | Same method is used in Zombies CP |
| `scripts/engine/utility.gsc:4040-4045` | `getnotetracktimes` and `getanimlength` calculate note time from an animation reference | Data query, not event delivery; custom-route argument type still unbound |
| `scripts/anim/notetracks_mp.gsc:86-103,130-159` | `setanimstate` route waits for an event carrying note payload | ASM-oriented consumer, not proof that script models send that event |

The local IW7 native-name table lists `precachempanim` 0x184,
`scriptmodelplayanim` 0x8293, `scriptmodelclearanim` 0x8292,
`getnotetracktimes` 0x0BB and `getanimlength` 0x07A. These identifiers corroborate
names, not permission or instructions to call native addresses.

The first proposed visual route is a precached `script_model`, following the
existing Beacon actor lifecycle. A generic `setanim` call is not assumed
sufficient. No custom animtree is presumed mandatory for this prop route; add
animtree/ASM only if a verified engine route requires it. The retail call shape is:

```gsc
precachempanim( "paris_original_probe_bend" );
// After approved model/animation registries, preload and actor lifecycle:
actor scriptmodelplayanim( "paris_original_probe_bend" );
```

This is a proposed call shape, not a deployable fixture. The coordinator must
establish the exact precache phase and animation registry for the custom name.
Pinned `NetConstStringType` defines XMODEL=0 (`mdl`), ANIM=16 (`anm`), ANIMCLASS=17
(`acl`); enum values do not determine required asset name/scope/contents. Do not
invent a netconststrings asset.

## Ordered next recipe, each execution separately authorized

1. **Bind retained native model proof.** Have the model workstream bind the
   October 7 XMB/XSB pairs and writer receipt to the recovered writer/ABI/input
   hashes. Read both files completely. The one-bone Beacon cannot demonstrate
   the child bend. Rebuild only for changed source/inputs or missing provenance;
   use the recovered translation unit, actual headers and
   `/std:c++20 /EHsc /MD /W4 /WX /bigobj`, with current reviewed ownership and
   admission, not the historical wrapper.
2. **Close model/material FF dependencies.** Qualify each model/surface through
   a distinct FF build/verify/dump/readback. Resolve the existing material or
   review a new original material profile with its owner. Recheck bones, parent,
   tags, positive global binds, eight positions, six triangles, 48 blend bytes,
   zero rigid lists and both weight profiles after FF. Keep model native/FF,
   animation FF and material results separate. A default model is not a pass.
3. **Prepare the combined fixture.** Use a distinct zone identity and exact
   inventory: two models, their two surfaces, one proven XAnim, approved material
   dependencies, required model/animation netconststrings and fixture script as
   actually established. The two-row animation FF is not this combined pack;
   preserve its measured bytes. Review compile/preload and registry binding
   before launch. No blanket map/asset import.
4. **Observe the model.** After current resource/instance admission, use a
   retained private dedicated and free base client, full quality, fresh actual
   engine godmode and inactivity=0, sv_cheats=0. Preserve Main and occupied games.
   Start with a static copy and clearly labeled first/second animated copies at
   fixed origins. Face the YZ ribbon from negative X, not edge-on. Confirm
   silhouette/material/bind before attributing absent motion to the API.
5. **Measure deformation/cadence.** Compare neutral and both bends with CPU
   coordinates in the clip-rig report. Root-weighted points stay still; the
   child pivot is Z=8. Resolve which profile matches the engine and measure
   repeated cycles instead of assuming frequency 1 means one second. Capture
   native frames, actor/model/clip identity and camera/origin/angles. CPU error
   is reference math, not a pixel tolerance. A bone tag alone cannot establish
   vertex weight interpretation.
6. **Bind the real note consumer separately.** Establish the actual script-model
   event path for `probe_contact`, then measure timing/count per observed cycle.
   Never synthesize a timer or `notify` and call it native delivery. Without a
   verified prop event consumer, record visual playback separately and bind a
   real animtree/ASM route before note acceptance. No AI/damage callback yet.

The future client + dedicated proposal remains 12 + 4 GiB physical, with
independent commit headroom and current scheduler estimates rechecked before
admission. This is not a reservation or authorization. Source/FF and game work
remain sequential. No lease was created for this source tranche.

## Acceptance boundaries

Missing model/material/animation registry or wrong skeleton is a dependency
failure, not proof that custom XAnim cannot work. Default mesh, unresolved FF
row, culling-only disappearance, absent protected-client proof or occupied owner
game prevents visual acceptance. Retain fresh diagnostics for failures.

Offline success or a local rendered clip does not establish remote clients,
late join, map rotation, AI pursuit, attack/damage windows or owner acceptance.
Those remain later bounded experiments after the static rig proof.
