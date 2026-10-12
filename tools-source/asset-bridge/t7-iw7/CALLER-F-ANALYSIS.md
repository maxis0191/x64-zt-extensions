# T7 catalogue F: bounded caller analysis

This checkpoint analyzes existing private F captures only. No image/PDB was
opened, no process was launched, and no engine patch was applied. F remains
Failed / NoCatalogue with natural exit 0; capture success is not compatibility.

## Evidence and limits

The 12,273-byte receipt has SHA256
9d9dfda0c385a051a50b43eba7785609d3a8e1f9b456ee8d09ccee4f1a628684;
the 4,565-byte stderr has SHA256
09e8d5878864e49dd409e543fc8b4f4f6e8c1362ea1ec602d34fdce785d9e926.
Both were independently verified. Closure, release, input/output revalidation
are true, without quarantine. All three caller records are ok and match the
first occurrences in the same eight-frame stack, TID 27900 and exit RA
0x140AC00C4. Only 644 already captured code bytes were considered.

Capstone 5.0.7 decoded both full functions from their RUNTIME_FUNCTION starts:

| Caller | Function interval | Capture | Observed call ending at its RA |
| --- | --- | --- | --- |
| 0 | [0x140584F50, 0x1405850DF) | Entire 399 bytes | 0x140584FD3 calls 0x140AC00E0; RA 0x140584FD8 |
| 1 | [0x1401D9FE0, 0x1401DA135) | 85 bytes from 0x1401DA000 | Unique five-byte CALL candidate at 0x1401DA010 to 0x140501030; RA 0x1401DA015 |
| 2 | [0x140526C80, 0x140526D20) | Entire 160 bytes | Indexed indirect call at 0x140526CFB; RA 0x140526D02 |

Caller 1 starts 32 bytes before its captured readable region. Its prefix is not
function-entry anchored; the last three captured bytes are an incomplete
instruction. Decoding from its observed RA gives a branch back to 0x1401DA010,
supporting that call boundary, but does not recover the missing entry or callee.

Caller 0 sets up a 4,096-byte local buffer at RSP+0x50, passes the original first
argument as the helper's third argument, and passes the saved variable arguments
as its fourth. It then uses the same local buffer on a console path. This is
consistent with formatted fatal-error handling; its exact name and the message
are unproven. Under normal control flow, the observed RA follows the zero-result
branch after 0x1405814C0, then ECX=0 and the call at 0x140584FD3. The console path
is on the other branch. Neither following INT3 is evidence of its execution.

Caller 2 sets up TLS data and dispatches through an indexed callback table.
Neither the index nor table contents were captured. The retained source pin
fab935826c898806855376662a8a03317b3ad8f1 names only the relevant helper addresses
0x140597E40 (Sys_ShowConsole) and 0x140525EB0 (Sys_GetTLS). It supplies no exact
name for the three callers, 0x140501030, 0x1405814C0 or 0x140AB6460. No missing
fastfile, database error, anti-tamper failure or bootstrap repair is established.

## Proposed next observation; not implemented or authorized for execution

Observe the local text immediately after the already captured five-byte CALL
at 0x140584F98 to 0x140AB6460. The continuation is 0x140584F9D. Its instruction
boundary follows from the complete, gap-free decode of caller 0, not an address
guess. The captured 399-byte function's SHA256 is
6e07cffeb7e5f2dd6466dd4713537edc5c93050cbebc8a07892db032931f038b.
No captured byte window is included here.

The original helper receives RCX=buffer, RDX=0x1000, R8=original format argument,
R9=RSP+0x1078 (the original caller's saved first variable argument). A small
x64 wrapper can forward these four integer/pointer bit patterns unchanged to
the original helper, then observe the buffer and return the original RAX value.
It must not reformat, modify the buffer, catch exceptions from the original
helper, or alter the caller's subsequent termination. Preserve GetLastError
immediately after the original helper and restore it after all observation.
The compiler must preserve the normal nonvolatile registers and stack alignment.

Install only for this exact catalogue diagnostic, at the first existing T7 DPI
callback before component post_unpack. First qualify the named image/base,
readable committed region, whole-function digest, five-byte direct-call target,
continuation and relative reach to the wrapper. A mismatch leaves engine bytes
unchanged and emits an explicit installation refusal. This phase's bytes are
not assumed to equal F: the future runtime must prove the digest before writing.

The retained utils::hook::call supports relative CALLs, but its copy helper does
not check VirtualProtect/FlushInstructionCache results. It cannot by itself
prove guarded installation. A minimal proposed alternative is one aligned
8-byte compare/exchange at 0x140584F98, replacing only the five CALL bytes and
preserving the following three bytes. Require the observed PAGE_EXECUTE_READWRITE
protection, exact old word and relative reach; no allocation, far trampoline,
protection change or shared hook-library modification. Check instruction-cache
flush and bounded readback. Any rollback must compare against this probe's own
new word before restoring the old one. Report failure explicitly. This avoids
a multi-store CALL rewrite; it is not a claim of untested runtime equivalence.

After the original helper returns, select only one observation atomically.
Validate buffer/capacity and current-thread stack bounds, then VirtualQuery and
ReadProcessMemory(self) in a POD-only SEH reader. Read at most 384 bytes, clipped
to capacity and the same readable region; never read the format or va_list.
Serialize only bytes before the first NUL. Record read count, emitted length,
NUL presence and explicit refusal/partial/prefix/exception state. No strlen or
unbounded %s on engine memory. Flush before returning to the original caller.
Correlate the observation TID with the later exit winner; do not assume a match.

A proposed separate message schema adds one install and one buffer record.
Using [T7_CATALOG_MSG], schema=iw7.t7-catalog-message/1, numeric TID/error,
status strings capped at 32 ASCII characters, and buffer read/length/nul/data
fields, maximum widths including CRLF are 135 and 934 bytes. Together with the
unchanged 6,911-byte trace/EXIT/CALLER bound, the total is 7,980 bytes and fourteen
lines, within 8,192 bytes. Hex payload remains private; a prefix without NUL is
explicitly incomplete. These are proposal bounds, not an implemented parser.

Next: coordinator review of this narrow ABI/installation/capture proposal, then
source preparation and parser synchronization under a distinct profile. Build
and runtime need separate reviewed plans and GO decisions. Exit remains intact.
