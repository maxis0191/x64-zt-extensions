# FLAC dump metadata: source-only correction proposal

Status, 2026-10-12: proposal only. No patch, new native build, codec invocation,
payload read/hash, stock staging or game launch was performed for this analysis.
The failed [codec F checkpoint](../CODEC-DUMP-F-RESULT.md), its input and all
earlier artifacts remain immutable. The coordinator owns the next execution slot
and final integration. Tests below are proposed, not executed.

## Evidence and reusable source

The authorized strict decoder rejected `blocksize 4096 > 1024`. In the reviewed
IW7 `sound_bank.cpp`, `sound_asset_bank::flac::dump` writes both block bounds as
`BLOCK_SIZE = 0x400`, then appends the stored seek/frame bytes unchanged
(lines 2508-2514 and 2654-2697). The import path reads the original STREAMINFO
but retains only rate, channels and total samples in the SAB entry (2755-2773).
It discards block bounds, frame byte lengths and sample bit depth.

The source files were rechecked during this analysis:

| Native source under revision `fab935826c898806855376662a8a03317b3ad8f1` | SHA-256 of local source bytes |
| --- | --- |
| `src/zonetool/zonetool/iw7/assets/sound_bank.cpp` | `46bc9e333cc9985ad3358e68a44adbc9b8469feabdbfe946aeb4eff8c1a068b5` |
| `src/zonetool/zonetool/iw7/structs.hpp` | `adb62e481a533d27f97829e64d9038b13c5e9cd88e6b4aee8cac339b9492921a` |

`SndAssetBankEntry` is packed and statically asserted to 44 bytes
(`structs.hpp:13072-13091`). Its `BlocksizeKB` field has no use beyond its
declaration in the searched native `src` tree. Do not infer its semantics from
its name, start writing it, or enlarge the structure. The existing `StreamInfo`
and `write_metadata_streaminfo` can remain the serialization path.

No native FLAC frame parser or linked libFLAC/dr_flac helper was found in the
searched sources and dependency declarations. The common bit reader returns
zero on overread; it is unsuitable as an implicit bounds validator. Use a small
local byte reader with explicit failure. The existing independent Python
`read_flac.py` checks the generated verbatim subset, but is not a native helper
and must remain independent.

## Format constraints

STREAMINFO block bounds are 16..65535; the last frame is exempt from the minimum.
Frame byte lengths and PCM MD5 may remain zero when unknown. A seek table may
omit frames and contain placeholders. Fixed strategy identifies frame numbers;
its first canonical number is zero. Header fields encode block size, rate,
channels and depth, followed by CRC8. An inherited depth cannot be recovered
from this SAB entry. These constraints come from
[RFC 9639 sections 8.2, 8.5 and 9.1](https://www.rfc-editor.org/rfc/rfc9639.html#section-8.2).

## Smallest recommended first patch

Limit the first correction to fixed-strategy, explicit 16-bit, non-hybrid,
multi-frame streams. This covers the source fixture shape already proved by F.
It is a deliberate qualification boundary, not a universal FLAC exporter.

1. Add a local pure helper in the IW7 sound-bank source. Accept a const byte span
   and entry metadata; return a derived block size or a precise refusal reason.
   Validate positive 20-bit rate, 1..8 channels, known sample count, zero hybrid
   length, and the exact wide sum of seek bytes plus encoded frame bytes.
   Check the seek prefix fits the span and the metadata length field; require
   divisibility by 18 when present. Locate the first frame at `seekTableSize`.
2. Parse that first header with checked byte accesses: fixed sync/strategy,
   allowed field codes, mandatory zero bit and the canonical one-byte number
   zero. Read block-size extensions and rate extensions in their defined order;
   verify CRC8. Cross-check rate and channel count against the SAB entry. Accept
   the explicit 16-bit depth code only. A rate inherited from STREAMINFO may use
   the already range-checked SAB rate. Reject an inherited depth.
3. Decode the block-size code, including its optional one/two-byte extension,
   instead of substituting a new constant. Check `16 <= B <= 65535` and
   `entry.frameCount > B`: the first frame must be nonfinal in this initial
   profile. This first-header parser needs at most ten bytes, including CRC;
   it needs no generic UTF-8 reader because the first frame number is zero.
4. Set `info.min_blocksize = info.max_blocksize = B`. Keep frame-size fields
   unknown, retain the existing zero MD5, and serialize existing validated
   rate/channels/total samples. Do not change the seek/frame bytes. For the
   source fixture, this derives 4096; the final 2944-sample block does not lower
   the declared minimum. Those fixture counts are prior F evidence, not a new
   payload observation in this analysis.
5. Derive successfully before opening the output file. Refuse unsupported input
   instead of retaining the 1024 fallback. A simple `return false` is inadequate:
   loaded/streamed wrappers ignore `dump_internal`'s return at 3406/3416. The
   inspected existing `ZONETOOL_FATAL` headless path emits an error and exits
   nonzero. Use that established failure route for a native derivation refusal,
   and qualify it with a real negative probe later.

The caller at 3115 currently adds three 32-bit lengths before `read_bytes`, and
that helper does not report a short read. Include narrowly local checked wide
arithmetic, file-extent validation and an exact read-count check before passing
the FLAC span. Check entry/name reads and terminate the fixed name buffer before
using it as a string. Use the existing `file::read` return value; no shared
filesystem-provider edit is needed. Check output open/write/close results too.
These changes belong in the same sound source, not the shared bit-buffer helper.

Single-frame files, variable strategy, inherited bit depth, non-16-bit audio and
hybrid PCM are explicit refusals for this initial patch. A later extension can
handle them with separate evidence. Do not adopt `BlocksizeKB`, assume a complete
seek table, search compressed bytes for apparent sync words, or synthesize a
maximum of 4096/65535 to make the decoder accept an unexamined stream.

## What this would and would not establish

For a coherent fixed-strategy stream, its first nonfinal header supplies the
nominal block size. This helper does not walk later subframes, prove their CRC16,
check every seek target or prove the complete stream is coherent. A malformed
later frame can therefore survive derivation. The strict codec and independent
payload comparison remain required; full FLAC conformance stays a separate,
unproved claim. Keeping unknown MD5 is not PCM checksum verification.

The ABI, SAB import/write layout, source checksum fix and alias data stay intact.
Only a future standalone dump changes. Wider support could require a proper
bounded frame walker or a reviewed dependency; neither is needed to test this
specific fixed-stream correction. Refusing previously dumped unsupported assets
is a compatibility limitation to document before wider distribution.

## Proposed tests and later validation

Source tests should exercise the actual future C++ helper with synthetic header
arrays: 1024, 2048, 4096 and extension-coded sizes; every truncation boundary;
CRC failure; bad sync/reserved fields/number; variable strategy; invalid or
inherited depth; mismatched rate/channels; 65536; last/single-frame rejection;
bad seek prefix, length overflow and short reads. Output tests must prove that
refusal never opens the FLAC target and that allowed input changes only intended
STREAMINFO fields. Test sparse/empty seek tables without treating them as a frame
inventory. A first valid header plus invalid later data must not be described as
full conformance. A model alone is not a compiled native-helper test.

After source review and a separate coordinator GO:

1. Prepare fresh source guards, exact patches, build plan and response bindings.
   Preserve the existing bytewise checksum correction. Reuse reviewed toolchain
   and dependencies in read-only mode; no shared native/H1/T7 writes. The prior
   4 GiB RAM / 6 GiB commit build budget is a planning basis, not new admission.
2. Build and qualify native positive/negative helper probes in a fresh private
   output. Recalculate affected translation units, PCH consistency and artifact
   budgets from the final diff; historical Build F plans cannot be rerun.
3. Under a separately admitted native transaction, dump from the immutable F
   SAB/FF inputs into a fresh root, with their guarded identities. Keep the old
   failed dump and all old receipts. The prior 8/11 GiB native budget must be
   reviewed for that exact plan. No new SAB serialization is required merely to
   test a dump-only correction.
4. Qualify a new explicit codec profile and exact new input hash/state binding.
   Preserve `NativeDumpF` as historical failure. Under fresh 512 MiB / 1 GiB
   admission, use the same strict FFmpeg options and compare all 48000 mono16
   samples to the original PCM. Keep independent compressed-payload and byte
   boundary checks; do not relax old readers to admit the old invalid header.

None of these future stages proves an audible alias in IW7. `Ready`, playback,
native alias-index verification and full standalone conformance remain false
until their own evidence exists.
