# Existing SAB/FF transaction with checksum candidate F: prepared only

This document preserves the preparation checkpoint. A subsequent, separately
authorized unique cycle is recorded in [SAB-FF-F-RESULT.md](SAB-FF-F-RESULT.md).
The prepared plans and command below were executed unchanged; this historical
preparation does not authorize another invocation.

[Build F](native-checksum/BUILD-F-RESULT.md) produced the corrected native
executable and proved both C++ checksum probes. This preparation binds that exact
candidate to the existing original-sound build/verify/dump/read transaction. It
does not run ZoneTool, repeat the codec test, stage stock or create the new RunRoot.

The prior sound run stays failed with `SAB PCM checksum mismatch`. Its state
SHA-256 remains `c1b532dc3d61f0408f3ec4202e93fdf2d6394b0209ed3b2b9d2cdaaed7098276`.
The native Build E link failure also stays failed. No old receipt or output is
rewritten, and no fake E7 `build-artifact.local.json` is created for candidate F.

The candidate changes from the shared E7 EXE to the sound-owned
`runtime/zt-sound-md5-d/bin/zonetool-sound-md5.exe`, 21696512 bytes, SHA-256
`4740f0c22a1a7bab0b01f7a55ec0b133263ac218825ac3c0d15b9e269fe472b0`.
Its actual 413367-byte `build-receipt.json` is pinned to
`a8253c8efa5b315c7870f27c6732eb6893528c0bd4c8ad3ddcbe7dde407faf62`;
its 6864-byte `supervisor-state.json` is pinned to
`5a99ed368636d08d1d4407e3125cab73f5da879344880588c6aa54efcb556ed8`.
Both declare the same successful Build F generation and exact final artifact.

The local candidate binding requires successful before/after input proofs,
artifact verification, root exit zero, no job member, released admission and no
retained token. It refuses unverified probes or playback/readiness promotion.
Both receipts become ordinary retained transaction inputs. During the admitted
run, the same transaction guard list receives an EXE read guard **before** the
first binary hash, identity check or staging. Preparation and default Plan only
check binary existence/size; fresh binary and stock hashes remain execution work.

`prepare_sab_ff.py` reads and rereads the large build receipt in its own bounded
512 KiB metadata collector. The independent `read_sab.py` file, 256 KiB per-file
limit, 2 MiB read limit, checksum checks and all acceptance exclusions are unchanged.
The historical stock plan remains a stock reference only; its old E7 builder
field no longer supplies candidate provenance. The new review plan explicitly
supplies the sound candidate root. Historical parameter files are not modified.

The four changed production sources are only `prepare_sab_ff.py`,
`Prepare-SoundFF.ps1`, `SoundFF.Core.ps1` and the fixed tool SHA in
`sound_ff_phase.py`. The shared scheduler, job owner, phase runner, pipe drain,
transaction/restoration providers and sixteen canonical helper pins are unchanged.
This source revision changes the adapter hash formerly captured by native Build F;
that build's completed evidence remains historical and its plan is not reusable.

The new execution plan has 40 exact hash inputs. Relative to the failed sound
plan, it adds the two real F receipts and new review plan, removes four old E7
build metadata references and the previous review plan, and updates those four
sound source hashes. The three ZoneTool phase hashes switch to the corrected EXE.
No compiler or SDK resource-tool invocation belongs to this runtime transaction.

All 72 stock entries were compared exactly with the old execution plan and are
unchanged: 71 read-only hard links plus one 77-byte sentinel copy. Adding the same
four original sound inputs and the new tool still produces 77 staged inputs and
80 transaction entries. The original source is the retained `original-sound-source-b`;
its FLAC/PCM/aliases and the completed external codec evidence are unchanged.

The future transaction retains **8 GiB RAM / 11 GiB commit**, 64 MiB observed new
output stop, 2 MiB per pipe log, 240-second native / 30-second reader phases, the
existing five-second final decision allowance, two-second job drain and 15-second
failure cleanup. It still preserves FF/SABL/SABS, restores files only after proven
closure/integrity, and requires final accounting before release. No successful
build or C++ probe substitutes for the independent bank reader or playback.

The following ignored files are under `runtime/content-surfaces`:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `original-sound-sab-ff-review-plan-f.local.json` | 16530 | `5c0a3b4799fb3d9e2a998188ac61a213d89b75c515218cbef4843d5794f54b5b` |
| `original-sound-sab-ff-execution-plan-f.local.json` | 66270 | `3d90a5746a8ee698fb08715e270f2855f261b318393257f91a9e7f59e3ad39d5` |
| `original-sound-sab-ff-command-f.local.ps1` | 1049 | `2009fda548d75eaf7f32ba2b1023e106550c8262dfb918917adecb66dbd726f7` |

The proposed `original-sound-sab-ff-b` RunRoot is absent. The prepared command
uses a fresh persistent PS7 host and catches failure without exiting that host.
No invocation is authorized by these files. A separate coordinator review, fresh
complete admission and unique GO remain required; no retry is implicit.

Validation passed: twelve Python phase/preparation tests; thirteen PowerShell
candidate-evidence cases plus two rejected changed hashes; sixteen default-Plan
and helper-identity cases; and fourteen existing transaction cases with mocked
native ownership/admission and real tiny-file restoration. Candidate validation
was also checked to avoid hashing the native binary during source-only work.
No native process, reservation, stock staging or RunRoot was created by these tests.
The next action is independent review of this binding and coordination of the
next native slot. `Ready` and playback remain false.
