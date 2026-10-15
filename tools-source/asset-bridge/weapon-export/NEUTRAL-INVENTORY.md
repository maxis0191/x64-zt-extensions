# Descriptive neutral dependency inventory

This is the first bounded Source implementation of the reviewed V5 split.
It adds a descriptive inventory and pure identity checks to this existing
module. No CLI, native builder, input parser/routing, serialized manifest,
readback transaction or runtime caller is activated. No clone/T2, stock,
opaque tool/SDK artifact, FF or game input was opened for this Source work.

The previously merged PR213 foundation passed sixteen actual C++ fixtures and
both native TU compiles at Source `05c28704ff0af07ab08b5b35681356999d96b26a`.
Its result does not qualify this changed header or the new fixture. This lot
requires independent Source review, then a separately reviewed/admitted CPP
recipe and distinct GO before actual compilation/execution. No new C++ PASS
is claimed by the Python checks or authored cases below.

## Complete description and unchanged strict policy

`neutral_dependencies::Inventory` uses the same production typed walkers,
name-copy/UTF-8 checks, owner/origin/index records and fixed budgets as the
strict `Collector`. The only descriptive difference is that all thirteen
recognized direct external families may be recorded. It continues after a
recognized family whose reference-only implementation is not admitted, so it
can describe both owned roots completely. Unknown/IMAGE types, invalid FX
discriminants, unreadable names, bad private identities, invalid counts or
budget exhaustion poison the operation and never yield a complete inventory.

The two parser-owned roots, all visited subblocks/arrays and native name-header
pointers must already be valid within the caller's owned lifetime. The only
guarded copy here is the existing name copy; these walkers do not make
arbitrary native pointers safe. The future bounded input-schema/public-parse
route remains a separate gate. Inventory follows only direct names and never
recurses into external payloads.

Typed names deduplicate without losing distinct owner/field/index edges or
the occurrence count. Private weapon/PAP edges remain owned; they cannot
become external rows. The fixed two-root order, array limits, text/manifest
accounting and conservative sparse-array refusal remain unchanged.

`Inventory` is a private base adaptation of `Collector`; its distinct public
surface exposes records and completeness, but has no `verify_rows` and cannot
convert to the strict collector. The descriptive constructor selector is
private, immutable and accessible only to `Inventory`. Ordinary `Collector`
construction always retains the strict FX/VFX/RETICLE policy. There is no
caller-supplied predicate, widening flag or reset operation.

`policy_blocked()` is true for an incomplete/refused inventory or any unique
external reference outside FX/VFX/RETICLE. A complete inventory may therefore
remain blocked. `neutral_pair_contract::assess` reports incomplete, refused,
complete-policy-blocked or complete-with-no-policy-blockers plus the blocked
external count. The last state describes this finite type policy only; it
does not authorize a builder, create rows/tokens or prove external resolution.
The nine families covered by additional Source audits are still blocked, as
is external ATTACHMENT. No audit is adopted automatically.

## Pure typed identity contract

`native_neutral_pair_contract.hpp::check_identities` checks a finite caller-owned
array of typed owned/reference claims, without allocation or I/O. A reference
spelling may be bare or have exactly one leading comma; owned spelling must
be bare. It rejects malformed UTF-8/control/NUL/default names, empty or double
comma names, unknown/IMAGE types, invalid modes and out-of-bounds input. Native
keys remain case-sensitive with no Unicode normalization.

For the same type and canonical bare name, mixed owned/reference modes refuse
in either insertion order. Duplicate owned claims also refuse. Repeated
reference observations are legal; Inventory retains their provenance. Equal
strings in different native types remain distinct. The contract validates
identities only: it does not admit arbitrary owned assets, require a complete
private-pair plan or grant support to a recognized reference family. Its views
must refer to ordinary caller-owned readable storage for the entire call.

Input report hash/bytes/closed schema, bounded preparse allocation/shape checks,
same-file lifetime/readback, sealed search routing, generated branding rawfile,
actual zone inventory verification and the private readback leaf are deliberately
unimplemented. These require the next separate Source composition. No general
manifest framework or premature builder-token type is introduced here.

## Authored causals and Source checks

`test_neutral_inventory.cpp` includes the actual production header and pinned
native declarations. Its twelve cases cover all thirteen recognized families,
real walkers continuing after a model blocker, owner/index dedup, strict-policy
parity, incomplete/refused poisoning, unknown/IMAGE/FX refusal, inherited bounds,
compile-time API separation, canonical collisions in both orders, native typed
aliases, malformed claims and preserved private owned edges. A poisoned FX
payload ensures the visitor does not recursively inspect an external body.

These twelve cases are authored, not run. The old sixteen-case fixture remains
unchanged. The future CPP gate must run both fixtures and compile the two
patched native TUs, with exact Source pins, dependency guards, inherited-input
verification and the existing H1 lifecycle. A full CLI link, FF/readback and
gameplay require still later distinct gates.

Six new Python Source checks examine the actual production surfaces, mechanical
recognition coverage (including the shared FX helper), strict constructor/policy,
API/effect boundaries, preserved walker hashes and meaningful authored case
inventory. They do not simulate C++ or claim its behavior passed. The initial
recognition Source check omitted the shared `emit_fx` helper and failed on FX/VFX;
the corrected check inspects that real helper and confirms both walkers call it.
No production policy changed to satisfy this test.

Run the relevant light Source checks from this directory:

```powershell
python -B -m unittest -v test_neutral_dependencies_source test_neutral_dependency_inputs test_neutral_inventory_source
```

Next action: approve the exact Source head, then review the dedicated CPP recipe
and obtain its distinct admission/GO. Keep this PR unmerged until the new actual
production-code compilation/fixtures and exact-head CI disposition are reviewed.
