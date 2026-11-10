# Original platform: closed standalone writer qualification

The original `sdk_author_platform` project has a real standalone C++ writer and
native serialized geometry readback as of 2026-10-15. This qualifies its 24
vertices, 12 triangles, one root, one surface and one LOD. It does not qualify an
FF, material, shader ABI, rendered pixels, collision or player contact.
[Sanitized measurements](../ops/model-lab/artifact.authored-platform.measured.json)
retain the exact source revisions and local evidence lengths/hashes. Runtime
receipts, binaries, serialized assets, SDK installation and machine paths remain
outside Git.

## Frozen inputs and result

The actual producer was assets `8f55ac7819d93f5bcede273aea3e478ae9438a12`
(PR172), with the clean native Source checkout at
`fab935826c898806855376662a8a03317b3ad8f1`. The authoring project came from SDK
`c0185903bcdf3d1fca6aa3e43379814a55fff40f`. Its GSC and input geometry remained
byte-identical to runtime SDK `6dcfc719e0535509f109c593fa4342ce201b5523`;
no runtime consumer was repinned by this CPP run or this documentation.

Raw geometry SHA256 `6c9667ee...` and normalized prepared geometry SHA256
`31f8d2ae...` describe different text bytes. The normalized source is the
`geometry_source_sha256` used by the writer and downstream World connection.
Bounds are midpoint `[0,0,8]`, half-size `[128,128,8]`. LOD0 distance 1000000,
shadow cutoff 6 and collision sentinel 255 roundtripped unchanged. Null physics
and that sentinel are not a collision witness.

| Measured output | Bytes | Qualification |
| --- | ---: | --- |
| `model-writer.exe` | 122880 | Compiled and executed under the original lease |
| `sdk_author_platform_model.xmb` | 978 | Native writer/reader geometry comparison |
| `sdk_author_platform_mesh.xsb` | 1233 | Native writer/reader geometry comparison |

All output hashes in the measurement record were captured under the original
admission. No PE, XMB or XSB was reopened to produce the post-release handoff.
The reader supports existing dumps, but no FF dump was supplied in this run.
Normal encoding remains the unverified `H1-1010102-candidate`.

## Actual lifecycle and publication

One fresh bundled PS7 `-NoExit` host used the reviewed B2 caller and the existing
`Build-Writer.ps1`. Physical/CIM creation identity, CLR entry and exact managed
arguments were checked before imports. The caller rooted its real PSVariables
and held Source handles from their first hash through final native closure.
Inherited `PYTHON*` variables were saved, cleared for the Source verifier and
restored in `finally`.

The existing writer acquired one shared admission before NativeJob DLL reads,
VS/SDK discovery, compiler inspection or native execution. Its three original
jobs were `vswhere.exe`, `cl.exe`, then `model-writer.exe`; each exited zero and
closed. Discovery and the short writer had already exited before CIM registration;
their original job handles confirmed empty trees. The compiler's retained VCTIP
member was observed twice in its original job, then the existing compiler policy
closed that same job and confirmed zero members. No foreign process was stopped.

The native run and provenance snapshots were flushed, read back and hashed while
the lease remained held. The final closure binds both snapshots and confirms job,
input-guard and lease closure. The caller compared all three readbacks against
the unique actual records retained in `writerRoot.Publications`. The existing
PR172 strict typed closure consumer then accepted the same text evidence.

A preexit snapshot from that same host confirmed all six original-object
reference comparisons, final `CanExit`, restored Python environment, zero guards
and absent lease. The true PTY subsequently exited zero. Fresh process and lease
inventories were empty; Root independently corroborated the result. An initial
post-run snapshot filename containing an extra dot was refused before writing;
the literal `capsule-preexit.json` succeeded in the same host without rerunning CPP.

## Remaining validation and next operation

The historical Material C role records remained metadata only. None of those six
blobs, retail stock, DDS, FF or game inputs participated in this CPP run. Ready,
material closure, recipient resolution, shader/normal ABI, rendered pixels,
physics/contact and owner gameplay acceptance remain false.

Next prepare a separately reviewed FF capsule through SDK29 and the existing
authored ModelFF producer. Revalidate the six template roles only under its
future admission, generate the original 8x8 one-mip DDS for texture slot 1, and
retain all three writer closure snapshots. FF build/readback needs a distinct
exact-tuple GO. Do not restore retired stock or reuse historical file identities.
Protected placement, Use/contact and captures follow only after that FF result.
