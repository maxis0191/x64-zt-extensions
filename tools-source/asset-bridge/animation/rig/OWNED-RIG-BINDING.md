# Owned decoded rig binding

`owned_rig_binding.py` links one owned decoded skeleton, surface and clip through
explicit bone indices. It is a generic IW7 modding interface: BO3 is an optional
interop corpus. Kino and Ray Gun demonstrations are secondary consumers, never
prerequisites for generic engine work. No real asset identity is supplied here.

The Source caller supplies these ordinary Python package roots:

```python
# PYTHONPATH contains tools-source/asset-bridge and its t7-iw7 directory.
from animation.rig.owned_rig_binding import bind_owned_rig, require_same_inputs

plan = bind_owned_rig(skeleton, payload, shared, surface, clip)
require_same_inputs(plan, skeleton, payload, shared, surface, clip)
```

Helpers never edit `sys.path`. Source test/CLI entrypoints provide their package
root explicitly. The mapper imports `animated.preflight` and
`animated.reorder_proposal`; the latter uses its package-relative preflight.
Their calculations and public signatures are unchanged.

All five inputs use exact builtin types and closed field schemas. Every input
is bounded before owned container copies and codec allocation. Skeleton names
are 2–255 unique exact ASCII names, with one root and no cosmetic bones. The
existing 256 KiB surface and aggregate 4 MiB clip byte budgets apply. Existing
native stride, feature, loss and short-prefix refusals remain in force.
Clip rate/timing values must be finite **float**, including zero timing values;
integer coercion is refused. Counts are exact bounded **int**, flags exact
**bool**, arrays immutable **bytes**, and incoming name/category arrays exact
**list**. The result converts aggregate containers to immutable values.

Two bounded captures are compared through exact typed encodings before any
component helper runs. Only one retained owned capture reaches the validators
and mapper. This detects differences that the two observations expose; it does
**not** claim atomicity against concurrent mutation, or detect every transient
change between observations. The caller should stop mutating input containers.

The closed codec is versioned `iw7.owned-rig-binding/1` and includes the pinned
converter revision. Each component has a separate domain, ordered schema fields,
one-byte type tags and big-endian uint32 lengths. Integers use uint32, booleans
one byte, strings exact ASCII bytes, arrays exact original bytes, and floats
exact IEEE-754 binary64 bytes. Negative zero is preserved. Names and category
arrays retain their order and element types. No `repr`, Python hash, JSON float
normalization, case folding or unordered-set identity is used.

SHA-256 identities bind the complete skeleton, clip, payload, shared metadata,
surface metadata, and the complete ordered cohort. Skeleton identity includes
all counts, layout, names, raw parents, angles, positions, classifications and
base matrices. Clip identity includes every declared field and complete raw
stream, including uninterpreted schedules. `require_same_inputs` refuses reuse
against changed typed values. These data reports are not security credentials
or permission tokens; their identities do not authenticate a real donor.

After validation, root parent is `None`; each other parent is `i-distance`.
The channel table preserves clip order and resolves exact names to the model
bone order. Partial clips remain explicit subsets; missing channels are never
invented. Bone IDs and XAnim streams are never reordered. The existing stable
surface permutation still moves complete positions, attributes and weights,
and remaps triangles together. There is one target rig, without an implicit
union of view and hands models.

The plan, retained inputs, helper reports, mapped surface, permutations,
influence rows, identities and qualification fields are deeply immutable.
No caller-owned or helper-owned mutable aggregate escapes. All native,
provenance, complete-clip, engine and production qualifications remain false.
Hierarchy/base-matrix equivalence and engine weight direction remain unproven.

Run the authored causals and affected helper regressions from this repository:

```powershell
python -B -m unittest discover -s tools-source/asset-bridge/animation/rig -p test_owned_rig_binding.py -v
python -B -m unittest discover -s tools-source/asset-bridge/t7-iw7/animated -v
python -B -m unittest discover -s tools-source/asset-bridge/animation/rig/raygun -v
```

This runs no native tool, extraction, asset lookup, SDK, renderer or game. The
fifteen null model/clip/tag roles in the Ray Gun plan stay unresolved. The
NativeD/image stop and current owner/runtime restrictions remain applicable.

## Local Source validation, 2026-10-16

Python 3.12: 19 new authored linkage/identity/immutability/import tests, 16
existing animated component tests and 26 existing Ray Gun metadata/owned-skin
tests passed (61 total). The Source-only `demonstrate_losses.py` entrypoint
also retained its expected refusals and stable permutation. No native patch,
runtime asset, engine behavior or complete clip was tested by these checks.
Hosted CI and review are separate from these local results.
