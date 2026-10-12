# Suspended fixture creation and exclusive owned attachment

This is source preparation after [diagnostic B](CDB-FIXTURE-DIAGNOSTIC-2026-10-12-B.md).
That evidence was committed separately as `db0a13fe47f6b56918bd064bf6d1e4fcdce3ac09`.
B proved successful API evaluation with target `MemberValue=0`, while the transport
reported membership. It did not establish CDB's creation flags, an alternate
parent, breakaway, a platform defect, or departure from an original job.
The historical records and API guards are unchanged. No new native run follows
this change. The coordinator authorized studying/code-preparing attachment only
to the new fixture created and held by this transport; existing/retail PID
attachment remains unavailable.

## Research and chosen mechanism

Microsoft documents ordinary child job inheritance and its exceptions in
[Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).
[CreateProcess2](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/dbgeng/nf-dbgeng-idebugclient5-createprocess2)
and [its options structure](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/dbgeng/ns-dbgeng-_debug_create_process_options)
describe the DbgEng API, but do not expose the actual internal flags used by this
installed CDB invocation. A designated parent can affect job inheritance under
[UpdateProcThreadAttribute](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-updateprocthreadattribute).
That is a documented alternative, not evidence CDB used it. No causal claim is made.

`owned_fixture.py` instead calls
[CreateProcessW](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw)
directly in the admitted Python transport, with a fixed Python/fixture command,
`CREATE_NO_WINDOW | BELOW_NORMAL_PRIORITY_CLASS | CREATE_SUSPENDED` (`0x08004004`),
no inherited handles, no breakaway/debug flags, and no alternate parent or token.
It retains the process and primary-thread handles from
[PROCESS_INFORMATION](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/ns-processthreadsapi-process_information).
The declared Windows x64 structures are 104/24 bytes; pointers are 8 bytes and
BOOL results are 4 bytes. PID, TID and exact creation FILETIME are rechecked
through these same handles. It exposes no OpenProcess/OpenThread or supplied-PID
creation/ownership path, no replacement job, and no assignment by discovered PID.
The original BuildJob and JobMembers providers are unchanged.

## Stops and authorizations

| Phase | Required evidence before proceeding |
| --- | --- |
| TargetCreatedStopped | Root and new suspended target are exactly the two original-job members, with exact images, root creation time and target FILETIME. Only then publish `attach-owned-fixture-once`. |
| AttachedStopped | Fresh nonce-bound CDB target-PID probe equals the retained target identity. The original job contains exactly root, target and CDB. Only then publish `start-fixture-once`. |
| Fixture startup | Recheck original handles and FILETIME; `ResumeThread` on the retained primary handle must return exactly 1, then send one `g`. A different count refuses without a second resume. |
| ArmedStopped | Fixture manifest matches the earlier target PID/FILETIME; original three-member observation, stopped probe and actual breakpoint confirmation remain required before watch continuation. |
| CaptureStopped | Existing bounded capture parser, original-job shutdown, source restoration and release gates remain in force. |

The CDB command is constructed only from the live `OwnedFixture` object; a PID,
manifest, or other object is refused. It uses `-p <owned decimal PID> -pb -xe ld`
alongside the existing fixed symbol/no-shell options. According to
[CDB options](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/cdb-command-line-options),
`-pb` avoids requesting a break-in thread. We do not add automatic resume,
noninvasive attachment, reattachment or leave-alive switches.
[DebugActiveProcess](https://learn.microsoft.com/en-us/windows/win32/api/debugapi/nf-debugapi-debugactiveprocess)
describes initial state/DLL notifications; the proposed stop is a DLL notification.
At the first prompt, `sxn ld; bl` removes that temporary stop filter and checks the
fresh breakpoint table, before the PID probe and owner authorization.

An early source proposal used `-xe cpr`. It was rejected before testing:
[event documentation](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/controlling-exceptions-and-events)
limits control of `cpr` to child-process debugging. No native trial used that
proposal. The `ld` prompt path is still unqualified. If it supplies no usable
prompt, times out, or names another target, the code refuses; it does not add a
fallback resume or attach. Whether this installed CDB stops as expected while
the primary thread remains suspended is a concrete future qualification item.

[ResumeThread](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-resumethread)
returns the previous suspend count; debug-event freezing is separate from that
count. The protocol requests its one primary resume only while CDB is at the
verified stop, then continues the debug event. The fixture's own API/member guard,
deliberate DebugBreak and known write are unchanged.

## Closure and preserved uncertainty

Both initial two-member and attached three-member snapshots are retained, along
with the last observation even on validation failure. Parent PID observations
and their provider errors are diagnostic evidence, not a substitute for job
membership. Full identity checks bind the root, target and debugger separately.

On a transport exception, a newly created target can be terminated using its
original creation handle only; closure is reported only after its handle signals
exit. CDB/root recovery stays with the original job's independent deadline/Stop.
No detach, PID adoption, process-name kill, or second job is introduced.

`OriginalJobClosed` now distinguishes root-exit/Active0 from complete known
descendant closure. From root resume until membership is established, and again
while debugger creation/attachment is unproven, `DescendantClosureUnproven=true`.
A failed membership observation restores that uncertainty. Even after the
original job closes, uncertainty retains the lease and records quarantine rather
than claiming restoration/release. This is deliberately conservative, including
an ambiguous creation/attachment outcome. It provides no recovery authority over
an unrelated process. An individual target cleanup receipt cannot prove an
unobserved CDB was also closed.

## Plan and verification boundary

The default runner uses spec/source-plan v4, eight immutable source bindings
(the prior seven plus `owned_fixture.py`), and the same fixed fixture 4/6 GiB
estimate. Old v1/v2/v3 specs are refused. No existing PID or arbitrary command
field is added. Plan hashes/inspects small inputs only; it must report no native
execution, native types or lease and leave the future run root absent.

Pure verification covers 69 Python tests, including ten fake-Win32 owned-handle
tests and six added protocol refusals; 29 PowerShell transaction simulations;
23 member-identity refusals plus valid two/three-member cases; the existing
worker/profile/failure-envelope checks; and eight source-mutation/guard tests.
No CDB, fixture, WinDLL or native process helper is invoked by those tests.
These checks do not qualify the real attach prompt, resume count, target job
inheritance, deadline thread, resource peaks, watchpoint write or gameplay.

The local v4 default Plan on 2026-10-12 at 10:05 UTC bound 21 inputs and returned
`NativeExecuted=false`, `NativeTypesLoaded=false`, `LeaseAcquired=false`,
`Ready=false`, with its future run root absent. Private review artifacts use nonce
`5fb1fe14c1ce42488d4b244f63f1336f`. Spec SHA256 is
`f4c34ad7ac52939e47d92eaa544d23ce9392a2520a70a6d24af1d9c5bc2219f5`,
Plan SHA256 is `94cd29d36a5a428827c810fc19bd6811c66089469532a23472e9e8a859ebd84c`,
and the default command SHA256 is
`9944cc284d84feca9849a593d9232984322152c2cb650f7d4a3d4c267cdf4f1c`.
No admission or native preflight was performed. This candidate-checkout Plan is
review evidence, not an interchangeable integrated Run authorization.

Next: independent source review and a fresh integrated v4 Plan with actual
integrated byte hashes. Any native attempt requires a separate explicit GO,
fresh resource/Main preflight and the existing bounded evidence/closure review.
There is no implicit retry. Retail remains unavailable with its separate 10/14
estimate and locator/ownership requirements.
