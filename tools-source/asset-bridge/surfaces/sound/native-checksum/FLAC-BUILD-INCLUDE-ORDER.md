# FLAC B unqualified build and source-only C correction

2026-10-12. One separately authorized invocation of Plan B completed all 17
native phases with exit zero. Its real C++ FLAC probe emitted 103 successful
cases, unchanged inputs and successful extent checks. The worker exited zero
and emitted its build receipt. No dump, codec or gameplay transaction ran.

The supervisor nevertheless rejected completion with
`Completion mismatch: actual FLAC-profile compiler include paths`. B remains
unqualified: `Success=false`, `FinalArtifactsVerified=false` and
`DeferredArtifactProofPending=true`. Its six worker-declared artifact identities
were not accepted by the mandatory final supervisor pass. The later source fix
does not change that result or qualify B retrospectively.

## Exact mismatch and closure

The first failing report was `probe-original-compile`. Both lists contained the
same 156 paths. At zero-based index 80, PowerShell placed
`include/vcruntime_exception.h`, while the Python receipt placed
`include/vcruntime.h`. `Assert-FlacIncludeBytes` used culture-sensitive
`Sort-Object`; `include_report` uses Python character ordering. All nine retained
text reports have exactly the same path sets as their declarations and match
them in sequence under ordinal ordering. Counts: 156, 156, 90, 621, 551, 547,
549, 562 and 94.

The original job was positively closed with root exit zero and active count
zero. Inputs passed before/after checks, all 1412 guards were disposed and the
original lease was released with a null retained token. The host quarantine
entry was absent. Independent checks found no native children, heavy job or
lease. After preservation of this evidence the unqualified build's host exited
with observed code 1; host/parent/root/residual absence was independently
confirmed at 17:41:20.9352221Z. Main/UDP 27016 were absent and the unrelated Python
identity was preserved. No output artifact or binary was read/hashed after
release. Post-release diagnosis used retained text only.

| Retained text under `runtime/` | Bytes | SHA-256 |
| --- | ---: | --- |
| `zt-sound-flac-b/supervisor-state.json` | 3236 | `1649c3f9092b54a63962946aa4a9c35e35bd4ece66edb48737f7c4452eac0a1b` |
| `zt-sound-flac-b/build-receipt.json` | 426632 | `39d1c6643c22161bf7d2ab079deabb5c4b749ac7140d167389fea3efb6e06561` |
| `content-surfaces/original-sound-flac-build-host-b-outcome.local.json` | 1146 | `70d8ced8b0471411fb81e475a3c4bac331bfaa408c9abfa2cc5b8a6f15a9aafd` |
| `content-surfaces/original-sound-flac-build-failure-b.local.json` | 4177 | `733972e87ad7a154f20372f596d89d3291c88efac7fc4bc0ea4cca3c3d7d566e` |
| `content-surfaces/original-sound-flac-build-host-b-exit.local.json` | 1078 | `a13ab636dd20b8622e98c4c5b188c904bb27890dccbd56705269682fc72acaa4` |

## Minimal validation correction and C preparation

The only production change replaces the culture-dependent sorting in
`Assert-FlacIncludeBytes` with `[Array]::Sort(..., StringComparer.Ordinal)`.
The same parsed path set, exact canonical order comparison, include provenance,
source guards, provider identities, 32-file cap and six-artifact final proof all
remain required. No native source, historical fourteen-stage profile or shared
provider changed.

The new regression first failed against the previous helper, then passed with
the ordinal correction: 24 assertions across en-US, fr-FR, tr-TR and invariant
culture, including punctuation, duplicate case variants, wrong order, missing,
extra, changed and relative paths. All nine retained B stdout reports replayed
successfully under read guards. This text replay opens no binary/artifact and
cannot promote B. Receipt fixtures 15/21, Plan C contracts 20 and default-entry
119 source-only open/hash checks also passed.

Plan C is a fresh 44970-byte
`runtime/content-surfaces/original-sound-flac-build-plan-c.local.json`, SHA-256
`19d8a83dc326b47dbe48e541152c10907849798d12a5adcef63c794e02a0232f`.
It reuses immutable overlay `original-sound-flac-dump-source-c`, writes reviewed
responses in `original-sound-flac-build-review-c`, and proposes still-absent
`runtime/zt-sound-flac-c`. A source-only comparison with B established that only
private output relocation, the 14 corresponding response identities and the
validation helper identity changed. Native commands/sources are otherwise equal.

Dispatch `original-sound-flac-build-command-c.local.ps1` is 2569 bytes, SHA-256
`9859b0e7fee07b76a6b809f761e0e5fa41a5d28b86ca4e72ab620ef2593f622c`.
Its default returned PlanOnly with 17 commands and native/admission/Ready false.
C has not been executed. A and B remain preserved. DumpOnly preparation and any
later strict codec check must wait for a fully qualified candidate and separate
coordinator approval; F must not be regenerated or relabelled.
