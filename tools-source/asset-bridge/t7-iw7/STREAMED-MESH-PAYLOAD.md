# Selected BO3 streamed mesh payload

The first runtime export refused a shared mesh with `flags=9` and
`dataSize=18624`. This reader supplies a separate, bounded route from an observed
64-bit key to one owned CPU byte buffer. It does not change that resident-only
refusal, mask flags, infer the engine descriptor's three opaque words, discover
packages, or claim converted surfaces/FF/gameplay.

## Interface and ownership

`zonetool::t7::selected_xpak::read_selected_key(packages, key, expected, decoder)`
accepts a finite `span<const package>`, the observed key, expected size **18624**,
and a signed `int(const char*, char*, int, int)` LZ4 decoder. It returns
`payload{bytes, observed}` or throws `std::runtime_error`; no partial payload is
returned. The returned `vector<uint8_t>` owns its bytes.

Each package provides a name, stable identity, declared file size and exact-read
callback `(uint64_t offset, span<uint8_t>) -> size_t`. Portable callers must
retain immutable backing data. On Windows, `sealed_file(absolutePath).view()`
owns a shared RAII state retaining the original read handle, so views survive
destruction of the wrapper. A mutex covers the handle's seek/read transaction.

The Windows adapter accepts local absolute `.xpak` paths, refuses reparse or
inaccessible ancestry, opens with `FILE_SHARE_READ` only, verifies a disk file,
and compares its normalized resolved handle path with the admitted path after
open. Only the drive letter's case is normalized; alternate casing in path
components and short-name aliases are refused, including in case-sensitive NTFS
directories. It records `VolumeSerial8hex:FileIndex16hex`, size and last-write time.
Size/time are checked before and after each read. Views close the handle when
the last callback/state owner disappears. This is a stable input handle and
ordinary Windows sharing check; it is not a whole-file hash or an OS sandbox.
The launcher still owns source-root admission, the finite package list, live
resource reservation and the binding of the observed key to the selected mesh.

Observations include package name/identity, file bytes, key, hash-table and
matched-record offsets, absolute payload offset, compressed extent, original
packed entry size, actual indexed record bytes, codecs and opaque block-header
`Offset` values. Declared hash padding consumes the budget but is not read or
included in `indexed_bytes`.

## Accepted framing and refusal limits

| Input | Selected profile |
| --- | --- |
| Packages | Explicit nonempty list, at most 8 distinct identities |
| Header | Magic `0x4950414B`, BO3 version `0xA`, 120 bytes |
| Hash table | 24-byte records; aggregate declared size at most 8 MiB |
| Selected entry | Exact key, unique across all admitted indexes, 1–262144 bytes |
| Entry extent | DataOffset + relative offset; size uses low 56 packed bits |
| Command group | 128-byte header, Count 1–30, at most 128 groups |
| Command | Positive 24-bit compressed length; raw 0 or LZ4 3 only |
| Output | Exactly 18624 bytes; positive signed LZ4 result within capacity |

All header, hash and data ranges must fit the declared file. Nonempty sections
cannot overlap the header or each other. Every record's data range is checked,
including nonmatching keys. Indexes are read in 24 KiB chunks. An overflow,
short read, duplicate selected key, malformed later package, absent key or
unsupported profile prevents any selected payload read.

Only after the complete unique-index pass is one selected extent read. Commands
concatenate raw/decompressed bytes. Group padding aligns to 128 relative to the
entry's start. A final complete group may end at the extent end without unused
padding; present padding must reach a full boundary. Its byte values and header
`Offset` are opaque. Truncated padding, extra command data after full output,
unknown codecs, invalid signed LZ4 results and incomplete output are refused.
No BO4/Oodle/MW4 padding rule or process-wide XPAK cache is introduced.

## Format and dependency provenance

The adapter is original private code based on these pinned format observations:

- Owner ZoneTool `fab935826c898806855376662a8a03317b3ad8f1`,
  `src/zonetool/zonetool/t7/common/xpak.cpp` and the selected mesh loader.
- [Greyhound structures](https://github.com/Scobalula/Greyhound/blob/22c3d17f7428573042b56f43af0ed2585989bebd/src/WraithXCOD/WraithXCOD/DBGameFiles.h#L55-L95)
  and [selected entry decompression](https://github.com/Scobalula/Greyhound/blob/22c3d17f7428573042b56f43af0ed2585989bebd/src/WraithXCOD/WraithXCOD/XPAKCache.cpp#L154-L238).
  These corroborate framing; they do not qualify the opaque engine words.

Use the existing LZ4 1.10.0 dependency at
`1b0fc692949cf474eb0d89db5f0dfa3698e9aa56`. No dependency source is vendored here.
The CI fixture fetches only the pinned upstream `lib/lz4.c` and `lib/lz4.h`,
retaining their upstream license notices, and verifies these SHA-256 values:

| Source | SHA-256 |
| --- | --- |
| lz4.c | D8D5DC603D2157266C8A41285CCAF69EBE6432CBD92D40D3917D15A988E89888 |
| lz4.h | 774F26AFE507C3EA4E781FACA51DFCAD719F60804526CEF7FE223E3C3E534EEF |

## Validation and next integration

Source fixture: `test_streamed_mesh_payload.cpp`, C++20, links the pinned LZ4
dependency and exercises genuine `LZ4_compress_default`/`LZ4_decompress_safe`.
There are 49 core cases (10 reconstructions and 39 refusals), plus one Windows
sealing case. The latter checks retained-handle lifetime, ordinary write-open
refusal and release/cleanup. Inputs are entirely synthetic; the fixture takes
no arguments and reports `retail_files_read=false` and `engine_observed=false`.

The admitted native attempt A on 2026-10-13 at source `be0b6727ce9dbaaa081def243d73f5bcbaf51746`
compiled LZ4 and created `lz4.obj` (123791 bytes), but the owned compiler tree
did not complete before the 30-second group deadline. The fixture C++ build and
execution never started. The failure is preserved; owned-tree cleanup and lease
release completed, and the fresh registry was empty. No decoder/Win32 pass is
claimed for A. The driver was corrected by reusing the existing H1 original
root/member/stop adapters. Later attempts captured `vctip.exe` as the sole
remaining member after each successful original compiler exit; the selected
reader itself needed no code correction.

Attempt B at source `179114db9367d40123d55d6089f8480398bd3084` compiled both
translation units and actually ran the fixture successfully (exit 0 and the
expected 49+1 transcript), but its overall receipt remains **Failed**: the short
fixture had exited before live CIM child registration. This failure is retained.
The driver now accepts that missing live registration only when the existing
original kernel handle proves the exact root's completed PID/creation/image;
the lease and owned job remain retained until closure. Live or unknown identity
failures still refuse the run.

Attempt C at the same source revision passed the complete group on 2026-10-13:

- LZ4 C compilation, C++20 fixture compilation/link and actual execution all
  returned exit 0; the fixture uses MSVC 14.44.35207 `/O2 /MT /W4 /WX`.
- **49 core cases** (10 reconstructions, 39 refusals) and **one Windows sealing
  case** passed with expected output 18624. No retail file or engine was read.
- The original compiler root, expected artifact hashes and two original-job
  member captures preceded each owned residual stop. Fresh accounting/member
  lists were empty before ordinary close. All three jobs closed and the lease
  was released; the postflight had zero leases/heavy/game processes.
- Complete group: 4.2059378 seconds, 1739491 generated bytes. Fixture EXE:
  343040 bytes, SHA-256
  `F137A4EFD8CCEC8E97DE7348254D640DD40430A1BA43962C48634DFBA9374B3C`.

The compiled header SHA-256 is
`4572066E2A3692BFDEC563DAC87E8610506836C5BD7334F85672FE574D82208F`;
fixture source SHA-256 is
`B178C6C0EB7D069AC103368DD7C1A488E04CD8D3E4237E076BB474ED293C1096`.
These native source bytes remain unchanged by the validation documentation.
Failed A/B receipts and artifacts and successful C evidence remain preserved
under ignored runtime. The generated bytes do not include source packages.

The `Selected XPAK fixture` workflow compiles the same test on Windows with MSVC
`/std:c++20 /MT /W4 /WX`, then executes it. A local run must use the current
`iw7-mod-components` resource wrapper, one synchronous compile/link/run group,
and the existing VS2022/LZ4 inputs; no game launch or retail extraction is needed.
Admitted scenario: 256 MiB physical / 512 MiB commit estimates, under 4 MiB
generated, 30 seconds. Estimates are not measured peaks or memory caps.

Next, the native serializer owner must supply a freshly observed exact key and
admitted package identities, then retain the returned byte vector for its CPU
view/surface conversion. The proposed Freerun list has only
`mp_freerun_04.xpak` (786432 bytes) and `mp_freerun_04_d.xpak` (131072 bytes),
observed by metadata only. Neither a retail payload nor its key has been read
by this reader. That first real lookup and resulting FF require separate live
admission/evidence; synthetic decoder success cannot qualify them.
