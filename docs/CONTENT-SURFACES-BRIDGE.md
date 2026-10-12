# Content surfaces bridge — source checkpoints 2026-10-12

The dependency inspector, pinned ZoneTool reader patch and small beacon surface
were prepared at the first checkpoint. Native compilation, FF construction,
rendering, content-audio playback and client HKS execution were **not run by this
lot**. Later parent-owned full-tool and first-beacon evidence is distinguished in
the material-v2 section below. None establishes a qualified custom-material import.
The owner admin/lag investigations still gate heavy work; the parent coordinates
admission and integration. Main27016, the occupied client, banks, runtime installs
and shared source checkouts were not changed.

Implementation: `tools-source/asset-bridge/surfaces/`. Python3.12 standard library;
no dependency installation. All JSON schema names in this directory describe our
reports/preparation manifests, never undocumented IW7 asset formats.

## Source evidence and concrete formats

`source_contract.json` pins17 actual ZoneTool interface files at owner fork
`fab935826c898806855376662a8a03317b3ad8f1`, plus the client UI loader at
`77e6d4d24e918ee363b3feee3735c3b889dff7d7`. Exact file hashes are checked before
using source-dependent rules or generating a patch. A byte mismatch stops the
operation; an equivalent checkout with different line endings needs a reviewed
contract update. No upstream refresh was repeated.

Paths below are relative to `src/zonetool/zonetool/` unless noted otherwise.

| Content | Actual source contract | Remaining prerequisite |
| --- | --- | --- |
| New resident images | `iw7/assets/gfximage.cpp`, `directxtex::load_image/parse`: `images/<name>.dds` or `.tga`, DirectXTex metadata/pixels, `streamed=0`, pixelData serialized in FF. IWI is a separate fallback. PNG is not read here. | Decode/format/mip validation and real color/alpha/UV witness. Small TGA need not use an image PAK. DDS presence alone is insufficient. |
| Native/streamed images | `images/<name>.iw7Image` and `streamed_images/<name>.iw7Image`; native assetmanager serialization, descriptors and `streamed_images/<name>_streamN.pixels`. Four stream descriptors are read for streamed native dumps. | Use the exact pinned reader and capture at donor registration. Resolve actual stream payload/PAK ownership. Do not recover pixels from late/stale pointers or invent native offsets. |
| Materials | `iw7/assets/material.cpp`: `materials/<name>.json`; actual `techniqueSet->name`, textureTable image/semantic/sampler/hash/character fields, constantTable name/hash/literal, stateFlags and material/info fields. `*` is cleaned to `_` in material/image file paths. | Exact IW7 technique, material state, shader constant layout and image bindings. H1 JSON is not a portable complete material by itself. |
| Material sidecars | `iw7/assets/techset.cpp`: `techsets/state/<techset>/<material>.stateinfo/.statebits/.statebitsmap`; constantbuffer `.cbi/.cbt` when constants exist. stateinfo is needed when JSON stateFlags is absent. statebits/cbi have152 technique indices. statebitsmap is JSON; cbt is native assetmanager data. | Correct states/buffers for this material, with valid index/offset ranges. A similarly named sidecar does not prove compatibility. |
| Techniques/shaders | `techsets/<name>.techset`, `.technique` via native reader; vertex declarations, pass arguments and VS/HS/DS/PS dependencies. Shader files `techsets/<vs|hs|ds|ps|cs>/<name>.cso`. | Valid DXBC is only a container gate. Shader stage, vertex input, code constants, technique mask/index and active draw pass must agree. No general H1 shader ABI compatibility is established. |
| Content sounds | `iw7/assets/sound_bank.cpp`: `soundbank/<bank>.json`, aliases and other CSV/JSON paths. Alias CSV has53 positional columns retained exactly in the contract. `File` resolves under `sound_assets/<File>.flac` or `.wav`; SecondaryAliasName, StopAliasName and duck form extra dependencies. | The pinned SAB writer explicitly rejects WAV even though it finds its path. FLAC decode, alias hash index, localization, SABL/SABS delivery and real playback remain necessary. FF alias metadata alone is not audio delivery. |
| LUI/HKS | `shared/assets/luafile.hpp`: LuaFile source is read at its literal asset name, serialized as name/len/buffer; no compiler or automatic require dependency closure. Client `src/client/component/ui_scripting.cpp`: disk `ui_scripts/<module>/__init__.lua`, plus enumerated LuaFile zone entries with this shape. Disk module takes precedence. | Matching client native loader, actual IW7 HKS execution, require paths, LUI registration/materials/fonts, input focus and VM teardown. Foreign Lua bytecode is not accepted as an interchangeable compiler output. Dedicated skips this component. |

The H1 converter lives behind `EXPERIMENTAL_IW7`. Its material JSON route uses
an explicit techset mapping and declines an unknown mapping. Its other converter
route, shader constant mappings and copied image flags/semantics are not a proof
of universal conversion. `h1/converter/iw7/assets/{material,gfximage,techset}.cpp`
are pinned for this reason. PBR PNG roughness/metalness and packed normal channels
must be mapped to a measured target material; do not label a guessed mapping H1
support. No H1 soundbank or H1 UI compatibility follows from a model conversion.

## Reader correction: explicit strict content build

`strict-content-sources.patch` changes only IW7 material.cpp, techset.cpp and
gfximage.cpp under the existing command-line flag mechanism. The actual
`src/common/utils/flags.cpp` parses a leading single dash and `has_flag` compares
the resulting name. The caller must pass **`-strict-content-sources`** to the
patched ZoneTool process. This switch is not an IW7-Mod runtime option.

1. Parsed material image and techset names become name-only dependency nodes,
   resolved through the existing `material::load_depending` and
   `zone_interface::add_asset_of_type` path. The latter applies the existing
   ignore inventory as named recipient references. This extends the previously
   `paris_enemy_`-only behavior without requiring a community zone to use that name.
   It does not fabricate a successful DB resolution.
2. Missing/default donor materials and missing image sources fail the strict build.
   The existing exact cached placeholder witness (auto-generated RGBA8,1x1,
   four bytes255/0/0/255) now also rejects strict community builds in
   `gfx_image::parse`, before `init` can return the cached dump. Legitimate red
   custom TGAs are not broadly rejected.
3. `material_data::get_parse_path` returns the exact missing path in strict mode
   instead of choosing another material's sidecar. Required missing cbt fails;
   statebits and cbi must have exactly152 bytes before fread. The ordinary fallback
   and source precedence are retained when the switch is absent.
4. Strict constant names use bounded copying into the real12-byte field instead
   of strcat. The measured template contains the full-width name `reflectionRa`.
   Names longer than12 bytes fail; full-width names need no out-of-field terminator.
   The dump macro also constructs its string from exactly12 bytes, preserving its
   existing trailing-NUL JSON text behavior. This read bound applies to all dumps:
   a name12 followed by four floats1.1 contains no NUL and exposed the old overread.
   Source-selection/default fallback behavior without the flag stays unchanged.

The patch is deliberately opt-in: unconditional global DB/search-path changes lack
retail regression evidence. Missing source must be supplied or deliberately listed
as a recipient reference; do not enable a default asset to conceal it. This is a
source correction awaiting native build tests, not a delivered runtime fix.

Preparation writes a fresh separate folder and cannot overwrite the shared source.
It checks all pinned interfaces, uses exact replacement anchors, writes the three
candidate files, a diff and hashes. `verify_prepared` recomputes the candidates
from the pin; it does not trust the output manifest alone. Parent integration can
apply the patch to its isolated source alongside the separate H1 geometry patch.

```powershell
$surface = 'tools-source/asset-bridge/surfaces'
python -B "$surface/prepare_reader_patch.py" --zt-source <existing-pinned-x64-zt> --output <fresh-reader-output>
git -C <existing-pinned-x64-zt> apply --check <fresh-reader-output>/strict-content-sources.patch
```

The apply-check is read-only. Applying to an isolated candidate, native compilation
and running the new switch remain parent-gated. Do not patch the shared retained
fork or invoke a build as part of this preparation.

## Inspector and evidence semantics

`inspect_content.py` reads explicitly named staged materials/images/soundbanks/UI
modules/shaders, hashes each inspected file and emits dependency edges plus exact
errors/pending evidence. It does not scan the entire game. Inputs reject traversal,
absolute/Windows ambiguous paths and links/junctions. Per-file reads are at most
8MiB, total input reads32MiB, and file/asset/alias count limits are4096. JSON/CSV
sub-limits are smaller. These bounds deliberately refuse large production payloads
until a separately budgeted inspector is needed.

Missing exact sidecars, absent custom images, shadowed representations, bad
statebit indices, malformed alias columns, unresolved secondary/stop aliases,
missing samples, unsupported WAV and invalid/truncated container data fail.
Native binary image/cbt/technique layouts are marked uninspected. The DDS/DXBC/
FLAC checks are structural only; no decode/driver/playback claim is made. Lua is
never executed; dynamic requires remain unresolved instead of guessed with regex.

Recipient inventory rows are declarations, not engine proof. `--references` accepts
root-relative `type,name` CSV rows for material/image/techset. Real DB default checks
in the target map are still required. `--reader-patch` verifies a prepared patch
and marks its native build pending; it cannot turn source preparation into a built
tool. No output of this inspector ever sets `ready=true` or runtime_verified=true.
Exit0 means the requested bounded static checks passed;1 means invalid input;
2 means explicit unresolved evidence remains. Handle2 without calling it success.

```powershell
python -B "$surface/inspect_content.py" --zt-source <existing-pinned-x64-zt> `
  --root <staged-sources> --zone community_beacon_surface_a `
  --material community_beacon_material_a `
  --references zone_source/community_beacon_surface_a_recipient.csv `
  --reader-patch <fresh-reader-output>
```

## Small SDK beacon surface, second variant

`prepare_beacon.py` reuses the six exact small inputs from the retained original
Doom checker preparation. Their8079 bytes/hashes are pinned; their bytes are not
committed. It generates original asymmetric32x32 BGRA8 top-origin opaque pixels
(4114-byte TGA), a new material named `community_beacon_material_a`, exact renamed
sidecars and two zone CSVs. All nine source payloads total **12394 bytes**, excluding
the preparation manifest. This material reuses measured IW7 state; its artwork is
original, its technique and normal map are recipient references. No retail pixels,
model, shader, PAK or complete donor zone is copied into the candidate.

```powershell
python -B "$surface/prepare_beacon.py" --checker-root <retained-original-checker-a> --output <fresh-beacon-source>
```

The source zone is `community_beacon_surface_a`, with `ignore` rows for the
recipient techset `mopw_l_sm_replace_i0c0s0o0n0p0` and normal image
`park_clown_zombie_shoes_n_3e46d100_packed_nog`. The recipient is cp_zmb.
The SDK's existing first beacon variant keeps its measured model and retail
material gate. For **variant2**, the model owner must rewrite the real model's
material binding to `community_beacon_material_a`, independently reread that
binding, then merge the supplied ignore/material/image rows into the model zone.
Do not merely rename the JSON manifest or relax `ops/model-lab/prepare_ff.stage`.
Keep `iw7.community-mod/1`; `h1-rigid-import/1` and `resident-custom-material/1`
remain unqualified until their separate compile/FF/render criteria pass.

Current server UI in [UI.md](UI.md) is GSC retail text HudElem and can display
the authoritative beacon counter on existing clients. It is not a custom LUI
menu. A real LUI route is a later client HKS capability and needs separate
deployment/lifecycle/input testing. Content sound events likewise remain separate
from microphone transport/native voice; this work changes no Windows audio state.

## Distinct material-v2 source preparation

The parent subsequently supplied the full ZoneTool build receipt with executable
SHA-256 `e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04`
and receipt SHA-256 `f0d4d7db132d51c789a999e33ab0ce905b2df749db453029f91356b9aa2e2165`.
The receipt records413 translation units, the experimental macro, fresh PCH and
the exact strict-content patch `4d7049216f24474e077ab704dac625c7f335c8264434b7de525e56a96a988d08`.
This preparation hashes/reads only the2430B receipt. The future execution wrapper
must independently verify the existing executable; no executable/PDB/toolchain is
copied and no native tool is run here.

The parent's first `sdk_beacon` FF is1048B, SHA-256
`76ed0701dc1480c501604db04999f300394c65877aa24a70dfe7afc2cd662d4a`.
Its separately owned build/verify/dump/read evidence is recorded in
`sdk/modding/beacon-ff-validation-2026-10-12.json` when integrated by the parent.
The native PNG `vertical-after/pre-action.png` in run
`20261012-025611-746-c01d8ac6` was visually inspected: a dark cube is visible and
the HUD reads `BEACON | YOU: 1 | TEAM: 1`. The parent reports that this run used
reduced graphics, including changed normal/specular/picmip settings. Darkness
alone does not diagnose a broken material, incorrect normals or missing lighting.
The native model observer currently requires exact `fs_game=mods/paris_model_probe`;
it supplies no material DB snapshot for this SDK path. No missing snapshot is
reinterpreted as successful resolution.

`prepare_material_v2.py` prepares an independent candidate while retaining the
first beacon and the earlier `community_beacon_surface_a` preparation unchanged:

| Asset | Distinct identity |
| --- | --- |
| Zone | `sdk_beacon_material_v2` |
| Model / surface | `community_beacon_model_v2` / `community_beacon_model_v2_lod0` |
| Material / image | `community_beacon_material_v2` / `community_beacon_color_v2` |
| Netconststrings | `ncs_mdl_community_beacon_model_v2` |

The generator checks the exact four retained writer inputs and six measured
material inputs. It renames the eight model-name occurrences in the writer,
changes only the geometry header's material binding, and emits a distinct native
report schema/model identity. All serialization, reread assertions, packed
vertices, UVs, tangent/normal encoding, rigid weights and LOD values stay unchanged.
The original geometry JSON is retained byte-for-byte as `geometry.baseline.json`;
its original model name is provenance, not the new binding. No H1 donor is needed.

The original asymmetric32x32 opaque color image has red/green/blue/yellow corners,
a white top bar and a magenta left bar. The material preserves the exact measured
state/constants/sidecars. It still references the recipient's technique and packed
normal image. This is an original **color-image/material-binding witness**, not a
claim of wholly original shaders or a newly authored normal map. The packed-normal
channel mapping and actual selected draw pass remain unmeasured; RGB normal-map
guesses or an unmeasured unlit technique would add variables to this experiment.

```powershell
python -B "$surface/prepare_material_v2.py" `
  --writer-root <retained-model-lod1m-source> `
  --checker-root <retained-original-checker-a> `
  --builder-receipt <reviewed-full-tool-build-artifact.local.json> `
  --output <fresh-material-v2-source>
```

The output has14files/46262B including the plan. The generated writer is13948B,
SHA-256 `91f3d70ff1cd24467a806b2130671f31948accb52d9d1be823fc169f073d8781`;
the header is2264B, SHA-256
`a569018b4f33b51e72f372d582fa7064cd788afa264481342d348eeb44036e88`.
Static material inspection reports0errors/4pending/ready=false. It does not decode
native CBT or prove recipient resolution. The FF input directory intentionally
contains no XMB/XSB and must not be treated as a runnable build input. The plan's
source-hash inventory describes preparation, not native execution provenance.

The concrete next sequence is:

1. After parent GO/admission, compile the distinct writer using the ten exact
   interface hashes in the plan. Preserve compiler, source and executable hashes.
   Run its real native roundtrip on a fresh output and require
   `iw7.content-material-roundtrip/1`, the exact new model/material, all geometry
   assertions and only the two bounded expected XMB/XSB files.
2. Use the distinct execution/staging adapter below after parent review/GO. Recompute source
   bytes and bind native process success/report/artifact hashes before staging.
   Do not change the variant1 `Build-BeaconFF` or `ops/model-lab/prepare_ff.stage`
   acceptance rules and do not accept a JSON report alone as native execution.
3. Reuse the final E7C956 full tool with `-strict-content-sources` in the SDK's
   bounded child-job lifecycle. Enforce the eight-entry plan inventory: two comma
   recipient references plus custom image/material/model/surface/NCS/rawfile.
   Build, verify, dump, then independently run this variant's exact writer with
   `--verify-existing` against the fresh FF dump. Bound FF to1MiB and each model
   artifact to8192B; re-evaluate an overrun rather than silently raising a limit.
4. Independently inspect the dumped material and decode the resident image:
   image name,32x32 dimensions, actual RGBA pixels, color semantic14, normal
   semantic15, constants/state and reference resolution. Pointer presence and
   filenames do not prove image correctness. Native negative strict-reader cases
   below still need execution; the prior source tests are not that execution.
5. Scope the native diagnostic to the exact new package/model before using its
   output as evidence. Under the current privacy workflow, require a fresh random
   password, launch+config `sv_lanOnly`, loopback default, native master-heartbeat
   suppression and fresh privacy telemetry before any join. Establish fresh engine
   godmode/inactivity protection. Reserve full-quality base client12GiB plus
   dedicated2–4GiB (combined14–16GiB RAM/commit); compare the same poses and show
   checker colors/orientation/opacity. Retain cold join/rejoin and owner acceptance
   separately. Use the current privacy/instance helpers, not this preparation code.

The writer requires4GiB RAM/6GiB commit; the proven SDK FF wrapper reserves8GiB
RAM/11GiB commit. These are separate sequential jobs under the shared scheduler,
not permission for concurrent native work. This phase performs no native build,
Add-Type, FF creation, game launch, lease, audio operation or download. Source
output is capped at128KiB, within the parent's2MiB preparation budget.

The earlier source-only plan recorded an unqualified2/3GiB writer estimate. The
coordinator rejected it before any native execution. The current generator and
adapter enforce the RESOURCE-WORKFLOW4/6GiB native minimum; regenerate a fresh
preparation rather than modifying the retained old plan. Geometry/header bytes
and their hashes above are unchanged by this admission correction.

Python tests now total38 unique cases: the original29 plus9 new source-gate tests
covering byte-preserving renames, exact binding, absent/duplicate anchors, variant1
inventory exclusion, changed/missing pinned input, unknown builder receipt and
existing-output refusal. Actual retained-input preparation also passed. Rendering,
recipient closure and native v2 compilation remain pending.

### Executable adapter, pure-test checkpoint

`Build-MaterialV2.ps1` now implements the six native phases, but defaults to a
read-only execution plan. No native phase was run in this checkpoint. The adapter
accepts explicit retained source/stock/toolchain paths; machine paths are stored
only in ignored local parameter/plan files. It recomputes all14 prepared files
from the exact original inputs and verifies the pinned writer/material interfaces.
It rejects the old2/3GiB preparation plan, altered inputs and an existing run root.

The seven shared helpers are used directly from a reviewed `SharedRepo`, with
hashes in `material_v2_helpers.json`; none was modified or copied:

| Shared helper | Reused responsibility |
| --- | --- |
| `ops/Base-Client.Core.ps1` | Unredirected bounded paths and reversible file transaction |
| `ops/Resource-Scheduler.Core.ps1` | Exclusive admission, independent RAM/commit and process registration |
| `ops/model-lab/ModelFF.Core.ps1` | NTFS source/target identity, final stock checks and guarded restore/release |
| `ops/hud-lab/HudFileIdentity.cs` | Existing NTFS file identity implementation |
| `sdk/modding/BeaconFF.Core.ps1` | Exact full-tool qualification, hashes, original-handle identity and64MiB output accounting |
| `sdk/modding/beacon_tool_phase.py` | Existing bounded2MiB-per-stream log drain |
| `tools-source/asset-bridge/model/BuildJob.cs` | Suspended BelowNormal child creation, non-breakaway kill-on-close job, original handles |

The v2 driver owns orchestration and source-specific gates; it adds no scheduler,
stock clone, native job implementation or shared SDK framework. Changing a shared
helper hash requires review, not an automatic pin refresh. Its source is in the
post-PR147 tranche, independently of the first-beacon proof.

The writer lease uses4/6GiB. Compilation uses installed MSVC/Windows SDK, one fixed
translation unit, no `/MP`, and fresh output paths. The controller retains the
actual compiler/source/writer hashes, child identity, exit code and zero-active-job
proof. Only a successful exact v2 native report and two bounded new XMB/XSB files
advance to FF staging. A JSON receipt supplied from another run is not an input.
The writer lease is released before requesting the FF8/11GiB lease.

The FF work area links the72 retained bootstrap inputs and prepared sources;
only the mutable77-byte sentinel is copied. It links the already qualified full
ZoneTool executable, builds the distinct zone with strict sources, verifies the
eight assets, dumps, and rereads the dumped XMB/XSB using the same newly compiled
writer's `--verify-existing` mode. The adapter does not invoke any game client,
test dedicated, SDK install or package deployment.

`material_v2_checks.py` compares material fields, state JSON/152-byte indices,
requires dumped constant-buffer data, and decodes only the pinned native IW7
resident image shape:32x32, one mip,4096 opaque RGBA8/BGRA8 bytes. It compares every
pixel against the original asymmetric diffuse, including orientation and alpha.
It does not substitute image names, accept a changed technique, decode compressed
foreign formats, prove native CBT semantics, or count the recipient normal as an
original texture. Recipient resolution and rendering stay false even on success.
Exact-reference dump behavior must be observed at the future run; any name/state
disagreement stops for evidence review rather than silently normalizing it.

All native phases run inside the reused shared job. A phase error, timeout,
surviving descendant, log overflow, output above64MiB, commit pressure above85%,
or `stop.request` stops only that original job. Restoration and lease release
require confirmed closure and unchanged source hashes; the existing ModelFF helper
then checks stock identity before restoring. An unresolved closure/source/stock
conflict preserves the transaction/evidence and reservation. The FF cap is1MiB;
model artifacts remain bounded to8192B. No captured pointer is a render proof.

```powershell
$v2 = Get-Content <reviewed-material-v2-parameters.local.json> -Raw | ConvertFrom-Json -AsHashtable
& "$surface/Build-MaterialV2.ps1" @v2          # plan only
# Only after parent review, explicit GO and successful current admission:
& "$surface/Build-MaterialV2.ps1" @v2 -Run
```

The actual read-only plan passed on retained inputs: six phases,72stock inputs,
writer4/6GiB and FF8/11GiB, with the run directory still absent. The corrected
preparation is retained separately as `runtime/content-surfaces/material-v2-b`;
`material-v2-a` preserves the earlier source-only estimate. The generated
writer/header and geometry are identical across that budget-only correction.

A later pre-commit plan refresh refused `StockRoot`: the retained `runtime/dt`
directory in the `doom-negative-textures` worktree was no longer present. The
existing stock receipt still describes that historical location. The earlier
successful plan is dated evidence, not current launchability. No replacement
stock, receipt rewrite or restoration was attempted; the coordinator must supply
a suitable existing stock root with valid transaction evidence before native GO.
This environmental refusal occurs before Add-Type, staging, lease or native launch.

Validation now passes54 Python tests (38prior plus16 adapter cases), two PowerShell
parses, pure compiler/quoting/budget gates and14 refusal fixtures. Native processes
in the new Python tests are mocks: they exercise tamper refusal, nonzero exit,
drain failure and timeout without spawning any executable. Synthetic images cover
RGBA/BGRA, wrong channels/orientation/alpha, truncated payload, unsupported format,
streaming and wrong name; they are not a decoded FF from a real native run.
No Add-Type, native compilation, FF execution, resource lease, download or game
was performed. The first native GO run must still validate process closure,
stock restoration, exact output semantics and independently rendered pixels.

## Validation record and failures retained

On2026-10-12, Python3.12.10 passes29 synthetic tests, plus11 checks against actual
pinned ZoneTool/UI sources: contract match, exact generated patch, preserved cached
placeholder predicate, actual flag parser source, `git apply --check`, CLI old
reader refusal/prepared-reader incomplete result, existing-output refusal,
tamper refusal and unchanged shared source hashes. No native C++ was compiled.

The first inspector assumed all optional material arrays existed and constant
names fit11 bytes. The real measured template disproved both assumptions:
absent/null arrays now match the native reader, names use the real12-byte field,
and the strict reader patch fixes the terminator write. Independent review found
that the initial image patch missed the cached-placeholder early return; the
current patch includes it and the exact-source assertion. A second review caught
the matching unbounded dump read for full-width constant names; it is bounded too.
Earlier prepared local v1/v2/v3/v4 outputs are retained but superseded by v5.

```powershell
python -B "$surface/test_surfaces.py"
python -B "$surface/test_pinned_source.py" --zt-source <existing-pinned-x64-zt> --native-source <existing-pinned-iw7-mod>
```

Tests for mismatched sidecars prove the inspector rejects a borrowed file; source
inspection proves the old reader fallback and the new strict branch. Native
execution of that negative case is still pending. No source assertion is described
as an executed C++ test. Shared-source hash equality is rechecked after tests.

Historical evidence stays distinct: [Doom source](DOOM-SOURCE-CANDIDATES.md) records
a91036-byte FF and correct geometry roundtrip with an **invisible helmet in both
poses**. A model pointer/setmodel/build is not pixels. [Rhino audio](CHARACTER-VOICE.md)
records isolated28-list/50-head closure; importing the full1430-list Beast bank
exposes unrelated aliases and is not a microphone fix. [Doom textures](DOOM-TEXTURES.md)
retires the390.03MiB inversion pack. Do not retry whole-map loading or that oversized
pack for this surface witness.

## Original experiment plan and remaining native negative cases

The subsequent full-tool/first-beacon work above advances this original plan.
Its native negative strict-reader matrix remains outstanding; do not rebuild the
full tool just to repeat already supplied compilation evidence.

After parent GO, combine the generic strict-reader patch with the separately
reviewed H1 work in an isolated owner fork. Build under the single scheduler lease
(one-node native build estimate4GiB RAM/6GiB commit). Run paired native source cases:
valid exact sidecars, missing sidecar with a foreign candidate present, truncated
indices, missing cbt, cached generated red placeholder, legitimate custom red TGA
and12/13-byte constant names. Assert strict failures and preserve the no-flag
baseline; use the original beacon source, no donor extraction.

Next build/re-dump the tiny FF, independently check custom image name/pixels,
material name/state/constants and explicit recipient references. The beacon model
owner supplies the rewritten/reread model. Budget new source/artifact output
initially<=1MiB for the surface-only fixture, stop/re-evaluate if exceeded; native
build intermediates are shared parent budgeting, not another copied toolchain.

Only then reserve one full-quality base client plus retained test dedicated
(initial14–16GiB RAM/commit, current scheduler admission authoritative). Prove the
same-pose original checker orientation/color/alpha and material resolution, plus
cold cache/join/rejoin under the SDK test. Keep native godmode/inactivity safeguards
and separate owner acceptance. Bounded captures/logs<=50MiB proposed; no full-game
copy or PAK. No heavy operation in this checkpoint consumed a lease. Local source
commit is handed to the parent for coordinated private PR/CI/merge and common
STATE/BUGS/CHANGELOG/VALIDATION/PLAN updates; it is not independently deployed.
