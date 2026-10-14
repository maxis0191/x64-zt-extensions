# Ray Gun BO3: model, rig and animation source handoff

The objective is a usable first/third-person Ray Gun with real clips, projectile
behavior and Pack-a-Punch. This initial source tranche has **no observed BO3
Ray Gun asset identity**. The tracked plan keeps all donor entries null.
`sdk_raygun_zm` and `sdk_raygun_pap_zm` are proposed private IW7 IDs, not BO3 names
or already registered weapons. Native62 owns their final coordination.

Animation owns view/world/hands model references, skeleton/tag/influence
metadata and idle/fire/reload clip bindings. Native62 owns weapon definitions,
projectiles and PAP lifecycle; materials5d owns authentic textures, materials,
FX/audio; serializer51 owns native serialization and its API. No shared weapon
converter, frozen original rig or generated source package is changed here.

## Known sources and exact recipient roles

The retained ZoneTool source pin is
`fab935826c898806855376662a8a03317b3ad8f1`. Its
`src/zonetool/zonetool/iw7/assets/weapondef.cpp:260-286` parses
`weapDef.gunXModel`, `worldModel`, `handXModel` and the three separate
`szXAnims`, `szXAnimsRightHanded`, `szXAnimsLeftHanded` package references.
The receiver slots are checked against the existing exact 260-entry
[weapon slot contract](../../../weapon/slot-contract.json):

| Role | IW7 symbol | Index |
| --- | --- | ---: |
| idle / empty idle | WEAP_ANIM_IDLE / WEAP_ANIM_EMPTY_IDLE | 107 / 108 |
| fire / ADS fire | WEAP_ANIM_FIRE / WEAP_ANIM_ADS_FIRE | 109 / 207 |
| reload / empty reload | WEAP_ANIM_RELOAD / WEAP_ANIM_RELOAD_EMPTY | 171 / 172 |
| raise / drop | WEAP_ANIM_RAISE / WEAP_ANIM_DROP | 179 / 182 |
| ADS up / down | WEAP_ANIM_ADS_UP / WEAP_ANIM_ADS_DOWN | 249 / 250 |

These are recipient reference slots, **not a T7 slot conversion**. No BO3 clip
name or timing is inferred from a matching word. `tag_flash` is the proposed
IW7 muzzle-role expectation, not an observed BO3 tag or a validated attachment.
Handedness, hands compatibility and third-person animation routing remain open.

The exact weapon-name shortlist is `ray_gun` -> `ray_gun_upgraded`, from row8 of
a [pinned third-party BO3 mod table](https://github.com/Kishkumen32/black-ops-3-mod-tools/blob/5d45cb9b36b2930456b5f05f25443e0e0c864fd2/mods/zm_classic/gamedata/weapons/zm/zm_levelcommon_weapons.csv#L8),
commit `5d45cb9b36b2930456b5f05f25443e0e0c864fd2`. This is primary source for that
mod, not official retail metadata or our runtime inventory. No `_zm` suffix,
model, material, tag or clip identity is derived from it. Candidates are kept
separate from observed asset declarations and cannot be marked runtime-observed.

The visible `p7_fre_platform_cap_02` MP Freerun platform and the original
`paris_doom_skin_two_bone_first_a` / `second_a` rig are comparison artifacts,
not Ray Gun donors. The RE46614578/Link workstream is a requested pointer to
retained evidence; its label alone proves no weapon/model/clip association.
No locator result substitutes for resolved bone names, hierarchy, binds or weights.

## Bounded metadata check

```powershell
python -B tools-source/asset-bridge/animation/rig/raygun/source_handoff.py
python -B -m unittest discover -s tools-source/asset-bridge/animation/rig/raygun -v
```

The checker reuses the reviewed `image_metadata_consumer.read_report` and
`strict_json` IO boundary, without calling its image consumer/schema. Requests
are limited to 32 KiB; the fixed existing 36,853-byte slot contract alone uses
an explicit 64 KiB bound. Lexical Windows/suffix, ordinary file/size and reparse
checks precede open, and opened handle identity/size checks precede bounded read.
Duplicate keys and nonfinite JSON are refused. It writes only a report to stdout. A future local
`--request` may declare exact observed asset names and receipt references.
Each evidence entry contains `source_kind: retained-bo3-metadata`, a lowercase
receipt SHA-256 and the observed source field. Model entries contain `name`,
`evidence_ref`, and `bone_names` (null until decoded); clip entries use
`channel_names`; tags contain `source_name` and `evidence_ref`.

The checker checks only declarations. It does not open or hash referenced
receipts, resolve assets, dereference pointers, read payloads or independently
verify provenance. Name arrays have a finite profile bound of 512, not a claimed
engine limit. Clips need exact channel membership in declared view/hands names;
tags need exact membership in the corresponding model names. Missing metadata
remains a gap. Even a complete declaration cannot qualify hierarchy, bind,
influences, clip cadence/notetracks, native payload, textures, rendering,
weapon/PAP/projectile behavior or ready. Synthetic tests establish only these
metadata refusal boundaries.

The initial October 14 source check passes 14 new metadata tests and the 11
unchanged weapon-reference tests. Reproducing the existing slot contract from
the retained source matches all 260 IW7 entries. Product ownership and whitespace
checks pass. The default report has no donor references and 15 explicit metadata
gaps. These checks involve no native compiler, retail payload, FF or game.

Independent review refused initial head `0fc0840`: the old reader opened input
before checking that it was an ordinary bounded JSON file. The correction reuses
the merged PR122 IO functions instead of adding another reader. Its 21 handoff
tests, 29 shared-IO tests and 11 weapon-reference tests pass. Causal spies show
the old head opens and reads all four exe/ADS/device/oversize cases; the corrected
reader opens and reads none. Replaced handle identity/size is refused before
reading, and growth is bounded before parsing. All fixtures are original source
data; no actual opaque file or referenced receipt is read by these tests.

## Next source evidence and separate heavy proposal

First obtain the small retained RE/51 receipt and exact observed BO3 weapon,
view/world model, material/image and idle/fire/reload names. Bind their roles
through actual weapon metadata; do not guess `wpn_*`, zones, tags or offsets.
Texture ownership/provenance and rig metadata precede any new weapon FF.

If the retained evidence still has no weapon names, the next proposed heavy
operation is one finite observation through the reviewed existing T7 caller,
after Root chooses the proven loading scope. The existing unused
[weapon-name observer](../../../t7-iw7/WEAPON-NAMES-OBSERVATION.md) caps observation
at eight Weapon/WeaponDef/Variant/Full calls and bounded text. Its loading route
and source cohort must first be qualified by RE/51. It is not currently wired,
and the Freerun catalogue is not chosen as a weapon-loading route.

Only after actual names/roles are bound should Root consider a separately
admitted selected model/texture/rig capture, followed by independent readback.
The [animated preflight](../../../t7-iw7/animated/README.md) documents unresolved
weight ordering, bind/stride, clip counter, channel, notify and schedule losses;
its original fixtures do not qualify a real Ray Gun. No complete donor copy,
new zone load, extraction, CPP/FF or game is authorized by this source plan.

There is also a concrete selected-export gap: the current
`t7_iw7_streamed_model.hpp:76-77` requires one bone/root and no cosmetic bones;
`:101-103` refuses `XSURFACE_FLAG_SKINNED`. Reusing that rigid profile for a
weighted/animated weapon requires separate reviewed support and a real donor
observation, not relaxed guards or an assumption that every weapon must have
multiple bones. The general T7 converter's existence does not close this gap.

Runtime acceptance belongs to a later protected session: correct FP/TP and
muzzle placement, idle/fire/reload, ammo and reserves, actual projectile hit and
splash/FX/audio, real PAP transaction and conservation, melee/offhand retention
and the selected maps. A static rendered prop satisfies none of those weapon
acceptances.
