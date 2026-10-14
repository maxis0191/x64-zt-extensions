# Selected image-field provenance source

This is a separate source-only instrumentation interface, approved after the
closed G3 image-header refusal and full Find/IsDefault interpretation. It does
not change or replay source E/F, the old G3 adapter, its receipt, or the IMAGE
registration bypass. It observes the same mp_freerun_04 /
p7_fre_platform_cap_02 / LOD 0 / material slot 0 / binding 4 / nameHash32
0xA0AB1041. The binding hash is not an image name or a stream key.

The opt-in source renderer accepts only the exact retained E5 main/CLI pair.
It emits the distinct flag and schema below, with exclusive ASCII arguments:

    -t7-iw7-image-provenance-v1 mp_freerun_04 p7_fre_platform_cap_02 0
    iw7.t7-selected-image-provenance/1

The existing IMAGE early return is byte-identical. For other types the wrapper
calls the original add exactly once and forwards its exact HEADER return;
original exceptions propagate. Only its own observation refusals are contained.
H_in is recorded as a scalar; it is never treated as the returned header or read
as an entry. No +8 adjustment is applied to H_return. With the mode inactive,
the callback immediately returns without source reads or memory queries.

Epoch A selects the field on the exact MODEL returned after the original add.
Epoch B uses the existing MODEL Find/IsDefault path after the fresh zone load.
No IMAGE lookup, new engine call, original registration policy change or image
pointer repair is introduced. Header/material/table/field addresses remain
separate, with phase, ordinal and thread metadata. HeaderChanged is recorded
only when both associations are bound; missing associations yield null
comparison fields and an explicit refusal. Equal addresses never establish
object identity or allocation lifetime.

The callback searches at most 1024 MODEL returns using the existing 64-KiB
reader budget. Each selected epoch has its own 64-KiB metadata-read budget,
bounded LOD/material/texture counts, exact binding hash and rechecks of its
copied model/table/material/binding. A mutex protects publication and final
serialization; activation and callback-error flags are atomic. The callback
does not hold its mutex while invoking the original engine add, and performs
no engine call while holding it. Duplicate target registrations, search errors,
missing associations, changed copied headers and malformed query ranges refuse.

The selected field's 264-byte address span is queried with VirtualQuery only.
At most two regions publish raw State/Protect/Type, allocation base and extent.
No byte of a GfxImage body, pixel payload or stream descriptor is copied.
Readable-at-query describes those memory metadata observations; it is not
permission to read an image or a retention/atomicity claim. The report retains
false image-header-read/body-admitted/pixels/lifetime/retention/G3-admission-
change/readiness flags and zero image-body/payload-byte counts.

The native fixture is authored to execute the real original-return forwarder
and observer with synthetic ranges/query records. It contrasts the old image
read refusal with a provenance observation that never reads the body, and covers
different incoming/returned/lookup headers, missing/duplicate registration,
original errors, search refusal, wrong binding, malformed query coverage,
same-address memory-state transitions and both callback-count/name-read budgets.
It has NOT been compiled or executed: CPP requires a separate coordinator GO.
Source checks execute the renderer and actual fixed/exclusive predicates, reject
wrong source epochs/pins and verify the old G3 output pair remains exact.

The first source test incorrectly banned JSON's .dump() along with asset
dumping. Its rule now targets namespace asset dump calls. Source review also
bounded serialization of an invalid region count; its native refusal case is
retained in the unexecuted fixture. Neither correction came from a native run.

This module currently provides a source overlay API, pinned source/output
contract, standalone fixture and typed native entry. It is not integrated into
the admitted build producer, operational recipient or owner launcher. Those
must consume a reviewed fresh source cohort and measured CPP result explicitly;
no old MaterialParts candidate/plan can be relabeled as this operation. Next:
independent source review, admitted fixture/CPP qualification, then the separate
consumer/operational plan and native GO. Authentic textures and the cause of F's
unreadable image header remain unqualified.
