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

The checker reads at most 64 KiB per JSON using a bounded read before decoding,
rejects duplicate keys, and writes only a report to stdout. A future local
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

The initial October 14 source check passes 12 new metadata tests and the 11
unchanged weapon-reference tests. Reproducing the existing slot contract from
the retained source matches all 260 IW7 entries. Product ownership and whitespace
checks pass. The default report has no donor references and 15 explicit metadata
gaps. These checks involve no native compiler, retail payload, FF or game.

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

Runtime acceptance belongs to a later protected session: correct FP/TP and
muzzle placement, idle/fire/reload, ammo and reserves, actual projectile hit and
splash/FX/audio, real PAP transaction and conservation, melee/offhand retention
and the selected maps. A static rendered prop satisfies none of those weapon
acceptances.
