# Next original animation: source decision, 2026-10-14

The next useful witness is a changing authored channel that names a bone actually
present in a model whose static display has passed. The existing SDK already
requests native prop playback; the present gap is clip/model compatibility and
unqualified runtime binding. No new animtree, ASM, NCS asset, controller framework
or native ABI is justified by the source evidence alone.

This is a revisable source plan. It creates no clip, model, FF, actor or process.
The actual RigidControl B FF and its producer/recovery receipts remain immutable;
its visible pixels have not been accepted. Ops55 owns that DISPLAY experiment.

## Exact existing pieces

| Piece | Source fact | Consequence |
| --- | --- | --- |
| RigidControl B | FF 888 bytes / `b7b7c4a1147e7e6c5d19cd33ad3a9e9701cda1bc31123ff22caa239d0aa4014a`; six assets, one `tag_origin`, one rigid list, zero blend data, no XAnim | Good data/control baseline after the separately gated visible DISPLAY; not an animated fixture |
| Original bend clip | `fixtures/probe-clip.json`: `tag_origin`, `tag_probe`; only `tag_probe` has keys 0/45/-45/0 degrees about X; no authored translation or delta root motion | It supplies no changing authored channel matching the rigid control's sole bone |
| Legacy combined rig | Original FF 1064 bytes / `ea7ba4be1d5e6f0878431b51e7b9b1ba9d2b10bf74b1ad21da14d55c414e145d`, seven assets including the bend clip; two-bone model/bind/weight CPU data | Existing candidate for child bend, but its own static skin display must pass; visible rigid B does not qualify it |
| SDK core | `sdk_original_rig_probe.gsc`, 4866 bytes / `49f7e1aa336bb2fdb73e5c36be03c213311ead4555fc9bca0d7b4e69ccdc219b` | Already precaches the bend in ANIMATE before any wait; play=1 issues one request to actors 1/2, keeping actor 0 static |
| Native B78 | Source reads both named XModel/XSurface headers and scene placement; accepts the rigid counts | No qualified DObj layout, tree/palette access, channel remapping or changing vertex observation |

The fixed historical asset names containing `two_bone` do not describe B's actual
one-bone topology. Do not select playback by the name substring.

The old clip remains `paris_original_probe_bend`. Its native XAB is the retained
281-byte `1284b72cf501ae42f77958579610dbcaf692b9153cd06ff66dcf2d1d11eeda7d`
profile. The SDK legacy combined FF records its own 281-byte redump
`a9cd7a3de12b805f5f3e73e5442980a714e39294912f689992f55e3d65576444`.
That is not the standalone animation-zone redump hash hardcoded in
`verify_clip_rig.py`. Keep these separate and use the existing combined-chain
reader/outer receipts for the legacy pack; never relax a hash check to mix them.

## What the playback source proves

The frozen SDK core uses `precachempanim("paris_original_probe_bend")` in init,
then `scriptmodelplayanim("paris_original_probe_bend")` once per animated actor.
It changes its mode to `PLAY_REQUESTED`, does not simulate poses or notetrack
notifications, and deletes its actors on STOP/game end. The existing retail
MP animatedmodels and Spaceland UFO examples corroborate the string prop route.
The SDK scenario binds init before `Scr_LoadLevel`, normal mod FF load and the
pinned Aurora precache-allowed patch; those source facts do not prove connected
client registration or animation consumption.

SDK owner 4cc confirmed that Creator AnimationProbe remains an unconnected,
Plan-only adapter and `skeletal-animation-import/1` remains blocked. Engine
owner 62 confirmed that neither the SDK's forward-declared DObj nor B78 qualifies
the internal simpletree, name-to-XAnim lookup, channel-to-bone map or absent
channel behavior. Do not claim an absent channel is ignored, rejected or
reassigned. Do not infer that two bones are required for every native animation.

The four missing runtime witnesses are:

1. The exact XAnim name is loaded/resolved for the script model.
2. The requested playback tree/time is consumed by that object's DObj, without
   guessing a layout or address.
3. A changing authored channel maps to a bone present in that model.
4. That same object's pose/pixels change, with actor placement and camera
   recorded and the static control preserved.

Pool enumeration or `PLAY_CALL_RETURNED` alone does not satisfy those witnesses.
No custom animtree/NCS dependency has been demonstrated yet. On a concrete
precache/playback failure, preserve its exact name/phase/error first, then ask
the engine owner for that missing primitive instead of adding speculative data.

## Minimum progression if rigid B becomes visible

Prepare a separate closed original root-rotation candidate. Proposed identity:
`paris_original_probe_root_rotate`, one channel named exactly `tag_origin`, four
X-rotation keys at frames 0/10/20/30 with 0/45/-45/0 degrees, 30 frames, framerate
30 and looping. Keep frequency 1 as the existing evidence-bound candidate,
not a measured one-second duration. Author no translation/delta root motion.
Reuse the existing note data only as data; native note delivery is a later gate.

This choice removes the child/weight ambiguity from the first motion witness.
It proposes local root rotation; whether the engine applies that as pose or
world placement remains a runtime observation, not an assertion in this plan.
The rigid models, geometry, UV/material, names, bounds, poses, camera and scale
stay the same. Do not rebuild the two model writers or add a second bone merely
to make the old bend clip's name fit this control.

| Order / owner | Small required change | Reuse / proof before the next stage |
| --- | --- | --- |
| 1. Toolkit source | A distinct fixed one-channel authoring profile and strict independent reader; preserve the old writer/preparer/reader profile | Derive from `prepare_probe.py`, `writer_probe.cpp`, `read_probe.py`, real pinned `XAnimParts` and unchanged production dump body; review channel counts/streams from source before setting any new wire fields |
| 2. Toolkit native, separate GO | Compile and emit only that new clip, then complete independent readback | Existing native-probe/original-job/phase/resource helpers; exact source/executable/input/output pins and actual closure. No model rebuild and no current Run authorization |
| 3. Toolkit FF, separate GO | A separately closed root-rotation zone/variant containing B's four model/surface files plus the new clip, reference material and its own branding rawfile | Existing FF build/verify/dump/transaction helpers, not a new FF builder. Seven typed assets, 79 staged inputs if the original 72 stock binding applies; actual full model/clip readback and restoration, not expected metadata |
| 4. SDK 4cc source | Separate opt-in root-rotation addon preloads the new exact name before its first wait and requests it once after the existing scene is placed | Keep core49f and the explicit stock addon unchanged, keep core mode DISPLAY, retain its static actor 0 and actor cleanup; do not change the core's hardcoded legacy bend call or prematurely open its ANIMATE mode |
| 5. Ops55 / Root, separate GO | Install a distinct strict consumer variant transactionally and observe a protected DISPLAY baseline, then one native playback request | Same actor/model identities and camera; actual fresh engine protection/inactivity proof. Preserve B/Original destinations, source and bank/config; no inferred GPU success or owner acceptance |

The future FF zone and consumer manifest must have distinct identities. The B
source plan remains its six-asset RigidControl contract; no seventh row or clip
is appended to its installed/source FF. The new script/clip hashes and typed
closure roots stay absent until they actually exist and are reviewed. This plan
does not manufacture a compiler receipt, future XAB hash or NativeABI contract.

At playback, record several timestamped cycles and actual placement alongside
native frames. A successful rotation must be distinguished from an entity mover
or root-motion/world placement. Add no script timers that mutate transforms,
pose setters, generated notifications or synthetic collision/attack effects.
Cadence, root-pose behavior and notetrack delivery are separate measurements.

## Existing fallback and creator boundary

If the legacy two-bone mesh separately passes its own static DISPLAY, the
already retained ea7 combined pack and core49f ANIMATE path are the smallest
existing child-bend experiment: keep play=0 while checking loaded identities,
then request playback once. This needs no new clip, tree asset or FF builder.
It tests the original two weight hypotheses and child pivot Z=8; the existing
CPU oracle is the reference, not a measured shader or pixel result. Retained
historical failed outcomes remain failed, even when CPU readback passed.

Prefer the new one-channel witness after a positive rigid B display when the
goal is native playback with the least unqualified skinning. The source API
remains an explicit experimental Plan describing fixed roots/preload/controller
and separate acceptance stages. Keep generic skeletal import, package delivery,
remote clients, AI/events and `ready` blocked until their own evidence exists.

Next source action after Root selects the witness: review the separate fixed
root-channel preparer/reader change with the actual pinned serializer source,
then hand off the exact clip identity to SDK4cc. Until then, no ABI field values,
tree implementation, new FF operator/profile or SDK source are changed here.
