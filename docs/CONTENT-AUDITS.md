# Content audits: is the content right, proven from real data

A port can build, load and still be wrong for the player: a weapon that sounds like the stock weapon it was
cloned from, a trail that is a stock trail in disguise, a texture the builder silently replaced by a default.
These tools catch that from facts, before anybody plays. None of them predicts what the engine will draw or
play: where only the running game can settle a point, the finding says so and an *engine question* is written,
so game time goes only to what data cannot prove.

## Three layers, from cheapest to most real

| Layer | What it reads | Cost | Tools |
|---|---|---|---|
| 1. Source audits | the `zonetool/<zone>` source tree and a local stock dump | 3 to 16 s, no engine | `t7-weapons/iw7_weapon_feel_audit.py`, `iw7_weapon_sound_audit.py`, `iw7_weapon_fx_audit.py`, `iw7_mod_preflight.py` |
| 2. Build and loader | the build log, then the compiled fastfile read back by the game's own loader | seconds (7 s for the weapons zone) | `zone-check/zt_buildlog_gate.py`, `zone-check/Read-CompiledZone.ps1` + `iw7_zone_readback.py` |
| 3. Engine bench | the real renderer and audio | a game run | owned by the server repository (`ops/bench`, `gamelab`) |

Layer 2 is still the real game code: ZoneTool hosts the loader of `iw7_ship.exe` in its own process, with no
window, no renderer and no sound device. Layer 3 answers the engine questions the first two layers write.

## The shared contract (`t7-weapons/iw7_audit_common.py`)

"Right" has three sources and nothing else: a **declared decision** (an intent file), the **stock population**
(read at run time from a local dump, never committed), and the **original game's value** where a port tool
recorded one.

- `error`: the files prove it is broken. `warn`: a fact somebody must look at. `info`: a fact, or where a value
  sits among stock.
- Each finding says whether `data` proves it or only the `engine` can.
- A warning is closed by changing the content or by a declared decision with a reason. It is never closed by
  lowering a threshold.
- Exit 0 pass, 1 with errors. With `--strict`, 2 while a warning is unanswered. A release gate is `--strict`
  returning 0.
- Absence from a dump is never proof of absence: such a case is a warning or a note with an engine question.
- Every tool takes `--stock DIR` (repeatable), `--intent FILE_OR_DIR`, `--json FILE`, `--strict`.

Declared decisions, one JSON file per item:

    {"schema": "iw7.content-intent/1", "item": "iw7_thundergun_zm", "kind": "weapon",
     "also": ["iw7_thundergun_zm_pap1"],
     "decisions": {
       "weapon:weapDef.aimDownSight":  {"value": false, "why": "the BO3 Thundergun cannot aim"},
       "animpkg:timers.iRaiseTime":    {"min": 900, "max": 1100, "why": "matches its 1.0 s raise animation"},
       "finding:FX-STOCK-COPY":        {"keep": true, "why": "the stock trail is the wanted one"}}}

A decision without a reason is refused. `iw7_weapon_feel_audit.py --write-intent-skeleton DIR` writes the
questions to answer for each weapon.

## Layer 1: the weapon audits

    python -I iw7_weapon_feel_audit.py  TREE --stock DUMP/cp_zmb [--stock ...] [--intent DIR] [--json out.json]
    python -I iw7_weapon_sound_audit.py TREE --stock DUMP/cp_zmb [--bank mod.sabl --loads-as mod]
    python -I iw7_weapon_fx_audit.py    TREE --stock DUMP/cp_zmb [--port DIR]

- **Feel**: raise, drop, reload, sprint, aim, spread, ammo, damage, recoil. Finds what was left over from the
  cloned stock weapon, timers that do not fit the length of their animation, the moment ammo arrives against
  the reload length.
- **Sound**: will the sounds load (bank name against the zone that loads it, samples, alias chains), are the
  fire sounds set up the way stock sets them up (type, channels, layers), and how loud the samples are. Levels
  are measured from the sample files with ffmpeg, never estimated.
- **Effects**: which effects each weapon really plays, whether they exist and were converted completely, and
  whether a ribbon, beam or tail has the settings of a stock one.

Measured on the recorded port history (10 Nov 2026), 3 to 16 s per run:

| Tree | Feel | Sound | Effects |
|---|---|---|---|
| Stock `cp_zmb` dump (must stay quiet) | 0 errors, 0 warnings | 0 errors, 1 warning | 0 errors, 0 warnings |
| Earliest four-weapon tree (the one that sounded wrong) | 9 warnings | 21 warnings | 7 warnings |
| Latest four-weapon tree | 20 warnings | 1 warning | 7 warnings |

The earliest tree's sound warnings are the reported fault: fire sounds of a type stock almost never uses for
a shot (9), layers all on one channel (8), aliases that do not exist (2). The seven effect warnings are the
ribbons that are copies of stock ribbons: the beam-like glitch. The latest tree's one sound warning is a
measured fact: the Ray Gun Mark II shot is about 10 dB quieter than the other three.

## Layer 2: build log and loader readback (`zone-check/`)

**Build-log gate.** ZoneTool does not stop when an image or a material is missing: it writes a default one,
prints a warning among tens of thousands of lines and still reports success. `zt_buildlog_gate.py LOG` reports
an unfinished build and error lines as errors, and each family of silent replacements as a warning. With
`--baseline FILE` only replacements that are new since the accepted build are reported. A baseline lists stock
asset names, so it is refused inside a git work tree.

**Loader readback.** `Read-CompiledZone.ps1` builds a private work folder (stock files as hard links, no disk
used, never written; the file under test and its `.sabl` / `.sabs` companions as copies), takes one scheduler
lease, lets the loader read the compiled file and dump what it holds, then runs `iw7_zone_readback.py` to
compare that with the source:

    pwsh -File Read-CompiledZone.ps1 -ZoneFile <zone.ff> -SourceCsv <zone_source/zone.csv> `
        -SourceTree <zonetool/zone> -Work <new folder on the stock's volume> -StockRoot <stock> `
        -ZoneTool <zonetool.exe> -TlsDll <tlsdll.dll> -Sentinel <main/fileSysCheck.cfg> `
        -SchedulerCore <prepared inputs>/ops/Resource-Scheduler.Core.ps1 [-Types kind,kind] [-Json out.json] [-Strict]

Exit 0 pass, 1 errors, 2 warnings unanswered under `-Strict`, 3 the loader did not finish (nothing is proven),
4 refused. The work folder stays afterwards: its dump is the evidence. Delete it file by file, never with a
forced recursive delete: forcing would change attributes on files shared with the stock.

What the comparison decides:

- an asset or a table row the source asked for and the loader does not hold: **error**;
- a value written in the source that the compiled file holds differently: **warning**;
- a value the source did not write and the builder filled in, or a value the compiled format has no room for
  (stock holds it empty too): a **note**, never a warning;
- tables listed by an asset (a sound bank's alias tables) are compared **row by row**: the builder merges
  several source tables into one, so the list of files is not compared;
- effects and animations are decoded on both sides and compared by content; kinds with no decoder (model
  surfaces, Lua) are reported as *not compared*, never as a pass;
- a limited dump (`-Types`) never proves that the other kinds are missing.

Measured on the compiled four-weapon zone (10 Nov 2026): the loader finished in 6 to 7 s, 9 s for the whole
run; 0 errors, 0 warnings; 66 of 66 effects and 51 of 51 animations hold the same content as the source; the
78 sound aliases of 6 source tables are in the compiled bank with the same values in all 53 columns. The same
dump compared with a source where one alias was added and one volume changed: exit 1, the added alias reported
as not loaded and the changed volume reported with both values.

## Limits

- No audit here launches the game. What the player sees and hears is confirmed only by the engine bench.
- 14 model files and 1 Lua file of the weapons zone have no decoder and are not compared.
- The loader's log does not list each asset it loads, so the loaded set is taken from the dump list.
- Stock numbers are read from the local dump at run time; committed tests use synthetic fixtures only.
