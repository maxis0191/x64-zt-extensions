# Resident BO3 export diagnostic B, 2026-10-13

## Observed result

One invocation selected `mp_freerun_04 / p7_fre_platform_cap_02 / LOD0`, with
the unchanged `resident-rigid-one-lod` request, 23 qualified bootstraps and
catalogue F. The runner source was `c7fc4383c0542a3fb068f23e0a902012e8944113`.
The closed diagnostic build supplied candidate SHA256
`859154f75732a3515b70bd308f769c758c8a1b73e75936d774545e10d27081a6`
(21,751,296 bytes); its identity was verified under admission, not rehashed
after release. The exact runtime image was `work/t7-zonetool-candidate.exe`.

The native process exited naturally with code 1 after 6460.8792 ms. Its
529-byte stdout contains:

```text
T7 resident IW7 export refused: t7-iw7-resident-static-v1: pilot requires one selected surface; observed numSurfs=5
```

Stderr is empty. No manifest, XMB or XSB was produced: **Failed / NoExport**.
The diagnostic read the value 5 at the existing guard. This is not independent
proof of the retail ABI, semantic surface count, serialization, compatibility
or gameplay. B does not justify dropping four surfaces or claiming an export.

## Preparation and observation limits

The first metadata-only preparation stopped before writing files because a
PowerShell DateTime cast converted a UTC string to local time. Comparing UTC
ticks fixed the check; the candidate metadata had not changed. DEFAULT then
passed without admission, native types, payload reads or runtime files.

The first local preflight command inherited from catalogue F omitted the
resident export profile import. It stopped on an unresolved validation function
before the launch proof, lease, attempt or native invocation. Adding the same
source import as the reviewed wrapper allowed a fresh preflight and the single
authorized B invocation. No runtime retry or source-framework change occurred.

A separate bounded stdout observer failed to obtain its read guard during the
lease. It returned `ReceiptAlreadyPresent / ObservedUnderLease=false` (session
51566, exit 2, tool chunk `9744de`). The existing runner inspected the absent
export manifest under admission. The producer read the small stdout text after
release and again under a size-bounded read guard after actual host exit; this
must not be reported as a live-lease stdout capture. No opaque payload was read
or hashed after release. A and F, and all original B evidence, remain unchanged.

## Closure and retained evidence

The original in-memory host reached normal `Closed`, `CanExit=true`, zero
wrapper guards and no lease, with 27 original and 27 alias identities checked.
Input revalidation, engine-output validation and unchanged source metadata all
passed. There was no quarantine, requested termination or incident-close route.
Actual PTY 2224 returned exit 1, tool chunk `26dbb6`, corroborated by completed
command `exec-de08b554-06f5-45e8-94cd-5ee4241ad470`.

At `2026-10-13T07:19:35.8291703Z`, the independent inventory witness confirmed
the exact host, parent and native identities were absent, with no descendants,
run-root process, heavy workload, lease, client or relevant listener. Main
remained stopped; the preserved Python identity was unchanged. It did not
reinspect old native handles, read stdout or independently validate the count.

Filenames below are under the `modding-distribution` checkout's ignored runtime;
this differs from export A's `modding-h1-model-bridge` checkout. The independent
absence file is retained by the `voice-resume-inventory` checkout.

| Evidence | Bytes | SHA256 |
| --- | ---: | --- |
| `t7-export-platform-b-plan.local.json` | 65250 | `0f858bda28385faa9c4a87ad77585e2229345a7c4ab9729e7e8f8518554e76ff` |
| `t7-export-platform-b-envelope.local.json` | 59326 | `1a7a574f902de4488debb1d9f8717ac3618ed919959face8c62d4ac9efacf4d3` |
| `t7-export-platform-b/evidence/receipt.json` | 34231 | `0b9ea08fc58bf3039b5aa59a861f6742dc392a6e7f093e721a0ae23741c978ff` |
| `t7-export-platform-b-host-exit.local.json` | 1713 | `5cfb37caf4a425ac7f6720c5b49a0f5c1b38034c7e39d1d1e25a23553e7928bb` |
| `t7-export-platform-b-diagnostic-observation.local.json` | 2202 | `340acd96dd573ca212e139050e79f716b429916a9a1cb5d87cf0998efb2634ab` |
| `t7-export-platform-b-completion.local.json` | 8995 | `0cd19928d6133b46cbb000d4a111a7303b49a4fa1d720a97ac1dc600fc4e0c84` |
| `t7-export-platform-b-independent-absence.local.json` | 6412 | `ddd28dc54f06627170588af159e7282a57d4d28461aa70fba97dc96a5443fe29` |

The producer counted 295,496 logical bytes in 19 new files. Adding the separate
6,412-byte witness gives **301,908 bytes in 20 files**. The 27 retained hardlinks
represent 808,849,688 logical bytes and are excluded from new data. These are
file-length totals, not NTFS allocation or a global storage measurement. The
70 MiB allocation remains inside the existing 4 GiB pool / 10 GiB global cap.

## Next action

Develop and source-test a separately selected, bounded multi-surface v2 contract
that preserves all ordered surfaces and material occurrences. Preserve strict
v1 compatibility. Native build qualification, an operational plan, admission,
export, independent readback and gameplay remain separate gates; no new Run is
authorized by this checkpoint.
