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

The key was absent from the first map/core, base/initial/base_patch and selected
TU patch scopes. The later bounded metadata discovery found it exactly once
among 203 admitted package tables: `zone/mp_initial.xpak`, 654,311,424 bytes,
HashCount1,298 and HashSize31,152. The selected encoded extent is [146723456,
146731136), 7,680 bytes. Other Index sections were not reinterpreted as Hash24.
This identifies a provider and permits a real one-package request; native
rechecking and decoding remain required. No payload, FF or gameplay is proved.

Source checks cover exact keys/identities, malformed provenance, version mixing,
serialized two-surface readback and Model Lab derivation. The native E3 build
of source `e345195` passed: main/CLI/link exit0 with input revalidation, original
job closure and reservation release. Candidate21,916,160 bytes SHA256
`2de24e4a715d92cebe767073f212241319c85bd7a5863201f1eaf9da39f9ff7d`.
The C++ move/copy assertions compiled. Its original host exited0, and the owned
hosts/stages were absent afterward. At this build checkpoint the candidate had
not run; the later stock result is recorded below.

## Actual stock refusal and diagnostic source on 2026-10-14

The one authorized E3 stock invocation exited1 after 5.88 seconds. It refused
`selected streamed rigid coverage differs` before `read_selected_key`, with no
manifest, XMB or XSB. Input and selected-provider metadata rechecks, owned job
closure and lease release passed; the original host actually exited1 and was
absent afterward. No selected payload read or decompression was reached by this
control flow. The compiled `e345195`/reader457/candidate2de tuple remains frozen.

The refusal combines five checks: root bone offset, full vertex coverage,
zero triangle offset, full triangle coverage and no collision tree. The stock
log did not contain their actual values, so no one field is established as the
cause. The new source reports the failing surface index, the captured rigid
values, expected surface vertex/triangle counts and collision-tree presence.
The condition and its position before payload access are unchanged. Values
come from the already captured header; no pointer address or extra dereference
is added. This source has not yet been compiled or used on stock.

The pinned ZoneTool type declares four 16-bit fields followed by a collision
tree pointer. That is a source layout, not runtime ABI proof. Greyhound's
[BO3 surface declaration](https://github.com/Scobalula/Greyhound/blob/22c3d17f7428573042b56f43af0ed2585989bebd/src/WraithXCOD/WraithXCOD/DBGameAssets.h#L849-L864)
leaves the corresponding tail opaque, and its
[simple root-weight fallback](https://github.com/Scobalula/Greyhound/blob/22c3d17f7428573042b56f43af0ed2585989bebd/src/WraithXCOD/WraithXCOD/GameBlackOps3.cpp#L817-L821)
does not verify the retail rigid-list layout or coverage. The next useful native
observation is the detailed refusal on the same selected donor; no guard is
relaxed and no geometry or ModelFF result is inferred.

Source validation passed296 Python tests with five optional skips and454
PowerShell build/profile checks. Fresh preparation and DEFAULT confirmed149
bindings (143 text/six opaque), 1,146 inputs and66 headers/87,204 bytes, without
native types, opaque-input hashes, lease or run-root creation. The PS synthetic
streamed transition initially retained the earlier CLI tuple and was correctly
refused; its exact new tuple was updated. Legacy transition tables are unchanged.

## Explicit qualified source cohort on 2026-10-14

The next source preparation adopts reader18512/SHA53265601 from the offline
CLI batchB qualification: 13 copy cases,46 refusals, one Windows sealing case,
42 options/containment cases, CLI compilation and help all passed. Its one
real selected extraction decoded7,680 bytes with LZ4 opcode3 into18,624 owned
bytes. This is a packet-reader result, not a rigid conversion or engine ABI
result. The generic public API permits1..256KiB; the selected streamed engine
wrapper still requires exactly18,624 bytes before any read.

The same future source cohort explicitly adopts PR23's MaterialE helper
(16489 bytes/SHA0ea84735) and fixture (13721 bytes/SHAcb27d4df), after its63
native synthetic cases passed. It retains copied binding scalars before image
dereferences and distinguishes refused from unvisited image rows. No retail
image name, format or pixels were qualified by those synthetic cases.

The source contract, rendered patch and streamed-only transition/runner pins
are recalculated together with the already merged rigid refusal diagnostic.
Neither engine CLI logic nor geometry guards change in this compatibility
commit. Legacy128/E2-v2144 tables, dependencies and archive stay unchanged;
the old E3 compiled packages and receipts retain reader457 and MaterialD50.
This new combined translation unit still needs its own native build and stock
observation before the detailed rigid refusal can identify the failing field.

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
