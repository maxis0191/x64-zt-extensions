# Surface-count diagnostic build A: passed and closed, 2026-10-13

One authorized build compiled fresh main and CLI objects and linked the
surface-count diagnostic candidate. All three native roots exited zero, their
original jobs closed empty, inputs were reverified and the lease was released.
The host actually exited zero; an independent witness confirmed absence of all
eight process identities. The candidate was **not executed** and no export ran.
The selected model's `numSurfs` remains unknown; this checkpoint proves
compilation and closure, not runtime behavior or multi-surface support.

## Reviewed source, exact plan and reuse

- Repository source: `43e663a98817332a70855186bfb52a95fe425e71`, PR193 merge.
- Pinned native source: `fab935826c898806855376662a8a03317b3ad8f1`.
- Plan: `runtime/t7-surface-count-build-plan-a/build-plan.local.json`,
  303182 bytes, SHA256
  `4bfb8c9aa45352b0e99acc0a66eab8df93eec8bcac15b9443b766e01a8fcb9e6`.
- Profile: `t7-catalog-message-publication`, schema
  `iw7.t7-message-publication-build/1`, stages **main, zonetool11, link**;
  preparation explicitly enables `--resident-surface-count-diagnostic`.

The existing `mesh.numSurfs == 1` refusal now appends the observed unsigned count
before dereferencing the surface array. It does not select surface zero or relax
the exporter contract. The prepared adapter is 13545 bytes, SHA256
`701e3d1eccb0e98ecccfd2012215aaf7eff8db7bd974b184e86648a138b6e3c3`,
replacing only the permitted old header pin
`6d2da3d4f7c3d0686909dc488f3d176ee2dd250e8d43d9a3cd9bcfa701482777`.

Six of seven prepared files, including main and CLI source, match
[publication build A](PUBLICATION-BUILD-A.md) byte-for-byte. All four response
files match it after prepared/run-root normalization; `xpak.obj.rsp` is retained
recipe evidence, not an executed stage. The link reuses 410 E7 objects and the
original C `xpak` object, plus 18 project libraries and one resource, alongside
the two fresh objects. No cache, SDK, stock or source tree was copied.

The plan's `ReuseCompile.ResidentSurfaceCountDiagnostic` proves the bounded
exception using receipt-pinned C dependency JSON and sealed E7 read/compile/link
journals. All 413 E7 linked objects have unique producers and matching dependency
records; none consumes the adapter, including through PCH. The C helper and
`xpak` also do not consume it; the C CLI does and is recompiled. Missing,
ambiguous or additional consumers fail closed. The default runner check passed
with 1080 input pins and none missing, without native loading or admission.

## Build outcome and actual host exit

Fresh preflight found no leases, heavy/game processes or relevant UDP endpoints.
Main was already stopped; the unrelated Python process retained its identity.
Admission used the unchanged 4 GiB physical / 6 GiB commit estimates, 120-second
stage limits, 600-second group limit, 5-second cleanup and 256 MiB output limit
including a 1 MiB receipt reserve. Exactly one invocation ran, without retry.

| Stage | Root PID | VCTIP PID | Native exit | Elapsed |
| --- | ---: | ---: | ---: | ---: |
| main | 13112 | 25304 | 0 | 3.917 s |
| zonetool11 | 35656 | 2612 | 0 | 7.482 s |
| link | 6792 | 22076 | 0 | 3.212 s |

Each stage completed the existing original-job compiler telemetry policy with
two identity-matched VCTIP observations, root exit zero and zero active/listed
members after closure. All three stderr logs are empty. The admitted group took
33.359 seconds and finished at 06:25:19.2350056 UTC on 2026-10-13.

Receipt `runtime/zt-t7-surface-count-a/receipt.json`, 22393 bytes, SHA256
`6cc2cab523115defa9ee0df2a9c5292a286236ce96d935fb374145a663510810`,
reports `Passed`, `InputsReverified`, `TreeClosureConfirmed`, `LeaseReleased`
and `Quarantined=false`. Lease `312f1011f3f84c6f8028bd6ba0a09a9e` was released.
The original host confirmed `Closed=true`, no lease, zero guards and no
quarantine before exiting.

Host PID 6444 was created at 06:24:39.1653940 UTC; parent PID 34924 at
06:24:38.9873480 UTC. Session **26937 actually completed with exit code 0**,
tool chunk `e08409`; absence is not used to infer this exit code. The host-exit
proof `runtime/t7-surface-count-build-a-host-exit.local.json` is 1513 bytes,
SHA256 `ef51bb73897669ca29fc79a267ca1218d5a031df3b5602d55364d8e8353d989d`.

## Candidate identity and compiled dependency

Candidate `runtime/zt-t7-surface-count-a/link/zonetool-t7.exe` is **21751296
bytes**, SHA256
`859154f75732a3515b70bd308f769c758c8a1b73e75936d774545e10d27081a6`.
This pin comes from the original receipt under admission. No native artifact
was reread or rehashed after lease release.

CLI dependency evidence
`runtime/zt-t7-surface-count-a/zonetool11/dependencies.json` is 76800 bytes,
SHA256 `3e7026826a953fa2f749c358b62c5f57b321b13db71e3c7f5f9260bbe6b1d631`.
Its 637 includes contain exactly the new plan's
`prepared/t7_iw7_resident_model.hpp`, with MSVC-normalized path casing.
Main's 541 includes contain no resident adapter. These bounded text records
were checked after closure; the new adapter was consumed by the actual CLI
compilation, while its runtime diagnostic remains unobserved.

## Independent closure and storage scope

At **06:33:04.2492301 UTC**, the independent witness confirmed that all eight
exact host/parent/compiler/telemetry tuples were absent. Scheduler and fresh
CIM observations agreed: zero scoped descendants, root processes, leases,
heavy/game processes and UDP endpoints on 27016, 27116 and 27117. Main remained
stopped and the unrelated Python identity was unchanged. The witness also
verified the completed owner tool record's actual exit zero. Original job
closure and binary hashes remain original-host evidence; the witness neither
reopened native payloads nor adopted old jobs.

Witness retained in the `voice-resume-inventory` worktree at
`runtime/t7-surface-count-build-a-independent-absence.local.json` is 7904 bytes,
SHA256 `fd10afff15e24122db747fa200aa0c99cffee39fbe3969e887404108939eac05`.
Source stayed at `43e663a9` and the checkout was clean throughout that witness.

Completion proof `runtime/t7-surface-count-build-a-completion.local.json` is
12504 bytes, SHA256
`9bf95a89ffc61ada843a297f9f232d8afe79d8964ecd0003ace9e7506046d60d`.
It accounts for 38 new preparation/build/evidence files totaling **168436315
bytes**: 15 frozen preparation files (486259 bytes), 17 runtime files
(167929890 bytes), five sidecars (7662 bytes) and the completion proof itself.
Adding the independent witness yields **39 files / 168444219 bytes**, before
this tracked note. Runner-observed peak output was 195872039 bytes. Preparation
and evidence fit the 16 MiB allowance, native outputs fit 256 MiB, and combined
accounting fits the approved 272 MiB slice. These are logical file sizes, not
NTFS allocated bytes or a measurement of global historical growth.

All original plans and receipts remain immutable. Earlier
`IndependentClosurePending=true` snapshots retain their capture-time meaning;
the later witness supplements them. No future export preparation or execution
is authorized by this checkpoint. Next is coordinator integration, review of
the candidate-specific export contract and a separate runtime GO with fresh
admission. `CandidateExecuted=false`, no export and `Ready=false` remain true.
