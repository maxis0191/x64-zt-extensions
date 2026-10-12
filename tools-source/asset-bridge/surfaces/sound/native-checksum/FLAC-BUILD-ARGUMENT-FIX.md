# FLAC build A failure and source-only B correction

2026-10-12. One authorized invocation of the exact FLAC Plan A failed. It was
not retried. Its Plan, dispatch, overlay B, response files and output directory
remain unchanged. The earlier source-only checkpoint is historical evidence,
not native build acceptance.

## A: observed execution and bounded diagnosis

The original job exited 1 after eight successful phase receipts: both checksum
compile/link/run triples, then FLAC probe compile and link. There is no
`probe-flac-run` phase directory and no final `build-receipt.json`. The FLAC C++
probe was compiled and linked, not executed. No consumer/candidate build, dump,
codec or gameplay transaction ran.

The missing final receipt caused a secondary completion-collector error. The
original worker's stderr was not captured by the existing no-window job owner,
so no original Python traceback is available. Source inspection found that A's
next command used `arguments=[]`, while the unchanged shared
`material_v2_phase.validate_spec` requires one to forty arguments. Passing the
exact next-phase spec into that real validator deterministically reproduces
`ValueError: bounded literal arguments required` before log creation or Popen.
This is a reproduced contract failure consistent with the observed stop, not
a recovered runtime traceback.

The failed original job was positively closed with active count zero. All
1412 input guards were disposed, inputs were verified before and after, and the
original reservation was released. The final state stayed `Success=false`,
`FinalArtifactsVerified=false`, `DeferredArtifactProofPending=true`. The host
quarantine entry was absent. After preserving diagnostics and an independent
child-absence check, the persistent host exited with observed code 1. An
independent witness established host/parent/root/residual absence and no heavy
job or reservation. Main and UDP 27016 were absent; the unrelated Python
identity was preserved. No output artifact or binary was read/hashed after
release; only small text evidence and source were inspected.

Retained text evidence under `runtime/`:

| Relative file | Bytes | SHA-256 |
| --- | ---: | --- |
| `zt-sound-flac-a/supervisor-state.json` | 3510 | `887ea4b6d1493fe7b250a15cc4cbb6f5581ba59488b7e2121bbc73d327643f14` |
| `content-surfaces/original-sound-flac-build-host-a-outcome.local.json` | 1298 | `b949136c5cda3d1200274b81ed441547fe06bc11e81b4d0d5340e838e945ae25` |
| `content-surfaces/original-sound-flac-build-failure-a.local.json` | 6813 | `e51aa19c4889d9aade563003b0d71e30a8481de5b6c4523f0d7a7b62415acb52` |
| `content-surfaces/original-sound-flac-build-host-a-exit-b.local.json` | 1298 | `059120be8fa6f26086cbb7fd6bab47f5270ec03346c882cf6702b121f860fd0e` |

The earlier `host-a-exit.local.json` contains only null after a witness-script
boolean typo. It is retained as invalid evidence; the `exit-b` file is the valid
independent observation. This witness correction did not rerun native work.

## B: minimal correction, not executed

The probe now requires exactly `--verify-headers`; missing, extra or unknown
arguments return 64 before processing any case. The Python and PowerShell
closed profiles require the same sole argument. The regenerated run command
therefore satisfies the unchanged shared phase validator. No shared provider,
historical fourteen-stage profile or native dump implementation changed.

New overlay `original-sound-flac-dump-source-c` preserves the three unchanged
source identities. Only `flac_dump_probe.cpp` changes: 2226 bytes, SHA-256
`3f0015a2e7958ccb4d7194e876212767ea19b0f3467ab52f96d3993f39064e86`.
Its source manifest is 1610 bytes, SHA-256
`78956400e563b4042f0c77f323005c3345b47f962b44daf91bccb43fad8cfa74`.

The new Plan `runtime/content-surfaces/original-sound-flac-build-plan-b.local.json`
is 44970 bytes, SHA-256
`2568d848bb7feaedfff530abdc3e25782c7873ca0b85539a6a89901834879964`.
It binds 17 commands, 14 responses in `original-sound-flac-build-review-b`,
51 source pins and the still-absent output `runtime/zt-sound-flac-b`.
Dispatch `original-sound-flac-build-command-b.local.ps1` is 2569 bytes, SHA-256
`9c450c7347473cbf591b9e2b8854b5fc394150bdfe2292d9d6500d5792277c37`.
Both literal entry invocations bind only the new Plan path/hash; default mode
validates source only, while Build requires the separately approved persistent
PS7 host. The entry source remains 6374 bytes, SHA-256
`b1f3c5222f8d99f005cfe5a79002b5fdb3b5b9b02daa29a0b09a1053c97ace18`.

Validation: 22 Python build/profile/worker/SDK/response tests and 11 FLAC source
tests passed. The integration test passes all 17 actual worker-generated specs
through the real shared `validate_spec` and stops before executable reads or
Popen; it also reproduces A's empty-argument refusal. The profile refuses empty,
extra and unknown probe arguments. C++ argument behavior is source-checked,
not newly compiled. PowerShell tests passed: Plan 20, SDK 14, receipts 15/21,
lifecycle 13 cases/72 assertions and 19 cases/283 assertions. The default-entry
test passed 119 source-only open/hash checks and all guard/release assertions.
No SDK binary was opened by default Plan/preparation.

The default B dispatch returned PlanOnly with native/admission/Ready false.
The 32-file receipt ceiling and mandatory post-closure six-artifact proof remain
unchanged. B requires fresh coordinator review and execution approval; no new
resource measurement, lease, compilation or retry accompanies this correction.
