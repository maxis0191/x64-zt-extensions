# Selective resident export: platform cap, LOD 0

This source adds `Operation: ResidentExportV1` to the existing owned catalogue
runner and host. An omitted operation retains catalogue behavior. The only
admitted request is `mp_freerun_04 / p7_fre_platform_cap_02 / 0`, target IW7,
profile `resident-rigid-one-lod`. There is no native rebuild or full-zone dump.
The existing publication candidate is 21751296 bytes, SHA256
`31b9d908d15fb5f0bf17a7b27309dc7183458d5e586dfc6e427cc8ec2b3fa647`.

This is source preparation, not a completed retail export. A frozen plan review
and separate exact-plan GO remain required. No new qualification, FF content
read, binary hash, native execution or real payload read was part of these tests.

## Evidence and admission

The plan has schema `iw7.t7-resident-export-plan/1`. It retains the catalogue F
candidate, engine, Steam dependency, unsealed donor metadata, 23 qualified input
descriptors, shared qualification and all 27 original metadata entries. The
three bounded historical text pins are fixed:

| Evidence | Bytes | SHA256 |
| --- | ---: | --- |
| F plan | 59287 | `718829c910020e96b94f59bf504a2ba318bcdd4f2baa80e0bc8a82526631a0d0` |
| F runtime receipt | 35780 | `7347a78280abc12eedd8e5f02ff536e0c411cae2264bc7b50101136aac2a717e` |
| F catalogue | 1669 | `d27e34f0f42ac8ccb2b675d4295b397e42636261213c149eaff942e7a7867e3f` |

The guarded receipt must confirm normal successful closure and point to that
catalogue. Its exact nonreference donor has one bone, one root, no cosmetic bone
and one LOD. These header counts do not prove the resident mesh passes native
selection. During a later admitted Run, the donor's new hash and file identity
must also match F's observed donor; this does not confer depot verification.

Nine additional text bindings cover this export helper, those three historical
JSON files, a standalone request JSON and the four existing reader sources.
The unchanged F collection therefore yields 97 bindings. ExportRequestFile is
at most 4096 bytes and must equal ExportRequest; reader sources are readback.py,
boot_contract.py, export_contract.py and h1-fixture/inspect_fixture.py.

The existing NativeJob, source guards, hardlinks, Main checks, identities,
quarantine, closure and lease rules remain in force. Admission stays 6 GiB
physical / 8 GiB commit, with 120 seconds native, 200 seconds group and 5 seconds
cleanup. Mutable output remains 64 MiB, total logical output 875958552 bytes,
metadata reserve 64 KiB and the existing whole-root 64-entry limit. No cap grows.
The export subtree additionally permits at most 32 entries and three final files.

## Native outputs and independent reader

The exact argument vector is:

```text
-t7-iw7-model mp_freerun_04 p7_fre_platform_cap_02 0
```

The private output key is
`t7_iw7_166d063bd97fb350636ad62a25f44b2d0492f33d4c7c626f23682ac2d9eae40b`.
Under `<RunRoot>/work/dump/<key>/`, the only final files are:

- `manifest.json`, at most 4096 bytes, schema `iw7.t7-iw7-resident-export/1`;
- `xmodel/p7_fre_platform_cap_02.xmb`, at most 1 MiB;
- `xsurface/<output_mesh_name>.xsb`, at most 16 MiB. The mesh name is observed
  at runtime, normalized to slash-separated safe components, never guessed.

The manifest binds names, counts, root bone and the sole unresolved material
name to file paths, sizes and digests. Unexpected files, unreferenced directories,
reparse points, multiple meshes, changed bytes and overclaimed evidence refuse.
Manifest/model/mesh reads are permitted only after original native closure while
admission remains held. Forced closure never triggers payload reads after release.
The native exporter denies ZoneTool XPAK helper reads; engine I/O is still unproved.
It exports no material payload or texture pixels.

Run/attempt/host evidence uses distinct `iw7.t7-resident-export-*/1` schemas and
ExportOutcome. A successful runtime status is `ExportObservedPendingReadback`.
TraceOutcome and MessageOutcome are `DisabledForResidentExportCLI`: the compiled
hooks only activate for the two-argument catalogue command, not this command.

After converter closure, the existing independent reader is a separate bounded
step, with its own approval/admission requirements:

```text
python -B -S tools-source/asset-bridge/t7-iw7/readback.py --request <request.json> --manifest <root>/manifest.json --root <root>
```

It checks serialized layout, names, root bind data, finite geometry, triangle
indices/areas and model bounds. It cannot prove equality to unseen T7 buffers,
complete shading, donor textures, zone ownership or in-game compatibility.
SerializedParseVerified, DependencyPayloadsVerified, CompatibilityProven and
Ready therefore remain false in the export runner's receipt.

## Source validation

`Test-T7ResidentExport.ps1` covers the new request/provenance/plan/output rules
using synthetic data. The existing catalogue and host suites also exercise
export success, missing output, nonzero exit, forced closure, quarantine, failed
lease release and incident closure through the actual common functions/finalizer.
The Python contract/readback tests use synthetic geometry only. A separate
bounded source check also passed against the three actual F JSON pins and a
temporary request (96930 bytes of text, no binary/FF read or native process).
Test counts and integration review belong to the coordinating source handoff;
no gameplay or retail export acceptance is implied.
