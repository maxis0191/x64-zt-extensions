# Standard BO3 Ray Gun: smallest source route

Target the standard Ray Gun and its Pack-a-Punch counterpart first. Mk II/Mk III
are outside this selection. This route changes no loader, exporter, serializer,
probe, launcher or game configuration.

## Names that can guide the next selection

[A BO3 mod's weapon table at commit 5d45cb9](https://github.com/Kishkumen32/black-ops-3-mod-tools/blob/5d45cb9b36b2930456b5f05f25443e0e0c864fd2/mods/zm_classic/gamedata/weapons/zm/zm_levelcommon_weapons.csv#L8)
maps `ray_gun` to `ray_gun_upgraded`. The 4891-byte table has SHA-256
`74b3ee9093d9614da78d14011556779114b5e0fcc86f07f277415fc38a25fdbe`.
It is a primary source for that mod's configuration, not official Treyarch data
or proof that either asset is available in the owner's loaded database.
Older T6 names ending `_zm` must not be substituted as BO3 identities.

| Dependency | Current useful identity | Qualification |
| --- | --- | --- |
| Base / PAP weapon names | ray_gun / ray_gun_upgraded | Textual candidates only |
| First-/third-person models and hand model | Unknown | No role/name binding observed |
| Skeleton/tags/influences | Unknown for Ray Gun | Platform root and authored rig are different donors |
| Idle/fire/ADS/reload clips and notetracks | Unknown | No Ray Gun clip observed |
| Materials/images/FX/sounds | Unknown for Ray Gun | Existing platform bindings are not weapon bindings |
| WeaponDef fields and projectile parameters | Unknown for BO3 Ray Gun | No T7-to-IW7 definition cast is justified |

The checked F10 catalogue and E5 export contain a Freerun platform, not a weapon.
Their small text pointers were shared with the rig owner: E5 manifest
2857/d44e799f..., E5 outer receipt 37038/b21394df..., and catalogue
1669/d27e34f0.... The platform has one root/bone, five surfaces and no verified
weapon role. The historical locator is IW7 RE, not an attested BO3 Ray Gun rig.
Identifier `RE46614578` has no attested path and is not used as evidence.

## Small local closure candidate, without claiming asset ownership

Immediate filename/length metadata of the owner's existing BO3 zone directory
was inspected on 2026-10-14. No file body or game hash was read in this work.

| Existing filename | Bytes |
| --- | ---: |
| zm_common.ff | 36332480 |
| en_zm_common.ff | 148160 |
| zm_common.xpak | 786432 |
| zm_common_d.xpak | 131072 |
| zm_initial.xpak | 1272184832 |

These are a candidate Zombies closure to assess using the existing qualified
bootstrap and finite name-observation route. They are not an asset-to-zone or
asset-to-provider map. Do not read the full XPAK, clone the game, assume this
closure loads, or claim that `zm_common.ff` supplies Ray Gun. If an admitted
targeted load cannot resolve the two candidate names, preserve the refusal
and select the next dependency from its actual evidence. There is no new load
or extraction authorization in this document.

## Reuse the converters; fill the selected-asset gap

At native pin `fab935826c898806855376662a8a03317b3ad8f1`, the
[T7-to-IW7 dispatcher](https://github.com/maxis0191/x64-zt/blob/fab935826c898806855376662a8a03317b3ad8f1/src/zonetool/zonetool/t7/zonetool.cpp#L156-L190)
has XModel, XModelMesh and XAnim conversion, but no WeaponDef conversion.
The [model converter](https://github.com/maxis0191/x64-zt/blob/fab935826c898806855376662a8a03317b3ad8f1/src/zonetool/zonetool/t7/converter/iw7/assets/xmodel.cpp)
already transfers bone names/parents and converts tag rotations/positions.
The [mesh converter](https://github.com/maxis0191/x64-zt/blob/fab935826c898806855376662a8a03317b3ad8f1/src/zonetool/zonetool/t7/converter/iw7/assets/xmodel_mesh.cpp)
contains `GenerateIW7BlendVerts` and a streamed skin-weight path. These are
reusable source implementations, not a measured Ray Gun rig/weight conversion.

The current [selected streamed pilot](t7_iw7_streamed_model.hpp) requires one
bone/root, no cosmetic bones, zero skin vertices and rigid surfaces. It cannot
admit a selected multi-bone/skinned weapon. Once a real model is identified,
the smallest missing export primitive is a bounded selection/copy/recheck of
that model's actual bones, tags, parents, bind transforms and surface influences,
feeding the existing converters. Counts and roles must come from that model;
do not remove the pilot's guards or replace weights with a root fallback.

## Concrete next sequence and ownership

1. Under a separate coordinator slot/GO, reuse the existing registration/name
   route against the assessed Zombies closure for the two exact candidate weapon
   names. The [unused name module](WEAPON-NAMES-OBSERVATION.md) has an eight-call
   cap, remains unwired and does not promise to encounter Ray Gun. Do not treat
   its overflow or absence as a donor inventory, nor increase its budget silently.
2. Establish the view/world/hand and clip bindings from an admissible primary
   weapon definition or legitimate authoring data before selecting those models.
   The naming convention alone is not a binding. Export one named model/LOD and
   required clips through the existing converters after the selected-asset gap
   above is qualified. Rig owner 5739 owns this implementation and its separate
   Ray Gun directory; this RE route does not patch those files.
3. Native owner 62 owns explicit IW7 weapon authoring from a qualified IW7
   template: distinct base/PAP definitions, rig/animation package, muzzle/effect
   bindings and typed projectile/impact/damage parameters. Reuse normal engine
   projectile and Pack-a-Punch paths. BO3 stats, FX and timings remain unknown
   until observed; no foreign WeaponDef reinterpretation or gameplay claim.
4. Image owners 51/5d qualify one selected image header after provenance, then
   use the existing exact-key, finite-provider, whole-object XPAK reader and
   typed DDS/readback path. F2 region metadata alone supplies no dimensions,
   format namespace, key64 or cumulative part-size delta. No pointer mask or
   guessed image key is part of this weapon route.

This is a source selection route, not a delivered gun. It requires subsequent
qualified donor observation/export, IW7 link/readback, protected first-/third-
person equip/fire/ADS/reload, PAP transition and projectile/impact checks.
Owner gameplay acceptance remains separate. No new runtime execution occurred.
