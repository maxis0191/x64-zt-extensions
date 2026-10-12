# Locate the first XSurface + 0x58 write

This work owns only `animation/rig/locator/`. The engine chat owns `rig-abi/`
and the future CDB probe. No native execution, attachment, stock copy or static
code scan is authorized by this document. The coordinator gives a separate GO
for the bounded static phase below; it is not a gameplay or debugger GO.

## Metadata result, 2026-10-12

The existing ZoneTool candidate is still SHA256
`e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04`.
Its PE CodeView identity matches the existing PDB: GUID
`aa767c25-a609-474e-a2de-9922d7dc159b`, age 1. The PDB is 135,532,544 bytes;
the build artifact records SHA256
`62b90fd57ec853f6366a768ae43f86186fba8d6b7d4443b9a5ae89221c41a1de`.
This metadata pass did not rehash the complete PDB.

Only the MSF directory/identity and symbol-record stream were read. Stream 1307
is 21,697,948 bytes; its 247,847 records were walked in 0.235 seconds with
21,840,128 bytes of PDB IO. The public records contain no `Load_XSurface`,
`Postload_XSurface` or `varXSurface` match. This is a scoped absence in public
records, not a claim about every PDB module-local/type stream. The source tree
also has no occurrence of those three names. The candidate PDB describes the
tool code; it does not supply symbols for the separately loaded retail image.

Useful public symbols exist:

| Candidate symbol | RVA | Preferred VA at candidate base 0x160000000 |
| --- | --- | --- |
| `zonetool::iw7::db_add_xasset_stub` | `0x525698` | `0x160525698` |
| `zonetool::iw7::xsurface::dump` | `0x5086c0` | `0x1605086c0` |
| `zonetool::iw7::xsurface::parse` | `0x508c3c` | `0x160508c3c` |

Use RVAs with the actual candidate module base in a future probe. These are
not retail addresses. `xsurface::parse` is the source-file import path and is
not an established breakpoint in the FF load path.

The pinned source installs the retail `DB_AddXAsset` detour at `0x140A76520`
(`zonetool/iw7/zonetool.cpp:2804`). Its stub calls `dump_asset` before invoking
the original registration function (lines 591-603). `ASSET_TYPE_XMODEL_SURFS`
is exactly 7 (`iw7/structs.hpp:132`). Thus a type-7 registration caller is a
specific reverse-search anchor. Registration/dump is already too late to set
the first-write watchpoint: E's alias exists by then.

## Proposed bounded static phase

Reuse the existing `unpacked-text.bin` (21,135,360 bytes, mapped at
`0x140001000`) and `unpacked-pdata.bin` (832,608 bytes, image-relative unwind
triples). Their historical hashes are recorded in the metadata JSON. Do not
infer current retail compatibility: the retained capture has no independent
capture-time/source-binary manifest. Rehash them under the analysis reservation.
Do not create a PE, copy the game, start ZoneTool or import a Ghidra project.

The proposed reservation is **1 GiB physical / 2 GiB commit**, one owned Python
process, BelowNormal, **60 seconds maximum**, **4 MiB maximum new report bytes**.
The algorithm uses at most 32 MiB input buffers, streaming Capstone instruction
objects, 128 direct-edge candidates and 128,000 decoded instructions. Admit the
whole phase through current main's resource helpers; any cap or ambiguity stops
the phase rather than widening the scan. No resource reservation has been made.

The prepared [static locator](locate_static.py) reads exactly 25,162,848 input
bytes across text, rdata and pdata, once each, and verifies their hashes. Rdata
is identity-bound but is not searched in this first pass. At most 17 scans of
the existing text buffer account for 359,301,120 linear opcode-search bytes;
decoding each candidate also reads its four-byte displacement. There is no
repeated file IO. It decodes at most 16 unwind-owned windows.
Twelve synthetic tests cover real versus embedded-immediate edges, argument
clobbers and branch bypasses, ambiguous unwind entries, hard caps and the
difference between an offset match and a proved writer. All twelve passed.
This tool has not been executed against the retained code.

Independent review of the first source revision found three missed cases:
LOOP-family control flow could bypass the type assignment, separate E8/E9 loops
performed twice the declared number of passes, and the final decoded instruction
could exceed its cap. The correction uses decoder control-flow groups (including
relative branches), one combined opcode search and a pre-acceptance instruction
limit. LOOP/LOOPE/LOOPNE/JRCXZ/JECXZ and exact-limit regressions now pass. The
earlier command manifest is obsolete because its source pin changed; the new
supervisor Plan must bind this corrected revision. Neither revision has scanned
retail code or established a first writer.
The follow-up review also reproduced an internal direct CALL entering after the
type assignment. It is now included in incoming-edge refusal; an ordinary
external call before a fresh type assignment remains supported.

The first invocation implements the registration anchor and three reverse
levels, retaining bounded instructions, call sites and unproved +0x58 store
candidates. It does not guess which four forward callees to inspect next.
Review its exact output first; selected forward inspection is a separate
coordinator decision within the same stated limits. A successful tool exit
means a candidate route is available, never that the first writer is proved.
The coordinator's launcher must bind the exact interpreter/script/command hashes,
acquire admission, create the Python process in its original BelowNormal Windows
job, enforce closure and retain the lease if closure is uncertain. A bare shell
invocation of the command text is not the authorized execution route.

The exact search route is:

1. Index only direct `E8`/`E9` relative edges whose target is the retail
   `DB_AddXAsset` address. Treat byte matches as candidates; validate instruction
   boundaries from a containing unwind entry. Reject absent/overlapping unwind
   ownership instead of decoding from a guessed byte boundary.
2. In bounded caller windows, find the path setting `ECX=7` before registration
   and the `RDX` header-pointer source. Reject intervening writes to the argument.
   Record the original instruction VA/RVA, containing function range, window
   hash and argument evidence. This identifies the XModelSurfs registration
   wrapper rather than any model/material registration.
3. Follow at most three direct caller levels and four selected forward callees,
   with no more than 16 complete function windows and 8 KiB per function. Trace
   the specific pointer used by that wrapper back through allocation/stream
   copy and the per-surface loop. Look for the 0x100-byte XSurface stride,
   source/destination pointer assignments and calls between copy and
   registration. Do not name a function `Load_XSurface` based on an address alone.
4. Within those evidenced functions, locate stores to the traced surface base
   plus 0x58 and their source register/dataflow. Distinguish an explicit store,
   an overlapping copy, a nested call and an unresolved indirect call. A field
   displacement match without the traced XSurface base is insufficient.

The desired result is an exact code location **after the 256-byte record copy
and before its first derived write**, plus the live surface-base expression
and a second instruction identifying the actual writer if statically visible.
The report must say whether +0x58 is still the authored zero at that boundary.
If static dataflow cannot establish this, return the narrow unresolved call and
its evidence; do not produce a guessed executable breakpoint script.

The engine chat can then prepare an exact owned-process CDB observation using
that location. Its future live GO must compare the selected code-window hashes
with the loaded retail image before installing a breakpoint/watchpoint and
capture the first writer, before/after value category, source pointer relation
and call stack. A mismatch refuses the candidate address. Static lookup alone
does not establish the field's engine meaning or authorize accepting nonzero
values in the rig reader.

The concrete [locator-only supervisor](SUPERVISOR.md) now provides an inert
default Plan and the reviewed-provider/F6 ownership route for a future Run.
Its source/mock checks and trapped Plan are separate from native validation;
no scan or live probe has been authorized by their completion.

## Existing tools and boundaries

Python 3.12 already provides pefile 2024.8.26 and Capstone 5.0.7. Microsoft
WinDbg/CDB 1.2606.22001.0 and VS2022 dumpbin/DIA are installed; no installation
or tool update is needed. CDB has only been identified and hashed, never
launched for this lookup. No third-party symbol-server request was made.

Current `origin/main` was fetched as
`c2396bf9ad7cb184717c9fa8cc90436c1b55c016`; the current resource, instance and
stock workflows were read. Main, candidate stock, `rig-abi/`, failed E receipts
and other chats' edits remain untouched. The metadata is a proposal input,
not proof that the early breakpoint or first writer has been located.
