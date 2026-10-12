# Strict external decode of the qualified C dump

`NativeDumpOnlyC` is a separate closed input profile in the existing codec worker
and supervisor. `OriginalSource` and the failed historical `NativeDumpF` keep their
original identities and behavior. No decoder, format, resampling or permissive
fallback is added.

The actual DumpOnly A run completed `dump,read`, closed both original jobs,
restored the reused stock/FF/SAB links, revalidated original inputs and the new
dump under admission, disposed guards and released its lease. Its independent
host-absence witness is recorded in `dump-only-checkpoint-2026-10-12.json`.
The dump is 96394 bytes, SHA-256
`1f20e4e3d2ea9160c833ba2f188950908573c9bf677e63e10edf639efd40c725`.
Its state is 62517 bytes, SHA-256
`761ef1246010482d9451e1feae1b7e0f2e75bcd0ea678a1ce70f294184d669df`.
Preparation uses this observed identity from the receipt; it does not hash the
audio again after release.

The new profile requires those exact state/input pins and validates the state
after the existing admission and retained guards: successful C dump/read phases,
zero job members, normal EOF, restored stock/source, confirmed byte accounting,
no quarantine or retained token, exact F provenance, 4096 reader scope, and the
dump identity captured/revalidated under the original lease. Default Plan mode
still reads only the Plan and checks input file metadata. Binary/audio hashes
and dump-state content validation during execution remain after admission.

FFmpeg stays at its pinned 8.1.2 binary and existing literal argument list:
`-xerror -err_detect explode`, one thread, file protocol only, no overwrite,
resampling, channel conversion or selected fallback. Acceptance still requires
exact PCM equality with the original WAV: 96000 bytes, 48000 mono 16-bit samples
at 48000 Hz, SHA-256
`72cb02b5178ce424fd3df3dbfb28b0b9613f69a4da3af71a022b8b542a46ddd9`.
The 512 MiB physical / 1 GiB commit reservation, 10-second execution and
5-second cleanup deadlines, 32 KiB per pipe, 128 KiB WAV and 1 MiB total output
limits remain unchanged.

Source validation: 20 mocked Python worker tests (including separate new-profile
success and cross-profile hash rejection), 53 synthetic profile/evidence cases,
19 default-Plan/refusal cases, four admission ordering cases and six cleanup
cases. The first synthetic positive case exposed PowerShell's automatic JSON
DateTime conversion: string equality rejected the same timestamp. The guard now
compares exact UTC ticks and its regression rejects a one-tick change. None of
these tests invokes FFmpeg or reads an actual audio/executable payload.

No external decode of this new dump is claimed by this source change. Its real
codec Plan/dispatch needs a separate reviewed GO. A successful decode would
qualify exact PCM recovery only; playback, alias index, checksum-checksum,
standalone FLAC conformance and Ready remain unverified.
