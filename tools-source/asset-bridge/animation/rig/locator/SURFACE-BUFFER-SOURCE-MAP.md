# Conditional XSurface buffer source map

Source-only review, 2026-10-13, based on private project `43e663a98817332a70855186bfb52a95fe425e71`
and retained provider `fab935826c898806855376662a8a03317b3ad8f1`.
No binary, snapshot or asset was read; no build, debugger or runtime observation
was performed. This maps a hypothesis from the locator, not an established ABI.

## Conditional layout

**If S is the start of this provider's IW7 XSurface with 64-bit pointers,
S + 0x58 is the slot `ID3D11Buffer* blendVertsBuffer`.**
The [IW7 declaration][iw7-layout] gives this sequence:

| Offset | Member |
| --- | --- |
| 0x00 / 0x02 / 0x04 | flags / vertCount / triCount (16 bits each) |
| 0x06 / 0x07 | rigidVertListCount / subdivLevelCount (8 bits each) |
| 0x08 / 0x18 / 0x1c | blendVertCounts[8] / blendVertSize / four padding bytes |
| 0x20 / 0x28 | verts0 / triIndices |
| 0x30 / 0x38 / 0x40 | vb0 / vb0View / indexBuffer |
| 0x48 / 0x50 | rigidVertLists / blendVerts (CPU data) |
| 0x58 / 0x60 | blendVertsBuffer / blendVertsView |

Offsets above are derived from the declarations and usual MSVC x64 scalar sizes;
they were not measured in a new build. The provider asserts `sizeof(XSurface) ==
0x100`, but has no field-specific offset assertion here. Its declaration has no
local packing override. A source size assertion does not identify a live record
or prove the retail binary uses that layout.

Variants prevent identification from the offset alone. [H1][h1-layout] has size
0x108: +0x58 is CPU `blendVerts`, and its buffer is +0x68. [IW6][iw6-layout]
also places `blendVertsBuffer` at +0x58, but vertices begin at +0x18 and
`blendVertsTable` occupies +0x50. [T7][t7-layout] uses shared surface data and
base offsets. IW7 flags change payload interpretation, not these member offsets.

## Parsing, dumping and FF publication differ

[IW7 parse][parse] reads the raw surface array, then replaces CPU payload pointers.
It does not create or reset `blendVertsBuffer`/`blendVertsView`.
[Dump][dump] writes the raw surface array before its separate CPU payloads;
the [generic writer][array-write] and [reader][array-read] transfer `sizeof(T)`
records. An old GPU-slot value can therefore survive as a numerical value in a
reloaded XSB; a nonzero field does not prove a live D3D object.

The [FF writer][ff-write] explicitly sets Buffer/View and other GPU slots to
null, then serializes CPU `blendVerts` using `blendVertSize & 0xfffffffe`.
Neither that null initialization nor an observed later store identifies a
resource-creation routine, GPU object or first writer over the complete load.

## Smallest discriminating observation, not executed

Use one identified `XModelSurfs` and its real `surfs`/`numsurfs` provenance;
establish `S = byte_address(surfs) + i * 0x100`, with a valid index, rather than accepting a
plausible header alone. In one correlated invocation/TID, verify entry R9 and
the store's RBX both equal `P = S + 0x58`. Record the relevant header fields,
RAX and the eight bytes at P before/after the store. A conflicting table,
layout, pointer, invocation or thread leaves the hypothesis unresolved.

This could establish the selected slot/store relationship. GPU identity still
needs an observation of that same resource; non-null values, vtable appearance
and source type names do not establish it. Earlier unexamined calls remain
outside the observed interval. Reuse existing lab/capture ownership and bounds;
this document supplies neither commands nor a runtime GO.

[iw7-layout]: https://github.com/bigmangeekf/x64-zt/blob/fab935826c898806855376662a8a03317b3ad8f1/src/zonetool/zonetool/iw7/structs.hpp#L1041-L1085
[h1-layout]: https://github.com/bigmangeekf/x64-zt/blob/fab935826c898806855376662a8a03317b3ad8f1/src/zonetool/zonetool/h1/structs.hpp#L4160-L4197
[iw6-layout]: https://github.com/bigmangeekf/x64-zt/blob/fab935826c898806855376662a8a03317b3ad8f1/src/zonetool/zonetool/iw6/structs.hpp#L2454-L2485
[t7-layout]: https://github.com/bigmangeekf/x64-zt/blob/fab935826c898806855376662a8a03317b3ad8f1/src/zonetool/zonetool/t7/structs.hpp#L1323-L1415
[parse]: https://github.com/bigmangeekf/x64-zt/blob/fab935826c898806855376662a8a03317b3ad8f1/src/zonetool/zonetool/iw7/assets/xsurface.cpp#L52-L112
[dump]: https://github.com/bigmangeekf/x64-zt/blob/fab935826c898806855376662a8a03317b3ad8f1/src/zonetool/zonetool/iw7/assets/xsurface.cpp#L445-L513
[array-write]: https://github.com/bigmangeekf/x64-zt/blob/fab935826c898806855376662a8a03317b3ad8f1/src/zonetool/zonetool/utils/io/assetmanager.hpp#L114-L123
[array-read]: https://github.com/bigmangeekf/x64-zt/blob/fab935826c898806855376662a8a03317b3ad8f1/src/zonetool/zonetool/utils/io/assetmanager.hpp#L668-L700
[ff-write]: https://github.com/bigmangeekf/x64-zt/blob/fab935826c898806855376662a8a03317b3ad8f1/src/zonetool/zonetool/iw7/assets/xsurface.cpp#L151-L225
