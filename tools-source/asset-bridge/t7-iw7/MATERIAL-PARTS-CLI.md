# Explicit selected image-parts metadata CLI

The successful E5 geometry export still used G2's five-argument `observe`.
All seven image headers were unread; binding 0 refused and 1..6 were not
attempted. Binding 4/nameHash `0xA0AB1041`/usage 1 is a diffuse classification
lead, not a 64-bit package key or acquired texture.

The explicit candidate command is:

```text
-t7-iw7-material-parts-v1 mp_freerun_04 p7_fre_platform_cap_02 0
```

It reuses the existing resident zone loader, denies legacy helper-XPAK reads,
finds the exact nondefault model and requests material slot 0, image binding 4
with its expected hash. It prints `T7_SELECTED_MATERIAL_PARTS_METADATA` schema3
from the separately versioned G3 helper, then exits. It selects no geometry,
opens no package, copies no pixels, emits no model/FF and does not guess a
provider. Refusals preserve the diagnostic and exit nonzero. A successful
metadata result must preserve false pixels/Ready and true header rechecks.
G3 omits `refused` on success. The caller accepts its absence or boolean false,
requires a boolean when present, and prints a boolean true refusal before
exiting nonzero. The first caller incorrectly required the field on success;
peer review caught this before native compilation or observation.

`prepare_material_parts.py` applies one finite transition after the existing E5
publication factory; the G3 module is inlined after the unchanged G2 observer.
Default `prepare_cli`, `native_cli`, G2/schema1/2, frozen C/C2 and prepatch V2
factories remain unchanged. The native mode is exclusive, exact five-argument
ASCII input; it cannot silently activate from a model name, surface count or
unrequested flag. No second observer or alternate launcher is introduced.

Preparation selects `--material-parts-v1` with the existing explicit
`--catalog-message-publication --selected-streamed-render-only-v2` source
family and both retained compilation proofs. This reuses the established
two-TU main/CLI plus link group, sealed E7 inputs, 66-header context and original
job/closure policy. It does not relax legacy binding limits or compile a new
full tool tree. The new source profile has 154 bindings (148 text/six opaque);
its 1,146 sealed native inputs remain unchanged. Binary qualification and
actual CPP/probe require the coordinator's separate group admission.

The fixed old E5 main is 43,254 bytes/`5aef1fad`; CLI 112,377/`c63d9552`.
The declared G3 source transition produces main 43,366 bytes/`031464d8` and
CLI 124,224/`0dd4b3be`, below the existing 128-KiB cap. Full source hashes are
in `material-parts-source-contract.json`; the runner binds its finite marker,
source pins and exact prepared outputs before any opaque input is opened.
The old G2 header remains 18,583 bytes/`a8848a92`.

The first actual source preparation (source `51f906b0`, capsule
`t7-material-parts-cli-source-a`, 2026-10-14 06:07 UTC) refused at the existing
256-KiB aggregate output cap. Python exited 1; its owned child closed and the
Analysis lease was released. No plan, DEFAULT, CPP, candidate or stock operation
ran. Its capsule, wrapper and refusal receipt remain unchanged. The corrected
caller plus the retained E5 response/header sizes total 263,522 bytes, which
exceeds 262,144. Only the explicitly selected, pinned parts transition now gets
a 288-KiB aggregate authored-source cap. Other profiles retain 256 KiB; the
2-MiB plan cap, individual source/header/read/geometry limits and resource
admission policy are unchanged. Source regression proves both caps and the
real generated transition. The later C qualification is recorded below.

The admitted B preparation (source merge `4e33b9c4`, 2026-10-14 06:30 UTC)
produced the 371,363-byte plan `e5048079` with 12 output files, 1,146 complete
input pins and no missing pins. Python exited 0, but actual DEFAULT exited 1
at the selected-streamed source binding guard before opaque qualification.
Its old render-only branch expected the 13,768-byte `test_streamed_contract.py`
fixture; the current shared source contains the approved C2 extension,
17,443 bytes/`9146f69c`. The parts profile now requires that exact extended
fixture pin. Frozen render-only/V1 pins remain unchanged; all four streamed
implementation pins and G2/G3 header pins remain unchanged. The corrected actual
input guard accepts B's immutable metadata; authored source-pin regression
covers parts, C2, old render-only and V1, plus old/new mismatches and drift.
This source check does not rerun DEFAULT or qualify opaque inputs.

B's owned children closed, its lease released and its original NoExit host
exited 1. B remains Refused. Its wrapper accidentally named the admission
directory/schema `plan-bdmission` through a broad suffix replacement; that
metadata spelling did not cause the source-pin refusal and remains preserved.
The next wrapper must change exact quoted paths without replacing the schema.
No CPP, candidate, stock, FF or game ran in either preparation group.

The separately admitted C preparation succeeded on 2026-10-14 at 06:59 UTC.
Its sealed source capsule is `t7-material-parts-cli-source-c`, product revision
`3b5af46ddb0ee94dffea99074e6ef24ad6466284`; the existing source verifier checked
916 text files/8,902,880 bytes. The corrected wrapper preserved the admission
schema and changed only exact quoted output paths. Python and actual DEFAULT
both exited 0. The 371,363-byte plan has SHA-256
`b9358e1e500046030650b48d489d63cfc6c76401b2a64be39a9a3b7fb28f2288`:
154 bindings (148 text/six opaque), 1,146 complete inputs and exactly
`main`, `zonetool11`, `link` stages. Prepared main/CLI and G2/G3 pins above remain
unchanged. DEFAULT reported false NativeTypesLoaded, BinaryInputsHashed,
LeaseAcquired, RunRootCreated and Ready; this qualifies the preparation contract,
not a native binary or image.

The C admission receipt is 8,383 bytes/SHA-256
`a4c6dd755529d0e6496c312b30d93fea678be8ebcb59e66ab77c8e10ba8df80e`;
actual DEFAULT stdout is 5,184 bytes/`3326a1e06437ed8ef0b36b9e2cce318e7fe4c5b57aefcc20c3a919fb06fe619a`,
with empty stderr. Both owned children closed, the Analysis lease released and
the original NoExit host actually exited 0. Fresh identity/registry observation
at 07:00:48 UTC found the owned host/children absent and no leases. The future
`material-parts-native-WAIT-ROOT-c` root remains absent. A and B stay Refused;
their historical files and claims are unchanged. No CPP, candidate, stock, FF
or game ran in C.

Native launch review found that the historical bootstrap also opened retained
`.tlog` bindings before its internal Build reservation. `Run-T7Build` now
defers only those reads in `-Run`, using ordinal case-insensitive extension
comparison after the existing strict boolean IsText check. After the unchanged
admission, group clock and output creation, it opens the same pinned tlogs with
the same Open-T7Bootstrap guards. DEFAULT keeps its previous read sequence;
source PS/CPP/RSP verification, opaque input admission, owner handles and
original finally/recovery remain unchanged. Authored execution of the actual
bootstrap/admission/read ASTs covers DEFAULT, both tlog cases, refusal before
admission, a deferred hash failure and invalid IsText. It invokes no scheduler,
compiler or real tlog/binary read. C stays frozen; native execution requires a
fresh reviewed plan bound to the corrected runner.

The separately admitted D preparation/actual DEFAULT passed on 2026-10-14 at
07:27 UTC, using sealed product source `ed62c6f9cf20e41d909fe801da9a50949f1cb4db`
and the existing preparer. Its runner is 60,689 bytes/`586a847c`; source manifest
is 322,827 bytes/`328dcb91`. The 371,363-byte D plan has SHA-256
`d0c82f92332a37d96f3be71f828f6d47386a5327c67f579e9b6089e9cea0504c`.
The admission receipt is 8,381 bytes/`4ea17c69dcd7c0f3eedd80d827b258db7542f90b3dd55deb5fd95ad7685d0698`;
actual DEFAULT stdout is 5,184 bytes/`c28caa65257afcae2f77c598b976bc761e3df80b73897380fdee086a1b30e1a5`,
with empty stderr. Both owned children and the original NoExit host exited 0;
fresh observation at 07:28:29 UTC found them absent and the lease registry empty.

Read-only C/D comparison retained all 1,146 input pins and 154 binding paths
after scope normalization. Exactly five binding hashes differ: the corrected
runner and four response files whose contents differ only in the new paths.
Actual prepared main/CLI and G2/G3 source bytes were rehashed and are identical;
retained opaque objects were not rehashed outside admission. The comparison
receipt is 3,106 bytes/`ced32f4fd3539ec8ce116035cd6cad8177f0851a24568290289c9275a4d43bd4`.
DEFAULT again reports no native types, binary hashing, build lease or run-root
creation, with Ready false. A minimal 892-byte capsule (`92496c02`) calls only
the existing D runner with the exact plan and main/CLI/link stages. A/B/C stay unchanged.

The separately admitted native D attempt on 2026-10-14 at 07:37 UTC refused
before compiler launch: Open-T7Pin reported `T7 input hash/length differs` while
guarding the retained inputs. Native receipt is 5,420 bytes/SHA-256
`55c96374d843403b3486a05b66e70dd19d74bf1a284d96f4017a2fb91f67b3a9`,
Status Failed, no stages, zero artifact output, confirmed tree closure/lease
release and no quarantine. The original NoExit host actually exited 1; fresh
07:40:17 UTC observation found it, its parent and compiler/link/telemetry processes
absent, with no leases. No EXE/PDB, candidate, probe, stock, FF or game was produced
or executed. Successful DEFAULT D remains a preparation proof; native D remains
Failed. Its generic error does not identify the offending pin. Diagnose that
exact input under a separate admission before correcting provenance or retrying;
never adopt a different opaque hash or rewrite the frozen D plan.

Two separately admitted read-only diagnoses narrowed this refusal. The six
opaque tool/job bindings all passed unchanged (receipt 5,302 bytes/`58e651d0`);
the subsequent exact Inputs list stopped after 1,138 passing pins, at index
1,139 (`plan.Inputs[1138]`), `C:\Windows\System32\TZRES.DLL`. Its size stayed
12,288 bytes, but the sealed SHA-256
`f3f5ef83a67c503991d728f62cf039cbb52a18d6eb82197dec23ede8f0996108`
differs from the under-lease observation
`1398cf1d866e49a8ba351e2a30a7803b50c8b595d17f776abe8d2ec4a9c6fb10`.
The input diagnosis receipt is 2,672 bytes/`c06117cbd2fe378dd9105a88ac84ccb3dbb323a8cfd247795b634e5a949525db`,
Status Refused, guards disposed and lease released. The original host exited 1;
fresh 07:51:41 UTC observation found owned absence and no leases. No later
input was read, no different hash adopted and no native retry performed.

This OS/toolchain pin originates in the immutable checksum seal `f52867e7`,
with an original 2026-09-08 modification date. The current file's observed
2026-10-14 02:39 UTC modification coincides with Windows servicing; Setup events
record UpdateAgentLCU staging/installing KB5127647, but do not identify that
file's replacement. An OS-update explanation remains an inference. Microsoft's
[TimeZoneInfo source](https://github.com/microsoft/referencesource/blob/main/mscorlib/system/timezoneinfo.cs)
uses System32 `tzres.dll` resources for localized time-zone names. Its current
identity/signature and the remaining input suffix need qualification before
any explicit environment refresh. Preserve the old seal and D failure; do not
roll back a Windows DLL or silently repin a historical build.

## Explicit dated OS context

The admitted union qualification later measured version `10.0.26100.9711`,
company Microsoft Corporation and a Valid Catalog signature from Microsoft
Windows for the observed 12,288-byte TZRES hash above. The exact D/V3 suffix
union of ten files passed unchanged under guards. Its 8,907-byte proof has
SHA-256 `5a282c19995af210fd9d7c55a8692d87d4456526352fe21034a8f07d83a9fd9d`.
The original host exited 0; fresh 08:09:56 UTC observation found owned absence
and no leases. The observation records ContractAccepted/PinAdopted false;
approval of a new environment is a separate source decision, not a rewritten D.

The coordinator accepted one new, finite context for future parts/V3 plans:
`--os-context-tzres-20261014 --os-context-proof <qualification-receipt>`.
There is no SHA parameter or arbitrary override. The source pins that exact
proof and validates its before/after, version, Microsoft Catalog identity,
closed observation and unchanged suffix. It replaces only the exact old TZRES
expected pin. Without the option the original context stays strict.

The new top-level `OSResourceContext` is separate from geometry/prepatch
markers. V3's 14 profile fields and ten marker fields remain unchanged.
Only one guarded text binding is added for the proof: future parts therefore
has 155 bindings, with its historical 154-member set checked unchanged; V3
similarly retains its historical cardinality plus that one finite proof.
The runner checks the same fixed transition and unique TZRES Input, holds the
proof through the existing guard lifetime, and hashes the new resource only
under the existing admitted execution. The 1,145 other parts Inputs, source
CPP, retained objects, original seal and old plans remain unchanged. Source
checks qualify this interface only; a fresh plan/DEFAULT and CPP still need
their own coordinator groups.

Source verification: 366 Python tests passed (nine optional source/environment
skips); actual AST guards passed 28 OS-context, 132 binding, 24 parts, 48 V3
and 100 V2 checks. Complete parts/V3 binding checks also accepted authored
copies of the frozen plan metadata with only the qualified context added.
These checks read text metadata only and do not qualify a new DEFAULT run,
binary inputs, compilation or engine behavior.
Independent review found collection-valued proof Binding Path/SHA256, Input
Path and profile Name could pass PowerShell comparisons. The correction checks
their string types; five regression mutations now refuse before proof opening.

## E preparation and DEFAULT with the qualified OS context

One separately authorized Analysis group prepared E and ran actual DEFAULT on
2026-10-14. Its immutable source package is revision
`a8ecff7cb61323cd0e6f75d10e596d55e63a7753`: 940 text files / 9,151,934 bytes,
manifest 331,468 bytes / SHA-256
`ed972cfad8de6985b9c307f65b56a0fe03de6cba442e590eebdddb0b7869db28`.
The qualified runner is 72,050 bytes /
`5b984d5bb28f9865e62c3ad50142e1e6cd0579bc06fbe388abb838707799895e`.
The 5,070-byte preparation wrapper (`f49dd6d2`) differs from reviewed D only
in four literal paths and the two finite OS options with the fixed proof path.
It preserves the existing one-Analysis lease, owned child identities,
timeouts, closure/finally and quarantine behavior.

Python preparation and the DEFAULT child both exited 0. Actual E plan:
`runtime/material-parts-plan-e/build-plan.local.json`, 372,668 bytes /
SHA-256 `cfeb5610dd5322d9137eaa9804590cf023a865236a1132e95e354919ef23084e`.
It contains 1,146 Inputs and 155 Bindings (149 text / six opaque), with one
top-level finite OS context and one added exact qualification-proof binding.
DEFAULT reports NativeTypesLoaded/BinaryInputsHashed/LeaseAcquired/
RunRootCreated/Ready false. The wrapper's Analysis reservation is distinct
from those DEFAULT flags; this group did not compile or execute a candidate.
The admission receipt is 8,381 bytes /
`c7135f3b25536bdd2a199f15a809620d789fb877e1fe8fb877ecbe453282a7ad`;
DEFAULT stdout is 5,184 bytes /
`88c4cbdfe58a6c9c4928593fa666faba44d7cb857f20de30b7bb6d954a7f43e5`,
and stderr is empty.

The receipt confirms child closure and lease release. Original NoExit host
25172 (parent 576) was captured before execution, then genuinely exited 0
through PTY session 79201 / chunk `1f66b0`. Fresh 09:40:13 UTC observation
found the host, parent and both children absent, no heavy/game processes,
and no leases. `runtime/material-parts-native-WAIT-ROOT-e` remained absent.
No CPP, binary input qualification, stock probe, pixels or runtime acceptance
is inferred from this preparation.

The light D/E correspondence reads only JSON and generated text: 1,145 Input
pins are identical and only the exact 12,288-byte TZRES hash changes from
`f3f5ef83` to `1398cf1d`. Generated main.cpp (43,366 / `031464d8`) and
zonetool.cpp (124,224 / `0dd4b3be`) are byte-identical to D. ReuseCompile and
stages are unchanged after scope normalization; all four response files differ
only by source/plan scope. The seven shared text-binding deltas are the reviewed
runner/preparer, the CLI source contract's additional weapon metadata, and
those four response paths. The added eighth binding is only the fixed OS proof.
The correspondence is 5,877 bytes /
`15777005e9aa0fcc3134cb3232b7d82d9eb614c3601e53433cc1280df2c98d0d`.

A source-only 892-byte CPP wrapper (`2b7860f1`) now binds the actual E plan,
using four literal substitutions from D's existing minimal wrapper. It retains
the runner's own single admission and does not add an outer lease. It has not
been invoked. Future main/zonetool11 Compile and Link stages keep 120-second
limits and the same 410 objects / 18 libraries / one resource. A separate CPP
GO and fresh original-host evidence remain required. Old D, the original seal,
V3 add721 and the accepted FF/readback/display cohorts remain immutable.

## E native build passed; metadata observation remains separate

The subsequently authorized E CPP group used the unchanged 892-byte wrapper
(`2b7860f1`) and actual `cfeb5610` plan. Main Compile, zonetool11 Compile and
Link each exited 0. Each stage's original compiler/telemetry job reports
Completed true, ActiveProcesses zero after closure, and TreeClosureConfirmed
true. The group receipt reports Passed, InputsReverified/TreeClosureConfirmed/
LeaseReleased true and Quarantined false. This validates the finite OS Input
transition in native execution; no other expected Input was repinned.

The receipt is 25,651 bytes / SHA-256
`e81604ea36272540d2a62df7aaa236dcdd92bb0d04821ab9b2f887636a074a25`.
Artifact tuples were measured by the runner while admission and guards were
held, then read only from that text receipt after closure:

- `link/zonetool-t7.exe`: 21,963,264 bytes /
  `cce8bbb8f068b4897a391880db316bd1d7586f26f7ec0c1cee2316d76c8644b3`.
- `link/zonetool-t7.pdb`: 139,145,216 bytes /
  `62b0125ae8567a1325ef5ffb3fadc89188d955aa1f12ad3c68f493d172e8335a`.

No post-admission EXE/PDB read or hash was used to obtain these tuples. The
original fresh NoExit host was 16544 (parent 9964), recorded before manually
invoking the wrapper. It genuinely exited 0 via PTY 16448 / chunk `8dd283`.
Fresh 09:56:37 UTC observation found both originals, all three compilers and
their three VCTIP children absent, no heavy/game processes and no leases.
The closure witness is 1,264 bytes /
`9018cc01cf90db101b291f56affa99c376a22e9adccdde7d8651bb61762c623c`.
CandidateExecuted and Ready remain false. The successful build did not invoke
the new CLI, read a retail zone, observe image descriptors, copy pixels,
build an FF or launch a game.

The next separately reviewed/admitted operation is one exact metadata-only
request: `-t7-iw7-material-parts-v1 mp_freerun_04 p7_fre_platform_cap_02 0`.
Its fixed selection is material slot zero / binding four / nameHash32
`0xA0AB1041`, which is not an XPAK key. Prepare that operation through the
qualified recipient and existing lifecycle; the older catalogue/export
profiles do not automatically authorize a new parts candidate or report.
The G3 helper reads two bounded owned 264-byte headers and describes four
physical stream parts. A future real report must qualify those descriptors
and rechecks; no part key or pixel provider is inferred from CPP success.

G3 uses two bounded owned 264-byte header copies approved by G2's existing
Readable guard. It rejects extra/ambiguous captures, differing addresses or
bytes, mismatched G2 metadata and any unqualified selected header/name/recheck.
It publishes four physical stream descriptors, their packed scalars, dimensions,
canonical hexadecimal keys and uninterpreted descriptor words. A declared
count beyond four remains inadmissible; no out-of-header read is performed.
The native format word and low byte are diagnostic values, not a runtime width
qualification. No atomic snapshot, retained allocation, pixel or appearance
claim is made.

Source checks cover the real finite renderer/selection and actual PowerShell
guard with authored metadata: malformed/mixed selections, changed base source,
G2 drift, missing proof and arbitrary output/source pins refuse. The initial
authored guard fixture refused because PowerShell culturally sorts the fixture
filename before the header filename; the expected inventory was corrected.
This did not execute a native child or read an asset. G3's separate native
fixture passed 32 actual native checks in the separately admitted H32 group
on 2026-10-14. The caller's E native compilation subsequently passed as recorded
above; stock metadata observation remains pending. The success/refusal predicate regression evaluates the actual
caller source with authored JSON; it does not claim C++ execution.

The accepted geometry FF B (`50ca9124`, 9,904 bytes), plan `750d25d7`, corrected
readback `7f8b628f` and first static-display cohort remain immutable. Next:
perform one separately reviewed and admitted metadata observation using the
closed E build. Only a
real 64-bit part key, exact decoded size and provider identity can select a
future bounded image read; `nameHash`32 and the geometry key are not substitutes.
