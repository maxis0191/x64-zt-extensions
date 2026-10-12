# Native FLAC dump correction: source candidate

This implements the reviewed [metadata proposal](../FLAC-DUMP-METADATA-PROPOSAL.md)
as a private helper and a patch against the exact existing IW7 sound source.
It is **not built or executed natively**. No retained audio, SAB, FF, executable
or PDB was read or hashed during this source task. The F failures/successes and
strict readers/codecs are unchanged.

`sound_flac_metadata.hpp` admits only fixed-strategy, multi-frame, explicit
16-bit, non-hybrid headers. It derives the block bound from the first header,
checks CRC8, canonical frame number zero, channel assignment and rate against
the SAB entry, and rejects unsupported/malformed metadata. Inherited sample
rate can use the checked SAB field; inherited sample depth cannot. The helper
does not allocate, do I/O or change its inputs.

The patch applies this result to both STREAMINFO block bounds. It preserves the
stored seek/frame bytes, unknown frame sizes/MD5 and SAB ABI. Derivation happens
before the FLAC file opens. Refusals use the existing fatal path, including its
nonzero headless exit; they cannot disappear through an ignored Boolean return.

The sound-bank reader now checks table extents, each exact read, asset-name NUL
termination, wide payload length and actual file extent before allocating the
payload. Only the FLAC case allocates/reads its payload. Reads use
`file.read(target, 1, count)` and compare to `count`; writes likewise request
one-byte elements and compare the returned element count. Open, short write
and close failures are checked. No shared filesystem or job provider changes.
The pre-existing missing-bank return and non-FLAC dispatch behavior remain;
this is not a general sound-bank validation rewrite.

## Current verification

- Ten pure Python tests passed, including an independent header oracle over
  103 synthetic cases: 49 admitted headers and 54 refusals. They cover all block
  codes, rate/channel encodings, unsupported depths, ten truncation positions,
  CRC failure, single/final frame, hybrid, span/prefix mismatch and wide sums.
- The patch passed `git apply --check --whitespace=error-all` against the pinned
  source without being applied to the native checkout.
- Source preparation verified the pinned input and exact patched output. The
  private overlay contains only four source files plus a source manifest;
  no compiler, native probe, linker or decoder was started.
- `flac_dump_probe.cpp` and the generated case header are ready for a future
  compiled test of the **actual C++ helper**. The current Python tests do not
  execute that helper or the production file I/O. Real short-read/write/fatal
  propagation and compiler diagnostics remain native validation work.

The local `.gitattributes` treats only this unified-diff file's mandatory context
prefixes as patch syntax. The resulting C++ whitespace is still checked by
`git apply --whitespace=error-all`; ordinary source and documentation keep normal
Git whitespace checks.

The intentionally invalid trailing-body case is admitted as a valid *header*.
Neither the helper nor the tests claim full-stream CRC16, subframe, seek-table,
PCM or FLAC conformance. A later strict decoder must still reject bad audio.

Run only the pure tests from this directory with Python's
`-m unittest -v test_flac_dump_source.py`. They use small synthetic byte strings
and temporary source fixtures, not retained game/audio data.

## Prepared source overlay

`prepare_flac_dump_source.py` reads bounded source files, applies a strict
one-file patch in memory, verifies its exact result, and creates a fresh private
source directory. It never calls a compiler or constructs an executable Plan.
The current completed overlay is
`runtime/content-surfaces/original-sound-flac-dump-source-b`; it must not be reused
as a writable output. Its pins are recorded in `source-checkpoint.json`.
Preparation A is retained as an earlier source-only snapshot. B removes a
redundant comparison to `size_t` maximum: the checked file extent already bounds
the allocation length to the `size_t` file size. Neither preparation ran native
code, and no retained runtime evidence was repaired.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `sound_bank.cpp` | 113219 | `8142eead0fe7cbdb6a0b17cc106efa4d02f0652e9955657f220ce1b82d66c95e` |
| `sound_flac_metadata.hpp` | 6337 | `2226b5a9fa8afc241f843a5a1dc8da38574eb0c931a43f4d66a1b5eae0a19eca` |
| `flac_dump_probe.cpp` | 2037 | `320c2a3cb9617411fa6fe648f6ade946869879ace50a08bb73ff796aa019b5a8` |
| `flac_dump_cases.hpp` | 10402 | `fbf0e8c03c850af01b45c46a03bf183b8ce5355c294b2618493ca72a75673cb3` |

The native pin stays `fab935826c898806855376662a8a03317b3ad8f1`. The patch is
additional to the accepted bytewise source-MD5 correction; it does not replace
that correction or modify the shared native checkout.

## Concrete next build recipe, not an executable Plan

Reuse the existing sound-owned build supervisor, input guards, reservation,
owned job, phase runner, EOF receipts, output limits and quarantine behavior.
Do not add another launcher or alter shared providers. The old 14-step checksum
profile must remain closed and unchanged for its historical plans.

The conservative next profile has 17 explicit stages:

1. Existing original-checksum probe compile, link, run (three stages).
2. Existing corrected-checksum probe compile, link, run (three stages).
3. New FLAC-header probe compile, link, run (three stages).
4. Existing four loaded-sound consumers, updated IW7 sound-bank source and
   corrected common bit-buffer compile (six stages).
5. Existing private common archive and final candidate link (two stages).

This deliberately retains the validated checksum rebuild rather than treating
old intermediate objects as independently sealed artifacts. Build F's receipt
pins the final common library and EXE/PDB/probes, not every intermediate object.
Its small JSON receipt was inspected; its binary files were not reopened.

For the sound-bank compile, replace only the source path with the prepared
`sound_bank.cpp`. Add the original IW7 assets directory to its include search so
`sound_bank.hpp`, `sound_bank_subset.hpp` and `../common/sound.hpp` resolve to
their retained originals. The new metadata header resolves beside the prepared
source. Preserve the corrected common-header include priority, definitions,
`/Y-`, `/showIncludes`, runtime/library settings, and existing SDK rc tool pins.
All object, compile-PDB, EXE/PDB, response and log paths must be fresh and private.

For the standalone FLAC probe, compile the prepared probe beside its two headers
with the existing MSVC release settings, no PCH, `/W4 /WX`, and a fresh object/PDB;
link using the existing probe link recipe. Its successful JSON must report schema
`iw7.flac-dump-header-probe/1`, exactly 103 cases, unchanged inputs and extent
checks true, with native-dump/full-conformance/Ready false. Check zero exit and
normal EOF through the existing phase runner. These are three additional native
stages, not a Python-model success relabelled as a C++ success.

Before any build GO, the owned build contract/receipt validator needs an explicit
new profile for that closed 17-stage order and probe schema. Response validation
must admit only the reviewed source/include additions and new probe commands;
the current response-revision validator intentionally rejects more than macro
repair/output relocation. Guard the new source/response inputs separately from
the immutable Seal C list; do not backdate them into that seal. Revalidate all
reused sealed inputs under complete admission. This adapter/profile work and a
reviewable exact executable Plan are still pending; this source overlay is not GO.

Planning retains the previous 4 GiB RAM / 6 GiB commit build request, 512 MiB
output stop and 768 MiB planning ceiling, subject to the reviewed final inventory.
No resources have been reserved here. On 2026-10-12 the coordinator reported Main
running again; earlier MainStopped preflights are invalid. Preserve that running
instance and take a fresh identity/resource preflight only when instructed.

After a separately approved build, a fresh native dump transaction can read the
immutable F SAB/FF into a new output root. No new SAB serialization is needed for
this dump-only change. Its payload equality and new STREAMINFO boundaries need
independent checks, followed by a new explicitly pinned codec profile using the
unchanged strict decoder options and full original PCM comparison. Preserve
`NativeDumpF` and its failure. No playback, alias lookup or Ready claim follows
from this source candidate.
