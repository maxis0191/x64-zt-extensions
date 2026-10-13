# Source-only diagnostic after the first fixture refusal

Historical A-to-B diagnostic preparation. B's independent proof is preserved in
[its trial record](CDB-FIXTURE-DIAGNOSTIC-2026-10-12-B.md). Current source work is
the [v4 owned-creation Plan](OWNED-CREATION-PLAN.md), without a new native GO.

The immutable [first trial record](CDB-FIXTURE-2026-10-12-A.md) was committed as
`d59a884fb7c9473a8f06fcc8ea4479a51f7947cb` before this change. The initial job
guard refusal is unresolved. This change improves the evidence for a separately
reviewed future fixture; it does not assert a job-inheritance fix or authorize a
second native run. The root checkout and its seven frozen sources were not edited.

## Separate the API result from membership

Both the transport and the target explicitly declare `GetCurrentProcess` with
no arguments and a pointer-width HANDLE result, and `IsProcessInJob` with two
HANDLE arguments, an output pointer to a 32-bit BOOL, and a BOOL return value.
The diagnostic requires the Windows x64 sizes (8-byte HANDLE, 4-byte BOOL).
`GetProcessTimes` also has an explicit BOOL return declaration in the fixture.

Before calling the query, the thread-local last-error value is cleared. The
immediate BOOL return, last error, raw membership value and validity are retained
separately. On API failure, `InAnyJob=null` and `MemberValid=false`; a stale output
value cannot become evidence of membership. On success, last error is retained
but marked non-authoritative. A successful false output is a distinct nonmember
result. These distinctions follow Microsoft's
[IsProcessInJob contract](https://learn.microsoft.com/en-us/windows/win32/api/jobapi/nf-jobapi-isprocessinjob).

The NULL job handle queries membership in any job, not specifically our original
BuildJob. `SpecificOriginalJobProven=false` is explicit. The existing independent
original-job observation must still confirm exactly three members and the target
creation identity before the watch continuation. The early guard remains intact:
API failure or nonmembership refuses the fixture before manifest/DebugBreak/write.

New bounded private records are `transport-job.json` and `fixture-job.json`, each
bound to its role, nonce and self PID. The latter is written before the guard
raises, so absence of `fixture.json` no longer discards the raw query result.
These are self queries, with no attach, adoption, or termination by PID.

## Preserve the initial failure

Every transport Failed event retains schema, nonce, `FixtureOnly=true`, root
PID, debugger PID when known, phase, worker state and bounded exception details.
Bound job evidence distinguishes `IsProcessInJobAPIFailure` from
`IsProcessInJobNonmember`; the immediate error (such as missing manifest) remains
a separate field. A later bootstrap handler preserves an already-bound first
Failed event instead of replacing it. Foreign-nonce evidence is refused.

The PowerShell consumer checks envelope identity/nonce before using a failure,
retains the complete Failed event in its private state and reports the cause
before requiring healthy workers. A foreign envelope still fails identity checks.
No Failed event can count as a capture or authorize continuation.

## CDB command review, with no option change

The command constructor remains unchanged: fixed CDB/Python identities and target
script, explicit startup file, no attach arguments, no shell and no retail mode.
The installed CDB binary was not invoked again, including with `-?`.

Microsoft's [CDB options](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/cdb-command-line-options)
describe `-noinh` as controlling handle inheritance, `-o` as debugging descendants
of the target, and `-pd` as leaving the target alive when debugging ends. None
provides evidence that this target belongs to our original job. They are not
added as speculative fixes. The existing `-sins`, empty local `-y` path,
`-netsyms:no`, `-noshell` and `-nosqm` remain unchanged. The first trial's gallery
messages are retained as a limitation, not evidence of a specific network event.

The CDB/DbgEng implementation's child-creation flags were not established from
the reviewed command constructor or public option documentation. Do not infer
CREATE_BREAKAWAY behavior or a platform defect from the ambiguous first guard.

## Qualification boundary

Pure tests exercise explicit signatures with fake API functions, successful
membership/nonmembership, API failure with stale output, nonzero BOOL semantics,
wrong pointer width, preserved refusal, bound failure identity and first-cause
retention. They extract fixture definitions from its AST; they do not import or
execute the target, load WinDLL, call the API or create processes/threads.

The fixed fixture 4/6 estimate, atomic admission, commit-pressure threshold,
original-job closure and deadline limits are unchanged. A distinct source-bound
v3 diagnostic Plan must be reviewed, then a separate GO is required. No new
preflight, API observation, memory-peak measurement or native retry is implied.
