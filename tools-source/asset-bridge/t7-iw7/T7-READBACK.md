# Independent static T7 export readback

`readback.py` reads the current `iw7.t7-iw7-resident-export/1` manifest and its
IW7 XMB/XSB byte snapshots. It is limited to `t7-iw7-resident-static-v1`: one
selected resident LOD, one surface, one root bone, one rigid list and one
unresolved material reference. This is a pilot profile, not a permanent SDK cap.

The manifest records actual names and counts, but **does not record donor
positions, triangles or bounds**. This reader compares names/counts with the
manifest and validates the serialized geometry internally. It cannot establish
equality with unobserved T7 buffers. No real T7 export was used for this tranche.

## Use after a separately qualified export

```powershell
python tools-source/asset-bridge/t7-iw7/readback.py --request request.json --manifest export/manifest.json --root export
```

The CLI prints a bounded summary as JSON or exits nonzero on refusal. It never
rewrites the inputs. Request and manifest are limited to 4 KiB each; duplicate
JSON keys and nonfinite constants are rejected. Artifact paths come from the
existing `export_contract.py` validation. Reads reject observed symlink/reparse
ancestry, nonregular files, size excess and observed identity/metadata changes.
The same immutable bytes are hashed and parsed: XMB <=1 MiB, XSB <=16 MiB.
These file limits do not prove the original resident buffer size or residency.

`inspect_pair(model_bytes, mesh_bytes, manifest, request)` is the primary Python
API and returns `iw7.t7-iw7-static-readback/1`. `parse_model` and `parse_mesh` are
lower-level helpers expecting an already validated manifest; the mesh helper
also returns every decoded position and triangle for independent comparisons.
The CLI omits these potentially large arrays, retaining their counts and extrema.

## Checks and source basis

The ABI/read order was inspected in the retained ZoneTool source pinned at
`fab935826c898806855376662a8a03317b3ad8f1`: `iw7/structs.hpp`,
`iw7/assets/xmodel.cpp`, `iw7/assets/xsurface.cpp` and
`utils/io/assetmanager.hpp` under `src/zonetool/zonetool/`. The T7 converter and
the current [resident selector](../t7-bridge/t7_iw7_resident_model.hpp) were read
to determine this profile's output features, not called as a test oracle.

| Serialized data | Independent checks |
| --- | --- |
| Model, 736-byte layout | One LOD/root/surface, exact manifest names, required pointer presence, unused/optional fields, finite positive scale and finite nonnegative radius |
| LOD descriptors | Selected surface range, finite nonnegative distance, five unused LODs, mesh reference and shared model/mesh bone bits |
| Root data | Exact engine-resolved manifest name, finite bind matrix, finite nonnegative bone bounds/radius, classification byte |
| Material | Exact manifest reference, present handle, finite nonnegative binary16 mip radius; no payload is read |
| Mesh/surface, 56/256-byte layouts | Exact name/counts, rigid `0x80` flags, required streams, absent skin/subdivision/physics/lightmap/tension/SH streams |
| 32-byte packed vertices | Every XYZ finite, both binary16 UV values finite, decoded extrema |
| 6-byte triangles | Every uint16 index below vertex count, nonzero triangle area computed from parsed XYZ |
| 16-byte rigid list | Bone index zero, complete vertex/triangle coverage, zero first triangle, absent collision tree |
| Bounds | Finite midpoint and nonnegative half extents, endpoints within float32 range, vertices enclosed by model bounds |

Bounds permit `4 * 2^-23 * max(1, abs(center), halfExtent)` rounding tolerance
per axis. Selected-LOD geometry need not touch every model-bound face. Bone
bounds are validated structurally; comparison in bone space is not qualified.
Packed normal/tangent/color/self-visibility words are consumed without claiming
their shading semantics. Radius and LOD-distance heuristic fidelity are not
independently established from donor data.

Only documented nonzero pointer slots are normalized for structural checks;
addresses are never dereferenced or treated as stable identities. Part bits
must not reference a bone outside the sole root (empty bitsets are permitted).
Unexpected optional data and trailing bytes fail rather than widening the profile.

The reader subclasses the existing [bounded record reader](../h1-fixture/inspect_fixture.py)
for cursor/type/end/raw-absence checks and reuses its scalar/zero-field checks.
It does not call the historical H1 geometry oracle or import a generator,
converter, serializer, native preparer or new framework. The former 256-element
fixture limit is replaced with the pilot's uint16 counts and byte budgets.

`OFFSET` records resolve only backward to the same logical type, stride and
valid element range. Present inline arrays/strings/asset names enter the file
ledger; absent records and aliases do not. Names require index zero. This is
deliberately stricter than the native untyped pointer ledger: cross-layout
reinterpretations, forward references, range overruns and optional RAW aliases
are rejected. An actual dump using an unqualified alias requires source review;
it must not silently bypass the check.

## Evidence boundary and tests

Successful readback sets only receipt/snapshot/serialization/triangle/enclosure
checks true. Native provenance, outer process acceptance, original geometry
correspondence, source-zone ownership, material/image payload closure, engine
I/O, bone-space geometry, packed shading, runtime and `ready` remain false.
The original export manifest is unchanged. The caller must bind this result to
the independently closed Run, executable/source identity and stock restoration;
file metadata checks are not exclusive locks or a process/provenance attestation.

```powershell
python -m unittest discover -s tools-source/asset-bridge/t7-iw7 -p test_readback.py -v
```

The tests author original translated irregular-pyramid and tetrahedron bytes,
a minimal flat triangle, and repeated synthetic geometry at 65,535 vertices and
triangles (>1 MiB). They check decoded coordinates/topology against explicit
expectations, variable names/root/material/selected LOD, alias ledger behavior,
all truncation points in both small files, overflow counts, float32 bounds,
nonfinite numbers, out-of-range/degenerate triangles, optional features, missing
pointers, stale digests and a synthetic-only CLI round trip. No retail data,
native build/process, extraction, FF packaging, SDK binding or game execution is
part of these tests. Real export compatibility and rendering remain pending.

Source verification on 2026-10-12: all 31 readback tests pass. The complete T7
Python group reports 121 tests, with 110 passing and 11 skipped because retained
native source/build bindings were deliberately not supplied. No native source
preparation, build-output hashing or process qualification was performed by this
test run. Integration, exact-head CI and merge belong to the coordinating chat.
