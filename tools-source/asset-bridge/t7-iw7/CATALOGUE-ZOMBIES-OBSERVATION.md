# Zombies catalogue C: identify the first failed lookup

Catalogue B ended with **Failed / NoCatalogue**, although its native process
returned 0. It reported the exact RawFile
`ui/uieditor/widgets/attachmentnamesdisplay.lua` and an empty default asset.
The retained trace places the error/exit in one asynchronous engine thread;
it does not identify the original lookup, the supplying FF, session mode, or
whether the failure precedes the requested donor load. The 148,160-byte English
locale was qualified separately. These observations are recorded in
[the B checkpoint](../t7-bridge/CATALOGUE-PLAN.md#zombies-locale-qualification-and-catalogue-b-2026-10-13).

## Source basis and remaining uncertainty

The existing owner fork at `fab935826c898806855376662a8a03317b3ad8f1` declares:

| File | Source fact |
| --- | --- |
| src/zonetool/zonetool/t7/functions.hpp:14 | DB_FindXAssetHeader at 0x1401D5FB0 returns an eight-byte XAssetHeader and takes type, name, errorIfMissing, waitTime |
| src/zonetool/zonetool/t7/functions.hpp:16 | DB_LoadXAssets at 0x1401D8740 takes the zone array, count, sync, suppressSync |
| src/zonetool/zonetool/t7/structs.hpp | RawFile type 0x2F; XZoneInfo has five eight-byte fields |
| src/zonetool/zonetool/t7/zonetool.cpp:105 | The existing lookup wrapper passes 0 and -1 as its last two arguments |
| src/zonetool/zonetool/t7/zonetool.cpp:430 | The donor load passes one request, sync, and suppressSync=0; allocFlags=0x10000 |
| src/zonetool/component/t7/zonetool.cpp | initialize runs during post_unpack; the boot stub later invokes engine initialization before start/handle_params |

Those are pinned **source ABI declarations**, not proof of the B runtime caller
or of retail compatibility. No explicit session-mode selection was found in
the reviewed catalogue/load/component path; this does not prove which mode the
engine actually selected. No retail payload, Lua bundle, map, or executable was
read again during this source task. Do not infer a missing FF from a Lua name.

## Optional overlay

`prepare_catalog_zombies_observation.wire_cli(final_lf_tu)` renders this module
into a reviewed final zonetool.cpp. It refuses changed/missing/duplicate anchors
and an already instrumented input. It neither modifies native checkout files
nor builds/runs anything. Existing renderers, hashes, profiles and E3/F plans
remain unchanged. Bind the returned bytes, this adapter and its module in a
**new** source/build cohort. The overlay is not selected by existing builds.

At runtime its hooks install only for the exact three-argument command
`-t7-iw7-catalog zm_common`, after checking the pinned T7 module/base and both
executable mappings. Compile-time assertions check the declared signatures and
header widths. The two detours forward each original call once with all four
arguments unchanged and retain its return value. Observation reads/logging
restore Win32 last-error and CRT errno before/after the original call.

The lookup observer selects only RawFile type 0x2F and the exact failed name,
including its NUL terminator. It records caller, thread, errorIfMissing,
waitTime, last global phase and returned pointer without reading its payload
or asking the DB another question. A fatal call can have an entry and no return.
The DB-load observer retains at most four requests, two 40-byte zone headers
per request, and 64 bytes per name. It reports existing flags without changing
them or loading an extra zone. Wait polling and callback calls remain intact.

Phase values are: 0 installed, 1 start, 2 handle_params, 3 catalogue entry,
4 wait entry, 5 wait return, 6 DB-load entry, 7 DB-load return, 8 finish callback
entry, 9 finish callback return, 10 load_zone return, 11 report publication.
Phases 12 and 13 surround the existing donor DB_LoadXAssets call itself, even
if the four initial DB-load request records were already consumed during boot.
Each phase prints once. The phase is a last-observed global marker: concurrent
callbacks and printed sequence order do not establish a lookup's causal origin.

## Qualification and next authorized experiment

The module adds at most 8 KiB of stderr (7 KiB general plus 1 KiB reserved for
the exact lookup). Each line is below 512 bytes; event counters are finite.
`split_observation()` validates only the new finite marker and returns the
legacy stderr unchanged for its existing validator. Unknown/malformed new
records are refused. An observer record never makes exit 0 a catalogue success.

The launcher owner must select a distinct C profile and a combined trace cap
of 16 KiB before using the overlay. The old F parser/cap must not silently
accept the new format. Existing catalogue/host identities, scoped aliases,
input guards, deadlines, output guards, closure and resource leases still apply.

Source/parser tests can qualify wiring and refusal cases. They do not compile
these hooks or prove their engine execution. A separate coordinator GO remains
required for the combined native build and one protected catalogue invocation.
Inspect the exact RawFile entry alongside boot/catalogue/DB phases; preserve any
refusal and select a real Zombies weapon/enemy model only from an actual report.
No new retail stock, fabricated RawFile, default replacement, UI bypass, broad
map enumeration, Main deployment or gameplay acceptance is part of this overlay.

Local source validation, 2026-10-14: 15 tests pass with the retained owner
native checkout supplied, including both actual-source wiring tests. Removing
only the overlay recovers the exact input TU; changed/duplicate anchors and
double instrumentation are refused. Initial test fixtures incorrectly added a
comment after an intact anchor; those four expectations were corrected to
actually remove/duplicate the anchors. A source review also reserved the possible
Windows CRLF byte in the native logging budget. Native compilation and a real
C catalogue remain pending.
