# First resident BO3 export: A, 2026-10-13

## Result and limit

The request selected `mp_freerun_04 / p7_fre_platform_cap_02 / LOD0`, using
`resident-rigid-one-lod` and source `2e62add853589ccc76c5476949e94955dd6ccf20`.
The native candidate was the retained publication-A build, SHA256
`31b9d908d15fb5f0bf17a7b27309dc7183458d5e586dfc6e427cc8ec2b3fa647`.
This identity comes from the frozen plan and admitted validation; it was not
rehashed after release.

One native invocation exited naturally with code 1 after 6626.454 ms. Its
508-byte stdout contains `pilot requires one selected surface`; stderr is empty.
No manifest, XMB or XSB was produced: the outcome is **Failed / NoExport**.
Catalogue/message hooks were deliberately inactive for the export CLI.

The guard is `mesh.numSurfs == 1`, so the refusal alone does not distinguish
zero from several surfaces or an incorrectly interpreted structure field.
There is no evidence yet of a multi-surface donor, successful geometry export,
engine I/O compatibility, IW7 FF or rendered BO3 model. The later diagnostic
source `d76bedcaee822d3e21349bfd770c3b1433f65375` adds the numeric field to the
same refusal before any surface access. It has favorable independent source
review and 71 producer-reported source checks; no native rebuild follows from
those checks. The existing build recipe refuses the changed header until its
dependency proof and exact transition are reviewed.

## Closure

The host's actual tool result is PTY 4913, chunk `7d6932`, exit 1, also present in
completed command `exec-232ef1fd-0cd0-4d05-a6e9-1416ac8f8a17`.
The original receipts report normal closure, no quarantine or requested stop,
released lease, closed guards, revalidated inputs, unchanged original metadata
and retained aliases. The independent witness at
`2026-10-13T05:33:12.2497924Z` links the actual exit and confirms the captured
process identities/descendants and run-root processes are absent, with no shared
heavy-work lease or game/lab listener remaining. Main remains stopped and the
unrelated retained Python process is preserved.

The witness does not inspect an old kernel job/handle, re-read stdout or infer
the host exit from process absence. It reads small closure JSON only; no game
payload or native binary is read or hashed after lease release.

## Retained evidence pins

These local evidence filenames are relative to the producer's ignored runtime,
except the independent receipt held by the inventory checkout.

| Evidence | Bytes | SHA256 |
| --- | ---: | --- |
| `t7-export-platform-a-request.local.json` | 195 | `e0a619fd2f9eedc32540fb4536cd26acec03a30353d8f37098c20400a98b7122` |
| `t7-export-platform-a-plan.local.json` | 64564 | `1b991b42a9c7b57f2e461d1e1aaba8bbb193de65220f046b72fc020c6f859ba4` |
| `t7-export-platform-a/evidence/receipt.json` | 34311 | `262dbbe643b58b84cfa68841decb18746724828bf85ef9a6332e83f062b42e09` |
| `t7-export-platform-a.host-postflight.json` | 1642 | `ac99e54251e8e1c844f84ed4bbcc8969ed27d8f99feb97fdae521d9b321b35d2` |
| `t7-export-platform-a-host-exit.local.json` | 1400 | `4c73313c2d57d65e37a7948d8ed0158005f2554315d312bd86e03883b2b12f30` |
| `t7-export-platform-a-completion-corrected.local.json` | 12664 | `e32be681e8676c183cba2158c38c698b6b7340beb431800d8769b6ef3d3d6c7b` |
| `t7-export-platform-a-independent-absence.local.json` | 6202 | `3124b63c6cebed98245d2d1926906f53e1f5494e63b41b80736280251ae8b434` |

The corrected completion retains the earlier accounting mistake, where two
PowerShell array `.Length` values counted files rather than bytes. It records
23 new files / 299352 bytes, plus the separate 6202-byte witness: 305554 known
scoped bytes. The 27 existing hardlink aliases represent 808849688 logical bytes
and are separate from new data. These are file-length totals, not a measurement
of global or NTFS allocation. The conservative 70 MiB attempt allocation remains
reserved in the orchestration ledger.

## Next action

Later checkpoint: the [numeric diagnostic build](../t7-iw7/BUILD-SURFACE-COUNT-A.md)
has passed and closed independently. The exact candidate transition in
ResidentExportV1 has favorable source review; a new operational export plan and
fresh admission remain required. The following paragraph records A's original
next action, before that build. A and its receipts remain unchanged.

Build the reviewed numeric diagnostic through the existing incremental pipeline
after its exact header-dependency transition is supported and reviewed. Freeze a
new candidate/plan and obtain a fresh shared admission before another attempt.
Preserve A unchanged; measure the count before deciding which conversion change
is justified. Never silently discard surfaces or declare FF/render acceptance
from the diagnostic alone.
