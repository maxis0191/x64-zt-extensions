# Multisurface native build C: failed and independently closed, 2026-10-13

The single authorized C build compiled main successfully, then MSVC rejected a
T7 layout assertion while compiling the CLI. Link never ran and no candidate
EXE was created. The original job closed, its lease was released, guards were
disposed and the original host actually exited one. This is a preserved failed
candidate, not a successful multisurface build or export.

## Source and preparation

- Repository: `7f23ae5c19a71e09d382026449a66c9c632e90ed`, PR200 merge.
- Native source: `fab935826c898806855376662a8a03317b3ad8f1`.
- Plan `runtime/t7-multisurface-build-plan-c/build-plan.local.json`: 365638 bytes,
  SHA256 `86ace553134b78596d513ba6175bf7aacad8f25fbeae9932d6285313f946c583`.
- Runner: 34246 bytes, raw SHA256
  `c184f179f7d30cc16351b8a01ffa21b69b6a2ec712b4de6b81d710242c15a1db`.
- Command envelope: 6379 bytes, SHA256
  `3a5db99616b400fc4d1fba043834f30f6b18684c10ec200dcb2dcdaef51892b9`.
- DEFAULT evidence: 4088 bytes, SHA256
  `74603b90d66b16957ad68cf5d98a858b978d90ca2b1123427ab8b6dc41012b3e`.
- Preparation proof: 10949 bytes, SHA256
  `d2dac433f3ed699ce28d02fffa44ac39c65b3722231ad10e51fbdb27d388bb4f`.

DEFAULT tool chunk `b25b28` exited zero with 1146 Inputs, 135 text Bindings,
six binary metadata Bindings and zero missing pins. All 1146 Inputs and the
complete retained C/D2/E7 proof match B. All seven prepared sources match B;
all four response files match after preparation/run-root normalization. Only
the runner and four response hashes changed among normalized Bindings.
The planned link retained 411 objects plus two fresh objects, 18 libraries and
one resource. A and B preparation artifacts remain unchanged and non-runnable.

## One admitted attempt

Fresh preflight at 09:03:15.7663536 UTC found both priority chats not loaded with
completed last turns, zero leases, heavy processes and relevant UDP endpoints,
and no owner client/Main process. Python PID23352 retained its exact
2026-10-11T14:25:16.1964170Z identity. Available RAM was 14784798720 bytes;
commit was 26549714944 of 47564615680 bytes. The 4 GiB physical / 6 GiB commit
projection passed. The runner then performed its own atomic admission.

Exactly the reviewed NoExit command ran once, in PTY session **58305**. There
was no retry, alternative host, new tool, export or game launch. The unchanged
limits were 120 seconds per stage, 600 seconds per group, five-second cleanup,
256 MiB native outputs including the receipt reserve and 16 MiB preparation.

| Process | PID | Created UTC | Outcome |
| --- | ---: | --- | --- |
| Original host | 29208 | 09:03:27.5224200Z | Actual PTY exit 1 |
| Launcher parent | 23432 | 09:03:27.2894320Z | Original parent identity retained |
| Main compiler | 9204 | 09:03:49.534743Z | Exit 0, original job closed |
| Main VCTIP | 5112 | 09:03:51.7647322Z | Two observations, original job closed empty |
| CLI compiler | 28748 | 09:03:55.5668997Z | Exit 2 from final original owner |

Main completed in 5990.569 ms. The group finished at 09:03:58.666583Z after
20910.912 ms. No CLI VCTIP identity was published in the failed stage's receipt;
none is inferred from another build.

## Compiler failure and closure evidence

CLI stdout is 207 bytes, SHA256
`b96df7ab8afc88e5ab565ea5ba0778720587993ebd78c3a33e55097a0fb2ca7d`:

```text
t7_iw7_resident_model.hpp(143,32): error C2607: static assertion failed
```

The assertion spans the expected T7 mesh/shared/surface/rigid sizes. The
runner's later `Successful original compiler handle identity required.` error
comes from the success-only compiler telemetry guard encountering that failed
compiler. It does not replace the compiler diagnostic. The assertion remains
intact pending an independently reviewed source/contract correction.

`runtime/zt-t7-multisurface-c/receipt.json` is 11011 bytes, SHA256
`cf8954ffab62b25b8ce18cf2fa098676a624438a447a941b3399bb9e29b44beb`.
It reports Failed, final ExitCode2, global TreeClosureConfirmed=true,
LeaseReleased=true and Quarantined=false. Lease
`1469498f1c694c87b816a909038e181f` was released. The CLI stage snapshot still
has TreeClosureConfirmed=false and lacks its stage ExitCode because failure
interrupted that stage before final cleanup. Preserve that snapshot: later
global/original-owner evidence establishes closure, not CLI compile success.
The final InputsReverified field is absent; full final revalidation is not claimed.

At 09:04:48.4872045Z the original host observed ContextClosed=true,
OwnerClosed=true, zero guards, no lease and CanExit=true. At 09:05:48.3511339Z
it rechecked those conditions and an empty registry before requesting exit one.
**Tool chunk `e7cac8` actually completed PTY58305 with exit code 1.** This code
was not inferred from process absence.

The original-host closure, exit request and actual-exit proofs are respectively:

- `runtime/t7-multisurface-build-c-original-host-closure.local.json`, 431 bytes,
  SHA256 `143c25deeb319a6851afd414bb18a2d084778f776ef4c39a2a6c25e1bd6e603d`.
- `runtime/t7-multisurface-build-c-host-exit-request.local.json`, 366 bytes,
  SHA256 `4d442cf6fa61101eb865dfa5a11117da91943f3351eacda8890ad8f860c32010`.
- `runtime/t7-multisurface-build-c-host-exit.local.json`, 818 bytes,
  SHA256 `8143e4ce9e166390c894930294972663a4f422152abf5ac6e747ee41e1aba3c3`.

The real compiler dependency JSON reports 541 main includes and 703 CLI
includes. All are covered by the plan; all 66 newly protected headers occur in
the failed CLI's record. This confirms observed include closure, not successful
compilation or ABI acceptance.

## Retention and remaining gate

Completion proof `runtime/t7-multisurface-build-c-completion.local.json` is
13184 bytes, SHA256
`d8f1fccb70416e588ee147b3160ea7005e70ef61352e0859e3da9b4b70e0af9a`.
Its capture-time independent-absence status remains pending in that immutable
proof; the subsequent independent witness below completes the closure. No closed job is reopened
and no native payload is reread or hashed after release. Main object/PDB pins
come only from the admitted receipt; the partial CLI PDB has metadata size
1189728 bytes and no recorded content hash.

C preparation/runtime/evidence totals 31 files / 4251715 logical bytes. Including
retained preparations A/B and the header-test witness gives **62 files /
5348104 bytes**, before the independent witness and this tracked note. Of that,
1679144 bytes are preparation/evidence and 3668960 bytes are native runtime
outputs, both inside the unchanged 16/256 MiB allocation. Counts do not measure
NTFS allocation or imply that historical files were freed.

At **09:09:53.3082217Z**, the independent witness in the `voice-resume-inventory`
worktree confirmed all five recorded host/parent/compiler/telemetry identities
absent, with zero scoped descendants, leases, heavy/game processes and UDP
endpoints on 27016/27116/27117/27816. Main remained stopped and Python23352 was
preserved. It directly checked the failed command execution's actual exit one
against PTY58305/tool chunk `e7cac8`. The CIM versus native CLI creation-time
precision difference is retained, not silently normalized into another process.

`runtime/t7-multisurface-build-c-independent-absence.local.json` is 7292 bytes,
SHA256 `23d93706dc882e4471cc3dd763472197dd7d3f8a708a2220a51af49bd154c35c`.
Witness tool chunk `dda7d0` exited zero. Including it gives **63 files /
5355396 logical bytes**, before this tracked note. No runtime bytes were freed.
The incomplete historical CLI stage snapshot and absent final input-revalidation
field remain distinct from the proven global original-job closure.

Next: reviewed correction of the layout assertion and any affected
cross-language geometry budget, then separately
authorized preparation/build. Do not rerun C, delete the assertion or infer a
successful v2 export, fastfile, rendering or owner acceptance from this attempt.
