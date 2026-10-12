# Content surfaces bridge — source checkpoint 2026-10-12

The new dependency inspector, pinned ZoneTool reader patch and small beacon surface
are prepared. Native compilation, FF construction, rendering, content-audio playback
and client HKS execution were **not run**. None is a qualified import capability.
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

## Next decisive experiment and budget

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
