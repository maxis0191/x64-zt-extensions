# H1 weapon asset bridge: animation package structure

The first implemented weapon conversion moves the three H1 weapon-animation
reference tables into IW7 `WeaponAnimPackage` JSON. It converts **reference slot
structure only**, using the real retained parser/writer schemas. It neither
converts the referenced animation clips nor produces a complete playable weapon.
The model, animation and material pipeline remains the prerequisite; this work
does not replace those workstreams or change their files.

## Concrete entry points and full-weapon boundary

All source observations below use the already-retained owner-fork ZoneTool pin
`fab935826c898806855376662a8a03317b3ad8f1`. Source paths in this table are relative
to `src/zonetool/zonetool/`. No upstream check or asset extraction was performed.

| Part of an H1 weapon | Actual retained route into IW7 | Remaining full-weapon requirement |
| --- | --- | --- |
| Weapon entry | `h1/assets/weapondef.cpp::dump` writes `weapons/<name>.json`. `h1/zonetool.cpp::dump_asset_iw7` has its weapon, attachment and XAnim calls commented out. | There is no working generic H1 weapon dispatcher merely because the full tool builds. IW7 `weapondef.cpp::parse` reads `WeaponCompleteDef`, then nested `weapDef`; the H1 root layout cannot be pasted into it. |
| View/world models and hands | H1 weapon JSON has `gunModel[2]`, `worldModel[2]`, `handModel`, `persistentArmXModel`, magazine/rocket/knife references. `h1/converter/iw7/assets/xmodel.cpp` and `xsurface.cpp` have actual conversion routes. IW7 weapon fields include `gunXModel`, left/right models, default models, shadow models and `handXModel`. | Select and bind each view/world/hand role explicitly, preserve rig/tag identity and verify packed geometry/materials. The array index alone is not proof of the IW7 role. Existing model limitations remain in [ASSET-BRIDGE-H1.md](ASSET-BRIDGE-H1.md). |
| Material and images | H1-to-IW7 `material::dump` calls `dump_json`, with explicit techset mapping. `gfximage.cpp` has texture-semantic conversion and an image route. | Exact IW7 techset/pass/vertex input, sidecars and pixel data remain necessary. This material route can substitute `default` for an absent image, skip the H1 environment BRDF LUT and add constants/identity maps; successful JSON emission does not prove visual fidelity. See [CONTENT-SURFACES-BRIDGE.md](CONTENT-SURFACES-BRIDGE.md). No material patch is added here. |
| Animation clips and bone/event data | H1 and IW7 have distinct `assets/xanim.cpp` readers/writers. H1 `XAnimParts` is 0xD8; IW7 is 0x88, with different count/pointer layouts and extra H1 data. | No byte copy/extension rename. Compressed channels, delta motion, bone bindings, first-person arms and notetrack names/times require the animation bridge. This converter only preserves each exact clip reference. See [ANIMATION-AI-BRIDGE.md](ANIMATION-AI-BRIDGE.md). |
| Weapon animation tables | H1 exports 190 symbolic entries per `szXAnims`, `szXAnimsRightHanded` and `szXAnimsLeftHanded`. IW7 expects each field to name an `ASSET_TYPE_ANIM_PACKAGE` with 260 slots. | **Implemented below:** exact source-enum correspondence, explicit separate IW7 template per active table, and a nested WeaponDef link fragment. Timings and gameplay compatibility are not inferred. |
| Notetrack consumers | H1 `notetrackSoundMap` uses Key/Value records (36 entries), plus rumble/FX/tag/hide-tag tables and attachment overrides. IW7 `WeaponCompleteDef` carries counted sound key/value arrays and overrides; `weapDef` carries rumble/FX/tag arrays with combined FX types. | Preserve events in the clip and separately adapt each consumer. This tool reports all nonconverted H1 fields and rejects animation overrides; it does not silently transplant H1 notetrack/attachment data into a different IW7 layout. |
| Attachments | Both engines have `attachments/<name>.json` readers, but H1 field-offset/property definitions and IW7 model variations/camo/property layout differ. IW7 complete weapons have six attachment lists and package overrides. | Translate by actual field meaning/type and apply the correct model/material/animation overrides. Numeric field offsets or attachment ordinals are not a conversion. No attachment conversion is included. |
| FX | IW7 weapon `vfxPackage` resolves through `weapon_vfx_package.cpp` / `vfxpkg/<name>.json`, whose combined references distinguish classic FX from particle-system VFX. | Rebuild the view/world muzzle, eject, projectile and notetrack effect bindings. H1-to-IW7 weapon FX dispatch is disabled. The metadata wrapper is not a converted particle graph. |
| Sounds | IW7 `sfxPackage` resolves through `weapon_sfx_package.cpp` / `sfxpkg/<name>.json`. Those alias names still need actual sound-bank assets. | Preserve view/world, reload/event and projectile aliases, dependencies and audio delivery. H1 sound dispatch into IW7 is disabled; a package name does not import PCM/FLAC or build a valid SAB. |

## Implemented conversion

The source-only implementation is in `tools-source/asset-bridge/weapon`:

- `source_contract.py` reproduces the slot contract directly from the retained
  C++ enum and JSON name tables. `slot-contract.json` records their exact hashes
  together with both weapon readers and structures. A CLI run recomputes this
  contract and refuses source drift before conversion.
- `weapon_anim_bridge.py` requires a complete H1 190-key object for every active
  table, or explicit `null`. Every active table requires its own explicit IW7
  template. No right/left-hand template or timing data is borrowed implicitly.
- `test_weapon_anim_bridge.py` contains only original synthetic fixtures. These
  are not retained retail templates, native dumps, or an imported weapon.

There are **114 exact enum-symbol matches and 76 without a match**. Examples:

| H1 JSON key | H1 index | IW7 JSON key | IW7 index |
| --- | ---: | --- | ---: |
| `IDLE` | 1 | `WEAP_ANIM_IDLE` | 107 |
| `FIRE` | 3 | `WEAP_ANIM_FIRE` | 109 |
| `RELOAD` | 24 | `WEAP_ANIM_RELOAD` | 171 |
| `WEAP_ALT_ANIM_ADJUST` | 132 | `WEAP_ALT_ANIM_ADJUST` | 255 |

The last row demonstrates why adding `WEAP_ANIM_` blindly also fails. Mapping
uses the source enum identity, never the numeric index, fuzzy text or a guessed
semantic alias. A nonempty unsupported H1 slot such as `SPEED_RELOAD` is an
error. Unsupported empty slots require no invented replacement. Unknown,
case-mismatched, numeric or incomplete keys are also errors.

Each generated package starts from the supplied IW7 template. Its common slots
are replaced with the exact donor strings, including clearing a common slot when
the H1 value is empty. IW7-only slots remain exactly as supplied and are listed
in the report. The tool preserves all non-animation template values: the four
`fireAnimTimesMs`, melee settings, timers and footsteps. It validates the native
shapes/scalar ranges, including 104 timer fields (unsigned-short values and two
bools), without deriving or changing those values. Explicit null timer/footstep
blocks remain null. A donor's `stateTimers` is **not** a matching IW7 timer block.

References retain case and spelling. Ambiguous case variants, leading reference
commas, unsupported path/control characters and nonempty animation overrides
are refused. Clip dependencies identify whether they come from unconverted H1
data, retained IW7 slots, or both. Matching asset names do not prove matching
clip payloads; native dependency resolution remains a later gate.

Outputs are limited to `animpkg/<prefix>_{base,right,left}.json` for active
tables, `weapondef-links.fragment.json` and `conversion-report.local.json`.
The fragment contains only `weapDef.szXAnims*`; it is **not a complete weapon
definition** and must not be submitted as one. A null H1 table produces an empty
IW7 package-reference string. Other H1 fields are listed as nonconverted, not
discarded under a claim of a complete port. No existing destination is overwritten.

## Explicit template input and use

The command requires an existing native IW7 animpkg dump with all 260 animation
keys. It cannot create a retail template, default timings or a melee profile.
The request also requires a local provenance file for each template and the
SHA-256 of both files. The source-kind declaration is `iw7-native-animpkg-dump`;
synthetic declarations are rejected by the production CLI.

The request JSON has `h1_weapon` (absolute path to the retained H1 weapon JSON),
`package_prefix` (a lowercase owned name), and `templates`. Each active H1 table
is a key in `templates`, with these exact members:

| Member | Required value |
| --- | --- |
| `path` | Absolute path to the real retained IW7 animpkg JSON |
| `sha256` | Exact SHA-256 of that file |
| `source_kind` | `iw7-native-animpkg-dump` |
| `evidence_path` | Absolute path to the retained extraction/provenance record |
| `evidence_sha256` | Exact SHA-256 of that provenance file |

These checks bind the bytes and require explicit evidence; they cannot prove
that a caller-labelled file actually came from the engine. The converter records
`native_origin_independently_verified: false`. The coordinator must inspect the
evidence and choose a compatible real template before a production use. An
invented record or the synthetic unit template is not acceptable evidence.

From the repository, with the retained source root supplied explicitly:

```powershell
python -B tools-source/asset-bridge/weapon/weapon_anim_bridge.py --request <local-request.json> --source-root <retained-x64-zt-root> --output <new-output-directory>
```

Input files have a 2 MiB read bound; generated sources have an 8 MiB total bound.
Validation completes before directory creation. Source files, hashes, local
paths and explicit unconverted dependencies are recorded in the local report.
Native templates, clips and reports with machine paths remain ignored/local.
Nothing is copied to stock, the live SDK, a mod package or the owner client.

## Verification and next concrete step

On 2026-10-12, all **11 Python checks passed**. They verify real displaced slot
indices from the pinned source, the exceptional enum name, independent hand
templates, exact clip strings, preservation of template fields, clearing empty
common slots, refusal of ambiguous/unmapped/invalid inputs, and write/read JSON
roundtrip with refusal to overwrite. The slot contract was reproduced from the
actual retained source and matched exactly. The CLI compares that reproduction
before conversion and refuses a mismatch; no native source was modified.

This roundtrip uses Python JSON and a validator derived from the pinned C++
schema. The existing C++ `weapon_anim_package::parse`/`dump` routines were read
but **not executed**: running them would require the prohibited native build or
execution. No FF, rig playback, notetrack delivery, real weapon import or game
acceptance is claimed. No real animpkg template was found in the bounded retained
runtime lookup, so a real-template conversion was not attempted.

The next useful input is one actual retained IW7 animpkg plus its provenance,
and one H1 weapon JSON whose populated slots fit the exact mapping. Apply this
converter to those inputs only after inspecting the template. In parallel, the
animation owner must supply a genuinely converted clip bound to the intended
viewmodel/hand skeleton, and the material owner must prove its normal render
path. Only their resolved outputs justify a native package/weapon build and
subsequent protected runtime tests. This tranche adds no native conversion hook,
downloads, extraction, game/stock copy, upstream poll or resource lease.

The parent owns global docs, PR/exact-head CI/merge and native-test scheduling.
The earlier packed-frame review and full-tool candidate remain intact.
