# Original sound static closure representations

The `StandardModC` SAB reader exposes the exact small dump representations needed
by the SDK. This is static evidence for the fixed original fixture. It does not
qualify native alias indexing, playback, package delivery, recipient compatibility
or owner acceptance. All existing readiness flags remain false. Historical
`NativeDumpF` and `DumpOnlyC` outputs are unchanged and cannot supply this proof.

## Interface

`read_sab.inspect(...)` retains schema `iw7.original-sound-sab-read/1` and adds
`closure_evidence` only for `StandardModC`. The new object has exactly:

```text
schema: iw7.original-sound-static-closure/1
representations:
  soundbank: {path, bytes, sha256, content_base64}
  rawfile:   {path, bytes, sha256, content_base64}
dependencies:
  source_alias: {path, bytes, sha256, content_base64}
  aliases:      {path, bytes, sha256, content_base64}
  sample:       {bytes, sha256}
  inventory:    {bytes, sha256}
  auxiliary:    {<each of 16 bank field names>: {path, bytes, sha256, content_base64}}
artifacts:
  mod.ff:   {bytes, sha256}
  mod.sabl: {bytes, sha256}
  mod.sabs: {bytes, sha256}
```

All hashes are lowercase SHA-256 of the measured bytes. Representation paths are
closed dump-relative names, relative to `work/dump/mod`; `source_alias` instead
comes from the pinned original source root. The source and dumped alias share
the relative name `sound/community_original_sound_v1.all.aliases.csv` but may
have different numeric formatting and hashes. The sample measurement is for
`sound_assets/community/original_chime_v1.flac`; inventory identifies the exact
current verify log bytes. No paths in this object authorize arbitrary file reads.

The soundbank node hash is the hash of the **raw dumped bank JSON bytes** at
`soundbank/community_original_sound_v1.all.json`. Neither the bank name, a JSON
rewrite nor the containing FF may substitute for it. The rawfile node uses the
actual 28 bytes at dump-relative `mod`, which must equal
`Compiled using x64 ZoneTool.` without a newline. The bank descriptor's hash
alone does not cover its CSV/audio dependencies; the evidence object binds those
separately. The alias and empty tables are internal dependencies, not invented
native asset callbacks or additional SDK roots.

The SDK consumer calls **`read_sab.validate_closure_evidence(reader_result)`**.
It is a pure function: no files, executables, native types, FF or SAB reads. It
returns the validated evidence object and raises on disagreement. It decodes
bounded canonical base64, recomputes every embedded representation hash, checks
the closed bank structure, rechecks alias values against the embedded original
alias pinned to 947 bytes/SHA `a1db885270d7ca0e4cfe46ad7eb37ca6334544a73798740d8498fa2532ab7c65`,
checks the empty exports, and binds its three artifact pins to Reader measurements.
Parse external JSON with duplicate-key rejection and a receipt size bound before
calling it; `read_sab.strict_json(raw, 16384)` is available.

**This function does not authenticate a receipt.** A caller must first apply the
existing producer gate to bind the Reader to the explicitly pinned plan/state,
successful current verify/dump/read phases, source pins and artifact measurements.
The embedded bytes prove their own content and hash, not which process produced
them. Sample/inventory pins rely on that producer chain and are not independently
redecoded by the pure consumer. Do not run `inspect` from the materializer to
reopen a retained FF or SAB. Bind the SDK's standalone GSC node separately to
the exact delivered GSC source; no GSC node or script hash is synthesized here.

## Closed native export scope

Pinned ZoneTool `fab935826c898806855376662a8a03317b3ad8f1` source
`iw7/assets/sound_bank.cpp` (SHA
`46bc9e333cc9985ad3358e68a44adbc9b8469feabdbfe946aeb4eff8c1a068b5`)
always emits fifteen table CSV references plus `sound/unk/<bank>.json`.
The reader requires exactly those paths, exact native header-only CSV bytes,
and literal `null` for the unknown table. Nonempty rows, changed headers,
unknown fields, omitted references, extra alias lists and redirected paths fail.
The native adjacent literals `"Alias" "Range_Min"` produce `AliasRange_Min` in
the empty ambient-element header; the reader preserves that pinned behavior.

The original alias permits no secondary/stop alias or duck dependency. Existing
SAB checks still require the one original loaded sample, an empty streamed bank,
zero dependency/reserved bytes, exact extents/padding, source PCM and checksums.
The current native inventory still has precisely soundbank plus branding rawfile.

The reader snapshots every new file through `Inputs` and rechecks size/hash before
returning. As before, sequential snapshots do not promise persistent read locks.

## Bounds and validation

No existing consumer limit is increased. Raw bank JSON is bounded at 16 KiB,
alias representations at 8 KiB each, each auxiliary at 1 KiB, and rawfile at
28 bytes. Closure JSON has a 14 KiB compact bound; the complete pretty-printed
Reader has a 16 KiB bound, conservatively including Windows CRLF. Oversized but
otherwise valid bank JSON is refused rather than silently enlarging a receipt.
The existing 256 KiB per-file and 2 MiB cumulative read budgets remain in place.

The synthetic native-shaped fixture uses a 1,692-byte bank JSON and 1,111-byte
alias CSV derived from original source and pinned writer formatting. Its closure
is 11,376 bytes compact; its complete Reader is 14,557 bytes with LF or 14,769
with CRLF, below the existing 16,384-byte `read/stdout.log` limit. This fits inline;
no sidecar or extra output artifact is needed. The retained F state remains
unchanged; the producer's full new state is still subject to its own existing
output accounting and the SDK's 256 KiB metadata limit.

Tests use synthetic SAB/FF inputs only. Coverage includes exact raw node hashes,
JSON and numeric formatting, all auxiliary files, missing/changed rawfile,
duplicate/extra bank fields, path substitution, changed embedded bytes with
refreshed hashes, source drift, output bounds and historical profile separation.
The size test invokes real `Read-BeaconJson`, `Read-IW7SoundMetadata`,
`Assert-SoundFFReadback` and `Assert-SoundFFStandardReadback` when PowerShell is
available; it starts no native build or game process.

On 2026-10-12, all 49 tests below passed locally, including the four real
PowerShell metadata/readback functions. Development inspected pinned C++ source
and retained JSON metadata only; it did not open an existing game FF/SAB payload.

```powershell
python -B -m unittest test_sab test_standard_mod test_sound_closure test_dump_only test_helper_sources -v
```

Run from `tools-source/asset-bridge/surfaces/sound`. Integration must refresh the
new plan's `read_sab.py` source pin. The shared `sab_ff_helpers.json` does not
currently list this sound-local reader; this slice does not modify that manifest,
`SoundFF.Core.ps1`, `BuildJob.cs`, any SDK validator or any capability declaration.
