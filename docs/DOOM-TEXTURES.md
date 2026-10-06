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

Cloned assets use the `doom_negative_` prefix. The effective Spaceland model
NetConstStrings registry is preserved and extended, rather than replaced with an
empty stub. Stock references must precede every clone in the build CSV so recursive
dependency loading cannot accidentally serialize retail surfaces or shaders.
Required material state and constant-buffer inputs are checked before writing a
candidate; the underlying parser can otherwise omit a missing buffer definition.
The reference-based pack and extended map registry are currently specific to
Spaceland. Keep the candidate dedicated on that map until other-map loading/unload
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
2. In a fresh owned runtime tool directory, use
   `ops/Invoke-LabAssetTool.ps1` with the recorded tool checksum and arguments
   `-headless -unbuffered-io -doom-textures-source`. This helper reserves
   Extract 6 GiB physical / 8 GiB commit and supervises only its registered process.
   The private overlay exports `dump/paris_enemy_doom_source`, not an entire map.
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
5. Build the resulting `assets.csv` as `paris_enemy_doom_negative` using the reviewed
   ZoneTool runtime guard. Keep the pack name's `paris_enemy_` prefix, needed by
   its strict material/image parser. Verify inventory and hashes, exclude scripts,
   world geometry and external PAK requirements, then package the resulting FF as
   `mod.ff`. This is preparation, not permission to promote an unverified pack.

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
