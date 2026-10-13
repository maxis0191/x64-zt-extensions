# Resident BO3 export C v2, 2026-10-13

## Observed result

One authorized invocation requested `mp_freerun_04 / p7_fre_platform_cap_02 /
LOD0` using `-t7-iw7-model-v2` in its frozen plan. The native process exited
naturally with code 1
after 6340.8583 ms: **Failed / NoExport**. No export manifest, XMB or XSB was
produced, so independent serialized readback did not run.

The 529-byte stdout is byte-identical to [diagnostic B](RESIDENT-EXPORT-B.md):

```text
T7 resident IW7 export refused: t7-iw7-resident-static-v1: pilot requires one selected surface; observed numSurfs=5
```

Stderr is empty. The original host context confirmed the expected v2 argument
vector and the D candidate. It did not independently observe the native command
line. The value 5 does not independently prove the retail ABI, mesh geometry or
semantic count.

Source diagnosis identified the actual launch discrepancy in the executed
`c5e3402` source: `New-T7CatalogueStart` in `T7Catalogue.Profile.ps1`, lines
696–704, reconstructed `-t7-iw7-model` for the shared `ResidentExportV1`
operation, including v2 plans. `Run-T7Catalogue.ps1:106` passed that start object
to `Invoke-H1OwnedStage`; `H1Native.Core.ps1:81` forwarded it to `NativeJob.Start`.
`Probe-NativeJob.cs:134–138` quoted `Start.ArgumentList` directly into
`CreateProcessW`, with no later command substitution. This source chain explains
the v1 refusal. It is source evidence, not a captured native process argument
vector. No native rebuild is justified by this finding.

## Frozen inputs and preparation

The execution source was merge
`c5e3402dd8b556f63d109f4141fc00e3583aa93b`, retained on the preparation branch.
[Native build D](../t7-iw7/BUILD-MULTISURFACE-D.md) was compiled from private
source `0bc0b16aafb2ceb3863f9c20b5f50fb5c8a5f777`; its upstream tool source was
`fab935826c898806855376662a8a03317b3ad8f1`. These are different provenance roles.

Candidate D was 21,805,568 bytes, SHA256
`3c9271a0ef0e96cce26f44c30e6b04aa4c2338c86057ac52da489a7bc0e28e7f`.
Its tuple came from the original admitted build receipt, then the export runner
verified the candidate and alias under its own admission. No opaque file was
read or hashed after lease release.

The [exact D qualification](RESIDENT-MULTISURFACE-QUALIFICATION.md) supplied
103 bindings: 75 text and 28 binary. Compared with B, 80 bindings remained
identical, 18 changed and five were added. The request, donor, 23 bootstraps and
all 26 noncandidate input metadata rows remained identical to catalogue F.
The v2 marker contained only its schema; the diagnostic marker was removed.

One preparation DEFAULT completed with `PlanCheckedPendingGO`, actual PTY
`98575`, exit 0, tool chunk `cc8349`. It loaded no native types, hashed no binary,
created no alias and acquired no lease. The coordinator explicitly resolved an
initial requirement mismatch: the existing validator requires four ordinary
empty directories (`runroot`, `work`, `evidence`, `temp`). Their creation was
authorized; attempt markers, host sidecars and output data remained absent.

The future launch used `-NoLogo -NoProfile -NoExit -File` and the exact frozen
host contract. Raw working-tree source bytes were pinned separately from Git
blob bytes, with LF/CRLF normalization checked only for source equivalence.
No frozen plan or evidence was rewritten after review.

## Closure and evidence

The original runner confirmed tree closure, lease release, input reverification,
engine-output validation, unchanged original metadata and retained aliases.
All 27 original identities and 27 alias identities were checked under admission.
There was no quarantine, forced termination, incident close or automatic retry.
Main remained stopped and the preserved unrelated process was unchanged.

The original in-memory host reached `Closed`, `CanExit=true`, zero wrapper
guards and zero registered leases. Actual PTY `33625` then returned exit 1,
tool chunk `b0a9a9`; exit was observed directly, not inferred from absence.
The independent witness captured at `2026-10-13T10:42:19.7788781Z` confirmed
absence of the three exact process identities, descendants, registered leases,
heavy workloads, games and the four checked UDP ports. It matched five JSON
pins and the producer's actual exit. It read no stdout, opaque manifest or binary.
Its checkout was clean at `99190cc`, with export and scheduler sources unchanged
from the execution source. That later source observation does not relabel C.

The following private evidence remains in ignored runtime storage. `plan/*`
means `t7-export-plan-platform-c/*`; `run/*` means `t7-export-platform-c/*`.
Full machine paths, process identifiers and lease tokens are intentionally absent.

| Evidence | Bytes | SHA256 |
| --- | ---: | --- |
| `plan/plan.local.json` | 66436 | `8d634bb499bd0ddb1ae983127091253aac948ef62b777638cc5d89c889f8e42a` |
| `plan/host-contract.local.json` | 1616 | `4f12dafb12618403ab54e11330d8fc269d0edaeea9594c1ffdf41da8662f4e1a` |
| `plan/envelope.local.json` | 36226 | `8e17f1a0356ac9c6ddffcd2c241e2d92cfbb6e44622e198c443139d62e1f051c` |
| `plan/budget-correction.local.json` | 3771 | `d65f71affd501771484146c95dc54979b88c8c37125b667bfe271380d63bcfc9` |
| `run/evidence/receipt.json` | 34229 | `9eaa980cc12bb7fdb98ac9cdb01bd581fd8382c608ecfeeed10ea7f584fa6e9b` |
| `t7-export-platform-c.host-postflight.json` | 1639 | `09ee39fd2da92fc3c21af1a592288114446e15a3de4a86a16e2970ccbf781a4c` |
| `plan/host-exit-request.local.json` | 1462 | `f153739fb34a3c562b4718384aa3fd1f85c831136f579ffdbbc0d92d8146dbf3` |
| `plan/host-exit.local.json` | 1720 | `e398f3451045d7099a90027b55edb93e875c6b59d4ce95b32a48d6d434419863` |
| `plan/diagnostic-observation.local.json` | 2624 | `e4a72236504b7910d918f8396e345e53530017ad06e4a6229bba5048bfe9d248` |
| `plan/completion.local.json` | 9238 | `0039034d1fd063fbc2106fe4f40f779ad5c1c4bd73af4b3597539a0e210da507` |
| `run/evidence/stdout.log` | 529 | `e6585fa483bc1a2ae99d75f16e9486a16b6f9107b228782dd262ea591987d936` |
| independent `t7-export-platform-c-independent-absence.local.json` | 7850 | `7d6af4a119bec929a8704ab2abf21209b45f5afe3954a4515acc1ce1cad06850` |

## Accounting and next action

The producer counted **300,225 logical bytes in 22 new files**, including
preparation and completion evidence, before the independent witness. Including
that 7,850-byte witness gives **308,075 logical bytes in 23 new files**. The 27
retained hardlinks represent 808,903,960 logical bytes of existing content and
are excluded from new data. The run tree has 45 entries: 34 files and 11
directories. New engine DLL and opaque manifest sizes were recorded as metadata
only after release. These are file-length totals, not NTFS allocation measures.

The fresh C allocation remains 70 MiB: at most 6 MiB preparation/evidence plus
64 MiB mutable output. The logical runner cap remains 876,012,824 bytes,
including shared aliases. Physical/commit admission remained 6/8 GiB and
native/group/cleanup deadlines remained 120/200/5 seconds.

The producer initially counted C's allocation twice in its pool arithmetic.
The appended correction preserves the original evidence: 1,569,871,019 bytes
before C plus 73,400,320 bytes for C equals **1,643,271,339 allocated bytes**,
leaving **2,651,695,957 bytes** in the 4 GiB pool. No older allocation was reused
and no global filesystem recount was claimed.

The correction selects the native command from the existing strict v1/v2 plan
contract. Its regression test executes the real runner launch expression and
owned-stage function with a synthetic `NativeJob.Start` capture. The test failed
against the old source at the v2 launch boundary, observing the v1 arguments;
v1 and diagnostic commands remain v1. The corrected asset-product commit
`b96a617e25d21ef272ac645544cc77d95e94aa7a` passed 1,089 targeted synthetic
checks in a composed source workspace, including 338 request/launcher checks,
230 diagnostic checks, 277 v2 geometry checks and 244 build-qualification
checks. An independent source review found no blocker. Frozen C evidence is
unchanged; these checks do not execute the candidate.

Next action: execute the distinct corrected export using the retained D
candidate after shared workload admission. C remains an unsuccessful
export; it establishes no serialized readback, gameplay or compatibility success.
Its historical budget describes that invocation only; the owner's later resource
policy and authorization govern subsequent work.
