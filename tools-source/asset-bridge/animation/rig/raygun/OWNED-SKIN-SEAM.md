# Owned decoded surface: source mapping seam for serializer51

This separate helper closes the source connection between selected shared-buffer
offsets and the existing stable skin permutation. It is a fixture implementation,
not a new native selector, decoder, exported model or production admission. No
Ray Gun payload or rig has been observed. Serializer51 retains the native export
and `t7_iw7_streamed_model.hpp`; RE owns ABI/extent qualification. The existing
one-bone rigid profile and its guards are untouched.

`map_owned_source_surface` accepts owned immutable bytes with length exactly
equal to selected `shared.dataSize`, the explicit shared/surface metadata and
resolved bone names. It opens no input, decodes no archive and dereferences no
pointer. Its 256 KiB extent cap matches the existing selected-payload profile.
It never uses `skinVertCount` to derive a weight offset or substitutes bone0.

The retained `fab9358` T7 declarations and `xmodel_mesh.cpp:119-179` supply these
source formulas, with V=`vertCount`, T=`triCount`, Bv=`baseVertOffset`,
Bi=`baseIndexOffset`, N=`shared.dataSize`:

| Rows | Start | Extent |
| --- | --- | --- |
| Positions | posOffset + Bv * 12 | V * 12 |
| Packed attributes | vertsOffset + Bv * 16 | V * 16 |
| Source weights (4 U8 + 4 U16) | skinWeightsOffset + Bv * 12 | V * 12 |
| Face indices | indicesOffset + Bi * 2 | T * 6 |

Bi counts indices, not triangles. All starts/counts are checked before slicing,
using nonwrapping arithmetic, `start <= N`, `count <= (N-start)/stride`,
Bv+V <= shared vertices and Bi+3T <= shared indices. Immutable byte copies
become a separate resident snapshot; the original shared flags/data are not
changed. The new profile selects only T7 pure-skinned flag2 and no rigid list,
and preserves the existing component restrictions including part-bit loss refusal.

`regroup_surface` and `decode_stream_weights` are reused without copying their
implementations. The same stable permutation moves complete positions,
16-byte attributes and 12-byte weight records. The inverse permutation remaps
every triangle corner. Influence IDs stay explicit indices into the supplied
bone-name order; no raw ScrString ID is carried into IW7. The helper returns the
permutation, typed influence rows and source-converter-shaped IW7 blend words.
Those wire words do not prove engine weight direction or shader conventions.

The literal golden fixture has six shared vertices, selected base vertex3,
base index3, and influence classes [2,1,2]. Expected permutation [1,0,2]
preserves every attribute and remaps the triangle to [1,0,2]. Independent
`read_blend` verifies IDs and stored words. Five source tests pass, covering
out-of-span offsets, nonwrapping uint32 arithmetic, shared/local count mismatch,
mutable/truncated bytes, rigid/unknown flags, joint IDs and discarded part bits.

**Native stride provenance remains Pending and production_admissible=false**,
even for passing input. These widths reproduce primary source, not a measured
Ray Gun capture. Nonroot tag positions are not mapped: their declaration says
12 bytes while the loader comment says16. The one-root Freerun model exercised
zero such tags, so it cannot resolve that conflict. Hierarchy/binds, native
extents/string resolution, clip timing/notetracks and native serializer wiring
remain separate gates. No consumer change or native invocation accompanies
this helper.

After the active H/Game group is closed, serializer51 can review this source
interface and choose an exact donor/loading scope from the pinned
`ray_gun`/`ray_gun_upgraded` mod candidates. Before a selected skinned export,
that scope must establish actual model roles/names, weights and nonroot tag
stride/extent. Authentic materials/textures and real idle/fire/reload clips
remain required; a static prop or original fixture cannot establish a usable
weapon, projectile behavior or PAP acceptance.
