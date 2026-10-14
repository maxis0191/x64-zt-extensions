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
The corrected H fixture has now compiled and executed 53 checks under a
separate coordinator GO; the bounded qualification is recorded below.
Source checks execute the renderer and actual fixed/exclusive predicates, reject
wrong source epochs/pins and verify the old G3 output pair remains exact.

The first source test incorrectly banned JSON's .dump() along with asset
dumping. Its rule now targets namespace asset dump calls. Source review also
bounded serialization of an invalid region count; its native refusal case is
retained in the fixture and passed in H. Neither correction originally came
from a native run.

Independent architecture review then found a refusal-publication race in the
first committed callback: its outer catch published only after releasing the
mutex. The corrected inner catch publishes while the same mutex is still held;
only failed lock acquisition reaches the outer catch. The authored causal
fixture pauses publication with a condition_variable. Its old-placement control
uses the real observer/finish to reproduce a positive result during the gap;
the corrected path owns the finish mutex through publication and then refuses.
There are no sleeps. Test access and its pause seam are preprocessor-only and
absent from the operational build. Its actual admitted CPP checks passed in H.

The first admitted fixture compilation, retained capsule F, failed with
compiler exit 2 before running any assertion. MSVC `/W4 /WX` diagnosed C4459:
the `stop` parameter named `publication` hid the global publication gate. Only
that parameter and its reference were renamed `publication_mutex`; `/WX`
remains enabled. The fixture source pin changes, while the observer, native
entry and generated operational main/CLI pair remain unchanged. The failed
compile receipt, stdout, original-host exit 1 and fresh empty process/lease
closure are retained. This correction used a fresh immutable source cohort,
reviewed additive capsule and separate CPP GO; F itself is not a 53-check pass.

The next admitted G compilation also exited 2 before any assertion: C4702
diagnosed the always-throwing authored original callback's template instance
as unreachable after the call. The fixture now takes that error branch through
a runtime atomic boolean and retains a reachable return branch. The error is
still deterministically exercised; the real forwarder, observer and /W4 /WX
remain unchanged. G's failed receipt and known original-host/job/lease closure
are retained. H used a fresh fixture source pin and reviewed capsule.

On 2026-10-14 H compiled source commit
`678bf7dde6a99207654256c1e53ebaaec286ffe1` with MSVC `/W4 /WX` and ran the
real fixture: both phases exited 0 and the exact transcript reports 53 checks.
The fixture source is 14892 bytes / f123c92c219c6d133882cadda2c8f62967de9bb86f2de0f55d0b468384d5f574.
The controlled old-placement race and corrected mutex publication are among
those checks. The engine was not invoked and no real image body was read.

The original compiler/VCTIP job closed before the test; both telemetry member
captures agreed and the final member list was empty. All 511 held inputs were
reverified, evidence publication completed, guards reached zero and the lease
was released. The same original NoExit context confirmed CanExit, then terminal
96124 really exited 0. Fresh observation found host, parent, compiler, fixture,
VCTIP and all heavy/game processes absent, with no leases. Total published
output was 6362996 bytes, below the declared 16 MiB limit. The console's final
Select-Object summary over an ordered hashtable printed null fields; the
verified receipt and same-context values were the authoritative evidence.

Retained text evidence: receipt 11759 bytes / 7e612f958494f52f236dd8a48c3b5d69437eb25ca5fe73036e3b0974243762a6;
test stdout 76 bytes / 6a704c3d42c843b585a02f93dc12dd82156dce6c7b441cf9374e94bb4e926f8f;
fresh closure 369 bytes / 5203527eed2c6e92575845a57e65aa0d8b6b3f30759e751e64d8e5436b1e75b8.
F and G failure evidence remains immutable. This qualifies the synthetic
fixture/API only, not the full CLI producer or a native image observation.

This module currently provides a source overlay API, pinned source/output
contract, standalone fixture and typed native entry. It is not integrated into
the admitted build producer, operational recipient or owner launcher. Those
must consume a reviewed fresh source cohort and measured CPP result explicitly;
no old MaterialParts candidate/plan can be relabeled as this operation. Next:
reviewed producer CPP enablement after source merge, then a separately admitted
full-CLI build and consumer/operational plan/native GO. Authentic textures and the cause of G3's
unreadable image header remain unqualified.
