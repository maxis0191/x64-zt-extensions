# Publication build A: passed and closed, 2026-10-13

One authorized native build compiled the bounded message-publication overlay
into fresh main and CLI objects and linked a new candidate. All three native
roots exited zero, their original jobs closed empty, input revalidation passed
and the build lease was released. The candidate was **not executed**. Actual
diagnostic publication, catalogue generation and the donor-loading cause remain
unverified; this is a compilation/linkage checkpoint only.

## Reviewed source and exact plan

- Repository source: `cd392c40a19a320bd2ac42f677ee560633c1cbfb`, PR185 merge.
- Pinned native source: `fab935826c898806855376662a8a03317b3ad8f1`.
- Plan: `runtime/t7-publication-build-plan-a/build-plan.local.json`, 300810 bytes,
  SHA256 `c5f14a40457e152ea4033468e91b51e8e1cbb81b2d8225c26a440a4c6592a80f`.
- Profile: `t7-catalog-message-publication`, schema
  `iw7.t7-message-publication-build/1`, stages **main, zonetool11, link**.

The separate plan review was favorable before the coordinator's one-build GO.
Preparation and the default runner check read source/JSON/tlogs and binary
metadata only: 1080 input pins, none missing, no native type, lease or candidate
root. The initial stale `.gitattributes` contract refusal and its merged repair
remain documented in [the build contract](MESSAGE-PUBLICATION-BUILD.md).

After substituting prepared/run roots, the main recipe matched message A and
the CLI recipe matched the original successful C compilation. The normalized
link changed only object 412 (response line 413), from retained CLI to fresh
CLI. It linked 411 reused objects and two fresh objects; 18 project libraries
and one resource remained retained. `xpak` was the only retained dependency
stage. Core/compiler/observer/policy/scheduler and T7 profile provider bytes
matched the earlier pins; their new bindings use the reviewed current checkout.

Both prepared sources match the reviewed overlay exactly:

| Source | Bytes | SHA256 |
| --- | ---: | --- |
| main.cpp | 42948 | b96e145dd96558ff6307854748d25ea43638b258d4f97b630c99f8f0c68d4c38 |
| zonetool.cpp | 36028 | 280e301f8be1b61133b0c6d86644a7d0ce0fb676fc41abc261ae206ad8b44524 |

## Actual invocation and closure

Fresh preflight at 02:55:15.8519903 UTC found zero leases and no game/build/lab
process. Main was stopped and the preserved Python process retained its exact
PID/image/creation identity. Admission allowed the unchanged 4 GiB physical and
6 GiB commit estimates; observed physical/commit usage was 49.48%/49.23%.

One fresh persistent PowerShell host, PID 20440, created at
02:55:19.9904470 UTC with parent 33220, invoked the exact reviewed runner once.
It started at 02:56:07.5701927 UTC and returned without exception at
02:56:47.7862537 UTC. The admitted group recorded 35.369 seconds, including its
input checks and closure. Stage limits remained 120 seconds, group 600 seconds,
cleanup 5 seconds and output 256 MiB including a 1 MiB receipt reserve.

| Stage | Root PID | VCTIP PID | Native exit | Elapsed |
| --- | ---: | ---: | ---: | ---: |
| main | 35116 | 32580 | 0 | 4.716 s |
| zonetool11 | 24744 | 10796 | 0 | 9.434 s |
| link | 11772 | 27068 | 0 | 3.610 s |

Each stage's compiler telemetry completed through the existing original-job
policy, with two identity-matched VCTIP observations, verified root exit zero,
then zero active and listed job members after closure. Both generated dependency
JSON files identify the new prepared source, with MSVC-normalized casing. Final
input verification completed under the lease. No reservation was nested or
budget reduced, and no retry occurred.

Receipt `runtime/zt-t7-publication-a/receipt.json` is 22352 bytes, SHA256
`5bea8986157efc1749c3636b58f13c0293c8c40cb4dbd1ea0e5a17f44589edb1`.
It reports `Passed`, `InputsReverified`, `TreeClosureConfirmed` and
`LeaseReleased`, with `Quarantined=false`. Its BuildProfile equals the reviewed
plan. The host verified that the lease-specific AppDomain quarantine was absent.

Postflight at 02:58:30.9504417 UTC again found zero leases/builds, Main stopped
and the preserved Python identity unchanged. Only then did the owned host exit
zero. Session 2516 closed with exit code zero. A separate process observation at
02:59:30.4440741 UTC found host, parent, all three compiler/link roots and all
three telemetry PIDs absent. The coordinator's independent witness belongs in
its separate checkpoint; this file does not claim or substitute for that result.

## Produced artifacts and storage

The following hashes are copied from the receipt generated and revalidated
under admission. No binary was reread or rehashed after lease release.

| Artifact under runtime/zt-t7-publication-a | Bytes | SHA256 |
| --- | ---: | --- |
| main/main.obj | 581570 | 326e0ab4a6b5f708d3678db27e3964df548ee729a6739f8df61270e9bcf594c8 |
| main/compile.pdb | 1732608 | b845afba3dbb5187b407a97cba009521eec8f211268f7ce074478bcdefd0614e |
| main/dependencies.json | 62100 | f4817402f160f8d6381a63aea09a7f17c1828660f8151269868e8a5049943aa8 |
| zonetool11/zonetool11.obj | 3630479 | 21407d1d27bd262cbc1bbe1df89286d11643c9bd53a5269f5414de8d837eda5f |
| zonetool11/compile.pdb | 3559424 | 33c3aa728c3d1384262ec686736b540b1866be9178ccefac651fd05c8c93c4d3 |
| zonetool11/dependencies.json | 76792 | cac1245bb4d7e82c23306da9007eb69ee03fccc3e54c3f15295a39957582f103 |
| link/zonetool-t7.exe | 21751296 | 31b9d908d15fb5f0bf17a7b27309dc7183458d5e586dfc6e427cc8ec2b3fa647 |
| link/zonetool-t7.pdb | 136507392 | 35aa0658c198fb8dbc694b1e6d59d51cb6ea53a238e1bf9802fd662cdf5b4b2f |
| link/zonetool-t7.lib | 6744 | f922f8b672d7483ac5d4e056e45f3dcdfbda7db51a4f80451d478fbe512d453d |
| link/zonetool-t7.exp | 3925 | 0c4cea6468ed63fd852ae5305b11bce52ad03c76a85be559fbd70b0981208ae3 |

Maximum observed output was 167912632 bytes. Final metadata accounting found
17 build files totaling 167934984 bytes, plus 24 preparation/evidence files
totaling 546636 bytes and 23291 bytes of associated preparation scripts/notes.
This conservative local accounting totals 168504911 bytes (about 160.70 MiB),
before this small tracked note. It fits the approved 272 MiB slice **within** the
existing 4 GiB pool; it does not add to the global 10 GiB ceiling. Logical file
size is not an NTFS allocated-byte or global-used-total measurement. No stock,
source tree, SDK or cache was copied.

The unchanged plan, source/recipe diffs and source-only audit remain under
`runtime/t7-publication-build-plan-a`, alongside `preflight-run.local.json`,
`host-identity.local.json`, `host-outcome.local.json`, `postflight.local.json`
and `host-exit.local.json`. Existing candidate/plan/receipt histories remain.

Next: coordinator integration of this checkpoint and independent closure
evidence, then a separately reviewed runtime plan using the actual candidate
identity and distinct publication profile. A new runtime GO and fresh admission
are still required. The build retains `CandidateExecuted=false` and `Ready=false`.

## Independent closure

The independent witness at 03:04:17.1735568 UTC confirms absence through fresh
scheduler and CIM observations: host, parent PID, all six tool/telemetry processes,
observable descendants and scoped roots, with no remaining heavy work, game,
lease or relevant UDP endpoint. Main was stopped and the unrelated Python process
retained its identity. Five small receipts were pinned; the worker's actual
session 2516 exit zero was independently checked in its completed tool record.

Witness `t7-publication-build-a-independent-absence.local.json` is 7499 bytes,
SHA256 `cf7813cc93a7cc931d06b8049f6725b0e1edb607a7c5623ce28ea85c398833cc`.
It retains the provenance limit: seven complete process tuples were recorded,
but parent 33220 has only a preserved PID reference. Its absence is observed,
not a retrospectively invented image/creation tuple. The witness reads no native
artifact; job closure and artifact hashes remain original-host evidence.

The worker checkout had advanced to documentation-only commit `4c05f9e` after
the build; executable source and helpers were unchanged from `cd392c40` and the
checkout remained clean during the witness. This observation closes the build
group without executing or qualifying the candidate's runtime behavior.
