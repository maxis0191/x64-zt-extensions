# Recipient I: requested match count and script naming

2026-10-12, source and retained small logs only. No further native run, retail
content read, compilation or dump followed I. E7 and its shared source checkout
remain unchanged. The original [I proof](native-validation-i-2026-10-12.json)
and local observations stay immutable; this note corrects the meaning of its
`index_available: 0` field and earlier "empty index" wording.

## What zero actually measures

In retained native `zonetool.cpp:1942-1958`,
`index_enemy_scriptfiles_by_content_name(requested_names)` enumerates effective
`ASSET_TYPE_SCRIPTFILE` entries with `includeOverride=false`. The callback:

1. Skips null ScriptFile pointers and null names.
2. Copies `script->name` to a string.
3. Returns unless that exact string occurs in `requested_names`.
4. Inserts only matching names, refusing distinct pointers with the same match.

Line 2107 prints the resulting map size as `available`. I requested one module,
so `available=0` means **no exact requested utility name match was retained**.
The callback total, skipped headers, other names and numeric names were never
recorded. The same log can result from an empty database, a populated database
with different names, or other enumeration/loading problems. It cannot choose
between them, and it cannot establish absence of utility from the game.

This semantic correction does not change the actual failure: the exact request
was not exported, manifest status is `missing_asset`, no script file exists,
native exit is `0xE06D7363`, both original jobs closed, and restoration passed.

## Exact request, type and timing

The SDK request is 23 bytes: `scripts/engine/utility` followed by LF, SHA256
`a50b245fff515068331a50818435914a0cb81adcbc74de218753b4218d89d52d`.
`Recipient.Core.ps1:150-154` accepts that exact value (normalizing CRLF for the
comparison), and stages it unchanged. `recipient_contract.py:11` has the same
module. The Python phase passes the request filename to the fixed native CLI;
it does not translate names, add an extension or substitute another list.

Native `dump_enemy_scripts:2063-2089` accepts an optional UTF-8 BOM, trims line
whitespace/CR, rejects duplicate/unsafe names and stores that unchanged module
in both `script_names` and `unique_names`. `unique_names` is the sole producer
of the index filter for this call. It performs no token lookup, slash/case
conversion, suffix stripping or path alias matching. Numeric requests are
accepted by native validation, but the outer recipient contract deliberately
requires utility's canonical text name; changing it to `2626` is not an approved
retry and would also change serializer name/path/size expectations.

`structs.hpp` assigns `ASSET_TYPE_SCRIPTFILE=49`. Its `ScriptFile` begins with
`const char* name`, followed by three int lengths and buffer/bytecode pointers.
The enum wrapper calls `DB_EnumXAssets_Internal` with the requested type and
override flag. This source definition is not independent validation of the
engine address/signature or of a particular live header.

| Point | References | Script export |
| --- | --- | --- |
| Initial mode | dump/csv/verify false, filter clear, target IW7 | Same; also sets the output pack's fastfile path |
| Source load | `load_enemy_source_zones("cp_zmb")` | Same helper and donor |
| Load helper | Explicit 25 available zones; each `load_zone(..., DB_LOAD_SYNC)` | Same |
| Per-zone wait | `wait_for_database()` before lookup/load; already-loaded zones return | Same |
| Lookup after helper returns | Direct database entry lookup for each reference, type and default checks | Enumerate ScriptFile entries once, then exact requested-name filter |
| Output/dump state | Write reference CSV | Enable dump only after the index is constructed, serialize matches |
| Failure handling | CLI has a local catch and explicit failure exit | Missing result throws after manifest, reaching headless C++ exception handling |

Both I logs contain the same 25 ordered zone markers (20 loading, five already
loaded) through `patch_cp_zmb`. The helper does not unload zones before indexing.
`DB_LOAD_SYNC` is supplied to the engine; there is no extra wait immediately after
the final load. A timing problem is not proved by source or these logs, so adding
sleep or an arbitrary second load would be speculative.

The common DB-add hook (`zonetool.cpp:591-603`) invokes `dump_asset` and forwards
to the original registration function. The inspected no-renderer startup and
fastfile hooks apply to both CLI routes. No script-specific suppression was
identified in those inspected sources. They are still an offline tool startup,
not a normal playable-server script-VM witness; unnamed engine patches and the
enum implementation are not thereby qualified. The output fastfile setting is
used by dump paths and the stop-dumping hook; no proof currently attributes the
missing name to it.

## Naming evidence already retained

The linked gsc-tool source maps `scripts/engine/utility` to token **0x0A42 = 2626**
at `src/gsc/engine/iw7_token.cpp:2639`. Its CLI resolves numeric filenames through
`token_name` at `src/tool/main.cpp:436-445`; dependency input resolution uses
`token_id` and a decimal `.gscbin` filename at lines 500-516. Thus numeric script
names are an existing tool convention, while this particular exporter requires
an exact literal `ScriptFile::name` match and never invokes that mapping.

This makes a numeric live name a concrete hypothesis, not a measured root cause.
No I artifact records `ScriptFile::name`, the engine database name or a lookup of
`2626`. Even finding the token in a source dictionary does not bind current retail
bytes to it. Do not rename a dump header to the module merely to satisfy the
existing verifier: that would destroy the exact loaded-representation claim.

Targeted retained decompiled sources also establish the historical logical name:

- `scripts/engine/utility.gsc` defines `flag_exist` and `flag` at lines 532/540.
- `scripts/cp/maps/cp_zmb/cp_zmb.gsc` calls utility at lines 93/94/133, among others.

These are the already retained `mjkzy/iw7-gsc-dump` reference at
`1dd48a78e55ef9c99519fc5221a206168ce2e98a`, not fresh loaded ScriptFile evidence.
Only those two known files were inspected; no retail scan or bulk GSC traversal
was performed.

## Smallest proposed next witness, not yet prepared or authorized

The root cause is not demonstrated enough to change name semantics or stock.
Prefer one bounded **name/metadata observation** in a separate reviewed candidate:

- Count enum callbacks before filtering, null headers/names, numeric names and
  exact requested matches separately. Preserve the original match/export logic.
- For only the two fixed relevant identifiers (`scripts/engine/utility`, `2626`),
  observe direct-entry type, database/content names, default status and three
  declared lengths; report which observations were unavailable. Preserve both
  exact raw name strings. Do not read compressed/bytecode payloads or hash them.
- Record one bounded summary, at most 4 KiB, without arbitrary name samples or
  pointer addresses. Cap enum callbacks at 4096 and individual names at 240 bytes
  plus one termination sentinel, refusing overflow instead of silently truncating.
  These proposed caps require review against the actual future implementation.
- A pure synthetic test should cover populated-but-unmatched enum, numeric and
  canonical matches, null entries, duplicate pointers versus ambiguous pointers,
  caps, and the absence of any payload access. A test that only checks log wording
  would not establish correct classification.

This is a proposal, not a new Plan/GO or a claim the instrumentation exists.
Building another candidate would require separate source review, exact provenance
and admitted build/execution. Preserve E7. The existing script-catalog command is
unsuitable for this question: it constructs and hashes every enumerated script's
compressed buffer and bytecode, up to 4096 entries. Do not run it as a name-only
shortcut. No extra image PAK, bulk dump, gameplay launch or utility dependency for
SelfContained is implied.

## Source provenance

Native source pin remains `fab935826c898806855376662a8a03317b3ad8f1`, with clean
tracked status during this inspection. Hashes were computed from source text,
not game binaries or payloads:

| Source | SHA256 |
| --- | --- |
| `src/zonetool/zonetool/iw7/zonetool.cpp` | `f1c9fb861b81727dc7e3882f5116231e6dc0d1a0e6f5838953a62232171059bc` |
| `src/zonetool/component/iw7/zonetool.cpp` | `be37e50690c515fc116f0c6092f8dd361b973aa73f9b56faf32ee457f3c90ed4` |
| `src/zonetool/component/iw7/fastfiles.cpp` | `4150edb3af3c94f74e0c6ce55f3b95da41287266b3b6603b7e1052f1e3e2c461` |
| `src/zonetool/component/exception.cpp` | `c0bccf3a82afa86c33626ebd3861b51919f4fa84fc7526b9877899b10bfbb502` |

gsc-tool submodule pin is `3300e430d1efef00e54c66a8bd416e18a2a9882a`.
`src/gsc/engine/iw7_token.cpp` SHA256 is
`3f6a339f7f54d553f7cf6ba6da064bdf8edb0127fa44779db646ed7cab1c855c`;
`src/tool/main.cpp` SHA256 is
`5487544d9e56b11842496b19ac23b74abb74be4fa0f32a1ba1cf35a185529897`.
Retained decompiled utility is 94,770 bytes, SHA256
`007f026cb956a4c256977d60c2691cc554e0cc78a13dfd1694469acf707bbdf7`;
the targeted cp_zmb entry is 104,125 bytes, SHA256
`9600c4160c272a3b8768c4b9fe9ba27019ba677080e1deace4e69ca2371132b5`.

Next action belongs to the coordinator: review the corrected interpretation and
choose whether to prepare the bounded name witness. The original utility route
remains unqualified; SelfContained composition continues independently.
