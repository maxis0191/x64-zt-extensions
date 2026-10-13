# Multisurface build D: passed and independently closed, 2026-10-13

D compiled the corrected native adapter and linked one candidate successfully.
The original host closed its jobs, released its resource lease and actually
exited zero. An independent witness then confirmed the recorded processes absent.
This is **build evidence only**: the candidate was never executed; no v2 export,
fastfile, rendering, gameplay or owner acceptance is established.

The build used clean repository commit
`0bc0b16aafb2ceb3863f9c20b5f50fb5c8a5f777` (PR201 merge) and retained native source
`fab935826c898806855376662a8a03317b3ad8f1`. The earlier
[C compile failure and its source correction](BUILD-MULTISURFACE-C.md) remain
preserved. A/B/C preparations and C's failed native products were not overwritten,
deleted or treated as reclaimed budget.

## Reviewed preparation and exact invocation

The new preparation is `runtime/t7-multisurface-build-plan-d/`; the new native
output scope is `runtime/zt-t7-multisurface-d/` in the producer worktree. The latter
was absent through preparation and DEFAULT validation. Its one native invocation
used the exact `FutureBuild` image/argv in the frozen commands envelope, including
`-NoExit`, the absolute plan path, the plan SHA256 and `-Run`.

| Preparation file | Bytes | SHA256 |
| --- | ---: | --- |
| `build-plan.local.json` | 365638 | `551a4017b334d573e5873dfda3e6134968549db08e0aabacbc269ad4a398488a` |
| `commands.local.json` | 6718 | `7b96de27fe3d7aef76646b060f68a08032d69e7b13ad9ad5ab2ecd5763d5222c` |
| `default-validation.local.json` | 4223 | `e755f477c93350eec36db680f9fba536728e0e6716630beee4b1e9621ae7dd5d` |
| `preparation-proof.local.json` | 15939 | `a21108a62793ddb9c6a022b44d46387aadd976483b213cfacfc9634278396e51` |

Preparation tool chunk `bd187d` exited zero. The single DEFAULT call, chunk
`f59e1f`, exited zero in 7.6329698 seconds: 1146 expected Inputs, zero missing
pins, no native types loaded, binary content hashed, lease acquired or run root
created. Its saved result is a semantic JSON transcript of that observed output,
not evidence of another invocation. The preparation totals 15 files / 570698 bytes.

All 1146 Inputs equal C; Bindings remain 135 text plus six unchanged binary
metadata records. The 66 added writer-header pins total 87204 source bytes.
Six of seven prepared sources equal C; only the adapter changed. All four
response files equal C after normalization of the new preparation/output paths.
The link names 413 objects: two freshly compiled and 411 retained, plus the
unchanged 18 project libraries and one resource.

The corrected adapter is 21290 LF/raw bytes, SHA256
`857d57b5f3c1c970f45e513e357215f3506e9c48b2daea4b4f62cb33e0d9bce4`.
Its `sizeof(XSurface) == 96` assertion remains present. The logical geometry
bound is `256 + 384*N + 60*V + 12*T <= 16777216`; this is neither serialized size
nor a process-memory estimate. The canonical three-transition proof is 714 bytes,
SHA256 `fcedb13a3e4b16bd2b4af0957780b755e235d99a91ffe1dc4b8f9bc7a3ed5a46`.
Only the adapter hashes changed in the retained conversion proof.

The actual runner had CRLF bytes: 34721 bytes, SHA256
`e9953cd4bdf8feec074c04a035c5b6c7559474a9ca0cc142edcb970e56a21e57`.
Its normalized LF representation is 34246 bytes, SHA256
`6e769aa552399535e2a638e0d311cb456fa3da803ff16841652d970bd7cfe369`.
The plan binds the actual working-file bytes. Existing admission, original-job,
compiler telemetry, dependency and final input-revalidation guards were retained.

## Fresh admission and native result

At 09:44:13.9235265Z, the producer preflight found zero leases, heavy/game/compiler
processes and UDP endpoints on 27016/27116/27117/27816. Both protected admin and
network chats were freshly `notLoaded`, with their last turns completed. Main
and the owner client were absent; Python PID23352 retained its recorded identity.
The memory snapshot reported 14369845248 bytes available physical RAM and
26920132608 committed of a 47564615680-byte limit. The projected 4 GiB physical /
6 GiB commit request passed. This snapshot did not reserve resources: the fresh
original runner subsequently acquired the account-wide lease through the normal
atomic admission path.

The unchanged limits were 600 seconds for the group, 120 seconds per stage,
five seconds for cleanup, 256 MiB for D outputs including reserved metadata,
and the shared 272 MiB storage allocation including historical evidence.

| Stage | Native exit | Elapsed ms | Final original-job active processes |
| --- | ---: | ---: | ---: |
| `main` compile | 0 | 5295.5502 | 0 |
| `zonetool11` compile | 0 | 10404.9978 | 0 |
| `link` | 0 | 4727.3197 | 0 |

Each stage verified 141 bound inputs and closed its exact compiler/linker and
VCTIP membership through the original job. All three stderr logs are empty.
The main dependency JSON has 541 includes; CLI has 703, including the corrected
prepared adapter and all 66 added headers. Neither has an unknown include.

The final receipt is `runtime/zt-t7-multisurface-d/receipt.json`, 22380 bytes,
SHA256 `25d2593dbb412ac676f5e11f1b4d8ae34f26623217159ddb36dfc3f42d96ce0b`.
It finished at **09:45:25.6786346Z**, after **42332.3863 ms**, with `Status=Passed`,
`ExitCode=0`, `InputsReverified=true`, `TreeClosureConfirmed=true`,
`LeaseReleased=true`, `Quarantined=false`, `CandidateExecuted=false` and
`Ready=false`. Lease `11b316f2089048f9985a557ddcbbc7b2` was released.

| Candidate artifact | Bytes | SHA256 recorded under the original lease |
| --- | ---: | --- |
| `link/zonetool-t7.exe` | 21805568 | `3c9271a0ef0e96cce26f44c30e6b04aa4c2338c86057ac52da489a7bc0e28e7f` |
| `link/zonetool-t7.pdb` | 136810496 | `a82b2225e8ab9b1c672ca86e5d51035144ef9495ed06d6f30a45318a8a9e713c` |

These opaque hashes were copied from the admitted receipt. After lease release,
only file sizes and bounded text receipts/logs/dependency JSON were inspected;
the EXE, PDB, OBJ, LIB and EXP contents were not reopened or rehashed.

## Original-host exit and independent absence

The launch returned PTY **98083**, tool chunk `d22df3`; chunk `e25d25` reported
the passed build. The original host observed `Closed=true`, `OwnerClosed=true`,
native owner exit zero, zero guards, null lease and zero registry leases at
09:46:25.1271248Z. It rechecked those conditions at 09:46:46.9809131Z and executed
`exit 0`. Tool chunk **`d29829` returned actual exit zero**. This was subsequently
matched to command execution `exec-2e14a0ee-d604-4fb8-9bce-1b60666df90b`, completed
with exit zero; exit was not inferred merely from process absence.

| Role | PID | Creation UTC |
| --- | ---: | --- |
| Original PowerShell host | 33796 | `2026-10-13T09:44:34.5735770Z` |
| Parent PowerShell | 36856 | `2026-10-13T09:44:34.3895760Z` |
| Main compiler | 19356 | `2026-10-13T09:44:53.0485825Z` |
| Main VCTIP | 35868 | `2026-10-13T09:44:55.2296202Z` |
| CLI compiler | 36524 | `2026-10-13T09:44:58.3640660Z` |
| CLI VCTIP | 35552 | `2026-10-13T09:45:02.1174456Z` |
| Linker | 32560 | `2026-10-13T09:45:08.8723393Z` |
| Link VCTIP | 28480 | `2026-10-13T09:45:10.3911122Z` |

The receipts retain full image paths: the bundled PowerShell for host/parent,
and MSVC 14.44.35207 `Hostx64/x64` for compiler, linker and telemetry processes.
The producer postflight at 09:48:15.3909496Z found all eight identities absent,
zero scoped descendants, leases, heavy/game processes or listed UDP endpoints,
with Main stopped and the same Python PID23352 preserved.

The **independent** witness at **09:51:49.8183525Z**, tool chunk `42674d` exit zero,
confirmed those eight exact identities absent, zero descendants/leases/heavy/game
processes and the same four ports absent. It verified the six small receipt pins,
the producer's actual completed command, source commit and clean checkout. Its
original-job closure conclusions come from the pinned original receipts; it did
not inspect old managed contexts or handles, adopt a job or read/hash any opaque
artifact.

Evidence sidecars below are under `runtime/t7-multisurface-build-d-` in the
producer worktree, except the final independent witness, which is retained in
the `voice-resume-inventory` worktree.

| Suffix | Bytes | SHA256 |
| --- | ---: | --- |
| `preflight.local.json` | 1935 | `7a83f67b14cd1878deb06531f2aab4eb0c30cd56390ec72849e00dcb7d770dcb` |
| `host-identity.local.json` | 835 | `8b2726f6bcc3c27a548c9b3e3aa1e6fce97be56aaec44211de9f004c8751d217` |
| `original-host-closure.local.json` | 368 | `690e509cd2363e4937b22a915164a03bceb8b167ec6cb5c5098fda32242ff1f0` |
| `host-exit-request.local.json` | 300 | `81ed2f7c600254e535b9d2bb26b400c672e5c0a2b0f75b64a9440bc3789f533e` |
| `host-exit.local.json` | 1290 | `b776e7cce3ad68c0e994fb12a29aa7dcfc769663985260125c2a6308c8c2bbfe` |
| `postflight.local.json` | 4516 | `00fff73d40e6c0870af876a2351271dcadace9f35c4705ef85f84fc81ae09a88` |
| `completion.local.json` | 16438 | `962e795e474f8fd5a86a41eff3f4bd31879ba07d77c510053b0442a98c8ae199` |
| `independent-absence.local.json` | 8167 | `29fc704e3c173b4ae1c72fe4a3e4f6627c4d6768209a5a685905ab63d039dd19` |

The producer's frozen completion/postflight records correctly retain
`IndependentAbsencePending=true` as their capture-time state. The separate final
witness supplements them; those earlier records were not rewritten.

## Retained storage and validation boundary

D preparation is 15 files / 570698 bytes; native output is 17 files /
169688782 bytes; its seven producer sidecars total 25682 bytes. D's producer
scope therefore totals **39 files / 170285162 bytes**. Including historical
A/B/C and their witnesses gives **102 files / 175640558 bytes** before the final
independent D witness. Adding its one file / 8167 bytes yields **103 files /
175648725 bytes**, leaving **109563947 bytes** under the unchanged 272 MiB
allocation. This final addition is arithmetic, not another global disk recount.

All preparation/evidence now totals 2290983 bytes, leaving 14486233 bytes within
its 16 MiB allowance. D's native outputs leave 98746674 bytes within its 256 MiB
output cap. These are logical file sizes, not NTFS allocation or measured global
disk growth; they exclude this tracked note and README edit. Nothing historical
was freed, and remaining allocation does not authorize another run.

The independent source/build review was favorable. Native compilation now proves
that the corrected layout assertion is accepted in the actual CLI translation
unit; linking proves a candidate was produced. It does not prove v2 model
selection, serialization, dependency completeness for a real model, IW7 fastfile
compatibility or rendered behavior. Source-only qualification of this exact
candidate's build receipts is the next coordinated step. Any export, new native
invocation, game test or retry needs its own reviewed scope and separate GO.
