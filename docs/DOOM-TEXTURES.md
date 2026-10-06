# Doom Fight negative texture candidate

Scope: Spaceland Doom Fight in [issue 91](https://github.com/maxis0191/iw7-paris-server/issues/91).
This candidate is separate from the encounter. It is absent from the normal
module catalog and is not deployed to Paris Main. Rendering/playability acceptance
requires an admitted protected standard-client test; source checks cannot establish it.

## Distribution contract

The existing Aurora client negotiates the server's `fs_game` and `mod_hash`,
downloads `mods/<name>/mod.ff` through `sv_wwwBaseUrl`, verifies its hash, then
selects the mod and reconnects/reloads as required. Empty `fs_game` cannot carry
this pack. The supported automatic file list contains FF and optional SABL/SABS,
not an arbitrary texture PAK or client executable. See the official
[party component](https://github.com/auroramod/iw7-mod/blob/develop/src/client/component/party.cpp)
and the existing local pinned source used by the verified Rhino pack workflow.

The proposed mod is `mods/paris_doom_negative`. Its full-resolution color mip
pixels are resident inside `mod.ff`; players must need no manual file operation,
configuration or replacement executable. Loading a mod is a session-level action;
appearance inside/outside Doom is controlled by distinct model names, without
overriding the originals globally. No additional launcher, public hosting or Main
configuration is installed by these source helpers.

## Exact visual change

The roots are `park_alien_gray`, `zmb_brute_mascot_body`, and all five retail
`park_clown_zombie` color variants. The private exporter follows model/scriptable
model dependencies, including part-state models, so a helmet or backpack cannot
silently escape the inventory. The closure/bindings must be examined before a pack
is described as complete.

For color semantics 2 and 14, each decoded RGB byte becomes `255 - byte` at every
original mip size. Alpha remains identical. Shader-specific semantic 0 maps require
explicit `--extra-color` review; names alone do not prove an emission map. Normal,
specular and unrelated packed maps retain their retail references. Geometry,
physics, animation dependencies, shaders and material state/constant-buffer bytes
also remain unchanged. The output uses resident RGBA8 (matching the input's sRGB
flag) to avoid recompression loss and an external PAK. Measure its actual resident
and FF sizes before full-quality acceptance.

Cloned assets use the `doom_negative_` prefix. A separate COMMON model
NetConstStrings registry, `ncs_mdl_doom_negative`, contains only the ten aliases;
the retail MAP registry remains byte-for-byte unchanged. Replacing `ncs_mdl_level`
failed the map-before-mod audit because the first registered table won. Stock
references must precede every clone in the build CSV so recursive
dependency loading cannot accidentally serialize retail surfaces or shaders.
Required material state and constant-buffer inputs are checked before writing a
candidate; the underlying parser can otherwise omit a missing buffer definition.
The reference-based pack is currently checked against Spaceland stock.
Keep the candidate dedicated on that map until other-map loading/unload
is proved; do not assume that phase restoration makes five-map voting compatible.

## Reproducible local preparation

Use current `origin/main` resource/storage/instance helpers. Keep game-derived
inputs, textures, binaries, dumps, diagnostics and output under ignored `runtime`.
Reuse legitimate stock through minimal read-only retail hardlinks; never hardlink
a generated output or copy a complete game for this worktree.

1. Reuse the clean reviewed ZoneTool source at
   `fab935826c898806855376662a8a03317b3ad8f1`, baseline executable SHA-256
   `B11706598DAD6A5256AF458A597908EC110082C1FF80263F176A5FBD1A6F0372`.
   `ops/Build-DoomTextureTool.ps1 -PinnedToolRoot <path>` creates a private source
   overlay and reserves its single-worker Build job (4 GiB physical / 6 GiB commit).
   Shared dependency sources are read-only; project-reference/prebuild actions are
   disabled. The first manual attempt exposed missing generated-project/prebuild
   inputs; the corrected helper copies the project files and disables that event.
2. `ops/Prepare-DoomTextureWork.ps1 -ToolBinary <exporter> -ToolSHA256 <hash>
   -StockRoot <retail-root>` creates fresh ignored scratch with the reviewed retail
   executable, only needed FFs, and PAK input hardlinks. It copies `fileSysCheck.cfg`
   into a separate mutable cache directory. Omitting that file caused initialization
   to stall; the next diagnostic identified a hidden missing-assetfile1.pak error.
   The supervised jobs timed out and closed only their exact owned tool processes.
   In that scratch directory use
   `ops/Invoke-LabAssetTool.ps1` with the recorded tool checksum and arguments
   `-headless -unbuffered-io -doom-textures-source`. This helper reserves
   Extract 6 GiB physical / 8 GiB commit and supervises only its registered process.
   The private overlay exports `dump/paris_enemy_doom_source` and a sibling
   `_aliases` directory, not an entire map. Names are changed on typed model,
   scriptable and material pointers while the retail serializer runs, then restored.
   Raw name-token rewriting could also rename an unrelated physics asset and is
   rejected by the converter.
3. Inspect `closure.csv`, `bindings.csv` and the dumped material JSON. Make an
   explicit list of color/emission images. Capture those sources with the reviewed
   tool's existing `-enemy-image-dump cp_zmb <list>
   paris_enemy_cp_zmb_doom_<unique>_images -dump_streamed_image` route. It captures
   fresh database registrations; late image pointers are not reliable inputs.
4. Reuse bundled CPython/Pillow or run
   `ops/Install-Tools.ps1 -IncludeDoomTextures -DoomPython <CPython312AMD64>`.
   The optional venv installs the official Pillow 12.3.0 binary wheel with its
   pinned SHA-256. Run `ops/doom-textures/prepare_negative.py <source-dump>
   <selected-image-dump> <new-candidate-directory> [--extra-color <name>]` under an
   appropriate admitted asset job. Preserve failed candidates and diagnostics.
5. Keep prepared sources inside that scratch directory. Run
   `ops/Build-DoomNegativePack.ps1 -WorkingDirectory <scratch>
   -PreparedDirectory <prepared> -ToolSHA256 <hash>`. It reserves Extract 6/8 GiB,
   supervises compilation/parse and both loading-order audits, uses an identity-
   guarded short drive alias for long material paths, and rejects unexpected stock
   serialization or an external PAK. Core shader zones are loaded without their
   full MP counterparts: the first broad recipe exhausted the weapon pool.
   Canonical `proceduralbones` references replace the rejected original type alias.
   Hash resident pixel bytes at asset registration; TEMP-block pointers can be
   reused after consumption, so hashing them after subsequent zones gave false
   mismatches. Package the checked FF as `mod.ff` under ignored runtime. This is
   preparation, not permission to promote an unverified pack.

## Offline candidate checkpoint - 2026-10-06

The real extraction contains 10 models, 4 scriptables, 36 materials and 61 distinct
images, of which 34 are color/emission images. All original mip sizes are
retained. Source/output byte checks cover 152,873,640 RGBA texels including alpha;
the resident image payload is 611,494,560 bytes (583.17 MiB). The built FF is
408,978,108 bytes (390.03 MiB), SHA-256
`32746D5CC8CA21DFD39C0573174746DC23586DC37E745970738F64493558BDC6`.
The corrected exporter/auditor is SHA-256
`414A68DBC3E1DDE6C26159FEC77DE0BF2077F854700F034BDD44C2443E2B4DF5`.

Engine round trips pass with the map loaded before and after the custom FF: all
10 aliases remain in their separate common registry; every retail MAP registry
string remains identical; 277 surfaces preserve stock LOD, physics, bones, shader,
material constants/state flags and non-color image pointers. Registration-time
SHA-256 matches every byte of the 34 resident images. The inventory contains no
script/world asset or external PAK; its only ordinary rawfile is the tool footer.
This is headless engine parsing, with no renderer, client download or combat proof.

At 19:06:24 UTC, admission of the complete 12 GiB client + 4 GiB dedicated scenario
was refused: 18.59 GiB RAM was available, versus 23.95 GiB required to retain the
25% physical reserve. About 5.36 GiB more available RAM is needed; commit headroom
was sufficient. That refused test started no game and modified no client/profile. The
parent's reviewed Doom native/scripts remain on stopped Main; the negative pack
and controller are not deployed. [Sanitized record](deployments/2026-10-06-doom-negative-offline.json).

## Optional controller and remaining acceptance

`src/custom_scripts/cp/experiments/paris_doom_negative.gsc` additionally requires
dedicated Spaceland, exact candidate `fs_game`, and
`paris_doom_negative_candidate=1`. It follows the parent encounter's actual
`level.paris_doom.active` state, switches only grey/Brute/clown agents between
their original and prefixed model, and reapplies after retail grey merges.
It does not fabricate the Doom state or alter actor health/ASM.
It retains each changed entity until phase cleanup so an actor removed from
`level.agentarray` by death can still be restored if it survives. Separate native
corpse/gib entities and render snapshots remain part of runtime acceptance.
Cleanup also strips the prefix from a scriptable-selected part-state root model,
rather than limiting restoration to the seven initial bodies. The production
leaf-body fixture covers these source decisions without simulating native parts.

The polling candidate has a maximum 50 ms switch delay. Crucially, `setmodel` can
reinitialize scriptable attachments: unchanged source bytes do not prove preserved
helmet, health-light or shield state. Do not enable this optional script in the
ordinary catalog until those effects are observed and corrected if necessary.

Acceptance requires a fresh-cache automatic download and matching hash with the
unchanged standard client; full-resolution rendering for every root/part-state
variant; real protected combat including grey merge, Brute helmet changes and
clown behavior; original rendering after phase end/abort/map transition; and a
matched normal-settings resource/render check. Reserve the complete scenario,
establish fresh engine godmode and inactivity=0, keep `sv_cheats=0`, use a stopped
candidate dedicated with its own config/bank, and preserve an occupied owner client.
Do not reduce quality or the reservation to bypass refusal. Owner acceptance
remains separate even when agent technical checks pass.
