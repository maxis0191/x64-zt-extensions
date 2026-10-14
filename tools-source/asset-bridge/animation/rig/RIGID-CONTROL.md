# Exact original ribbon: rigid-format control

This source-only control preserves the original procedural ribbon's eight XYZ
vertices, six triangle indices, normals, UVs, tangent handedness, vertex colour,
self-visibility encoding, shoe-material reference, model bounds, root bind pose,
asset scale and single-LOD settings. It is original geometry, not a BO3 asset.
It tests the rigid-format path; it does not establish the cause of the earlier
invisible skinned render or qualify the material's rigid shader technique.

`prepare_rigid_control.py` reads only three hash-pinned text sources. It derives
the existing `ops/doom-source/writer_rigid.cpp`, retains its measured-cube
provenance notice and includes the real ZoneTool headers at native pin
`fab935826c898806855376662a8a03317b3ad8f1`. Shared writer/compiler files, the SDK,
native observer, server and previous artifacts remain untouched.

## Format changes and fixed data

| Field | Original two-bone artifact | Rigid control |
| --- | --- | --- |
| Bones / roots / client bones | 2 / 1 / 0 | 1 / 1 / 0 |
| Surface flags | `0x86` | `0x82` (skinned bit cleared) |
| Model flags | `0` | `0x80000` (`HAS_RIGID_VERT_LIST`) |
| Rigid lists | 0 | 1: bone 0, eight vertices, six triangles, no collision tree |
| Blend histogram / bytes | `[4,4,0,0,0,0,0,0]` / 48 | eight zero counts / 0 |
| Surface, surfs and LOD part bits | `0xc0000000` | `0x80000000` |
| Parent / child bind streams | one child | absent |

The root retains quaternion identity, translation zero and `transWeight=2`.
Bounds are midpoint `(0,0,8)`, half-size `(0,4,8)`, radius `sqrt(272)` and root
radius squared exactly `272`. The original raw index sentinels remain `255`.
Normals pack to `e0080000`, tangents to `200ffe00`, colour to `ffffffff`, and
self visibility to `01fe0100`. UVs include 0, .25, .75 and 1, with no V flip.
LOD distance stays 1,000,000, shadow cutoff 6 and collision LOD 255.

Two independently named models and meshes retain the fixed observer identities
`paris_doom_skin_two_bone_first_a` / `second_a` and their `_lod0` mesh names.
These historical names do not describe the new bone count. Both headers encode
the same geometry and root; their names alone differ. No xanim is included.
The expected built inventory has six rows: one material reference, two meshes,
two models and the distinct zone's rawfile.

`geometry-reference.json` preserves the original two-bone source and weights as
a comparison reference. Only the two `rigid_geometry.hpp` files drive this
writer. Do not use the reference's old weights as new rigid payloads.

## Source preparation

```powershell
python -B tools-source/asset-bridge/animation/rig/prepare_rigid_control.py `
  --output 'C:\absolute\fresh\rigid-control-source' --addon-case A
python -B tools-source/asset-bridge/animation/rig/test_rigid_control.py -v
```

The fresh output contains eight text files: the adapted writer, half-UV helper,
original geometry reference, two headers, zone CSV, plan and hash manifest.
Preparation does not read game stock, compile, emit native assets, build a FF,
install or launch anything. Existing output and linked ancestry are refused.
Select exactly A (649b stock addon) or B (40e scale-after addon); no default or
automatic mixing is provided. This choice changes the plan, not geometry.
FF bytes, SHA and build/readback receipts stay null; readiness stays false.

## Separate admitted stages

1. Root admits native writer compilation. Compile the same adapted writer twice
   with the corresponding `first` or `second` header include directory and the
   actual pinned ZoneTool headers. Reuse the established compiler environment,
   original job ownership and reservation helpers; no new ABI or build framework.
   The existing Doom wrapper's manifest/schema is different and must not be
   bypassed or passed fabricated metadata to accept this control.
2. Root separately admits native emission and the existing ZoneTool FF
   build/verify/dump route for zone `sdk_original_rig_rigid_control`. Each writer
   accepts only its two named owned native paths, creates them fresh and checks
   its own roundtrip. Run each `--verify-existing` against the actual FF redump
   and retain all exits, input/output hashes and ownership receipts. Its checks
   compare packed vertices, indices, rigid list, zero blends, all three part-bit
   scopes, root bind/bounds, material and LOD metadata. Native/FF checks remain
   unexecuted until this admission and cannot be replaced by source tests.
3. Consumer owner 55 qualifies a closed `ArtifactVariant=RigidControl` using
   actual FF bytes/SHA/producer commit and native/build/readback receipts. The
   existing default Original remains the exact 1064-byte `ea7ba4...` FF. Use
   separate private destination roots and the existing transactional installer;
   never overwrite that source FF or edit installed bytes in place.
4. Root separately admits one protected DISPLAY session with original SDK49f,
   unchanged camera/poses/fs_game and one explicit stock addon. ANIMATE is
   refused. Native B78 can observe one bone/root, rigid-list and blend counts
   without new IW7-Mod C++, but those scalar observations do not prove GPU
   palette, shader selection, draw submission or visible pixels. Both model
   pointers must resolve nondefault, readable, distinct and name-matched.

The B78 hash is
`b78b6020c1e0afdd9e548b81fc3910c68477c253abfb43ede159aed36d9752ce`.
Its asset snapshot is once per connection and its scene observation once per
ARM: require a fresh bound/protected session after loading the new control FF.
The old SDK49f, original ea7 FF, native d25 and A/B evidence remain frozen.
Source or FF roundtrip success is separate from visible rendering and owner
gameplay acceptance.

Source checks on 2026-10-14: five targeted rigid-control tests and eighteen
existing original-input fixture tests passed. Product ownership and whitespace
checks passed after adding the three exports. No native compilation, native
emission, FF build/readback or game test was performed for this control.
