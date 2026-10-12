# First real T7 catalogue: preparation only

2026-10-12. This is a reviewable stock/command/resource proposal, not an executable
plan or a launch authorization. The coordinator owns the native slot; the T7
worker owns the D2 candidate/source, and the engine worker owns the PE/address
review. No native process, game link, asset copy or new supervisor was created
for this preparation. Acquisition evidence is in
[bo3-executable-observation-20261012.json](bo3-executable-observation-20261012.json).

The next experiment is now the separate [pre-patch witness](PREPATCH-ENVIRONMENT.md),
which stops before ZoneTool initialization and requests no zone. This catalogue
proposal remains deferred; its stock closure is not a prerequisite for that
earlier diagnostic stage.

## Working directory and fixed request

Use a new ordinary directory `runtime/t7-catalog-a/work` in the conversion
worktree. Resolve every ancestor and refuse reparse points. Keep `work/zone`
an ordinary directory; do not junction the complete owner zone tree or expose
XPAKs through either `zone` or the helper's second search root `../zone`.
The exact absolute machine paths belong only in the private local plan.

Once D2 is qualified, stage its one EXE as `t7-zonetool-candidate.exe`. The native
command has exactly these two arguments:

```text
t7-zonetool-candidate.exe -t7-iw7-catalog mp_freerun_04
```

Do not append engine/dvar arguments: the reviewed CLI requires argc=3. Its
expected create-only output is
`t7_iw7_catalog_1d7749fdf2454720fad852816e9ddde027a157a4cc486aa18b3eb8fd4a25c2ce/catalog.json`
under that working directory. `zonetool_paths` and competing H1/H2/S1/IW6/IW7
engine filenames must be absent. No real model name has yet been established.

## Known inputs versus unresolved stock

| Input | Observed identity | Preparation decision |
| --- | --- | --- |
| D2 ZoneTool | Final candidate receipt/hash still pending | Bind only its successful exact build result; no fallback to E7 or failed C |
| Dedicated engine | 21,737,352 bytes; SHA256 `3df511d71e3690b14517379783bbfb713f6fe2ed2f2e73b445b4878216686156` | Reuse the durable read-only acquisition under its exact engine filename |
| `steam_api64.dll` | Existing owner file, 235,600 bytes; SHA256 `71af8666392acad2080a816b9f1196fe9ccb950e1db8a549f8312c4d231f55a8`; depot SHA1 matches | Reuse in place; engine worker reports it is the only non-Windows static import |
| Requested `mp_freerun_04.ff` | Existing owner file, 16,977,344 bytes, no reparse flag | Proposed smallest map in the bounded inventory; no payload hash/read in this preparation |
| Companion `mp_freerun_04.fd` | Existing owner file, 1,650,439 bytes, no reparse flag | Presence alone does not establish that the engine requires it |
| Bootstrap FF/FD files | Exact required set not yet established | Resolve before a complete catalogue plan; do not infer requirements from filenames |

The map is absent from the retrieved dedicated-server manifest 545991. Its
compatibility with that engine remains unknown. `core_gfx.ff` is smaller
(6,105,536 bytes) and present in both metadata inventories, but it may already
be loaded before the request. The CLI deliberately refuses an already loaded
zone. Neither candidate's model inventory/residency is known from metadata.

At source `fab9358`, `component/t7/zonetool.cpp` invokes original engine init
`0x140504170` before `zonetool::t7::start()` / `handle_params`. The C++ wrapper
does not disclose all earlier engine file reads. `main.cpp` reads the engine
name from cwd; `loader::load_library` maps it and resolves its actual imports.
An EXE, one Steam DLL and the chosen map therefore form a known starting set,
not a proven complete startup closure. BATs, playlists and additional Steam
DLLs are not justified by this source/static-import evidence.

After the address and stock gates are resolved, use a few explicit same-volume
hardlinks with source/destination file-ID receipts where path-local names are
necessary. Hold original input handles with read sharing only for the whole
attempt. Never change attributes/ACLs through a stock hardlink, overwrite an
existing destination, or expose an entire source directory. Bind/hash only the
selected inputs during the admitted stage, and repeat identity checks after
closure. Engine reads outside the allowed set are not proven confined by this
filesystem layout or by the ZoneTool XPAK-helper denial.

## Proposed admission, output and closure

Reuse the existing witnessed NativeJob DLL and scheduler/original-handle
helpers, with one small T7 profile. Do not reuse AppInfo's fixed command as an
arbitrary-process launcher or invoke an H1 compiler/fixture stage. Default
preparation must start no provider, lease or process.

- One Extract lease: 6 GiB physical / 8 GiB commit, BelowNormal. These are the
  existing conservative extraction estimates, not measured T7 maxima.
- One 200-second total clock including guards, launch, observation and final
  acceptance; root execution at most 120 seconds, and existing 5-second failure
  closure. Finalization cannot turn a late/forced result into success.
- Stop on `stop.request`, invalid telemetry, committed memory above 85%, output
  overflow, changed input identity, native failure or deadline. Stop only the
  retained original job; uncertain closure retains/quarantines its live host,
  handles and lease. Never stop the owner's client or Main.
- Catalogue maximum 512 KiB, at most 1,024 names and 256 KiB name storage, matching
  the CLI. Outer stdout/stderr at most 1 MiB each; proposed aggregate mutable
  output 64 MiB and 128 entries, reserving 64 KiB for receipt. Sampled caps are not
  OS quotas. Immutable bound input aliases are accounted separately.
- Accept only root exit0 plus a fresh original ActiveProcesses0 observation,
  normal closure, valid complete catalogue and successful lease release. A
  forced stop, missing dependency or empty/no-eligible catalogue is retained as
  failure or insufficient discovery, never a fabricated donor.

Before launch, preserve the existing Main PID/creation/image/UDP27016 identity
and refuse any ownership conflict. This command is a short engine extraction
process, with no player connection or server configuration change. Existing
fixed-address patches suppress server-thread/online startup only if compatible;
their safety cannot be assumed while the engine review is unresolved.

After confirmed closure, retain raw logs/receipts privately. Remove only the
exact aliases created by the preparation, after file-ID and resolved-parent
checks; retain originals, candidate/debug evidence and output. No recursive
stock cleanup. Because owner files/profiles/configs were not edited, restoration
consists of removing those aliases and verifying original identities; unexpected
external writes require diagnosis before declaring restoration complete.

## Gates still open

The engine review reports conflicts in the static PE windows; unpacked bytes
versus incompatible layout remains under investigation. A separate explicit
coordinator GO is required after that decision, the successful D2 identity,
the exact startup stock list and the reused supervision profile are reviewable.
Do not create links, execute the candidate, add DLLs speculatively or weaken
address checks while these gates remain open. A real catalogue would prove only
names observed during the requested load, not source-zone ownership, geometry,
conversion, materials, an IW7 build or rendering.
