# T7 animated components: bounded source preflight and conversion proposals

This is a separate source-only path from `../readback.py` and its resident static
one-bone profile. It consumes **already decoded field/array snapshots**, never a
T7 pointer, process, fastfile, XPAK, XMB, XSB or XAB. Original fixtures are the only
inputs qualified here. No native reader, real donor conversion, export, renderer,
animation playback or engine compatibility has been established.

Every successful report keeps `ready`, `real_t7_provenance`,
`complete_native_reader` and `engine_verified` false. A successful component
check is not a complete model/clip check. The combined-rig refusals for
`XModel.lodInfo[0].surfs` at offset 272 and `XSurface.blendVertsBuffer` at offset
88 remain unchanged; this folder neither imports nor relaxes that reader.

## Reproduced conversion losses

All references below are relative to the retained ZoneTool source at
`fab935826c898806855376662a8a03317b3ad8f1`. `source-contract.json` records the exact
raw source-file SHA-256 values read during this work. No upstream refresh,
native binary read, game-asset read or native build was performed.

| Finding | Exact source reference | Original minimal reproduction and refusal |
| --- | --- | --- |
| Weights move without their vertices | `src/zonetool/zonetool/t7/converter/iw7/assets/xmodel_mesh.cpp:15-68,126-148,150-179` | Three vertices with influence classes `[2,1,2]`: vertices stay `[0,1,2]`, blend rows become `[1,0,2]`. `weight_vertex_order_loss` refuses this input. |
| Four counters narrow before copying | `src/zonetool/zonetool/t7/converter/iw7/assets/xanim.cpp:21-26` | Each of `dataByteCount`, `dataShortCount`, `dataIntCount`, `randomDataIntCount` set to 65536 with a correctly sized original array becomes zero under the unsigned-short cast. `counter_uint16_loss` refuses before array traversal. |
| Bone categories narrow to a byte | `.../xanim.cpp:43-47` | A count of 256 becomes zero if assertions are disabled. `bone_counter_uint8_loss` refuses independently of build configuration. |
| Channels/metadata are omitted | T7 `structs.hpp:1165-1213`; `.../xanim.cpp:28-39,49-65,123-135` | A one-byte `extraChannelData` snapshot or `startupNotifyCount=1` is absent from the converter output path. Explicit `extra_channel_loss` or `channel_or_metadata_loss`; other omitted flags/IK/timing fields are also refused. |
| Notification information is lost | T7 `structs.hpp:1064-1070`; `.../xanim.cpp:125-130` | Only `param1` and `time` are copied; type/param2 are lost, startup/shutdown events are not copied. This profile refuses every notify rather than treating the reduced event as equivalent. |
| Random shorts depend on data shorts | `.../xanim.cpp:68-74` | Nonzero random-short count with zero data-short count bypasses allocation/copy. `random_short_copy_loss`. |
| Rotation prefix lacks bounded reads | `.../xanim.cpp:95-119` | Declared frame sample count beyond the supplied stream is refused as `short_prefix_truncated`; excessive sample count is `frame_sample_count`. |
| Native tag-position stride is unresolved | T7 `structs.hpp:1275-1280`; `.../xmodel.cpp:53-59` | The declaration has xyz (12 bytes), while its Load_Stream comment says 16 bytes per tag. Any position layout other than the explicitly original declaration-shaped fixture is refused. No native stride is guessed. |
| Part bits lose their final four words | T7 `structs.hpp:1215`; `.../xmodel_mesh.cpp:198-201` | The permutation proposal refuses nonzero bytes 32-47. It does not reinterpret dropped bits. |

The mesh ordering defect is **conditional**: source search under the retained
`src/zonetool/zonetool/t7` found the declarations and H1/IW7 conversion loops,
but no proof that T7 requires influence-sorted vertices. The original input is
admissible to the decoded source-row parser, but deliberately inadmissible to
the current converter preflight. It is not evidence that a real BO3 donor uses
that ordering, nor proof that the real format permits it. A real donor
observation remains outstanding.

Run the small reproductions from the repository root:

```powershell
python tools-source/asset-bridge/t7-iw7/animated/demonstrate_losses.py
python -m unittest discover -s tools-source/asset-bridge/t7-iw7/animated -p 'test_*.py' -v
```

## Component contracts

`preflight_skeleton` accepts 2-255 bones, one root, no cosmetics, resolved unique
ASCII names, backward parent distances, exact arrays and finite transforms.
Half-float tag quaternions must meet the original near-unit policy (squared-norm
error at most .002), then use truncation of `value * 32767`, matching
`src/zonetool/game/shared.cpp:302-307`. It never silently normalizes or clamps.
The baseMat transWeight relation is an explicit positive-bind fixture policy.
This component does **not** establish general hierarchy/baseMat equivalence;
the independent existing CPU oracle checks that relation only for the original
fixture during tests. Native stride and general bind semantics remain unproven.

`decode_stream_weights` reads exact little-endian `GfxStreamWeight` rows
(`structs.hpp:1303-1314`): four bytes followed by four unsigned-short IDs.
The conservative policy requires positive contiguous influences summing to 255,
unique raw bone IDs in range and zero unused IDs. These are profile restrictions,
not proven universal T7 rules. `preflight_weights` additionally refuses any
decreasing influence class because the pinned converter groups the rows.
One-to-four blend layouts are checked against an independent `read_blend.py`
and a literal golden byte string. The reader returns stored weights and the
residual; **it does not decide which bone receives each stored weight**.
The existing skin oracle checks both first/second hypotheses on an original
translated hinge; neither result qualifies the IW7 engine convention.

`preflight_clip` requires every declared field, including absent-feature flags.
Unknown or omitted fields are rejected. Counter checks precede traversal, the
aggregate byte budget is 4 MiB, and all lengths are exact. This pilot requires
no translation categories, no delta, no notifications, no extra/IK/mask channels,
zero discarded timing metadata and no opaque int/random-byte streams. Bone
category partitions and names are checked against the supplied skeleton names.
The uint16-vs-byte index element width follows `numframes > 255`.

The short-prefix interpreter follows only the two animated and two static
rotation categories in the pinned converter. It bounds every access, decodes
binary16 samples and refuses any trailing short words. For frames above 255 it
bounds the extra raw ushort prefix word, without inventing its schedule meaning.
`dataByte` and `indices` remain uninterpreted schedule bytes; their range/order,
key timing, bone-channel order and sampling semantics are **not verified**.
Thus even a fully consumed short prefix reports `clip_semantics_complete=false`
and `key_schedule_verified=false`. No faithful complete clip is claimed.

Snapshot adapters do not exist yet. In particular, resolved string names do not
qualify source string-table IDs or their narrowing, and an empty array does not
prove a corresponding native pointer was null. This is not a memory safety
gate for native pointer dereferencing.

## Separate, unapplied native proposals

`proposed-mesh-reorder.patch` targets only the pinned T7-to-IW7 mesh converter.
It retains each vertex's original index in the four existing weight groups,
then applies the same stable permutation to **the entire converted
GfxPackedVertex** (xyz/color/UV/normal/tangent/selfVisibility together). It
allocates new triangles and remaps all three indices through the inverse
permutation, preserving winding and source arrays. Blend rows already use
that group order. No attribute is moved independently of the others.

Actual permutations are restricted to a shared resident buffer, exactly the
skinned flag, no rigid-list pointer/count (thus no list collision data),
surface-local triangle indices and zero discarded part-bit words on both mesh
and surface. Any of these unsupported cases returns an error instead of
performing the permutation. Already grouped inputs retain their existing path.
This patch is **only an ordering correction**: it does not validate source
buffer extents, source weight normalization, string resolution, model bone
binding or all other converter assumptions. The decoded preflight remains
separate and is not secretly wired into native conversion.

`reorder_proposal.py` proves the permutation on original source-shaped data by
moving every 16-byte vertex-attribute record, every 12-byte position record,
every 12-byte weight record and triangle index together. Tests cover every
triangle corner across all 64 three-vertex class sequences (1-4 influences),
plus fixed expected bytes for the `[2,1,2]` example. This is an independent
algorithm/identity proof, **not execution of the proposed C++ patch**.

`proposed-xanim-loss-guards.patch` refuses the known counter losses **before
any cast**, makes byte-category guards effective without assertions, and refuses
discarded metadata/channels/delta and omitted random shorts. Its dump wrapper
checks a null conversion result. It does not repair overflow after corruption,
implement unsupported features, bound the native rotation cursor or establish
faithful clip conversion. Those remain separate follow-up work.

Both proposals passed read-only `git apply --check` against the retained pin.
They are saved solely for attribution and independent review: neither was
applied to shared converter files, compiled, exported or loaded in a game.
The coordinating chat owns integration, PR/CI/merge and subsequent admission.

## Validation and next action

See [VALIDATION.md](VALIDATION.md) for exact checks and remaining gates.
The next conversion step is to assign review of these two native proposals,
then add bounded source-buffer/prefix checks and obtain an admitted real donor
snapshot with measured ordering, position stride, weights and clip schedule.
Until then, the current rigid reader and both combined-rig refusals remain
the applicable gates for native output.
