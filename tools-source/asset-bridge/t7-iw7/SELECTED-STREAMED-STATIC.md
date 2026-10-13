# Selected streamed static model

The explicit option is `-t7-iw7-model-streamed-v1 <zone> <model> <lod> <flat-request.json>`.
It preserves resident v1/v2 refusal and the lock on the legacy global XPAK cache.
Request schema: `iw7.t7-iw7-selected-streamed-request/1`; export schema:
`iw7.t7-iw7-selected-streamed-export/1`; geometry profile:
`t7-iw7-selected-streamed-static-v1`.

The request binds a lower-case 16-digit hexadecimal key and one to eight exact
private `zone/<token>.xpak` paths with retained Windows identities and lengths.
The reader requires one key match across every admitted hash table, at most
8 MiB declared index data, a 256 KiB encoded extent, raw/LZ4 commands and exactly
18,624 decoded bytes. Views retain original read handles. Descriptor tail words
remain opaque.

The selector requires raw flags9 and the observed key. Model/mesh/shared/surface/
rigid headers are captured and rechecked; this proves no atomic snapshot or
engine allocation pin. Only an allocated CPU view changes storage routing to
flags8 and clears copied surface stream bits. Engine objects remain untouched.
The payload and caller allocator must survive synchronous conversion/dump;
the DB remains required for borrowed bone/material metadata. Selection is
noncopyable and movable. Existing rigid-root, ordered-surface, stream-range,
finite-value, triangle and 16 MiB logical geometry checks are reused.

The manifest preserves raw flags, source surface flags, exact key, opaque words,
package identity, offsets/extents/commands and decoded payload digest. Materials
remain unresolved; dependency payloads, IO fidelity, runtime and readiness stay
false. The independent byte reader and Model Lab use the existing multisurface
serialization grammar with this distinct origin. Material replacement uses
explicit ordered source-to-IW7 bindings, with no BO3 appearance claim.

## Evidence on 2026-10-13

Closed E2 observed `p7_fre_platform_cap_02`, LOD0 in `mp_freerun_04`: key
`f58d58f1fc9b6b01`, five surfaces, 560 vertices, 490 triangles. Declared ranges:
indices [0,2940), positions [2944,9664), attributes [9664,18624). These are
header observations, not decoded geometry.

Material slot0 refused a readable-range guard after five names. PR18's updated
helper is explicitly adopted for this fresh source epoch: failure stages and
partial textures preserve all full-result/pixel gates false on refusal. Its
changed synthetic native fixture passed50; E2/old helper bytes remain frozen.

The key is absent from eight checked map/core Hash24 tables, three checked
base/initial/base_patch containers and eight selected TU32–TU24 patch tables.
Other Index sections have not been interpreted as Hash24 or payload routes.
No executable request is manufactured from a missing match. A proven provider
or key/layout correction is required before retail export. No payload, FF or
gameplay result exists.

Source checks cover exact keys/identities, malformed provenance, version mixing,
serialized two-surface readback and Model Lab derivation. Native compilation,
the move/copy static assertions and real conversion remain separate gates.

## Build preparation

`prepare_build.py --selected-streamed-static-v1` selects a separate transition
table and marker. Legacy128 and E2/v2144 bindings remain unchanged. This epoch
has149 bindings (143 text/six opaque), 1,146 inputs and the same66-header proof.
CLI source may exceed64KiB only under the explicit marker, below128KiB, with
exact source and transition pins. DEFAULT loads no native types, hashes no
opaque inputs, acquires no reservation and creates no run root. Run needs its
own coordinator slot and exact fresh committed package/plan.

Preserved corrections: duplicate mutex include initially refused the unique
publication anchor; only the rendered duplicate was removed. Omitted streamed
base-verification selection refused preparation before output. The old64KiB
CLI bound refused the new TU; the larger cap is marker-specific. A plan replay
after runner edits correctly refused its bootstrap pin. Fresh plans preserve
all earlier records. The targeted RE review also found implicit selection copy
could leave the CPU pointer on the old buffer; copy is deleted, move explicit,
and allocator/DB lifetime documented. The current CLI never copied selection;
no corresponding crash was observed.
