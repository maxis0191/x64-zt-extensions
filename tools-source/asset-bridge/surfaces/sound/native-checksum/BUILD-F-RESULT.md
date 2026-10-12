# Build F: candidate and native checksum probes verified

One authorized invocation of Plan F completed from source
`f7e57c924a3115ba06cbc8adea0c941d602b7e5e` on 2026-10-12. Its Plan SHA-256 is
`91280092489387e909516693d4234c60ea0416657166cf6bd8674bd974729c3a`;
the 1083-byte persistent-host command SHA-256 is
`cd5639e41cb7124fc4fb99c9eaed4711472566653501db911ec350e695b2da94`.
All fourteen native stages returned zero with both streams reaching normal EOF.
This includes eight compilations, three links, two C++ probe runs and one archive.
The previous C/D and E failures remain preserved and failed.

The original C++ probe reproduced `78000000000000000000000000000000`.
The patched probe returned `24fe5af1473ea8f4be33912348210c78`, exactly the original
PCM MD5. Both synthetic-envelope field/payload/outside-field checks passed. The
eight compiler include reports established the expected original or private patched
header, rejected the shared unpatched header and contained only sealed includes.
The new common archive retained the twelve unchanged member payloads and the one
new bit-buffer object. The final link succeeded with the pinned SDK resource tools.

The five final artifacts were independently rehashed after original-job closure
while the reservation and input guards remained held:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `bin/zonetool-sound-md5.exe` | 21696512 | `4740f0c22a1a7bab0b01f7a55ec0b133263ac218825ac3c0d15b9e269fe472b0` |
| `bin/zonetool-sound-md5.pdb` | 135786496 | `4a8498c29b5dfcc92e34d32e9107dbfe076a000c799299d3e648dead434e1d92` |
| `common/common.lib` | 3965694 | `8ce05af2302374314ade30279d410ced3f753ac8025b6fe206f75415fb4a4ed4` |
| `probe/original.exe` | 278016 | `8a5f8a65b72a65346812e38163a1b41f3371ef8748711ffd076b398652986dc1` |
| `probe/patched.exe` | 278016 | `70bc89c0ce1c2da999a6c4a66b1570551c189f60acafe3d041e1886d78f1c080` |

The 4 GiB RAM / 6 GiB commit reservation covered the complete run. All 1410 original
Seal C inputs passed before/after proofs; the twelve response files and two SDK
tools had separate retained bootstrap guards. The outer proof read 2369029504
bytes: two passes over the 1103512385-byte input set plus the five final artifacts.
All 1415 input/artifact guards were disposed. The full observed elapsed time was
144687 ms. The 65 retained output files total 194323460 bytes, also the observed
peak, below the unchanged 512 MiB stop threshold.

The qualified v6 collector identified the one pinned `vctip.exe` residual through
two fresh original-job membership captures and a guarded image-file hash. The
source-bound completion receipt passed, the original job was stopped, and a
fresh observation confirmed root exit zero and zero active members. The close
observation was 234 ms after root exit was observed, within the unchanged
2000 ms drain. The collector held 24167550 bytes. This does not claim compiler
ancestry or attestation of loaded process memory.

Final state is `Success=true`, `FinalArtifactsVerified=true`, `TreeClosed=true`,
`LeaseReleased=true`, with no retained token. The host checked the exact final
state digest and absence of its AppDomain quarantine key before exiting normally.
Fresh postflight at 11:17:35 UTC (13:17:35 Paris) found an empty registry, no other
heavy process, no surviving build/host PID and unchanged Main executable/creation
identity and UDP 27016 owner. All 42 source pins and six providers still matched.

| Evidence | Bytes | SHA-256 |
| --- | ---: | --- |
| `supervisor-state.json` | 6864 | `5a99ed368636d08d1d4407e3125cab73f5da879344880588c6aa54efcb556ed8` |
| `build-receipt.json` | 413367 | `a8253c8efa5b315c7870f27c6732eb6893528c0bd4c8ad3ddcbe7dde407faf62` |

The sanitized [checkpoint](build-f-checkpoint-2026-10-12.json) records phase,
probe, include, archive, artifact and closure evidence. Complete local files stay
under `runtime/zt-sound-md5-d`; preflight and host outcomes stay in the existing
ignored Plan directory outside that output. No native output is committed.

The corrected native executable is built, but it has not yet serialized the
original sound into a new SAB/FF. No playback was tested, no server was deployed,
and `SABFFVerified` / `Ready` remain false. Next action is source-only preparation
of the existing four-stage sound transaction using this exact candidate, followed
by a separately reviewed native GO. The coordinator owns integration and slots.
