# Animation and AI asset bridge — source tranche, 2026-10-12

This tranche adds a bounded, read-only H1/IW7 ZoneTool `.xab` envelope inspector
and exact-name skeleton binding plan in
[`tools-source/asset-bridge/animation`](../tools-source/asset-bridge/animation/README.md).
It does not import or animate a game asset. No game, native build, Blender,
extraction, decompilation, resource lease or download ran. Main27016, owner client,
banks and configurations were not touched. The parent owns integration/PR/merge
and the heavy-work gate; the owner-admin and disconnect investigations take priority.

## Concrete source findings

ZoneTool owner-fork pin `fab935826c898806855376662a8a03317b3ad8f1`
is retained in `modular-agent-platform/tools/x64-zt-enemy`. The five interfaces
in [source-contract.json](../tools-source/asset-bridge/animation/source-contract.json)
were hash-compared with the older `d5e2117` checkout and match byte-for-byte.
No upstream novelty check was repeated. These are local pinned source facts,
not a fresh compile or engine ABI measurement.

| Boundary | Source evidence | Consequence |
| --- | --- | --- |
| XModel skeleton | `iw7/structs.hpp:1442`, `iw7/assets/xmodel.cpp:49,253,281`: byte `numBones`, byte `numRootBones`, ushort client bones, byte parentList, global baseMat, tag angles/positions | Start with two ordinary bones and zero client bones. Hierarchy/name compatibility alone cannot validate bind matrices or surface blends. Mesh/XSurface writing stays with the ZoneTool owner. |
| H1 versus IW7 XAnim | `h1/structs.hpp:3920`, `iw7/structs.hpp:793`: sizes 0xD8 versus 0x88, bone buckets 12 versus 10, different pointer/count ordering, H1 uint32 versus IW7 uint16 randomDataIntCount | No file rename or struct memcpy conversion. H1 secondary/alternative/blend-shape/IK/scripted-viewmodel information needs explicit handling. H1 comments for flags/boneCount/frequency have stale offsets; field order gives 16/17/52. |
| XAB container | `utils/io/assetmanager.hpp`: ARRAY=8, OFFSET=9, RAW=10, STRING=6; `dump_single` is a one-element ARRAY | Bound counts and alias references before allocation. Preserve exact string identity. Container validity is independent of compressed-track validity. |
| XAnim channels/events | both `assets/xanim.cpp`: `boneCount[9]` channel strings, six packed arrays, index width changes at numframes256, notify entries plus name strings | A skeleton reorder needs a channel map; renaming cannot retarget motion. Event time and event consumer are separate dependencies. No automatic lowercasing or deleting notetracks. |
| Root motion | both `assets/xanim.cpp` dump `deltaPart` translation/quat2/quat blocks with frame indices and raw frames | Validate envelopes now; decode/interpolate delta and reconcile collision/navigation/ASM movement later. A moving skeleton root is not proof of actor displacement. |
| Animation class/tree | `iw7/structs.hpp:5964-6023`, `iw7/zonetool_rhino.hpp:84`: state entries, aliases, aimsets, animTree, scriptable, sound/effect notes | `.atr`, every state/aimset XAnim, scriptable and event mappings form the closure. The retained Rhino dependency walker adds animations/rawfile/FX; it does not itself prove complete sound alias delivery. |
| ASM/BT | `iw7/zone.cpp:596-597` dispatches retained `rhino_anim_class`/`rhino_behavior_tree`; Rhino GSC binds 13 action functions before retail registration | Existing same-engine serializers/callback adaptation are a starting point, not an H1 behavior converter. Script ASM modules and animclass state-machine data are separate dependencies. |
| Weapon animations | `iw7/assets/weapon_anim_package.cpp:311,489,544`: JSON symbolic `WEAP_ANIM_*` names map to XAnimParts; dependency/write loops cover the package | Carry correct IW7 slots and WeaponDef/package/attachment references. H1 numeric slots must not be copied by ordinal. First-person arms, third-person/world models and reload/fire/ADS timing need separate checks. |
| Cross-engine precedent | `t7/converter/iw7/assets/xanim.cpp:35-137` narrows counters, converts half-float rotations to int16 and copies delta | Cross-engine packed samples can require conversion even when structs look related. This is source precedent only; no T7 or H1 clip acceptance follows. The retained H1→IW7 converter directory has XModel support but no XAnim converter file. |

## Recovered evidence and exact gaps

The accepted historical Rhino used `alien_rhino`, `alien_queen`,
`alien_rhino_animclass`, retail BT/ASM, 27 ScriptFiles, 13 function callbacks,
`queen_` events and the actual `cp_final.all` bank. Owner evidence included
pursuit, textures, attack/spawn animations, sounds and FX; see
[ENEMY-PORTING.md](ENEMY-PORTING.md) and
[the dated evidence](deployments/2026-10-02-rhino-functional.json).
This is not a fresh test or acceptance of the later natural-round/multiplayer
variants. Whole `cp_final` cross-loads and forced BT ticks were failed approaches.

Current retained source explains the integration seams:
`src/custom_scripts/cp/experiments/paris_rhino.gsc:62-106` seeds and verifies the
live function table; `paris_rhino.cpp:325-384` extends/verifies `ncs_acl_level`
before DB registration; `:454-471` adapts the two Beast quest callbacks.
Reserved-enemy lifecycle releases the actual slot on death. Every new agent must
rediscover these counts and ownership; copying 13 callbacks is not a generic fix.

The [Doom source inventory](DOOM-SOURCE-CANDIDATES.md) records Slayer's 255 JOINT
nodes/15 skins but no DAE animation channels; Imp's 670 raw bones, 182 FCurves and
no bAction do not establish a walk/attack clip. Driver/constraint rigs need an
explicit deform-bone selection and evaluated bake before conversion. Third-person
Slayer is not a validated FPS hands rig. The SSG mesh/weapon source is not evidence
of fire/reload animations or viewmodel linkage. No source asset or license grant
was added by this tranche.

The dirty retained `doom-source-pipeline/ops/doom-source/` goes further than the
merged inventory: `prepare_skin_fixture.py` defines original 8-vertex/6-triangle
`tag_origin` + `tag_probe` geometry; `SKIN-ABI-CONTRACT.md`, the two-profile
`writer_skin_two_bone.cpp` and independent readers retain first/second weight
hypotheses. They are unbuilt source contracts at the inspected checkpoint.
Reuse them with their owner; do not redo meshes or infer runtime skinning.
`inspect_blender.py` is prepared but has no executed Blender rig/bake evidence.
The animation fixture deliberately uses those same two names.

## Network and multiplayer closure

| Consumer | Needed before an imported enemy/weapon can be accepted |
| --- | --- |
| Dedicated | Correct agent definition row, map-scoped script preload/linkage, live BT/ASM callbacks, model/animation registry, damage/target/death and reserved-slot ownership. Avoid map quest globals accidentally inherited from the donor. |
| Every client | Same model bones, XAnim/state/tree identifiers, relevant animclass net-constant registry, materials/FX/sound dependencies and compatible native behavior where used. Prove remote pose/attack events, not just the server state variable. |
| Delivery | A real mod.ff/nonempty hash and supported download configuration for client assets. The pinned delivery implementation in [CLIENT-COMPATIBILITY.md](CLIENT-COMPATIBILITY.md) does not distribute arbitrary native hooks or EXEs. A custom parser/native component requires a separately compatible client path. |
| Late join/rotation | Reconstruct current pose/state and attached weapon, deliver event semantics without replaying stale damage, maintain registry identity across map loads, release old assets/actors and avoid default substitutions. |

Do not add a new animation network protocol until a measured need exists. First
use an existing actor and existing retail replication with a tiny original asset.
Offline names/hashes, a dedicated startup or synthetic snapshots cannot establish
remote rendering or four-player behavior.

## Initial preflight checkpoint

23 unittest cases pass with only Python stdlib, including both ABIs, all three
delta forms in static/keyed variants, frame255/256 widths, truncation at every
byte for two fixtures, 500 deterministic byte mutations, notetrack bounds,
bad presence/counts/aliases, exact bone mapping and CLI exit/no-write behavior.
Successful mutation parses retain the explicit opaque-track limitation: mutations
inside opaque bytes can be invisible to an envelope inspector.

The executable emits `envelope-pass`, never animation-ready. H1 extensions and
blob aliases are explicit `unsupported` refusals; malformed input is `invalid`.
Root delta values, regular compressed channels, flags semantics, bind/axes,
weights, damage timing and engine behavior remain unvalidated. Actual dump/native
roundtrip checks are pending. These tests were not added to the shared CI workflow
because this lot's ownership is local; the parent can invoke the exact command in
the README during integration. No native assertions, pack or game test executed.

## Native original clip checkpoint, 2026-10-12

The source follow-up and bounded native serializer gate have now passed. The
original `paris_original_probe_bend` authors X rotations 0/+45/-45/0 at frames
0/10/20/30 on `tag_probe`, an identity `tag_origin`, and `probe_contact` at
normalized time 0.5. The real pinned ZoneTool IW7 dump method and assetmanager
compiled with the actual IW7 ABI assertions, then emitted a 281-byte XAB.
Independent readback recovered every key/value, note and exact EOF. Frequency 1
is supported by two bounded retained-header observations but remains a runtime
timing hypothesis. No root motion is authored.

The [writer/readback record](../tools-source/asset-bridge/animation/PROBE-WRITER.md)
and [sanitized hashes/results](../tools-source/asset-bridge/animation/native-validation-2026-10-12.json)
retain both the initial launcher failure and the successful correction. Actual
compile, writer and reader exits were all zero, under one authorized workload
scope with fresh admission and BelowNormal processes. Artifacts plus receipts
are below 0.4 MiB; the reservation was released and no heavy child remained.
39 lightweight tests also pass. This closes native IW7 layout/serializer proof
for this exact original profile only; H1 conversion, FF and runtime gates remain
open. Mesh/material work belongs to the other bridge workstream.

## Next decisive experiment, after the parent's gate

1. Feed the actual native XAB into the smallest existing ZoneTool FF
   parser/serializer roundtrip under a separate parent's GO and admission.
   Preserve import/output hashes and prove the exact keys and note survive.
   Do not rebuild the passed standalone writer without a concrete need.
2. Combine the clip with the other workstream's original two-bone skin fixture
   only after its own native/FF gates. Compare parent list, binds, asymmetric
   weights, rotation samples, event times and root delta separately. Keep root
   motion disabled. No client-bone/IK/blend-shape work.
3. Use a retained test dedicated plus the base client, after confirming the owner
   client is free and fresh engine godmode/inactivity protection. Record two
   known poses, a repeated keyed bend, one named notetrack per cycle and a static
   control. Resolve first/second skin-weight interpretation visibly. Keep actor
   movement/AI disabled in this visual fixture.
4. Only then attach the proven clip to a minimal attack state on an existing
   retail agent. Measure state entry → notetrack → server damage → recovery and
   death/slot cleanup. A remote observer/late join proves replication in a later
   bounded scenario. Imp pursuit/attack and SSG reload are later consumers.

Budgets proposed for the parent: source/preflight input at most4 MiB per file;
tiny original fixture bundle at most1 MiB; generated pack target under8 MiB;
bounded evidence/logs at most16 MiB. Reuse existing compiler/game/runtime files;
any native object/build growth needs a separate measured cap before admission
and counts against the program's remaining10 GiB. Native build admission remains
4 GiB physical/6 GiB commit; sequential full-quality visual test budgets a
12 GiB client plus2–4 GiB dedicated, retaining independent commit headroom.
Only the standalone animation writer reservation above has been executed here;
the later fixture/runtime estimates are not measured maxima. Do not download
another Blender SDK or restore a retired stock lab.

## Integration handoff

Ownership is only this document and `tools-source/asset-bridge/animation/`.
Parent integration should link this tranche in STATE/CHANGELOG/BUGS/VALIDATION/
PLAN as appropriate, run its exact lightweight suite, preserve dirty historical
work and complete the private PR/CI/merge record. No direct runtime deployment
is warranted by this source tool. FF, rendered animation and gameplay gates remain
open; native-layout proof applies only to the exact original IW7 writer above.
