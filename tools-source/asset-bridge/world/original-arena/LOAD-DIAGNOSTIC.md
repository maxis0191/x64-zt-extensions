# One bounded CP load diagnostic

The failed M reference checker timed out at global_mp before reaching CP. The
retained fab source exposes no CP-only reference switch. Existing loadzone and
verifyzone handlers do not perform the required named nondefault reference
check. This experiment preserves the loader order and recipient request.

Add `-LoadDiagnostic` to a **fresh** Measure-StockReference source Plan; it does
not run by default. It binds the capture/debugger source files and the existing
offline CDB metadata. Actual Python/CDB/producer hashes remain under the helper's
single Extract admission. It uses the existing 72 inputs, stock guards, original
NativeJob owner and restoration; no new stock clone, process adopter or scheduler.

One original-reference job runs for at most 120 seconds. If its exact final line
is Loading global_mp, total elapsed is at least 45 seconds and the log length has
not changed for 15 seconds, one diagnostic is armed only before 60 seconds.
The full 60-second helper/closure budget must remain; a later trigger is refused.
Every helper deadline is additionally clamped to the original remaining time
minus a ten-second combined closure reserve. Progress or another zone does not
trigger it. The callback verifies the current original job's live root
and uses the identity captured from its creation handle, never an arbitrary PID.

The existing iw7_capture.py records five seconds of thread CPU/I/O, then captures
one light minidump, with ten- and fifteen-second owned-helper deadlines. Its flags
are 0x1820: normal stacks, unloaded modules, memory-region information and thread
state. Full memory data (0x2), data segments and private heap flags are absent.
[Microsoft MINIDUMP_TYPE](https://learn.microsoft.com/en-us/windows/win32/api/minidumpapiset/ne-minidumpapiset-minidump_type).
The normal type is intended for stack traces; memory-region information is not
the full-memory payload. Capture can perturb timing and is not a crash witness.

Accept only a nonempty dump at most 32 MiB, then run existing CDB **offline** for
at most 20 seconds with `!runaway; ~* kP; lmv; .time; q`. No debugger attaches to
the live target. The diagnostic jobs share the existing admission and have their
own original owners. Unknown diagnostic closure forces the encompassing context
to stay unconfirmed even after its original target closes. Source/stock guards,
the reservation and AppDomain context remain quarantined in the NoExit host.
The 256 MiB output threshold is sampled, not a hard write cap; overshoot is not
bounded by this protocol. Dump/stack acceptance does not relax that truth.

After capture, stop the exact original target through its existing owner rather
than repeat the former 240-second material attempt. Preserve diagnostic.json,
original identities, helper closure receipts, CPU sample and raw dump/stack; then
perform existing source/stock proof, restoration and release. Successful cleanup
reports DiagnosticCaptured and MaterialReferenceMeasured=false. If the target
exits before the trigger, report DiagnosticNotTriggered and retain its outputs;
do not manufacture a material proof. Writer, FF, GPU and collision remain gated.

Interpret only primary evidence: a runnable CPU-heavy thread's resolved loader
or lookup frames can identify a busy loop; blocked file/I/O/resource lookup frames
plus missing/default asset evidence can suggest a dependency problem. Raw stacks
or missing PDB matches are unresolved evidence, not a diagnosis. Check PDB GUID/
age and module bounds before assigning symbols/source locations. Neither an
external FF inventory name nor a stock metadata match proves the CP dependency.

Only this one new diagnostic experiment is proposed. Native capture, dump bytes,
stack classification and restoration are unrun until coordinated GO. Pure source
mocks cover the one-shot trigger, identity refusal, offline-only CDB arguments
and unknown-diagnostic retention. They do not qualify native capture or symbols.
