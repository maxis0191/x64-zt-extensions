# Animations from outside the game: glTF to and from the game's animation format

Status 11 Nov 2026. Tool: `tools-source/iw7-anim/iw7_anim_gltf.py` (Python 3.12, standard library only). It reads
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
| 4. Zone source | `iw7_anim_gltf.py zone-source <work>/dump --zone mod --tree my_anims --out <work>/src` | `zonetool/mod/xanim/*.xab`, `zone_source/mod.csv`, the name table `ncs_anm_mod`, the animation tree file `animtrees/my_anims.atr` (scripts that ask the game about a clip need it, see P3) |
| 5. Build | `pwsh Build-AnimZone.ps1 -Source <work>/src -Work <new folder> -PreparedSource <server prepared inputs> -StockRoot <stock> -ZoneTool <zonetool.exe> -TlsDll <tlsdll.dll> -Sentinel <main/fileSysCheck.cfg> [-WaitForSlotSeconds 3600]` | `<new folder>/zone/mod.ff` |
| 6. Check | `Read-CompiledZone.ps1` (docs/CONTENT-AUDITS.md) on that file | the game's loader holds the same animation as the source |
| 7. Play | on a script model: `precachempanim( "my_clip" );` at load, then `model scriptmodelplayanim( "my_clip", 1 );`. On a stock zombie: give the clip the name of the stock animation it replaces | see "Proven in the game": measured for the zombie, accepted but not seen for the script model |

Other commands: `inspect <anim>.xab` (what an animation is), `compare <a> <b> [--model <body>.xmb]` (error between
two animations, each an `.xab` or a `.glb`), `sample <clip> --model <body>.xmb --bones a,b` (model-space bone
positions at every frame), `compare-run <run>/anim-<name>.json <clip> --model <body>.xmb` (bone positions logged
by the running game against the clip; the log comes from the gamelab steps `anim` and `pose` of the server
repository, docs/GAMELAB.md there).

`cut <anim>.xab --from F --to T --name N --out <dump> [--pingpong] [--loop] [--no-notes] [--drop-note PREFIX] [--note NAME:SECONDS]`
writes frames F to T (inclusive) of a game animation as a new one, header bytes (asset type, additive flag) kept: the
way to split a one-shot stock clip into a take-out, a hold and a put-away. `--pingpong` runs the range forward then
back, so the first and last key are equal and the clip loops without a jump (a held pose that breathes); notes inside
the range keep their time, `end` is written again. A clip with root motion is refused (its delta track is cumulative).
To find a hold, `sample` the clip and pick the frames where the holding hand barely moves. Used for Maxis' Phone
(server repository docs/MAXIS-PHONE.md, "Animation"): the multiplayer selfie (84 frames) cut at frames 38 and 53, where
the hand holding the phone moves less than 2 units a second in the first-person and the third-person clip; the cuts
differ from the source by 0.003 degrees at most (the 16-bit storage).

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
| Header bytes the tool does not understand | flags, asset type and two more bytes are carried in the extras and written back when the file came from `to-gltf` (unless `--loop`, `--no-loop` or `--asset-type` is given). A new clip gets asset type 2 with root motion and 1 without, as stock has them | so a stock animation round-trips unchanged |
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
| Not full-body (2,700 view-model animations, 127 props and partial bodies) | 2,827 | 2,827 |
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

The error is the 16-bit storage and nothing else: a translation track is stored as 65,536 steps of its own range,
and the worst case is a dance clip whose prop bone travels 736 units. 0.046 unit is 1.2 mm. Nothing failed for an unsupported track kind: the codec decodes all 4,029
stock animations, and the root delta is decoded and re-encoded by this tool in its three forms (translation, turn
about the vertical, full rotation; the last does not occur in Spaceland and is covered by the tests only).

Two things the numbers do not say:

- 11 of the qualifying animations have asset type 6. Their tracks round-trip like the others, but they are
  **additive** (a difference to lay over another animation), so the pose glTF shows for them is not a pose the
  game ever shows. `inspect` flags them (`additive_suspected`).
- The animations that list bones the model lacks are not lost: `to-gltf` reports the missing bones and converts
  the rest. They belong on their own skeleton.

Evidence (kept outside the repository): folder `anim-gltf/p1`, `results.json` (one row per animation and model) and `summary.json`.

## Measured: a new animation through the game's loader (P2)

Three new animations for the zombie skeleton (`police_officer_zombie`), each 2 seconds, none copied from a stock clip:

| Clip | Made with | Content |
|---|---|---|
| `animgltf_wave` | `author_clip.py` (Python) | torso turned 40 degrees, right arm raised 100 degrees (wrist travels 32 units); note `animgltf_hit` at 1.0 s |
| `animgltf_walk` | `author_clip.py` | the same pose change, root motion 96 units forward, note `animgltf_step` at 0.5 s |
| `animgltf_blender` | Blender 5.2 from the command line (`blender_key_clip.py`: import `rig.glb`, key spine and left shoulder at the first and last frame, export glb with default settings) | torso turned the other way, left arm raised (wrist rises 18 units) |

Blender exported all 102 bones and its own easing; `from-gltf` matched 102 of 102 by name, wrote 102 bones (100 of
them a single value), and the bind pose came back exact (the wrist at frame 0 is where the model has it, to 0.004
unit). Conversion error of the three clips against their glTF source: at most 0.003 degrees and 0.002 unit in model
space. Conversion time 0.05 to 0.08 s a clip. Sizes 1.4 KB, 1.9 KB and 3.6 KB.

Two more clips were made for the in-game measurement (P3): the stock zombie idle's first frame held still, with the
same arm and torso motion authored on top and a note at 1.0 s, under the names of the two stock idle animations.

Built with `Build-AnimZone.ps1` (community ZoneTool, IW7 mode): the five animations, the name table and the
animation tree file compiled to a 6,568-byte `mod.ff`; the compile step took 31 ms (the rest of a build is ZoneTool
starting and loading the game's base zones; it was not timed apart from the wait for the build reservation).

Read back with `Read-CompiledZone.ps1`: the game's loader finished in 6 s; **5 of 5 animations hold the same content
after decoding, 0 differ; 0 errors, 0 warnings**; the name table is identical. `compare` between each source file
and the file the loader gave back: 0.000003 degrees, 0 units, root motion 0, notes equal.

So: the game's loader accepts our files. Evidence (outside the repository): `anim-gltf/p2` (clips, reports) and
`anim-gltf/p3b` (`src`, `ztwork/zone/mod.ff`, `readback`, `readback.json`).

## Proven in the game (P3, P4)

All runs: private dedicated server on loopback with a random password and one engine bot, no client
(`Invoke-GameLabHeadless.ps1` of the server repository, about 1.1 GB, 40 to 90 s a run), map Spaceland, the mod zone of
P2 loaded with `-FsGame mods/animgltf`. The plan steps `anim`, `pose` and `animinfo` log what the server itself
computes; `compare-run` compares the log with the clip. Evidence (outside the repository): `anim-gltf/p3/runs/<name>/run1`
(`client.stdout.log`, `anim-<step>.json`, `gamelab.result.json`).

### What the game's own functions read from our files (run `b1`: PASS, 7 of 7)

A script names the animation as a value (`#using_animtree("animgltf"); %animgltf_walk`) and asks the game:

| Asked | Authored | The game answered |
|---|---|---|
| `getanimlength` of the three new clips | 2.0 s (60 frames at 30) | 2 |
| `getmovedelta( walk, 0, 1 )` (root motion over the clip) | 96 units forward | (96, 0, 0) |
| `getmovedelta( walk, 0, 0.5 )` | 48 | (48.0007, 0, 0) |
| `getmovedelta` of the two clips without root motion | none | (0, 0, 0) |
| `getnotetracktimes( walk, "animgltf_step" )` | 0.5 s of 2 s | 0.25 |
| `getnotetracktimes( wave, "animgltf_hit" )` | 1.0 s of 2 s | 0.5 |
| `getnotetracktimes( blender clip, "end" )` | end | 1 |

The animation tree file that `zone-source` writes is what makes this work. Without it (the same script under the
stock tree `mp_script_model`, run `e1`) the server stopped while loading scripts, printed nothing and never started
the map: an animation named as a value must be listed in the tree the script names.

### Bones of a zombie playing our clip, measured on the server (P3)

A dedicated server does not pose a script model (next section), but it does pose its zombies. So the measurement
uses a zombie: the mod zone carries our authored clip under the names of the two stock idle animations, the stock
zombie's idle state plays it, and the `pose` step logs the origin of six bones every server frame (50 ms).

First the method on stock content, no mod (runs `c1`, `c2x`): the logged bones of an idle stock zombie against the
stock idle animation as this tool decodes it.

| Run | Body | Samples | Clip start found | RMS | Worst | Against the other stock idle |
|---|---|---|---|---|---|---|
| `c1` | male (`zombie_male_outfit_2_5`) | 181 x 4 bones, 9 s | 0.700 s after the log began; the idle's `end` note arrived at 700 ms | 0.004 unit | 0.033 unit | 37 units |

So the tool reads the game's format the way the game evaluates it: rotations, translation offsets, timing and loop.

Then our clip (run `a4z`, zombie `z1`, male body `zombie_male_outfit_5_3`; `compare-run` against the **glTF
source**, not against our own output):

| Samples | Clip start found | RMS | Worst | Right wrist travel, game / clip | Against the stock idle it replaced |
|---|---|---|---|---|---|
| 147 x 6 bones (head, both wrists, right elbow, pelvis, left ankle), 7.3 s = 3.65 loops | 1.000 s; the clip's `end` notes arrived at 1000, 3000, 5000, 7000 ms | 0.004 unit | **0.007 unit** | 14.283 / 14.279 units | 31 units |

After 7.35 s that zombie left the idle state by itself (the error then grows within three server frames), which is
the game's behaviour and not part of the clip; `compare-run --to-ms 7300` limits the comparison to the stretch, and
without the limit it reports the same instant (`within_limit_until_ms`: 7350). The command:

    python iw7_anim_gltf.py compare-run <run>/anim-idle_z1.json iw7_cp_zom_stand_idle_01.glb --model <dump>/xmodel/police_officer_zombie.xmb --loop --to-ms 7300

What this proves: the game evaluates the file our writer produced to the bone positions computed from the glTF
source, on the game's own skeleton, at the game's own timing, including the loop. What it does not prove: anything
about a client's picture (no frame was taken), and nothing about blending into or out of the clip.

Two things learned on the way, both now in the tools:

- Zombies come in several bodies, and the body sets the proportions: the same idle on a female body puts head and
  wrists 2 to 3 units away from where the male skeleton has them (run `c2x` against the male skeleton: worst 2.9; the
  pelvis agrees to 0.1). Expected positions must be computed on the skeleton of the body that was spawned. The
  comparison above uses zombies with the male body, whose bones match `police_officer_zombie` (stock run: worst
  0.03). The female body's full skeleton is spread over several part models and was not assembled.
- Zombies standing in a crowd step around and leave the idle state; the measurement spawns each zombie alone.

### A script model on a dedicated server is not posed (run `a1`)

`precachempanim( name )` at load and `model scriptmodelplayanim( name, 1 )` were accepted for the three new names
without any error line. For 2.4 s after each call the server reported every tag exactly where the bind pose has it
(49 samples a clip, three tags, travel 0.000; the first sample is 0.006 unit from the model's bind, which is the
print precision). The same for a stock animation name. The model's origin did not move with the root-motion clip
either. So on a dedicated server a script model's animation is the client's business: the server sends the name and
knows nothing about the pose.

**Not proven: that a client shows the clip on a script model.** No client session was run for it. What it needs:
a client session of the same plan with frames (`Invoke-GameLab.ps1` has no option to load a mod zone today: that is
the missing piece, a `-FsGame` and a mod copy as the headless runner now has), then either frames judged by
reviewers, or a client console command that prints an entity's tag positions (native code, components repository)
so the same `compare-run` works on a client. Retail plays its animated props and the robot N31L this way
(`scriptmodelplayanim` by name), which is why this route was chosen.

### Root motion and notes in the game (P4)

**Notes: proven on a zombie.** The clip above carries the note `animgltf_hit`, authored 1.0 s into its 2.0 s. The
game sent it to the zombie's script (`self waittill( "idle", note )`, the notify retail uses) at 0, 2000, 4000 and
6000 ms of the log, and the clip's `end` at 1000, 3000, 5000 and 7000 ms: the note fires 1000 ms after each loop
start, as authored. A server frame is 50 ms, so that is the resolution of this number. A second run (`a2x`, another
zombie) gave 2200, 4200, 6200, 8200 against `end` at 1200, 3200, 5200, 7200: the same 1000 ms.

**Notes on a script model: not measured.** Nothing listened for them, and since the server keeps no pose for a
script model it is unlikely to send any. No retail script waits for a note of a script model; they read the note
time with `getnotetracktimes` and wait that long (run `b1` above shows the game returns our note times exactly).
A script that needs the event does the same.

**Root motion: read exactly, not shown moving a model.** The game's `getmovedelta` returns the authored 96 units
(and 48.0007 at half time) for our clip. A script model played with `scriptmodelplayanim` did not travel (its origin
after the root-motion clip equals its origin before, run `a1`), and the game function that would move it
(`scriptmodelplayanimdeltamotion`, known from other games of the series) is used by no retail script of this game
and was not tried. A zombie moved by a root-motion clip of ours was not tried either: its walk states are driven
by the path code, and which state lets the animation move the body was not established. What is missing for
"the model advances by the authored distance in the game": either that state for agents, or a three-line script
that moves a script model by `getmovedelta` every frame (which then proves the script, not the engine).

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
| **Root motion that moves a body** | a script model played with `scriptmodelplayanim` does not travel on the server (P4); the game function that would move it (`scriptmodelplayanimdeltamotion`) is used by no retail script of this game and was not tried; a zombie moved by our root motion was not tried | move the model from script with the distance the game itself reads from the clip (`getmovedelta`, P4), or use an agent |
| **Notes that call script** on a script model | measured for a zombie (the game sends the notes to its script, P4); not measured for a script model, and no retail script relies on it | read the note time with `getnotetracktimes` and wait that long, as retail scripts do |
| Fewer keys (real compression) | the encoder writes every frame | key reduction in the codec; not needed for correctness |
| Scale tracks | the game format has none; a glTF scale animation is reported and ignored | nothing |
