# T7 / Black Ops 3 to IW7: retained source audit

2026-10-12. Source-only inventory of the existing ZoneTool commit
`fab935826c898806855376662a8a03317b3ad8f1`. No upstream update, new tool installation,
retail enumeration, FF/XPAK read, native launch or extraction occurred. The BO3
download directory remains untouched. Historical H1 fixture success is reusable
supervision evidence, not T7 conversion or runtime evidence.

## Existing route

The retained tree already contains `src/zonetool/zonetool/t7` and a direct
`converter/iw7` implementation. README lists T7 dumping and marks T7-to-IW7
experimental. The actual dispatch in `t7/zonetool.cpp:156` is narrower:

| T7 input | Existing converter | IW7 serialized output | Evidence boundary |
| --- | --- | --- | --- |
| `XMODEL` | `converter/iw7/assets/xmodel.cpp` | `xmodel/<name>.xmb` | Model metadata, bones, LOD and dependency names; not dependency payload closure |
| `XMODELMESH` | `converter/iw7/assets/xmodel_mesh.cpp` | `xsurface/<name>.xsb` | Geometry, packed vertices, skin weights and rigid lists; may need streamed XPAK data |
| `XANIMPARTS` | `converter/iw7/assets/xanim.cpp` | `xanim/<name>.xab` | Animation arrays, half-float rotation conversion and notifies; no T7 runtime proof |

The converters call the existing IW7 dumpers. These `.xmb/.xsb/.xab` files use
ZoneTool's IW7 structure/dumper format; they are not generic DCC interchange
formats and are not a built fastfile. The corresponding IW7 parsers exist in
`iw7/assets/xmodel.cpp:32`, `xsurface.cpp:52` and `xanim.cpp:30`.

Only these three conversion dispatches are active. There is no Material, Image,
PhysicsAsset, sound, map or ScriptFile conversion registered in this T7-to-IW7
dispatch. In particular, `xmodel::dump` writes material references with
`dump_asset`; `utils/io/assetmanager.hpp:239` writes the referenced name, not its
payload. The IW7 model dependency loader subsequently requires the named
materials, model surfaces and any physics assets. A converted model file alone
cannot establish a textured or self-contained port.

## Engine and command boundary

`main.cpp:19,35-74` expects **`BlackOps3_UnrankedDedicatedServer.exe`** and loads
that engine. The T7 components use fixed engine addresses. Merely having
`BlackOps3.exe` or an unfinished BO3 download does not qualify this route. No
claim is made about which executable the owner's download contains, its version
or compatibility; inspecting that installation is deferred.

The console command at `t7/zonetool.cpp:608` accepts a target such as IW7 and an
optional comma-separated type filter. Its target dispatch can reach the three
converters. This is not the same as an automated process command:

- `handle_params` at line 738 sends `-dumpzone <zone>` to `game::t7`, without an
  IW7 target argument.
- `dumpasset` at line 661 also fixes `globals.target_game = game::t7`.
- `dump_asset_t7` at line 199 has its only shown asset dump commented out.

Therefore neither existing short command is a qualified single-asset T7-to-IW7
export command. A successful exit or a printed dump message would not prove
converted bytes. The future adapter needs an explicit IW7 target, exact asset
name/LOD selection, expected output list, successful parse/readback and refusal
of unsupported dependencies. The current console type filter alone can include
every matching model in a zone; it is not a single-asset bound.

## Streamed geometry and conversion gaps

`xmodel_mesh.cpp:80-98` uses resident data when available, otherwise the embedded
XPAK reader receives an entry key and expected byte count. That reader builds
its cache by enumerating `.xpak` files in **both `../zone/` and `zone/`**
(`common/xpak.cpp:320-340`). This is a nonrecursive directory traversal, but it
does not impose a reviewed file allowlist, total index budget or stock guard.
It reads package hash entries and decodes raw/LZ4 blocks; finding a key is not a
proof of an allowed donor package. Do not run it against the downloading tree.

The source contains material conversion limits that require fixtures and
fail-closed checks before retail use:

- Models assert fewer than 256 ordinary bones; cosmetic-bone support is marked
  untested. They truncate LOD count to six and derive LOD distance from a source
  triangle-area heuristic. Material count is cast to `unsigned char`.
- A model with collision maps creates a PhysicsAsset name placeholder, not
  converted physics bytes. Some contents/surface flags are copied with pending
  conversion comments.
- Mesh conversion reads offsets and weights from a shared data block. The XPAK
  size equality is an `assert`; bounds, counts, indices and compressed-block
  ranges need explicit runtime validation, not release-disabled assertions.
- Animation conversion narrows several counts to 16 bits and relies on
  assertions for 8-bit bone categories. Rotation-stream sizes/consumption,
  notifications and delta arrays need independent fixtures and complete-read
  checks. Its Greyhound translator credit is source provenance, not an installed
  extractor or a tested cross-tool pipeline.

These are source observations and review targets, not reports of a reproduced
retail failure. No T7 format is accepted merely because structures compile.

## Smallest next preparation

Preserve the direct T7-to-IW7 route as the first candidate. Prepare synthetic,
bounded fixtures for model/mesh conversion and serialized IW7 readback before
considering stock. Reuse the existing retained-job supervisor through a small
Recipient/T7 profile; do not create another process ownership framework.

A later stock Plan must establish the exact dedicated engine build, fixed
donor files/XPAKs and their permitted lookup roots, one selected model/LOD,
dependency names, explicit material/physics treatment and byte/output/resource
bounds. A rigid prop with a small bone/material count is the simplest first
shape to validate; no donor name is selected or claimed present yet. Animation
and faithful material/texture transfer remain separate gates. The IW7 SDK
runtime demonstration and Sound work retain priority.

The source hashes and read scope are recorded in `source-inventory.json`.
The initial inventory claimed no patch or native result. The next preparation
below adds a review-only patch; no stock seal, FF build, rendered-model result
or owner gameplay acceptance is claimed.

## Proposed boot contract

`boot_contract.py` validates an option implemented only in the prepared patch:
`-t7-iw7-model <zone> <exact-model-name> <lod>`. The target is fixed to IW7.
The first profile permits one exact model, one explicit LOD 0..5 and resident
rigid geometry only. Asset names retain case, both slash spellings, internal
spaces and legitimate dots, up to 255 ASCII bytes. The shared rule rejects
absolute paths, traversal, ADS, unsafe Windows device aliases (including
extensions), empty components and trailing dots/spaces. The export route also
rejects a leading comma, the engine's referenced-asset marker. Zone names remain
flat tokens of at most 64 bytes. No input name is sanitized or renamed.

Boot mode is selected from executable presence. `main.cpp:512-541` checks H1,
H2, S1, IW6 and IW7 before T7. A future isolated T7 run must reject competing
engine executables and bind the exact unranked engine binary/build. The
T7 `wait_for_database` and `dump_zone` loops currently have no internal deadline;
the reused original-job supervisor must impose the admitted wall-clock deadline
from launch, including engine initialization and database waits.

The first profile allows **zero XPAK payload files**. Reject any streamed/shared
mesh before calling the old converter, so the global XPAK cache is never reached.
This still requires an admitted, sealed engine/zone stock profile later; it
does not eliminate the engine's own FF/dependency reads. Future streamed support
needs an exact package/entry allowlist and bounded header/index/compressed/output
validation; narrowing the current working directory alone is insufficient
because the existing helper also scans its parent `zone` directory.

The conversion owner supplies the nonmutating one-LOD selection/preflight
adapter. Boot/CLI integration must use it before the two existing dump calls,
and keep automatic dump/CSV/reference expansion disabled during the donor load.
The private output-root key is separate from the engine's exact asset name;
model/mesh names and dependency references must stay mutually consistent.
`filesystem::set_fastfile` also reads `zonetool_paths`, so the future private
profile must prohibit or explicitly bind that input and check every output
ancestor for reparse points. Existing serializers open files with `wb`; an
absent private output root and an exact expected output list are mandatory.

The six pure boot tests use invented names and exercise target/argument,
path and scalar refusals. They do not qualify the command in a native binary.

## Prepared CLI patch, still uncompiled

`prepare_cli.py` binds four original files to the source inventory and prepares
`zonetool-fab9358-t7-resident-cli.patch`. It never applies the patch. Three
translation units change: main, T7 ZoneTool and the existing T7 XPAK helper;
the fourth file adds the helper's declaration. No process supervisor is added.
The external `t7_iw7_resident_model.hpp` and `t7_asset_name.hpp` are owned by the
conversion chat and must be pinned and copied together into the private
prepared-source include path before a future build. `cli-source-contract.json`
records both source dependencies.

The patch rejects a missing T7 engine before the old missing-engine dialog and
rejects competing engine mode before `main_internal`. Its exact four-argument
branch cannot fall through to the legacy `-dumpzone` route. It rejects non-ASCII
original UTF-16 arguments before consuming the narrowed values returned by the
old argument helper.

Before loading the requested zone, the branch disables automatic dumping,
CSV/reference expansion and permanently denies reads through the existing
XPAK helper for this process. The atomic denial is checked before package-cache
enumeration. Engine FF/dependency I/O remains outside that helper and still
requires a separately admitted stock Plan. After a synchronous load/database
wait, the branch requires an exact nondefault model and calls the nonmutating
resident selection adapter. It dumps only that model view and selected mesh.

The private output-root key is SHA256 of the exact requested zone, model and
LOD separated by LF, prefixed `t7_iw7_`. Model/mesh content names remain unchanged
and their validated relative paths stay under that absent root. The expected
output list is exactly one `.xmb` and one `.xsb`; per-file reads are bounded to
1 MiB and 16 MiB, with a 32 MiB observed aggregate stop. A maximum 4 KiB manifest
uses the retained exclusive-create/readback writer. The external supervisor
must count all process output, logs and temp files and impose the launch-to-exit
deadline; this patch is not a complete executable stock or resource Plan.

The manifest's XPAK claim is specifically the ZoneTool helper denial; engine
I/O remains unverified. It includes exact dependency names and byte digests. It keeps
dependency-payload, complete serialized parse, runtime and readiness claims
false. It also keeps **asset-zone ownership false**: loading a requested zone
and finding a model in the resulting database does not prove which loaded
dependency zone supplied that model. `requested_zone` is deliberately not
called a verified source zone. `export_contract.py` checks receipt structure
against the request; it does not independently verify those file bytes or job
closure.

Validation after the corrections below: 19 pure/source tests, exact preparer check and read-only
`git apply --check` pass. The first patch-generation attempt was rejected by
Git because upstream `xpak.hpp` has no final newline; the preparer now emits
the proper unified-diff no-newline marker and preserves those original bytes.
No patch was applied to the shared checkout and no native code was compiled.

Coordination update: the owner confirmed BO3 download completion; the
conversion chat owns the bounded metadata inventory and dedicated-engine
acquisition plan. This chat did not rescan that installation. Its source CLI
preparation does not imply that the required dedicated engine is present.

## Shared name-validation correction

The independent review of the conversion adapter found that ASCII validation
alone could admit traversal names when the public selector was used without
this CLI's path guard. Commit `4de21ed` preserved the initial CLI checkpoint;
the correction now delegates native asset-name checks to the selector's public
`resident_iw7::asset_name` and shared `checked_asset_name` helper. It validates
both source model and selected mesh inside the selector as well as at export.
The Python receipt/request policy matches that rule and preserves the exact
engine name; only receipt **relative-path separators** use forward slash to
match C++ `generic_string`. A backslash spelling is not silently renamed.

The conversion owner supplies this boundary fix in
`cf1949658fa374bcd14db79865247243fca7c34c`, plus 51 C++ cases on the actual helper.
Those 51 cases remain source-only and unexecuted. They require the next admitted
native qualification along with the three minimal T7 translation units; no
stock export is authorized by their presence.

## SDK observation fields

The existing asset manifest additionally carries `root_bone_name` resolved from
the selected T7 root bone's real script-string ID and `selected_counts`
(`bones`, `roots`, `surfaces`, `vertices`, `triangles`). These values are captured
from the selected model/mesh in the same stable database scope before dumping;
no root tag or cube counts are fabricated. Bone names are observations, not
filesystem paths, and retain their bounded printable ASCII spelling.

The SDK will compare these observations with the fully parsed, independently
read dump after Run closure. The external Run receipt owns request/manifest
hashes, engine and ZoneTool identities/hashes, source/header/patch pins, selected
stock, job closure and restoration. Those fields are not duplicated in this
asset manifest. Material references remain unresolved and requested-zone
ownership remains unverified. The CLI does not export or modify the SDK's
SelfContained GSC.

## Bounded donor catalogue (source only)

The retained console `dumpcsv <zone>` writes all asset types without a byte or
count bound. The retained CLI has no `-dumpcsv` route; `-loadzone` only loads.
Neither is the reviewed discovery path. The separate `-t7-iw7-catalog <zone>`
route shares the exact dedicated boot checks, ASCII arguments, flat zone rule,
irreversible XPAK-helper denial and fresh synchronous load/database wait with
the model exporter. Existing command behavior is retained.

The existing DB-add hook copies distinct printable ASCII XMODEL names only
while this request is active. It retains no engine pointers, catches errors
before returning to the engine, and bounds captured names to 1,024 and name
storage (including terminators) to 256 KiB. Failure or overflow stops capture
and refuses publication after the load; it never publishes a truncated success.
Sorted names are resolved again in the stable database. Only the model-header
bone/root/cosmetic-bone/LOD counts are read. Surface counts are deliberately
absent because they require reading a mesh header; no mesh or bone arrays,
geometry, converters or package payloads are accessed by the catalogue code.
Referenced aliases and unresolved/default names keep null counts.

One create-only `t7_iw7_catalog_<zone-sha256>/catalog.json` is limited to 512 KiB
before the output directory is created, using the retained exclusive writer.
Provenance says only `observed_during_requested_zone_load`: it does not establish
zone ownership or completeness of the zone's asset inventory. Engine IO remains
unverified, as do geometry and runtime acceptance. The Python contract checks
invented receipts; no real donor name has been established and no native run or
stock read occurred. All 27 source tests and the four-file patch apply check pass.
This addition still changes only the same three translation units plus xpak.hpp;
the prior export-only plan/pins remain historical evidence and must not be reused
as the catalogue build identity.
