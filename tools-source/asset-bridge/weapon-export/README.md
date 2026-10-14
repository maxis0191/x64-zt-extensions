# Bounded IW7 player/PAP source export support

2026-10-14: inactive source support. No native compilation or export has run.

`native_player_templates.inc` adds one support function to the IW7 owner-fork
ZoneTool source pinned at `fab935826c898806855376662a8a03317b3ad8f1`. It uses the
existing shared/map load, exact registered database lookup and full native
weapon/attachment serializers. It introduces no engine hook, binary schema,
stdin route, NativeJob or resource API. The CLI/build owner must wire an explicit
opt-in call separately; this module has no call-site or default activation.

The one allowlisted pair is `iw7_shredder_zm` / `shredderpap1` on `cp_zmb`.
These are player/PAP references in retained retail GSC at pin
`1dd48a78e55ef9c99519fc5221a206168ce2e98a`: `utility.gsc:4193-4195` and
`cp_zmb.gsc:109`. This is evidence for a source candidate. It does not establish
the complete JSON, numeric projectile fields, native PAP flag or actual reload.
No NPC weapon, normalised PAP name or invented alias is substituted.

The future caller supplies exactly two strict CSV rows, in either order, LF or
CRLF, optionally with a final newline:

```csv
weapon,iw7_shredder_zm
attachment,shredderpap1
```

Input reads stop at 257 bytes and refuse oversize before decoding. The module
requires non-null, non-default, exact database names. It checks native primary
projectile/class/clip/ammunition/damage/speed/lifetime and FP/TP/animation-package
pointer fields; it refuses a PAP without its native projectile/PAP fields.
Each of the six attachment arrays is limited to 64 entries. The exact PAP
registration must occur once, with a same-name different registration refused.
These checks can refuse this candidate. GSC's `is_pap_attachment` substring
check is not a substitute for the native `papAttachment` boolean.

Only after compatibility checks does it create a fresh ordinary
`dump/paris_enemy_cp_zmb_<token>_player_weapon_source` directory. It invokes the
existing serializers for one complete weapon and one attachment, reads each
result with a 2 MiB + 1 bound, checks JSON identities, records sizes/hashes, and
writes/readbacks a manifest bounded to 16 KiB. It changes no authored weapon
field. Source templates and generated JSON stay private and ignored.

```powershell
python -B tools-source/asset-bridge/weapon-export/prepare_module.py `
  --native-source-root <retained-exact-fab935-source> `
  --output <fresh-absolute-source-directory>
```

The preparation operation reads/writes bounded source text only. It checks the
normalised original IW7 file hash, inserts inactive support into a new source
copy and records hashes. It neither changes the retained dependency in place
nor wires the shared CLI/build recipe. `module-source.json` keeps `cli_wired`,
`compiled`, `native_export_executed`, `full_templates_observed` and `ready` false.
Native CPP, schema/runtime behavior and the paired export remain unmeasured.
Eight Python preparation tests cover drift, insertion cardinality, unchanged
entry code, cap growth, newline handling, real source writes and path/overwrite
refusals. They do not execute this C++ function or a native serializer.

The complete authoring consumer is private `iw7-mod-components` PR30, merge
`a5f76a38e1fe9363b08700a7ff51b2a8417571a2`,
`ops/raygun/prepare_weapon.py`. Authentic BO3 model/texture/animation/FX/audio
assets remain separate. A Shredder-derived definition is an IW7 prototype.

Before actual export, require a reviewed CLI integration and compiled candidate,
a new valid identity-bound stock receipt, a fresh original physical NoExit host,
the existing H1 original context/job/guards/lease, bounded whole output and exact
closed readback/closure. The former 72-input stock manifest points to the owner-
removed Doom root and cannot launch; preserve it unchanged. M7 material proof
and its frozen wrappers are not a weapon capsule. No stock, PE/assembly read,
FF, native compile or game is authorized by this source preparation operation.

PAP machine completion also requires a custom family/key and attachment mapping.
Retail `getrawbaseweaponname` does not strip `sdk_`; the private
`sdk_raygun_zm` key needs a real `level.pap`/maximum callback and attachment-map
registration. `pap_used` occurs before pickup. Measure payment, pickup/grant,
ammunition, the player's tier increment and `weapon_level_changed`; a direct
upgraded grant cannot qualify the transaction. No EE/fuse/DC bypass is supplied.
