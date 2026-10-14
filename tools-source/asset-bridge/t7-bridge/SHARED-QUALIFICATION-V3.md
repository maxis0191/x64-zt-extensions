# Shared qualification within QualifiedCollectionV3

This source-only extension preserves legacy, V1, V2 and V3 plans without the new
option. It does not select inputs, prepare a real plan, refresh game metadata,
acquire admission or authorize a native catalogue. Existing eight closed
qualifications can remain pinned while one shared source qualifies the twelve
additional, explicitly selected inputs. No dependency or load order is inferred.

## One optional catalogue schema boundary

The existing `iw7.t7-catalogue-plan/1` accepts **`SharedQualification` only with
`BootstrapPolicy: QualifiedCollectionV3`**. Its exact fields are `Script`, `Plan`
and `Receipt`; each is an ordinary `{Path, Bytes, SHA256}` text pin, at most
32 KiB. The script filename is `Qualify-T7BootstrapGroup.ps1`. All three paths
are distinct and outside the catalogue attempt root.

Selected `Bootstraps` reuse exactly that `QualificationScript` pin. Other items
retain distinct qualification scripts. Every input path, alias, file ID and
per-item `QualificationReceipt` remains distinct. Sharing a receipt, using the
same script path with a different hash/size, or overlapping another protected
path is refused. The existing item/aggregate bounds remain 512/768 MiB, with
1..32 literal names. Sharing a script does not widen other binary/text limits.

Bindings contain the shared script only once and add the two shared plan/receipt
pins. The exact count is **22 + 2N + D + 2**, where N is all catalogue bootstraps
and D their distinct qualification scripts. Eight existing scripts plus one
shared script for twelve new items give **73 bindings**. Twenty inputs using one
shared script give 65. Without the option, the old `22 + 3N` rule is unchanged.
Only the opt-in absolute binding ceiling grows by two, from 118 to 120.

The runner and common H1 core are unchanged. Their existing text guards cover
both additional pins before receipt validation. The profile reads these bounded
JSON documents and requires the complete group, exact input order/metadata/IDs,
and each individual receipt's exact path/size/hash. All shared members must be
present; selecting a subset or crossing indices, names, IDs or hashes fails.
Every receipt is checked before the runner's `-Run` boundary and before aliases.

## Group plan and receipt formats

`iw7.t7-bootstrap-group-plan/1` has these exact fields:

| Field | Contract |
| --- | --- |
| Schema, Runner, Script | Schema above; exact qualifier path; its `{Path, Bytes, SHA256}` pin |
| SourceDirectory | One canonical literal directory; no scan or wildcard |
| RunRoot | Fresh `runtime/t7-bootstrap-group-<label>` under the qualifier repository |
| Inputs | 1..32 explicit entries, each `{Name, Path, Bytes, FileId, Attributes, CreationUtc, LastWriteUtc}` |
| Bindings | Eight exact source/helper pins with `IsText: true`, at most 128 KiB each |
| HostImage | Reviewed absolute PowerShell 7 host image |
| Main | Existing `{MainBaseline, PreservedMain}` preservation contract |
| PreservedPython | Exact `{PID, CreatedUtc, Image}` to preserve |
| PhysicalBytes, CommitBytes | 6 GiB and 8 GiB respectively |
| DeadlineSeconds, RetryAuthorized | 200 and false |

The eight helper pins are H1Native.Core, T7Catalogue.Profile, T7Prepatch.Profile,
Resource-Scheduler.Core, Resource-Memory, Resource-RecorderOwnedProcess.Core,
ResourceMemory.cs and HudFileIdentity.cs. The qualifier guards its own script
and plan separately. A small bounded text bootstrap first verifies the plan's
supplied SHA256, then its exact **raw H1 pin before importing H1**. Its read/share-read
guards stay retained; failures close them even when H1 has not been imported.
It never normalizes line endings or substitutes a historical source hash. Plan
and qualifier source are limited to 32 KiB; the H1 bootstrap remains <=128 KiB. Default
validation reads only these local source/plan files; input path validation is
syntactic. Actual metadata and native IDs are not consulted until an authorized
`-Run` has passed fresh admission.

Per-item receipts retain `iw7.t7-bootstrap-qualification/1` and its existing
two-pass, metadata, identity, guard, release and scope flags. Shared members add
only **`QualificationGroup: {PlanSHA256, InputCount, InputIndex}`**, with a
zero-based index within the shared members, preserving their declared order.
Receipts are named `<Name>.receipt.json` under the group RunRoot.

The final **`iw7.t7-bootstrap-group-qualification/1`** receipt is
`RunRoot/group-receipt.json`. It binds `PlanSHA256`, `ScriptSHA256`, all existing
lifecycle/scope flags, `GroupComplete` and the complete `Items` array. Each item
is `{Path, Bytes, SHA256, FileId, QualificationReceipt}`. The consumer compares
these pins with every declared bootstrap; it also checks the plan's exact
6/8 GiB, 200-second, no-retry contract and canonical receipt locations.

## Reading and closure

One persistent `-NoLogo -NoProfile -NoExit -File` host takes one fresh scheduler
reservation. It preserves Main and the declared Python process, refuses occupied
admission/heavy work, then checks all actual metadata and IDs before reading any
payload. It loads only the existing small file-ID helper, never the game engine.

Each file is opened twice with **FileShare.Read**. Both handles remain retained
through the entire group. Each pass uses the existing FileStream/SHA256 pattern
with one **64 KiB buffer**, incremental SHA256 and deadline checks before and
after each read. Memory high-water checks occur every 16 MiB and at group end.
The two lengths/digests must match. Metadata and native IDs are rechecked under
the guards, including a final pass over the whole collection. No whole-file arrays,
headers, payload copies, aliases or native engine jobs are produced.

The existing `Complete-H1Stage` handles release/quarantine; its wrapper closes
guards only after release succeeds. A release failure retains the exact context
and handles in the existing quarantine slot and persistent host. No retry occurs.
Individual receipts are published only after the complete group succeeds and
closes. Their small text hashes are recorded in the group receipt, published last.
A missing/failed/quarantined group receipt prevents the catalogue from accepting
even an otherwise valid prefix of individual receipts. A final deadline overrun
uses the existing retained `.deadline-exceeded` artifact and canonical failed
receipt pattern. A failed publication never becomes a complete positive group.

The 200-second deadline includes reads, closure and publication, with checks
between chunks. Synchronous OS reads are not forcibly interrupted mid-call.
The reservation stays **6 GiB physical / 8 GiB commit**; neither budget is
reduced. Real large-file duration, memory costs and engine compatibility remain
unmeasured. A source review is not permission to run the group or the catalogue.

## Verification and next operational boundary

`Test-T7BootstrapGroup.ps1` uses invented metadata, fake IDs/clock/release,
small original temporary files and a fresh PowerShell host for DEFAULT only.
It covers shared/mixed collections, unchanged legacy limits, crossed receipts,
names/IDs/hashes, fake script pins, incomplete groups before alias creation,
512/768 MiB metadata bounds without large allocation, two streaming passes,
failure at first/middle/last reads, retained guards, release refusal, deadline
failure and publication invalidation. The existing four catalogue/reader suites
remain regression checks. No test accesses game stock or acquires a real lease.

Initial source checks on 2026-10-12: shared group **190**, bootstrap collections
**443**, legacy bootstrap **177**, catalogue **188**, metadata host **97**;
**1,095 checks passed**. The real qualifier DEFAULT was exercised in a fresh
PowerShell host against a nonexistent synthetic input directory and real source
pins only. Native providers/types, admission and `-Run` were not invoked.
During development, regression checks caught an unintended relaxation of the
legacy distinct-script check; it was restored before this handoff. Group plan
timestamp validation also accepts PowerShell's JSON date conversion while still
requiring explicit valid timestamps. Neither correction changed runtime limits.

An integration DEFAULT then exposed a stale H1 bootstrap constant in the initial
commit `ab133583`: the local core was 9,760 bytes, SHA256
`a5657b8aada6a30befc3bd401cd7a6bc755a43e6a48b6f9b7e847dcea84478ad`,
whereas the current integration core was 11,268 bytes, SHA256
`55430822f5251ae58008bc7e15c36831e3481e7dae4cf0961254c633f001e3f5`.
Both were CRLF; the current core also includes reviewed dump-observation/artifact
support. This was a source-version difference, not merely checkout line endings.
The separate correction uses the operational plan's guarded raw pin as described
above. The integration file's Git blob was confirmed equal to `ce18ea57`:
`48c6889c40fdf2b566ba57a76b2f43247a96c391`.

The corrected group suite passed **207 checks** using that current integration
core in read-only mode via `-ReviewedCorePath`. Its LF and CRLF source fixtures
each seal their own different raw hashes, and both real DEFAULT invocations pass.
An altered unpinned core containing observable import code is rejected before
import; exclusive reopen checks in the same test host prove plan/script/core
guards closed without relying on process exit. These fixtures copy only small
source text; the integration checkout is never changed. No payload/metadata of
the game, admission or `-Run` was used by the correction.

The prior metadata-only inventory totals 748,135,232 bytes for twenty explicit
files; eight Q inputs account for 75,726,016, leaving 672,409,216 for qualification.
With the 21,750,272-byte candidate, the catalogue's exact logical output limit
would be **875,944,664 bytes**. Its existing hardlinks do not duplicate payload
storage, but logical tree accounting still counts those bytes. A future concrete
plan must be separately pinned and checked against the 128 KiB plan and 64-entry
catalogue tree limits. Source preparation changes none of the sealed Q pins.

## Future helper bound correction, 2026-10-14

The source-suite DEFAULT failed before admission because the reviewed
`T7Catalogue.Profile.ps1` had grown beyond the original 128 KiB helper bound.
The future qualifier retains 128 KiB for every other helper. Only the exact
Catalogue path can exceed it, with raw LF tuple 150,096 bytes /
`57c9ef83b9eb9535d57f0d8d4fa1fffdff3e389849258892993715382922b6d6` or
raw CRLF tuple 151,909 /
`a5d67419a16f246b2f96c51950a0ced538ab48e720322887b39ff4909d348d29`.
These identify the reviewed source at main `e21ecbb2ce73b7993279dca43043ad771e12ef70`;
there is no runtime line-ending normalization, generic cap increase or payload
allowance. Other role/path/hash/size/type combinations remain refused before
source import. The source fixture now checks both raw representations and
mutation refusals; actual DEFAULT runs use an absent donor directory and do not
qualify any stock. Old qualifiers, plans, receipts and sealed Q inputs retain
their bytes. Changes to this larger helper need another reviewed source tuple.
