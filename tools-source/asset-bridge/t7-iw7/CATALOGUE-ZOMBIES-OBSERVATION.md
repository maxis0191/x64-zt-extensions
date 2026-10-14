# Zombies catalogue C: identify the first failed lookup

## Actual C native build, 2026-10-14

The separately authorized build used the frozen merged source
`fa45c395597697843053ffc23195320dca6ae73d` and exact plan SHA256
`627f3aacf6ef892af2a7bc94c00ad0f40e811649bbdf2aa49aecad6569930a15`.
Fresh main and zonetool11 compilation, then linking, all returned 0. The build
receipt reports Passed, 25,920.0061 ms, input reverification and completion at
2026-10-14 00:03:10.848 UTC. The candidate was not executed.

| Artifact | Bytes | SHA256 captured during the original lease |
| --- | ---: | --- |
| zonetool-t7.exe | 21,925,376 | `88f2147de79e696d3342f4e838cf5b7b8b25da29cddea41def9395b6933342c8` |
| zonetool-t7.pdb | 138,514,432 | `03d23285b0b478c6190c967d59c805d366961c3957861ac2e501b04d769839e6` |

The three original compiler/link jobs each captured the owned VCTIP member
twice, then verified zero active processes and an empty original job after
guarded closure. TreeClosureConfirmed and LeaseReleased are true; quarantine
is false. The original host returned 0, with its context closed and zero input
guards. Fresh metadata confirmed all seven original identities absent and an
empty resource registry. No opaque artifact was read or hashed after release.

The bounded actual build receipt is 25,317 bytes / SHA256
`5f817f2f3f24c04868d022b41a3b68da492b75818816c37bb99eb1f6c8805051`.
Private local evidence retains the original entry/completion and a six-pin
closure bundle linking the actual tool return, inventory, build completion and
receipt. Symbols, objects, logs and the original candidate remain preserved.
This establishes native compilation and lifecycle closure, not execution of
the observer or a successful Zombies catalogue. Catalogue B remains
Failed/NoCatalogue with an unresolved RawFile cause; a new stock invocation
requires separate qualification and coordinator authorization. The earlier
source-only checkpoints below remain historical evidence.

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

## Explicit C compilation plan, 2026-10-14

The build producer now accepts `--zombies-catalogue-observation` only together
with `--catalog-message-publication`, `--selected-streamed-static-v1` and both
retained compilation proofs. It first validates the unchanged current E4 reuse
closure, then applies one exact additional CLI transition. Existing legacy
transition rows stay unchanged. The separate six-field
`ReuseCompile.ZombiesObservationC` records schema, source profile, base CLI
length/hash and final CLI length/hash. There is no arbitrary changed-TU allowance.

`BuildProfile.Name` is `t7-zombies-catalogue-observation-c`. It retains every F
publication field and adds only `ObservationSchema`, `ObserverSource` and
`ObserverAdapter`. The two source pins are the approved Source25 module/adapter;
no new contract file is required. C has exactly 151 bindings (145 text, six
binary), 1,146 input pins and the same 66-header proof. F/E4 retain their existing
149-binding branch. C still compiles fresh main and zonetool11, then links; it
retains only the already qualified xpak dependencies.

The base published CLI is 107,785 bytes / SHA256
`c480fbd39525df09bd5677026678743c73fa66eb3ca0752e78729eee2f4dcc50`.
Its source-only C output is 118,485 bytes / SHA256
`917c2f9025185d23a8b2b683157144c2da62fe747f17f11e0f8c1abcf66be987`.
This tuple is a prepared source file, not a compiled executable.

The preliminary DEFAULT plan passes with no missing expected pins; native
types, binary hashing, leases and the future build root remain absent. Five
actual DEFAULT mutations refuse the missing marker, altered module, altered C
transition, renamed F profile and relabeled base CLI before a deliberately
missing binary path can be queried. Six new Python source tests and 485 combined
PowerShell profile/input checks pass. Existing Python preparation tests also
pass (32 executed, three optional retained-command tests skipped without E7).
Final committed-source preparation and exact-head CI are recorded in the PR.
This source validation does not grant a build or qualify a native C catalogue.
