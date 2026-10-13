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

Subsequent observations are recorded separately: [diagnostic B](RESIDENT-EXPORT-B.md)
and [the v2 export C attempt](RESIDENT-EXPORT-C.md). C retained its reviewed v2
request and build D candidate but returned the v1 single-surface refusal without
an export. These later records do not change this original v1 contract.

## Selected mesh/material observation E2 stock A, 2026-10-13

The E2 build qualification was independently reviewed and merged in
[asset PR15](https://github.com/maxis0191/x64-zt-extensions/pull/15), merge
`b2730c6044c4184b7b115892714ca62a1097948d`. Its targeted source suite passed
1,139 checks; the read-only real-build qualification passed on 23 held texts.
The separate compiled synthetic material fixture passed 32 checks. Those
results qualified source/build/fixture behavior, not stock material readability.

A fresh source package at that merge contained 870 text files / 8,040,231 bytes
and explicitly adopted the current H1 telemetry policy. The stock plan had
106 bindings and retained the same selected MP model, request, 23 F bootstraps,
shared qualification and source catalogue. It reused E2 candidate 21,849,600
bytes / `7c7ad775b201dea60ec050a28e5943cbf1eeeaa8e6386eba675c7ffc001f5e7f`.
No native rebuild or stock clone was made.

Preparation first refused an incorrect array traversal, before creating a plan.
After correcting it, default validation refused the proposed run-root prefix.
A distinct plan revision uses the existing `t7-export-*` root contract; the
earlier scripts, sealed plan and unused root remain retained. Default validation
passed without binary hashes, native types, admission or Run. A separate
coordinator grant and fresh zero-group observation preceded the unique stock
invocation of `-t7-iw7-model-v2 mp_freerun_04 p7_fre_platform_cap_02 0`.

The native process exited naturally 1 after 6,302.1892 ms. The runner returned
**Failed / NoExport**, retaining this refusal:

```text
t7-iw7-resident-static-v2: selected mesh must use one bounded resident shared buffer; flags=9 bytes=18624
```

Before that refusal it captured one bounded mesh record from the requested
model. Raw JSON was retained, parsed with exact Python integers and rendered
as 16-character hexadecimal strings; no JavaScript Number conversion occurred.

| Observation | Exact value |
| --- | --- |
| XPAK key | `f58d58f1fc9b6b01` |
| Three opaque uint64 words, in order | `0000000000000000`, `0000000000000000`, `0003ffffffffc000` |
| Shared flags / declared data bytes | 9 / 18,624 |
| Shared vertices / indices / surfaces | 560 / 1,470 / 5 |
| Position / attribute / index / skin-weight offsets | 2,944 / 9,664 / 0 / 0 |
| Payload bytes read by the observation | 0 |

The descriptor field semantics, atomic snapshot, retained allocation, geometry
and runtime verification flags remain false. These are observed header values,
not decoded XPAK payload or proven geometry. No manifest, XMB, XSB or successful
readback was produced. The resident guard was not relaxed.

Material slot 0 separately retained the five ordered names
`mc/t7_metal_trim_safehouse_mobile_09`, `mc/t7_metal_trim_freerun_black_01`,
`mc/t7_rubber_floor_grip_white_fr_diamond_blk`, `mc/metal_chrome_01` and
`mc/t7_fre_emissive_teal_01`, with aliased slots `[0]`. Its deeper observation
refused `t7-iw7-resident-static-v1: range is not committed readable memory`.
No texture header, diffuse selection or pixels were captured. The synthetic
fixture pass does not convert this engine-side readability refusal into success.

The original native owner confirmed root exit / zero active processes, normal
tree closure, released lease, guarded input revalidation, unchanged metadata,
validated output scope and all 27 original/alias pairs. The host's initial
conservative process observation refused a native-PID/run ambiguity. Its cause
was not established; fresh metadata then showed absence. The unchanged original
`Finish` passed with `Closed`, `CanExit=true` and zero wrapper guards. No process
was killed, guard bypassed, original receipt altered or native invocation retried.
PTY 91936 actually exited 1 (tool chunk `cc532d`). The 21:00:56 UTC observation
confirmed both owned identities absent, zero leases/heavy/game processes and
the stopped Main/UDP baseline preserved, before handing the slot to another
authorized test. No stock payload was read or hashed after lease release.

Private bounded evidence under `t7-e2-stock-platform-a-20261013/` pins the
preparation, exact JSON extraction, original exit and subsequent absence;
runtime receipt/stdout remain in the composed package's E2 stock A directory.

| Evidence | Bytes | SHA256 |
| --- | ---: | --- |
| Plan revision 2 | 67,435 | `dbf39b436d82a175a936365d3f24264f056081ff5379188a222a46c03cc04eb3` |
| Host contract revision 2 | 1,415 | `871c50b62e7f02511a3f9b73152340f3b19a698e958e3fc99b6859e87d3b5c1e` |
| Runtime receipt | 35,077 | `8f1446ae5e6d3430725026fd2fa8b1e4dcbe08fc5d39eebe057c7013b2313626` |
| Stdout | 2,727 | `d8a0e60b176af71ebcbfac7718d487a1e47c5f120736b1f64e3613d421f26196` |
| Exact mesh JSON line plus newline | 1,483 | `be56661e12a192c346613fe5ab1ac5f4606621e7a230c33bef1ce55d8e53a021` |
| Exact material JSON line plus newline | 526 | `d936810e073c6056fdaa6230e4ad1777ad649fb67be80ee8454140f94d9ab5e7` |
| Completion | 5,850 | `a4086e2e0510a20dc53922a431c5cbc3df4ef5a54e2ed8257811e890a367ef02` |

Next action: qualify the exact selected XPAK package identities under separate
admission, then give the bounded reader this key and the genuine observed
extent request. Investigate the selected material's first failed readability
check before choosing a diffuse. The native serializer, XPAK and material
owners received the exact raw texts; this checkpoint authorizes no additional
stock run and proves neither rendering nor owner gameplay acceptance.

## Corrected v2 export D, 2026-10-13

[Launcher PR2](https://github.com/maxis0191/x64-zt-extensions/pull/2) fixed the
v1 command substitution and merged as `cd33c9fb06d3a4d9425b9ff807f473040a979993`.
Its exact head passed targeted local checks and independent review. GitHub
Actions did not execute: runner ID 0, no steps, and the exact-head annotation
reported failed account payments or the spending limit. The existing owner
exception was used; this is not a CI pass.

One distinct D invocation used composed asset source
`b96a617e25d21ef272ac645544cc77d95e94aa7a` and the retained native build D
candidate (21,805,568 bytes, SHA256
`3c9271a0ef0e96cce26f44c30e6b04aa4c2338c86057ac52da489a7bc0e28e7f`).
The real launch builder's argument vector matched the frozen plan:

```text
-t7-iw7-model-v2 mp_freerun_04 p7_fre_platform_cap_02 0
```

The native process exited naturally with code 1 after 5,831.6639 ms,
**Failed / NoExport**, with this v2 refusal:

```text
t7-iw7-resident-static-v2: selected mesh must use one bounded resident shared buffer; flags=9 bytes=18624
```

No manifest, XMB or XSB was produced; serialized readback could not run. The
message confirms the v2 path was reached, but does not establish the meaning
or correctness of the shared-buffer ABI fields. Never relax this guard from
the numeric values alone. Native shared-buffer interpretation is the next
diagnostic task, separate from the corrected launch selection.

The original runner confirmed normal tree closure, input reverification,
engine-output validation, unchanged 27 original identities, 27 retained aliases
and lease release. Its original host reached `Closed`, `CanExit=true`, zero
wrapper guards and zero leases before actual PTY 61743 exited with code 1
(tool chunk `687ab5`). Fresh process/registry observations then confirmed the
host and native identities absent, zero heavy/game processes and zero leases.
Main and the four checked UDP ports stayed absent. An unrelated idle MSVC
telemetry helper was preserved; it was not an active compiler.

Private evidence remains under ignored `t7-export-d-20261013/` and the composed
source package's `runtime/t7-export-platform-d-20261013/`. Only bounded text
evidence was read or hashed after release; no opaque payload was opened.

| Evidence | Bytes | SHA256 |
| --- | ---: | --- |
| `plan.rev2.local.json` | 66286 | `a9f01c1178e40bd6fa9b89115da6934ab56f50a608552c35531a678ddea7aba1` |
| `host-contract.rev2.local.json` | 1362 | `e137304395ea283e070a213e55758bdb82bbc1a365e8199c8b3069ee42c82ae4` |
| native `evidence/receipt.json` | 34257 | `fe79176cd43ffd71512d231b67ce15d4f0d5d27c8733e5f037ca48a06ac4d22a` |
| native `evidence/stdout.log` | 551 | `457b2d4a9aa3bf383b54778cb517cc30642106860fc81e339db3ad5ba27fe785` |
| original `.host-postflight.json` | 1639 | `744ae2ff065d034262f5bf95f6fbf8e9b35159e0ad824052b42b607c64c40509` |
| `host-exit-request.local.json` | 554 | `30ca4c1dc44919e1c1b613a72d3044ad03812cad0f7a70eca03a34bdebdd4a2f` |
| `completion.local.json` | 4368 | `80e414edcafe0a098cb122fb7c887f11c0703f05494afa328e9a991ab075fde7` |

The first preparatory DEFAULT refused relocated historical bootstrap
qualification references. A separate plan revision restored their exact
original paths; its DEFAULT passed without native types, payload hashes, aliases
or leases. Earlier plan files and C evidence remain unchanged. A local
preflight also initially misclassified the idle telemetry process, then omitted
the H1 path-helper import; both corrections happened before the sole Run.
No native rebuild or automatic retry occurred. The composed source package
contains 859 text files (7,804,942 bytes), with reused retail stock as hardlinks.

## Original v1 contract

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
