# Decode the native F dump: source-only plan

This preparation record was followed by one separately authorized execution of
post-commit Plan B. [CODEC-DUMP-F-RESULT.md](CODEC-DUMP-F-RESULT.md) records its
failed decode and confirmed closure. The preparation and original F dump remain
preserved; this document does not authorize a retry.

The [completed F transaction](SAB-FF-F-RESULT.md) proves the original sound's SAB
payload and checks the dump's exact metadata rewrite. It did not decode that
standalone dump. The native writer sets STREAMINFO min/max block sizes to 1024,
frame sizes to zero and PCM MD5 to zero; the unchanged payload contains eleven
4096-sample blocks and a final 2944-sample block. `read_sab.py` reconstructs the
original metadata before decoding SAB bytes, and deliberately leaves
`dump_standalone_flac_validated=false`.

The next proposed operation is one FFmpeg decode of the unmodified dump, followed
by an exact PCM comparison to the original WAV. No source rewrite, header repair,
resampling, ZoneTool build, stock staging or game is needed. A successful decode
would establish interoperability with this pinned decoder, not general FLAC
conformance or audible IW7 playback.

## Existing implementation and closed profiles

Only `Invoke-SoundCodec.ps1` and `codec_worker.py` change production behavior.
They reuse the existing scheduler, original Windows job owner and bounded pipe
drain without modifying those providers. Execution/worker/result schemas are now
version 2. A missing, unknown or incorrectly cased profile is refused; old schema
1 plans and receipts cannot silently become new execution authority.

| Profile | Exact FLAC SHA-256 | Successful status |
| --- | --- | --- |
| `OriginalSource` | `9f807b3f4dfee213dfd44e3f60b9109075327b233f321bdf38f594c3a0c47bbb` | `ThirdPartyPCMVerified` |
| `NativeDumpF` | `a4e9276568dfeaf42d39deefe243b1efc2b9095b2f558bcb3512b98c417154d9` | `DumpDecodedByFFmpeg` |

Both FLAC inputs are 96394 bytes. The dump profile binds the completed F state,
65117 bytes and SHA-256
`d0a57123f7940eee29ef42da7440dd353e63eeffbfc025d37b162f4feda9e1a9`, including its
successful status, original work path, closure/restoration and retained exclusion
flags. Input paths are fixed to the retained original source B or native F dump.
The worker independently chooses the expected hash from the same two closed
profiles; a caller cannot supply an arbitrary replacement hash.

The installed FFmpeg 8.1.2 is 242496512 bytes, SHA-256
`ad8f211bc894755e0061c55ab280ae00e8d3d4f15a8cc4372b24cfa247b5942e`.
The original WAV is 96044 bytes, SHA-256
`299727b757b46804ca52144133b7e72405f13ddcdaf8aea30a497afc62ca9cb4`.
These are prior pins, not fresh executable or payload hashes from this preparation.
The plan separately binds Python, the source manifest, F state and provider sources.

## Admission, guards and failure handling

Default Plan hashes/reads only its bounded JSON, then checks path, size, attributes
and timestamp metadata. It does not import the scheduler, load native types,
acquire a reservation or hash any declared input content. During Run, the plan
guard is retained first. Five exact bootstrap sources are individually guarded
and hashed before importing admission: this entry script, scheduler core,
Resource-Memory.ps1, ResourceMemory.cs and recorder-owned-process core. This small
source bootstrap is necessary to bind the code that acquires the reservation.

Atomic 512 MiB RAM / 1 GiB commit admission precedes every executable, audio and
F-receipt hash. Each input guard is acquired before that input is hashed; the
complete guarded set must pass before F evidence is parsed or a job is prepared.
On admission refusal, finally only rechecks already guarded bootstrap sources.
It cannot read an unguarded executable or audio entry through a failure path.
Partial input acquisition or uncertain original-job closure retains the lease
and reports failure; closing the host does not preserve file locks.

The original-job closure sentinel is set before its creation call, and the
10-second phase clock starts before resume. Success requires root exit zero,
zero active job members, both normal pipe completions, a bounded typed receipt,
exact profile and PCM evidence, and unchanged inputs before lease release.
The dump success flag is separate from original-source decoder validation.
`StandaloneFLACConformanceVerified`, `Ready` and `PlaybackVerified` remain false.
No SAB receipt or alias-index/checksum-checksum flag is changed.

## Concrete future operation and limits

Input is the retained file under
`runtime/content-surfaces/original-sound-sab-ff-b/work/dump/sdk_original_sound_v1/`
`sound_assets/community/original_chime_v1.flac`. The fresh output root is
`runtime/content-surfaces/original-sound-dump-codec-a`, which remains absent.
The post-commit plan and persistent-host command are prepared in the same ignored
parent directory and reported to the coordinator with exact lengths and hashes.
No runtime output is committed.

The FFmpeg argument vector is exactly the existing one: `-nostdin -n`,
`-loglevel info -xerror -err_detect explode`, one decoder/encoder thread,
explicit FLAC input, `-protocol_whitelist file`, first audio stream only,
no video/subtitle/data, metadata removed, PCM S16LE, bitexact flags and WAV output.
Neither `-ar` nor `-ac` is accepted. The output must contain exactly 48000 mono
16-bit samples at 48000 Hz: 96000 PCM bytes with SHA-256
`72cb02b5178ce424fd3df3dbfb28b0b9613f69a4da3af71a022b8b542a46ddd9`, equal to the
original samples. Incorrect WAV parameters, a codec error or a sample mismatch
stays failed.

| Bound | Value |
| --- | ---: |
| Complete RAM / commit reservation | 512 MiB / 1 GiB |
| Original-job phase / failed cleanup | 10 s / 5 s |
| Each captured pipe | 32 KiB |
| WAV success and observed stop limit | 128 KiB |
| FFmpeg `-fs` | 131072 bytes |
| Worker receipt | 16 KiB |
| Observed total output stop | 1 MiB |

Limits are observed stop checks, not filesystem quotas. Failed evidence is
preserved. A fresh PS7 `-NoProfile -NoExit` host is required; the prepared command
catches an error without exiting that host. The coordinator must separately
review and authorize one invocation, obtain fresh admission, verify postflight
closure/integrity/release and then close the host. No retry is implicit.

## Source validation only

Twenty Python tests cover both fixed profiles, swapped hashes, unknown profiles,
resampling refusal, exact synthetic PCM, codec failure and pipe/deadline failures.
Six actual-finally cases check original/dump success, unknown closure, failed
disposal, input drift and failed lease release. Four actual acquisition/finally
cases verify guard-before-hash and admission-before-payload ordering, including
refused admission and partial acquisition. Twenty-one pure profile/evidence
cases reject changed origin, paths, hashes, state flags and overclaims.
Nineteen default-Plan controls reject changed profiles, pins, arguments and limits;
read/hash spies permit only the plan JSON. Native owners/admission are mocked.
No real codec, binary hash, audio payload read, reservation or game belongs to
this source validation. Concrete plan preparation uses only metadata for retained
executables/audio and prior receipts for their hashes.
