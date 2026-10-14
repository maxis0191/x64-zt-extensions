# Explicit selected image-parts metadata CLI

The successful E5 geometry export still used G2's five-argument `observe`.
All seven image headers were unread; binding 0 refused and 1..6 were not
attempted. Binding 4/nameHash `0xA0AB1041`/usage 1 is a diffuse classification
lead, not a 64-bit package key or acquired texture.

The explicit candidate command is:

```text
-t7-iw7-material-parts-v1 mp_freerun_04 p7_fre_platform_cap_02 0
```

It reuses the existing resident zone loader, denies legacy helper-XPAK reads,
finds the exact nondefault model and requests material slot 0, image binding 4
with its expected hash. It prints `T7_SELECTED_MATERIAL_PARTS_METADATA` schema3
from the separately versioned G3 helper, then exits. It selects no geometry,
opens no package, copies no pixels, emits no model/FF and does not guess a
provider. Refusals preserve the diagnostic and exit nonzero. A successful
metadata result must preserve false pixels/Ready and true header rechecks.
G3 omits `refused` on success. The caller accepts its absence or boolean false,
requires a boolean when present, and prints a boolean true refusal before
exiting nonzero. The first caller incorrectly required the field on success;
peer review caught this before native compilation or observation.

`prepare_material_parts.py` applies one finite transition after the existing E5
publication factory; the G3 module is inlined after the unchanged G2 observer.
Default `prepare_cli`, `native_cli`, G2/schema1/2, frozen C/C2 and prepatch V2
factories remain unchanged. The native mode is exclusive, exact five-argument
ASCII input; it cannot silently activate from a model name, surface count or
unrequested flag. No second observer or alternate launcher is introduced.

Preparation selects `--material-parts-v1` with the existing explicit
`--catalog-message-publication --selected-streamed-render-only-v2` source
family and both retained compilation proofs. This reuses the established
two-TU main/CLI plus link group, sealed E7 inputs, 66-header context and original
job/closure policy. It does not relax legacy binding limits or compile a new
full tool tree. The new source profile has 154 bindings (148 text/six opaque);
its 1,146 sealed native inputs remain unchanged. Binary qualification and
actual CPP/probe require the coordinator's separate group admission.

The fixed old E5 main is 43,254 bytes/`5aef1fad`; CLI 112,377/`c63d9552`.
The declared G3 source transition produces main 43,366 bytes/`031464d8` and
CLI 124,224/`0dd4b3be`, below the existing 128-KiB cap. Full source hashes are
in `material-parts-source-contract.json`; the runner binds its finite marker,
source pins and exact prepared outputs before any opaque input is opened.
The old G2 header remains 18,583 bytes/`a8848a92`.

The first actual source preparation (source `51f906b0`, capsule
`t7-material-parts-cli-source-a`, 2026-10-14 06:07 UTC) refused at the existing
256-KiB aggregate output cap. Python exited 1; its owned child closed and the
Analysis lease was released. No plan, DEFAULT, CPP, candidate or stock operation
ran. Its capsule, wrapper and refusal receipt remain unchanged. The corrected
caller plus the retained E5 response/header sizes total 263,522 bytes, which
exceeds 262,144. Only the explicitly selected, pinned parts transition now gets
a 288-KiB aggregate authored-source cap. Other profiles retain 256 KiB; the
2-MiB plan cap, individual source/header/read/geometry limits and resource
admission policy are unchanged. Source regression proves both caps and the
real generated transition. A fresh actual plan/DEFAULT is still pending.

G3 uses two bounded owned 264-byte header copies approved by G2's existing
Readable guard. It rejects extra/ambiguous captures, differing addresses or
bytes, mismatched G2 metadata and any unqualified selected header/name/recheck.
It publishes four physical stream descriptors, their packed scalars, dimensions,
canonical hexadecimal keys and uninterpreted descriptor words. A declared
count beyond four remains inadmissible; no out-of-header read is performed.
The native format word and low byte are diagnostic values, not a runtime width
qualification. No atomic snapshot, retained allocation, pixel or appearance
claim is made.

Source checks cover the real finite renderer/selection and actual PowerShell
guard with authored metadata: malformed/mixed selections, changed base source,
G2 drift, missing proof and arbitrary output/source pins refuse. The initial
authored guard fixture refused because PowerShell culturally sorts the fixture
filename before the header filename; the expected inventory was corrected.
This did not execute a native child or read an asset. G3's separate native
fixture passed 32 actual native checks in the separately admitted H32 group
on 2026-10-14. The caller's native compilation and stock metadata observation
remain pending. The success/refusal predicate regression evaluates the actual
caller source with authored JSON; it does not claim C++ execution.

The accepted geometry FF B (`50ca9124`, 9,904 bytes), plan `750d25d7`, corrected
readback `7f8b628f` and first static-display cohort remain immutable. Next:
review/merge source, qualify the one admitted incremental CPP group and G3
fixture, then perform one separately admitted metadata observation. Only a
real 64-bit part key, exact decoded size and provider identity can select a
future bounded image read; `nameHash`32 and the geometry key are not substitutes.
