# One observed image object to the existing reader

`selected_image_request.py` consumes the distinct closed native envelope
`iw7.t7-selected-image-metadata/1` and d468's copied-header DTO
`iw7.t7-selected-image-header-metadata/1`. It does not consume an old F2 or G3
record as a production request. F2 alone contains no body, dimensions or key.
The native producer/guard belongs to 51; the owned C++ DTO mapper belongs to
d468. This Python module performs no capture, engine lookup or extraction.

`select_image(report, part_index=..., native_exit_code=...,
qualified_object_mip_count=...)` requires the exact source/selector, nondefault
model, two header copies, observed body, association/header/name rechecks,
successful original exit and a complete same-pass F2 diagnostic. All retained,
The producer's successful failure_stage/reason fields are null; non-null
diagnostics, including empty strings, are refused by the request consumer.
atomic, lifetime, runtime ABI, pixel and Ready claims stay false. The header
DTO must attest the pinned source layout and DXGI member; a pending namespace
refuses. Source-layout attestation does not prove the retail ABI or lifetime.

Select an explicit active part from all four physical descriptors. Cumulative
bytes are `packed_size_raw >> 4`; the selected whole-object delta is the positive
difference from the previous active descriptor (zero for the first). The entire
active sequence must increase. Keys remain sixteen lower-case hexadecimal
digits, including values above 2^53. No name-hash-to-key conversion or provider
discovery occurs. Low-four-bit counts remain raw and are never used as mip facts.

The caller must separately qualify the actual whole-object mip layout.
`qualified_object_mip_count=1` is that required fact, not a default or a shortcut
from byte equality. Any other/unknown value refuses. The complete delta must
then equal the exact single tight 2D mip for the selected dimensions and typed
format, using `resident_image.object_layout`. Padding, extra mips, arrays/cubes,
unsupported format or delta above the existing 262144-byte reader limit refuse.
Raw streaming/fallback/flags stay in the original DTO; no resident flags are
fabricated. No DDS or pixels are copied from fallback data.

The returned immutable request exposes the `CompleteImageObject` view for the
merged DDS119 API. `argv(providers, output)` returns only existing
`selected-xpak.exe --key ... --expected-bytes ... --out ... --package ...`
arguments. Providers must be 1..8 explicit local paths with distinct observed
Win32 file identities and sizes. The actual reader still checks their resolved
identities, index scope, unique key, extent and closure under separate admission.
Returning arguments grants no GO. Never hash or scan entire packages.

After a separately admitted extraction has supplied owned immutable bytes,
`publish_dds(pixels, output)` reuses `object_to_dds` and creates a new private
`.dds` exclusively under existing ordinary directories. It opens no input pixel
path or metadata reference, refuses mismatched bytes and never overwrites an
existing file. A publication failure may leave an owned partial output; preserve
it and use a fresh path. Its receipt keeps material/render/Ready false.
Then 51's image/material/FF path binds only pilot slot 0, preserving the mesh and
other four handles; independent `verify_iw7_object` compares name, explicit IW7
semantic and every byte before renderer validation.

Validation: eight targeted authored Python tests pass on 2026-10-14, covering
old/missing/refused body, pending namespace, native recheck/exit contradictions,
typed part/key/size validation, no low4 inference, SRGB preservation, complete
delta refusals, reader argv without IO and create-only DDS publication. No real
image header, XPAK, pixel data, native process or game was read or run.
Contract review corrected an initial empty-string success assumption to the
actual producer's null diagnostics; the failed e47d4f6 review remains retained.
