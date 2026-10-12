# T7 executable: bounded static preparation

Source reviewed: `fab935826c898806855376662a8a03317b3ad8f1`, 2026-10-12.
The official candidate is app545990, depot545991, public manifest
2350066205567669287, build4500243. These identify acquisition metadata;
no executable has been inspected by this work and compatibility is unproved.

`main.cpp:447-454` checks only IW6. T7 selects the executable by filename,
loads it through `LoadLibraryA`, and triggers `post_unpack` through the replaced
`SetProcessDPIAware` import. T7 symbols return absolute addresses without rebasing.
The CLI overlay's existence/mode checks are not a version check.

## First comparison

Keep the acquisition receipt and its actual executable SHA256. No historical
known-good hash is required or fabricated. Check AMD64/PE32+, preferred base
`0x140000000`, image size, sections/permissions, entrypoint, imports, relocation
directory/DynamicBase metadata and relevant `.pdata`/UNWIND_INFO. A preferred
base does not prove the eventual mapped base. No PDB/CodeView requirement applies.

The first five source-selected windows total **864 bytes**. RVA is VA minus
`0x140000000`; file offset must be resolved through a unique file-backed section.

| Site VA | Window start VA / length | Source expectation, not observed retail evidence |
| --- | --- | --- |
| `0x1401D5FB0` | same / `0x100` | DB_Find returns XAssetHeader; arguments type/name/bool/int; caller uses 0/-1, model type4 and mesh type5 |
| `0x1401D8740` | same / `0x100` | DB_Load takes XZoneInfo*/count/sync/suppressSync; includes the five-byte NOP at `0x1401D87AE` |
| `0x1401632C0` | same / `0x80` | SL_ConvertToString takes unsigned int and returns char* |
| `0x140502AA9` | `0x140502A89` / `0x60` | Five-byte CALL, original target inferred as `0x140504170` because the replacement invokes it |
| `0x140537840` | same / `0x80` | RET replacement must be at a function entry, before a prologue or side effect |

The boot CALL displacement is computable from source addresses; it is not an
observed signature or a known-compatible fingerprint. `utils::hook::call` writes
five bytes without checking the original. Likewise, the DB_Load NOP needs whole
instruction boundaries at both ends. `XZoneInfo` has a pointer followed by four
uint64 fields; qboolean is int. Plausible prologues cannot prove those ABIs.

Do not decode backwards from an arbitrary window start. The inspector anchors
at `.pdata` BeginAddress only when that entry lies inside the selected window.
Otherwise its decode is explicitly `source_assumed_site`, with an indeterminate
boundary. Missing unwind metadata, packed/transformed code, truncated windows
or unavailable disassembly must not become positive compatibility evidence.
Overlapping `.pdata` function ranges invalidate the directory as an anchor:
the report remains indeterminate and never silently chooses one overlapping
record. Adjacent half-open ranges are valid and have unique boundary ownership.

## Remaining fixed sites

The inspector's fixed `SITES` list includes the following bounded extensions;
there is no scan, address override, recursive call following or asset read:

- Original init/frame/image loader: `0x140504170`, `0x140501F90`, `0x1401DB2B0`.
- Other RETs: `0x1401E6050`, `0x1407EA850`, `0x1407D5F70`; short-branch opcode
  replacements: `0x1401A18DF`, `0x1401A1B5B`; image CALL: `0x1401B1E5D`.
- DB detours: `0x1401D4600`, `0x1401D3F00`; scheduler: `0x1405020E0`;
  command jump: `0x1404F9CD0`.
- Precomputed integrity sites: `0x140064DC4`, `0x140909BD4`, `0x1410654C1`,
  `0x1400621A8`. `arxan.cpp:16` enables the precomputed path. Comparisons use
  the existing source's pattern expectations, not independently observed bytes.
- Actual database readiness: `0x1405261E0`; DB name/existence/default:
  `0x14019F080`, `0x1401D5C20`, `0x1401D7260`.
- `load_zone` callees: `0x140506C70`, `0x1401360A0`, `0x1406FF940`,
  `0x14014C610`, `0x140309FF0`, `0x14038ED20`.
- Only the first scalar/pointer-sized disk sample of asset-name/zone globals
  and the current fastfile-name pointer. BSS is not file-backed data; disk
  contents never prove the initialized runtime values.

## Inspector and evidence

`inspect_t7_executable.py` reuses `rig-abi/symbol_identity.py`'s bounded reader
and its **4 MiB cumulative read budget**. It reads PE metadata, at most128 import
descriptors/4096 total thunks/512 bytes per string, at most2 MiB of `.pdata`,
bounded unwind records and the fixed windows. It checks file-handle identity,
size and timestamps before/after. It neither maps nor executes the input image.

No dependency is installed. Metadata, RVA checks and tests use stdlib. Capstone
is imported only inside actual inspection and is optional: unavailable means
no disassembly and explicit indeterminate observations. The existing local
Python312 has Capstone. Tests cover a missing-Capstone path; the optional native
decoder test skips when unavailable. CI needs no pefile or Capstone dependency.

After acquisition and coordination, from the checkout root:

```powershell
python -B tools-source/asset-bridge/t7-iw7/inspect_t7_executable.py <official-exe> --output runtime/t7-static/inspection.json --acquisition-sha256 <receipt-sha256>
```

The optional acquisition hash is labelled **unverified by this inspector**.
The hash of the observed read sequence is not a full-file hash. JSON includes
raw bytes and local identity, so output is restricted to a new file under this
checkout's ignored `runtime/`; no overwrite. Do not commit or upload that JSON.
Version a small receipt containing input provenance/hash, source/script hashes,
read budget, conflict/indeterminate counts and the actual review decision only.

Source-pattern deviations, non-executable code sites, an incompatible preferred
base, out-of-image fixed addresses or anchored instruction-boundary conflicts
produce `stop_before_boot`. Unknown observations remain indeterminate; even a
clean report is `indeterminate_manual_review_required`. Exit0 means a report
without detected conflicts was written, not compatible or authorized. Invalid
top-level headers/read bounds stop with exit2; optional metadata or window-read
failures remain explicit indeterminate observations. `boot_authorized` and
`runtime_compatibility_proven` are always false.

A reviewer must resolve conflicting sites before boot. Coherent static evidence
may justify a separately authorized supervised experiment; it does not replace
resource admission, runtime mapped-base verification, logs or cleanup proof.
No new runner, debugger, CDB execution or launch authorization is introduced.

Validation: synthetic PE tests cover section/RVA boundaries, overlap, truncation,
BSS, import termination, metadata budget, unwind lookup, source-derived CALL
checks, changed-file refusal, optional disassembly and raw-output confinement.
No retail executable, server process, acquisition or lease was used for them.
Review correction: the initial inspector checked increasing starts but could
silently select one overlapping function range. That approach is superseded by
the explicit overlap rejection and synthetic overlap/adjacency regressions.
Local result: 20/20 tests pass with the existing Capstone; `python -B -S` also
passes (19 executed, one optional decoder test skipped). This is a portable
dependency check on this workstation, not a claim that hosted CI executed.
