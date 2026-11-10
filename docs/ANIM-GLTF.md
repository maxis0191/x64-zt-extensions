# Animations from outside the game: glTF to and from the game's animation format

Status 10 Nov 2026. Tool: `tools-source/iw7-anim/iw7_anim_gltf.py` (Python 3.12, standard library only). It reads
and writes the animation files ZoneTool dumps and builds (`xanim/<name>.xab`) and ordinary glTF 2.0 (`.glb`, or
`.gltf` with its buffers). The byte layout comes from `tools-source/asset-bridge/t7-weapons/iw7_xanim_codec.py`; the
skeleton reader from `tools-source/iw7-skinned-writer/xmodel.py`. The tool lives in its own folder because it needs
both and belongs to neither the weapon port nor the mesh writer.

Game files are never committed. Every command reads them from a local path you give it. The tests use made-up
skeletons and clips.

## What a creator can do now

One command turns a glTF animation, made in Blender or anywhere else, into a game animation for a stock skeleton:

    python tools-source/iw7-anim/iw7_anim_gltf.py from-gltf my_clip.glb --skeleton <dump>/xmodel/<body>.xmb --name my_clip --out <work>/dump

The bones of the file must carry the game's bone names (start from the skeleton file the tool writes, see below).
A skeleton from another game is not converted: see "Not possible yet".

The whole route, each step one command:

| Step | Command | Result |
|---|---|---|
| 1. Get the skeleton to animate on | `iw7_anim_gltf.py skeleton <body>.xmb --out rig.glb` | the stock skeleton in bind pose, with a stick figure so Blender builds an armature |
| 1b. Or start from a stock animation | `iw7_anim_gltf.py to-gltf <dump>/xanim/<anim>.xab --model <body>.xmb --out stock.glb` | the same skeleton with the stock clip on it |
| 2. Animate | Blender: import `rig.glb`, key the armature, export glb (all defaults). Example done from the command line: `blender -b --factory-startup -P blender_key_clip.py -- --rig rig.glb --out clip.glb --turn j_spine4:z:-35 --turn j_shoulder_le:x:100` | `clip.glb` |
| 2b. Or make a test clip without any tool | `python author_clip.py <body>.xmb --out clip.glb --rotate j_shoulder_ri:0,100,0 --move 96,0,0 --note hit:1.0` | `clip.glb` |
| 3. Convert | `iw7_anim_gltf.py from-gltf clip.glb --skeleton <body>.xmb --name my_clip --out <work>/dump [--loop] [--note NAME:SECONDS]` | `<work>/dump/xanim/my_clip.xab` and a report |
| 4. Zone source | `iw7_anim_gltf.py zone-source <work>/dump --zone mod --out <work>/src` | `zonetool/mod/xanim/*.xab`, `zone_source/mod.csv`, the name table `ncs_anm_mod` |
| 5. Build | `pwsh Build-AnimZone.ps1 -Source <work>/src -Work <new folder> -PreparedSource <server prepared inputs> -StockRoot <stock> -ZoneTool <zonetool.exe> -TlsDll <tlsdll.dll> -Sentinel <main/fileSysCheck.cfg> [-WaitForSlotSeconds 3600]` | `<new folder>/zone/mod.ff` |
| 6. Check | `Read-CompiledZone.ps1` (docs/CONTENT-AUDITS.md) on that file | the game's loader holds the same animation as the source |
| 7. Play | script: `precachempanim( "my_clip" );` at load, then `model scriptmodelplayanim( "my_clip", 1 );` | see "Proven in the game" |

Other commands: `inspect <anim>.xab` (what an animation is), `compare <a> <b> [--model <body>.xmb]` (error between
two animations, each an `.xab` or a `.glb`), `sample <clip> --model <body>.xmb --bones a,b` (model-space bone
positions at every frame), `compare-run <run>/anim-<name>.json <clip> --model <body>.xmb` (bone positions logged
by the running game against the clip; the log comes from the gamelab steps `anim` and `pose` of the server
repository, docs/GAMELAB.md there).

## The mapping, and why

| Point | Choice | Reason |
|---|---|---|
| What is animated | every bone the game animation lists; other bones stay in the model's bind pose | this is the game's own rule (a bone an animation does not list keeps the model's pose) |
| Space | parent-relative (local) rotation and translation per bone | both formats store it that way; no accumulated error |
| Translation | the game stores an **offset from the model's bind translation**; glTF gets bind + offset, and the way back subtracts the bind | measured, see below. Rotations are stored whole (not as a difference from the bind) |
| Axes | game (x forward, y left, z up) becomes glTF (x, z, -y) | a pure rotation, so no mirrored bones; Blender's importer turns glTF's y-up back, so Blender shows the game's own axes and the character faces +x |
| Units | game units are inches; glTF is in metres, factor 0.0254 (`--scale` on every command; the factor is also written in the file and read back) | glTF's unit is the metre; Blender shows true sizes |
| Frame rate | one key per game frame, linear; the animation's own rate (30 a second for 4,016 of 4,029 stock animations, 24 for 13). `from-gltf` resamples any glTF timing (linear, step, cubic spline) to `--fps` (default 30) | the game interpolates linearly between keys |
| Length | a game animation of N frames has N + 1 keys and lasts N / rate seconds | as stored |
| Loop flag | `animations[0].extras.iw7.loop`; `--loop` / `--no-loop` on `from-gltf` | glTF has no loop flag |
| Root motion (delta track) | the node `iw7_root_motion`, parent of the whole skeleton: its translation and rotation are the game's root delta. Rotation about the vertical only is written as the game's two-component form, anything else as the three-dimensional form | a DCC tool shows the character really travelling, and the animator keys one extra bone |
| Notetracks | `animations[0].extras.iw7.notes` = name, time 0..1 and seconds; `--note NAME:SECONDS` on `from-gltf`. A note `end` at 1.0 is always written (every stock animation has one) | Blender does not keep glTF extras on export, so the command line is the reliable way |
| Header bytes the tool does not understand | flags, asset type and two more bytes are carried in the extras and written back when the file came from `to-gltf` | so a stock animation round-trips unchanged |
| Compression on the way in | one key per frame; rotations as four 16-bit numbers, translations as three 16-bit numbers of their own range; a bone that never moves becomes a single value, a bone that never leaves the bind is left at "no track" | the only forms the encoder writes. Cost: file size (a 2.1 s, 90-bone stock walk: 33 KB stock, 49 KB from us) |

How the translation rule was measured: stock full-body animations carry two helper bones, `tag_ik_foot_loc_le/ri`,
whose bind position is the ankle's. With translations read as offsets from the bind, the ankle computed through
hip and knee lands on its helper in the animated pose too (within 0.5 unit in 920 of the 924 stock animations that
carry the helpers, median 0.12; the 4 others are additive animations); read as absolute values, the pelvis of every
stock character sits 5 units under the ground. The running game agrees (see P3).

## Measured: round trip without the game (P1)

For every stock Spaceland animation: `to-gltf`, `from-gltf`, then `compare` with the original decoded tracks, for
one zombie body (`police_officer_zombie`, 102 bones) and one player body (`body_zmb_hero_jock`, 105 bones).
An animation qualifies when it is a full-body animation (it moves the pelvis, spine, head and both knees and is
not a view-model animation) and every bone it lists exists in the model.

| | Zombie body | Player body |
|---|---|---|
| Stock animations | 4,029 | 4,029 |
| Not full-body (view model, props, faces, partial) | 2,827 | 2,827 |
| Full-body but lists bones the model lacks (another character's rig) | 256 | 356 |
| **Qualify** | **946** | **846** |
| Round trip within tolerance | 946 of 946 | 846 of 846 |
| Bone set, notes and loop flag identical | all | all |
| Rotation error: worst / 99th percentile (degrees) | 0.0050 / 0.0028 | 0.0050 / 0.0028 |
| Translation error per bone: worst / 99th percentile (game units) | 0.023 / 0.0034 | 0.023 / 0.0034 |
| Bone position error in model space: worst / 99th percentile (game units) | 0.046 / 0.013 | 0.046 / 0.013 |
| With root motion | 789 | 749 |
| Root motion error: worst translation (units) / rotation (degrees) | 0.0049 / 0.0024 | 0.0049 / 0.0024 |
| Time for both conversions: median / longest | 0.40 s / 86 s (2,700 frames) | 0.40 s / 88 s |

The error is the 16-bit storage and nothing else; the worst translation is on a clip whose track spans 1,500 units
(a 384-unit drop). 0.046 unit is 1.2 mm. Nothing failed for an unsupported track kind: the codec decodes all 4,029
stock animations, and the root delta is decoded and re-encoded by this tool in its three forms (translation, turn
about the vertical, full rotation; the last does not occur in Spaceland and is covered by the tests only).

Two things the numbers do not say:

- 11 of the qualifying animations have asset type 6. Their tracks round-trip like the others, but they are
  **additive** (a difference to lay over another animation), so the pose glTF shows for them is not a pose the
  game ever shows. `inspect` flags them (`additive_suspected`).
- The animations that list bones the model lacks are not lost: `to-gltf` reports the missing bones and converts
  the rest. They belong on their own skeleton.

Run folder: `IW7-Runtime/anim-gltf/p1` (`results.json` one row per animation and model, `summary.json`).

## Measured: a new animation through the game's loader (P2)

@@P2

## Proven in the game (P3, P4)

@@P3

## Not possible yet

| Not possible | Why | What it needs |
|---|---|---|
| An animation made for **another game's skeleton** ("the same movements" from another game) | bones are matched by name, and the tool does not convert between skeletons: other bone names, other rest poses, other proportions. Today only Black Ops 3 weapon animations are converted, onto the game's hands (`t7_vm_retarget.py`) | a full-body retarget step before `from-gltf`: a bone-name map per source game, rotations carried in model space relative to each rig's rest pose, pelvis height scaled, feet pinned by two-bone IK (the method `t7_vm_retarget.py` already uses for arms). Its proof would be the same P1/P3 measurements with a source clip from that game |
| **Additive** animations (asset type 6: view-model poses and offsets, aim and lean layers) | the tracks convert, but they are differences, and the tool shows and writes them as if they were poses. A new additive animation cannot be authored: the reference pose it is a difference to is not known to the tool | the reference pose per additive family, then "pose minus reference" on the way in and "reference plus difference" on the way out. Which byte marks an animation additive is inferred from 4 stock cases (see P1), not read from engine code |
| **Faces** | stock faces are bones on the head model, driven by their own animations; nothing here was tested on a head model, and no facial clip was converted | run the same P1 on a head model and its facial animations; nothing in the format is known to block it |
| **Cloth, hair, jiggle** | not animation files: the model names simulated bones (`proceduralbones`), the game moves them | out of scope of an animation converter; the skinned writer keeps the reference to the stock set |
| A character **with its own skeleton** | this tool only writes animations for bones of an existing game model. A new skeleton comes from the skinned writer (`tools-source/iw7-skinned-writer`), which today keeps the stock skeleton too | a model writer that writes new bones, then this tool unchanged |
| **Animation classes and behaviour trees** (a zombie or boss that chooses its own walk, attack, pain, death) | a new animation can be played by name on a script model, and it can take the place of a stock animation by carrying its name (P3). It cannot be added as a **new** state: the state list (`animclass`), the behaviour tree and the per-map table of class names are separate assets, and the table needs native code today (docs/ANIMATION-AI-BRIDGE.md) | an animation-class writer (states, aliases, transitions) and the table extension without native code |
| **Blending between two clips** on a script model | `scriptmodelplayanim` plays one animation; nothing was measured about a blend, and retail scripts clear the animation and start the next | either agents (animation classes blend), or accept cuts and author transitions into the clips |
| **Root motion that moves a script model** | the game function for it (`scriptmodelplayanimdeltamotion`) is not used by any retail script of this game, and a script model played with `scriptmodelplayanim` does not travel (P4) | move the model from script with the distance the game itself reads from the clip (`getmovedelta`, P4), or use an agent |
| **Notes that call script** on a script model | the game sends animation notes to the script of an agent, not of a script model (P4) | read the note time with `getnotetracktimes` and wait that long, as retail scripts do |
| Fewer keys (real compression) | the encoder writes every frame | key reduction in the codec; not needed for correctness |
| Scale tracks | the game format has none; a glTF scale animation is reported and ignored | nothing |
