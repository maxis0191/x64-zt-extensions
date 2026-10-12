# SAB/FF F: original sound bytes verified, playback still pending

One separately authorized invocation from source
`d9a0e966d71775e47b8e3f1549347bc0a4de5831` completed on 2026-10-12 between
15:29:34 and 15:30:01 UTC. Build, verify, dump and independent read all returned
zero with normal completion of both pipes, no drain exception, original-root
exit and zero active job members. The existing reader and its checksum checks
were unchanged. No codec repeat, game launch, server deployment or retry occurred.

The exact preparation pins are preserved in
[SAB-FF-CANDIDATE-F.md](SAB-FF-CANDIDATE-F.md). Review plan SHA-256 is
`5c0a3b4799fb3d9e2a998188ac61a213d89b75c515218cbef4843d5794f54b5b`,
execution plan is `3d90a5746a8ee698fb08715e270f2855f261b318393257f91a9e7f59e3ad39d5`
and command is `2009fda548d75eaf7f32ba2b1023e106550c8262dfb918917adecb66dbd726f7`.
The native executable is the 21696512-byte Build F candidate with SHA-256
`4740f0c22a1a7bab0b01f7a55ec0b133263ac218825ac3c0d15b9e269fe472b0`.
Its read guard was acquired before its first binary hash under the admitted
8 GiB RAM / 11 GiB commit transaction. The existing stock profile and thresholds
were preserved.

The loaded bank has one entry with twelve frames, twelve seek points and 48000
mono samples. The independent reader verified payload MD5, PCM MD5 and original
PCM SHA-256 `72cb02b5178ce424fd3df3dbfb28b0b9613f69a4da3af71a022b8b542a46ddd9`.
It also verified the source alias/asset relationship, all dump alias values,
unchanged seek/frame bytes and the two-entry native inventory (soundbank and
zone-branding rawfile). The streamed bank is empty.

| Retained artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `sdk_original_sound_v1.ff` | 544 | `13e878aeec2c545d5e6c8c02a6b75eb6061fd1bec14c9199450ef6a45e135900` |
| `sdk_original_sound_v1.sabl` | 114816 | `e0ce851bc7264a03d06e6ca2a44d15d424f1f4c01957ab0dda915879ca4d0110` |
| `sdk_original_sound_v1.sabs` | 4096 | `e490efefe70da393fd7830102637f3e0df12f6b6b0945e8c54cada2a6fef3b6f` |

A bounded comparison against the preserved failed run found exactly sixteen
changed SABL bytes at offsets `[110592, 110608)`: the old checksum
`78000000000000000000000000000000` becomes the correct original PCM MD5
`24fe5af1473ea8f4be33912348210c78`. Every SABL byte outside that field is identical;
the FF and SABS are also identical. The old state still hashes to
`c1b532dc3d61f0408f3ec4202e93fdf2d6394b0209ed3b2b9d2cdaaed7098276` and stays failed.
No retained bank or receipt was repaired in place.

That comparison and the supplementary 51-file hash inventory were sequential
snapshots **after lease release**, without retained input guards or admission.
They were computed after the 15:32:19.7453009 UTC postflight and before checkpoint
creation at 15:35:34.9110077 UTC. A second complete inventory check ran around
15:38:16 UTC in the commit command. No per-file timestamp was captured. These
checks do not establish continuous immutability or extend the under-lease proof.
An earlier auxiliary inventory attempt read a partial catalogue and stopped when
the 549664-byte `toc0.dcache` exceeded its local 512 KiB limit; no native Run or
retry occurred. The later inventory used a separate 1 MiB per-file bound, without
changing any runtime or independent-reader threshold.

All 77 staged inputs and 80 transaction entries were restored. The final state
records confirmed job closure/disposal, unchanged source hashes, preserved stock
and released read guards; no cleanup error, quarantine or retained lease remains.
The 40 hash inputs and retained artifacts were checked by the transaction under
its admission and guards, separately from those later snapshots. The reused stock profile
remains 71 hard links plus its 77-byte sentinel copy. Final accounting converged
to 51 files / 1404291 bytes; the highest sampled total was 1522299 bytes. The
64 MiB total and 2 MiB per-pipe limits are observed stop thresholds, not quotas.

The persistent host independently checked the final state hash and empty lease
registry before exiting normally with code zero. Its first manual directory
recount omitted `-Force`, missing the four-byte hidden `__iw7_ship` file; the
corrected inclusive recount matched the sealed state. This inspection correction
did not rerun any phase or change the state. Postflight at 15:32:19 UTC confirmed
both host PIDs and all four phase roots absent, no heavy/lab process and no lease.
The reviewed `MainStopped` helper from `5707abd` confirmed the original PID,
expected executable and UDP 27016 absent both before and after; Main was not
restarted and its prior stop cause remains unknown. The unrelated Python process
retained its original creation identity.

The final 65117-byte state SHA-256 is
`d0a57123f7940eee29ef42da7440dd353e63eeffbfc025d37b162f4feda9e1a9`.
The sanitized [checkpoint](sab-ff-f-checkpoint-2026-10-12.json) pins all 51 retained
files, phase receipts, artifacts and external pre/postflight evidence without
raw logs, stock data, machine paths or process identifiers. Complete evidence
stays in ignored `runtime/content-surfaces/original-sound-sab-ff-b`.

This proves the narrow original sound's SAB bytes plus native FF build/verify/dump.
It does not validate the native alias hash index, the writer's `16xCC` checksum
placeholder, standalone decode of the dump's rewritten FLAC metadata, delivery
or audible playback in IW7. `Ready`, `PlaybackVerified` and owner acceptance stay
false. Next action is coordinator review and private GitHub integration of this
checkpoint. Any playback, delivery or further native cycle needs a separate
reviewed plan and explicit GO; the completed plans are not reusable authority.
