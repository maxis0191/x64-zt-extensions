# Standard original-sound package: source and Plan checkpoint

2026-10-12. This checkpoint prepares the existing sound FF cycle for a standard
`mod.ff` / `mod.sabl` / `mod.sabs` package. No standard package has been built,
loaded, downloaded or played. The coordinator must review the exact source and
Plan and grant execution separately. `HeavyExecutionAuthorizedByPlan`, `Ready`
and playback claims remain false.

## Closed variant of the existing cycle

`Prepare-SoundFF.ps1 -StandardMod` uses the same immutable F Plan/state metadata
and qualified compiler C receipts as `-DumpOnly`. It refreshes sound source pins
and reads text only. Python, original WAV and original FLAC pins are inherited
verbatim from F as three deferred `PayloadInputs`; no payload is hashed or copied
by preparation or the default `Build-SoundFF.ps1` Plan mode. Candidate C is reused
without a compiler build.

The four staged source entries have fixed bindings:

| Target under the temporary work root | Source |
| --- | --- |
| `sound/community_original_sound_v1.all.aliases.csv` | Immutable original B alias CSV |
| `sound_assets/community/original_chime_v1.flac` | Immutable original B FLAC, read only after admission |
| `soundbank/community_original_sound_v1.all.json` | Tracked `standard-mod/` overlay; only `zone` changes to `mod` |
| `zone_source/mod.csv` | Tracked `standard-mod/` overlay; same single soundbank row as original B |

The original B bank JSON and zone CSV remain pinned and guarded as reference
inputs. The overlay adds no sample, alias, sound table or generated asset.
The compiler C executable remains SHA256
`cef411cf9b4de69be02cb4017aabd964e9143e340e211188daa6b6bab366493a`.
Its receipt/state hashes remain `dfe3d7d1...` / `99c5c35f...`; full pins are in
the preparer and generated Plan. Historical F artifact hashes are reference
evidence only; the new package hashes must be observed during a future run.

The ordered phase commands remain inside the existing transaction:

1. C `-headless -unbuffered-io -strict-content-sources -buildzone mod`.
2. C with the same prefix and `-verifyzone mod`.
3. C with the same prefix and `-dumpzone mod`.
4. Existing Python reader against original B, `work/zone`, `work/dump/mod`, the
   current run's verify log and `--dump-profile StandardModC`.

The only mutable package outputs are, in order, `zone/mod.ff`, `zone/mod.sabl`
and `zone/mod.sabs`. Native timeouts remain 240 seconds; reader timeout remains
30 seconds. Existing original-job supervision, explicit pipe completion,
64-MiB output stop, 2-MiB per-stream cap, 15-second cleanup, NTFS identity checks,
file transaction, quarantine and lease release logic remain in use. Admission
remains Extract 8 GiB physical / 11 GiB commit before any deferred payload read.
Stock remains the F metadata set: 71 links and one 77-byte sentinel copy.

## Evidence that must agree

Disk names and bank identity are checked separately:

- Plan validation requires all three exact `mod.*` target paths and the exact
  zone name in every native phase. Arbitrary zone/tool combinations are refused.
- Overlay validation compares against the pinned original text, allowing only
  the bank zone substitution and CSV filename change. A wrong zone fails even
  when that modified text is given a fresh matching hash.
- The reader requires the three standard filenames and independently checks
  `zone=mod` in both SAB headers and the bank JSON extracted from the FF. The
  dumped bank name, languages and alias path must also match the original.
- The verify log must show zone/rawfile `mod` and the unchanged soundbank: two
  assets. The preserved F inventory cannot substitute for this run's inventory.
- Existing SAB extent, entry ID, payload, checksum, original PCM and dump alias
  assertions still apply. C's dump has the already-qualified 4096 block bounds.
- Reader hashes for all three files must equal the retained artifacts. The FF
  is an observed bounded opaque file to the independent reader; native verify
  and dump supply its engine-backed inventory/bank evidence.

Successful future closure would be `SoundStandardModBytesVerified`, without
claiming alias-index lookup, client loading, streaming delivery, audible output
or general FLAC conformance. The sixteen-CC checksum placeholder remains as-is.

## Source-only validation

No test below launches ZoneTool, FFmpeg or IW7 or reserves resources. Python
banks/audio are tiny synthetic fixtures; transaction tests use mock owners and
admission with real temporary file backup/restoration.

| Check | Result |
| --- | --- |
| Python SAB/phase/historical DumpOnly/standard tests | 43 tests pass |
| Standard Plan | 19 rejected mutations, independent repinned bank.zone rejection, four source bindings, default mode and admission refusal pass |
| Existing default Plan and source identity checks | 16 cases pass against the generated standard Plan |
| Historical DumpOnly Plan | 24 C evidence cases, 13 Plan mutations, default mode and admission refusal pass |
| Transaction lifecycle | 21 StandardMod, 12 DumpOnly and 14 historical F cases pass |
| Existing output accounting / monotonic deadlines | 9 / 11 cases pass |
| Unchanged codec | 20 worker, 53 profile, 4 admission and 6 cleanup cases pass |

The codec worker test suite emits an existing Python `ResourceWarning` about
its simulated failure log handle; the suite still exits 0. Codec implementation,
native-checksum sources, original bank contract and FLAC reader have no diff.

Historical `NativeDumpF` retains 1024 dump metadata and its earlier codec failure
checkpoint. `DumpOnlyC` retains 4096 metadata and preserved F inventory. The new
profile does not reinterpret either result. C remains refused for build/verify
of the historical `sdk_original_sound_v1` zone; it is allowed for the new closed
`mod` cycle only.

## Handoff and next gate

The local generated Plan records full machine paths, exact source pins and a
fresh absent run root. Its path/hash are handed to the coordinator separately;
machine-specific values stay ignored. Preparation and default Plan do not create
the run root. An exact-source native execution decision remains pending.

After review and explicit GO, run this existing transaction once under normal
admission, retain all three artifacts and closure evidence, and report any
failure without changing historical evidence. Client lookup and later WASAPI
measurement remain separate steps described in `RUNTIME-LOOKUP-PLAN.md`.
Agent-Lab, HTTP, SDK, native fixture and recorder sources are outside sound
ownership. Their current 20/20 recorder gates remain unchanged.
