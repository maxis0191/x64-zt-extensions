# Original PCM sound source adapter

Latest checkpoint, 2026-10-12: the single authorized FFmpeg decode passed against
the retained original source B. PCM and the complete resulting WAV match the
original exactly. See the final section and `codec-checkpoint-2026-10-12.json`.
SAB/FF creation, delivery and audible game acceptance remain unverified.

This source-only adapter prepares an original short WAV, lossless FLAC sample,
one IW7 alias and a bank/zone source inventory. It does not build a sound bank,
fastfile or executable, launch a codec/game, or prove audible playback.
The default command is a Plan and leaves the requested output directory absent.

## Existing local native entry points

Audited local x64-zt revision: `fab935826c898806855376662a8a03317b3ad8f1`.
Line references below refer to that retained revision, under
`src/zonetool/zonetool/iw7/assets/sound_bank.cpp`:

| Entry | Existing behavior / remaining gap |
| --- | --- |
| `sound_bank::parse`, line 3444 | Reads `soundbank/<name>.json`, its alias/table paths, then calls `sound_asset_bank::create`. |
| `aliases::parse_file`, line 214, and `aliases::parse`, line 358 | Reads 53 positional CSV columns, groups alias heads and creates the alias hash index. Unknown enum strings can silently resolve to default indices; the adapter checks emitted names against the pinned tables. |
| `find_asset_file`, line 3134 | Resolves `sound_assets/<File>.flac` first, then `.wav`. The alias File column excludes the extension. |
| `flac::parse`, line 2710 | Reads STREAMINFO metadata and optional SEEKTABLE; writes seek data and compressed frames into the SAB entry. It does not independently decode every frame. |
| `pcm::parse`, line 2888 | A WAV parser exists, but the SAB constructor does not call it. It accepts more formats than its PCMS16 label establishes, and its length/chunk handling is not a strict PCM validator. |
| `create_internal`, lines 3160 and 3295-3303 | The PCMS16 call is commented out and WAV logs an unsupported error; an empty entry can still be appended. The adapter never stages a WAV in `sound_assets`. |
| SAB dump, line 3122 | PCMS16 dump is also commented out. The dormant WAV dumper writes block alignment 0x400, unsuitable for a canonical mono16 PCM file. |
| `create`, line 3435 | Creates both SABL and SABS according to loaded/streamed alias flags. Their delivery beside the FF and actual engine decode remain separate future gates. |

The adapter hashes four local source files before preparing anything: the bank
reader/writer, common sound helpers, structs and sound-global tables. It reuses
the existing 53-column source contract without modifying it. No retail sample or
bank is read or redistributed. The native PCM path and shared providers are not
patched. A bank JSON/FF containing an alias is not proof of audio delivery.

## Bounded conversion

Input is canonical RIFF/WAVE with exactly `fmt ` (16 bytes) then `data`, PCM16
little-endian, mono, 48000 Hz, 16 through 96000 samples. Other metadata chunks,
stereo, float/ADPCM/extensible WAV, resampling, truncated/trailing bytes and
inconsistent rate/alignment/length fields are refused. A supplied WAV requires
`--attest-original`; this records the caller's assertion, not a rights inference.
The default original marker is one second of three faded integer triangle pulses
at 500, 750 and 1000 Hz, peak at most 4096, surrounded by silence.

The encoder uses the restricted FLAC format described by
[RFC 9639 sections 8-9](https://www.rfc-editor.org/rfc/rfc9639.html#section-8):
fixed 4096-sample blocks, mono16/48k headers, verbatim subframes, CRC8/CRC16,
STREAMINFO PCM MD5 and one exact seek point per frame. The final block may be
shorter. This deliberately trades compression for a small, inspectable source
fixture; the generated FLAC is slightly larger than its PCM payload.

`read_flac.py` is a separately implemented Python parser with no import from
the encoder. It reconstructs little-endian signed PCM and checks metadata,
sequence/counts, every seek offset, header/frame CRCs, MD5 and exact file closure.
Its polynomial-division CRC checker is separate from the encoder's shift-register
implementation. It refuses features outside this narrow subset. Comparing its
result to the original WAV establishes this source-level sample roundtrip, not
third-party decoder interoperability or IW7 playback. Those flags remain false.

The original alias is `community_original_chime_v1`: loaded, nonlooping, one head,
channel `scn_fx_unres_2d`, volume modifier `interface`, volume 0.5 and pitch 1.
No secondary/stop alias, duck, localized retail table or subtitle is borrowed.
The 2D presentation is a proposed fixture choice, not measured engine behavior.

## Source-only commands

Use Python 3.12 or later. All commands below are light Python/source operations;
these preparation entry points never call the separately gated codec observer.

```powershell
$sound = 'tools-source/asset-bridge/surfaces/sound'
# Existing pinned local source checkout; do not fetch/rebuild ZoneTool here.
python -B "$sound/prepare_sound.py" --zt-source <local-pinned-x64-zt> --output <fresh-output>
python -B "$sound/prepare_sound.py" --zt-source <local-pinned-x64-zt> --output <fresh-output> --write-source
python -B "$sound/read_flac.py" <fresh-output>/sound_assets/community/original_chime_v1.flac
python -B "$sound/test_sound.py"
```

`--wav <original.wav> --attest-original` optionally replaces the generated input.
The output must not exist and no root/input path may use symlinks or junctions.
Preparation uses exclusive new files and preserves any partial failure directory;
no overwrite/cleanup/retry is implicit. The Inspector's three observed files must
match the expected inventory, then all seven prepared files are reread and hashed
before publishing the final manifest. A drift refuses success and retains the
partial directory without that manifest. These sequential checks are a preparation
checkpoint, not persistent file locks; later native use must rehash/read-guard its
inputs. Prepared output is capped at 512 KiB, decoder input at
200000 bytes, and sample count at two seconds. Source artifacts stay in ignored
runtime storage; no WAV, FLAC, SAB or FF binary belongs in Git.

The manifest inventories the original WAV, FLAC, bank JSON, alias CSV, zone CSV,
PCM readback and existing-content preflight, with sizes/hashes plus source pins.
It binds the adapter Python sources and the existing content contract. The
existing inspector must report zero errors and exactly its pending SAB/playback
finding. `native_sab_built`, `ff_built`, `external_decoder_verified`, `delivered`,
`playback_verified` and `ready` all remain false.

## Measured source checkpoint: 2026-10-12

Twenty Python tests pass, including malformed formats, CRC/MD5/seek corruption,
signed extremes, partial final blocks, maximum size, missing source pins,
attestation, unchanged output refusal and Plan without writes. The Python stdlib
WAV reader independently confirms the generated input parameters and samples.
A real Plan and source preparation against the four pinned local files also
pass; none of those checks compile or invoke native ZoneTool code.

Retained current source: `runtime/content-surfaces/original-sound-source-c`.
It contains eight files totaling 199125 bytes. The standalone Python decoder
reads 48000 samples in 12 frames. Existing content preflight: 0 errors / 1 pending.

| Evidence | Bytes | SHA256 |
| --- | --- | --- |
| Source manifest B | 3158 | 06a2bf8650ba235e176746efe29b00f383e26144cd24ff5dd1774c28f9d71a01 |
| Source manifest C, final integrity checks | 3158 | 627ea10517bfe0f4cbfa6ca8d0c4b5b6b90024179fd776f917656c7ca4e5b5a7 |
| Original WAV | 96044 | 299727b757b46804ca52144133b7e72405f13ddcdaf8aea30a497afc62ca9cb4 |
| Prepared FLAC | 96394 | 9f807b3f4dfee213dfd44e3f60b9109075327b233f321bdf38f594c3a0c47bbb |
| Decoded PCM | 96000 | 72cb02b5178ce424fd3df3dbfb28b0b9613f69a4da3af71a022b8b542a46ddd9 |

The first source preparation A is retained unchanged, manifest SHA256
2507c294c9cd672b6c4452f49c23b1f1e1af8a18804fc6859970a3ec4c1cd3fd.
Review found lowercase alias booleans while the actual `FALSE_TRUE` table is
case-sensitive `False`/`True`; lowercase `precached=true` would resolve to false.
Source B corrects the spellings and extends exact enum checks to the common and
bank-local tables. Its CSV SHA256 is
a1db885270d7ca0e4cfe46ad7eb37ca6334544a73798740d8498fa2532ab7c65.
This was a source-review correction, with no native run or audio failure. A is
superseded for future native preparation; neither A nor B has native acceptance.

Independent source review then reproduced a preparation integrity gap: changing
alias volume from 0.5 to 0.2 between writing and Inspector allowed publication
using stale buffer hashes. The correction compares Inspector's observed inventory
to the expected bytes and rereads every prepared file before the success manifest.
Regressions mutate the alias before preflight and each of the six initial files
after preflight, including the original WAV outside the Inspector's dependency
set; all preserve partial evidence and refuse a success manifest. Fresh source C
passes those gates. Its seven payload/report files are byte-identical to retained
B, including FLAC, WAV and alias; only the manifest's adapter source hashes change.
The explicitly planned codec check can still target those exact hash-bound B bytes.
No source preparation has codec-native, SAB, FF or audible acceptance yet.

Next coordinated gate: first decode this exact FLAC with a reviewed independent
codec, then separately admit existing ZoneTool bank/FF creation and inspect SAB
entries, checksums, alias index and delivery. Do not rebuild ZoneTool just for
this fixture. A later protected private recipient test must prove lookup, audible
playback, stop/retrigger, language routing, cache/join lifecycle and restoration.
No game/native GO is included in this source checkpoint. Material C is unchanged.
Commits are handed to the parent for central private PR/CI/merge and common docs.

## Existing third-party codec observer: source/Plan only

`Invoke-SoundCodec.ps1 -PlanPath <plan.json> -PlanSHA256 <sha256>` checks the
reviewed JSON, exact argument array, required source/input pins and absent run
root, then returns the plan. This default path imports no scheduler, loads no
native class, takes no reservation and starts no codec. `-Run` is reserved for
the central unique GO after earlier queued heavy work is closed. There has been
no native codec execution at this checkpoint.

The planned codec is the already installed FFmpeg
`8.1.2-full_build-www.gyan.dev`, 242496512 bytes, SHA256
ad8f211bc894755e0061c55ab280ae00e8d3d4f15a8cc4372b24cfa247b5942e.
Its installed README and embedded version string were read without running it.
No install, copy, new framework or ZoneTool rebuild is needed. The exact retained
B FLAC and original WAV remain the inputs; source C has identical audio bytes.

Only this narrow one-second decode receives the approved Analysis estimate of
512 MiB RAM / 1 GiB commit; no other profile is reduced. The existing shared
scheduler admits it exclusively. The unchanged `BuildJob.cs` creates a suspended,
BelowNormal, non-breakaway, kill-on-close job around a tiny Python worker. The
worker calls pinned FFmpeg without a shell and reuses the unchanged SDK
`copy_bounded` function with an explicit 32768-byte limit for each log.
All reviewed input/source files and the plan have read handles denying write and
delete sharing until finalization. The codec executable is used in place.

Arguments explicitly select FLAC input, PCM16 WAV output, one decoder/encoder
thread, the local-file protocol and overwrite refusal. No sample-rate, channel
count or duration conversion is requested. The worker checks native exit 0 and
both pipe EOFs, then the Python standard-library WAV reader checks mono16/48k,
48000 frames, exactly 96000 PCM bytes, the expected SHA256 and equality with the
original. The parent checks the output file against the worker's size/hash.
Each pipe also needs an explicit completion event from the pinned drain's normal
return. A local wrapper catches every `BaseException`, records only its type
(at most 128 characters), and sets the shared failure event. Dead threads alone
never establish EOF. The PowerShell receipt check requires both normal returns.
This future evidence would qualify codec decoding only; no SAB/FF/delivery or
audible acceptance is inferred, and original preparation manifests are not edited.

The outer monotonic deadline is 10 seconds from Resume, including registration,
pipe drain and readback. Logs are capped at 32 KiB each, worker receipt at 16 KiB,
successful WAV at 128 KiB and all temporary outputs at 1 MiB. The 100 ms watchdog
refuses WAV growth beyond 256 KiB. FFmpeg `-fs 131072` is a secondary stop request,
not an exact hard file-size cap. Commit pressure above the shared 85% threshold
also stops the run. On failure, only the original job is stopped; cleanup must
observe its exited root and Active0 within five seconds. No captured PID is killed.

Acceptance requires worker/native success, EOF, original root exit 0, Active0,
output match and final source integrity. Reservation release follows closure,
successful disposal of the original job owner, and integrity. Finalization attempts
job disposal before releasing read guards. Kill-on-close requests termination but
does not establish descendant closure if the original observation failed.
`InputHashesMatch` reports the final hash snapshot; `InputsUnchanged` cannot be
true without proven closure and successful job disposal. Uncertain closure or
disposal keeps `Quarantined=true`, `InputsUnchanged=false`, the lease and evidence.
Read guards are then released and `ReadGuardsReleased=true` reports that fact;
they cannot protect inputs after supervisor exit. Quarantine therefore requires
central investigation, not an assumed surviving file lock or an automatic retry.
No PID-only termination or unbounded wait is added. Errors preserve their fresh
run directory. No stock, owner client or Main file is touched.

Sixteen mocked worker tests cover native nonzero exit, log flood/truncation,
deadline, inherited open pipe, PCM/metadata corruption, argument/hash drift and
existing output, plus read `ValueError`/`SystemExit`/`KeyboardInterrupt`, unformattable
and long exception types, write/flush failures, provider-caught `OSError`, and a
dead thread with no normal-return event. They use fake processes and do not
execute FFmpeg. Five cases execute the actual PowerShell finalization body with
mock owners/guards/leases: success, unknown closure, disposal failure, changed
input and release failure. They verify disposal-before-guard-release, quarantine,
the distinction between matching hashes and qualified integrity, and retained
leases. These are control-flow tests, not native closure or lock-lifetime evidence.
Six actual
default-Plan controls pass, including required-pin/hash/argument/root refusal and
absence of native classes or generated run root. PowerShell syntax passes too.

```powershell
python -B tools-source/asset-bridge/surfaces/sound/test_codec_worker.py
pwsh -NoProfile -File tools-source/asset-bridge/surfaces/sound/test_codec_cleanup.ps1
pwsh -NoProfile -File tools-source/asset-bridge/surfaces/sound/test_codec_plan.ps1 -PlanPath <reviewed-plan.json> -PlanSHA256 <sha256>
```

The prior standalone WAV comparison and provisional codec plans remain ignored
historical preparation. The execution plan pins this worker and the shared drain,
owner, scheduler and memory sources; it replaces the provisional second verifier
process with the same bounded WAV/sample checks inside the owned Python root.

Independent review of commit `58d78d0` reproduced a false EOF from an unhandled
drain-thread `ValueError` and identified overly broad integrity wording after
uncertain job closure. Both corrections above are local to this sound adapter;
the shared drain, job and scheduler remain unchanged. The prior execution plan
is retained as evidence and no longer matches the corrected source pins. A fresh
reviewed plan and central GO remain required; no codec has run at this checkpoint.

## Authorized native codec checkpoint, 2026-10-12

After independent review closed the drain-exception and uncertain-closure findings,
the central coordinator authorized one FFmpeg run on source commit
`b31695be7a39cc1aa05bd748e6b2cc72d7ce8e58`. The reviewed v2 execution plan SHA256 was
6430949bbfe3b55d08bb547e2fe01313853101f77e76e2af2041f35a26270541.
Current `origin/main:docs/RESOURCE-WORKFLOW.md` was fetched/read first. The fresh
registry had no lease, and the complete 512 MiB RAM / 1 GiB commit scenario passed
admission without changing any other workload estimate. No retry was performed.

The installed FFmpeg 8.1.2 returned zero and decoded the original FLAC into mono
PCM16 at 48000 Hz: 48000 samples, 96000 PCM bytes, SHA256
72cb02b5178ce424fd3df3dbfb28b0b9613f69a4da3af71a022b8b542a46ddd9.
The entire 96044-byte WAV also matched the original byte for byte, SHA256
299727b757b46804ca52144133b7e72405f13ddcdaf8aea30a497afc62ca9cb4.
Both pipe workers reported explicit normal return with no exception and EOF.
The owned Python root was observed exited with code zero and job Active0 after
467 ms from Resume. Its scheduler identity was attached successfully; no Stop
or failure cleanup was required. Original job disposal completed, all read
guards were released, and the state recorded no quarantine or retained lease.
All 14 reviewed files still matched size, attributes, timestamp and SHA256 after
the run. At 06:22:51 UTC the fresh registry was empty and neither run process
remained. This is measured codec and job evidence, not a lifetime guarantee.

The five retained output files total 101950 bytes: WAV 96044, state 1897, worker
receipt 805, stderr 3204, stdout zero. Their hashes and the result boundaries are
recorded in the sanitized checkpoint JSON. Local evidence remains in
`runtime/content-surfaces/original-sound-codec-check-b`; no raw log, local process
identity or machine path is included in the tracked receipt. The historical
source manifests and reviewed execution plans were preserved unchanged.

`ExternalDecoderVerified=true` now applies to this exact original FLAC. `Ready`
and `PlaybackVerified` remain false. This authorization did not include SAB/FF
creation, stock preparation, client launch or any action on Main. The next gate
is a separately reviewed/admitted existing-ZoneTool SAB/FF plan with bounded
independent bank readback; the small codec budget does not apply to that stage.
The coordinator owns the private PR, exact-head CI, merge and common documentation.
