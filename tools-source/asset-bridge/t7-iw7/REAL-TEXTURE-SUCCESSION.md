# First authentic BO3 texture on the IW7 model

The immediate target is a real BO3 diffuse image on material slot 0 of
`p7_fre_platform_cap_02`, followed by qualified normal/specular inputs and the
remaining four original material slots. Existing shoe references are a pilot
baseline, not BO3 textures. No image name, format, stream key or pixel payload
is currently qualified by the provenance metadata-only mode.

Reuse these existing stages, rather than building another capture pipeline:

| Stage | Existing interface and required evidence |
| --- | --- |
| Selected binding | 51's MODEL Add/post-load capture and the 115/117 JSON consumer. Fixed slot 0 / binding 4 / hash A0AB1041. This is selection, not a diffuse-role or lifetime proof. |
| Image body | A separately admitted bounded header/parts read, after actual epoch/region facts are reviewed. Reuse G3's exact selection/rechecks; do not transform a pointer or add a fallback. |
| Whole object | Existing `selected_xpak_cli`: exactly one observed key64, expected decoded size, and 1..8 identified providers. Existing caps are 256 KiB encoded/decoded; inspect also decodes and requires admission. No general scan/package hash. |
| DDS | `CompleteImageObject`, `object_to_dds` in `resident_image.py`: all immutable decoded bytes must equal one tight 2D mip in an explicitly qualified typed DXGI format. |
| IW7 image | Existing image loader/material authoring path, with a private image name and explicit IW7 semantic. Preserve bytes, dimensions, typed format and sRGB. |
| Independent bytes | `verify_iw7_object`: exact IW7 image name, semantic, dimensions, mip count and every pixel/block byte. This does not verify the material or renderer. |
| Material/mesh | Reuse the existing material/writer/FF path under 51 ownership. Change only pilot slot 0; preserve UV/indices/bones/LOD/bounds and the other four material handles. Then render and inspect the actual model. |

The first operation after image-body facts become qualified is a single-key
whole-object extraction. It needs the genuine image identity/role, confirmed
DXGI namespace, selected part dimensions/depth/map type, actual key64, exact
cumulative-byte delta and qualified provider identities. A read-only f2 report
does not contain those fields. Complete/unreadable metadata cannot authorize a
header read, and equal pointer values do not prove retention. Body/extraction,
FF build and game validation keep their separate coordinator GO and closure.

`object_to_dds` fills a concrete source gap: the old `to_dds` accepts only a
resident `CopiedImage`. A decoded stream object must not be passed through that
API by clearing streaming/fallback flags. The distinct object view supplies no
native flags, pointers or capture-proof claim. It uses the same DDS encoder,
18-format allowlist, 4096-dimension / 16 MiB bounds and independent IW7 byte
comparison. Its one-mip policy describes the new DDS; it does not assert the
meaning of the original low-four-bit count. Wrong size, padding, extra mips,
borrowed memory, unsupported/typeless format, cube/array and ambiguous namespace
are refused. Never use the diagnostic raw-preview truncation as conversion.

T7 and IW7 semantic numbers are different. In pinned source `fab9358`, T7 normal
is 4; IW7 normal is 5. T7 specular mask/specular/gloss/occlusion are separate;
IW7 also has packed color-specular (14) and normal-occlusion-gloss (15).
An explicit sampler/material-role and channel-packing review must select the
IW7 semantic/technique. Image names, binding index and a 32-bit name hash do not
prove channel meaning; no automatic cast, alpha/gamma transform or normal-Y
flip is performed by this converter. Byte equality alone cannot establish
shader fidelity.

M7 proves the named nondefault recipient reference
`mopw/character_park_clown_zombie_shoes` in `cp_zmb` only; its CSV SHA-256 is
`b691b56baf8b9db5f887d9ce6d2005c9bc1c1bc0527c7756bc8b792b9bd6230c`.
Historical source plans, receipts and packages stay immutable. Prepare new
conversion/material candidates from actual qualified facts.

Source validation on 2026-10-14: 48 targeted Python tests pass, including five
new complete-object test methods across all 18 formats, non-square BC data,
wrong-size/mip/type refusals, resident API isolation and IW7 byte/name/semantic
readback. All data is authored. No BO3 pixels were read, no authentic DDS/FF was
created and no native/game validation is claimed. The public resident CLI and
its copy schema stay unchanged; the new interfaces are pure bytes APIs.

RayGun models/materials/PAP/FX/audio and BO3 HUD images remain unidentified in
the current closed evidence. Coordinate the exact donor inventory with the
weapons/native/HUD owners. Existing IW7 player/perk images are adaptations;
ImageGen output, if needed later, must remain distinct from retail BO3 assets.
