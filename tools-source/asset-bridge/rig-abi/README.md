# XSurface +0x58: bounded offline write observation proposal

Status, 2026-10-12: **source-only preparation; no native GO**. The loader arm
instruction is unresolved. The included context deliberately cannot emit usable
commands. Material C remains waiting; this lot performs no resource measurement,
installation, stock staging, build, native launch, attachment or redump.

The target is one eight-byte field in the first original rig surface during an
offline ZoneTool load of recipe E. Paris Main, test dedicateds and game clients
are outside this observation. A matching address is not proof of field semantics.
Existing strict readers and the original `FailedRestored` result stay unchanged.

## Established inputs, not new dump analysis

The parent audit establishes that the FF writer zeroes XSurface offsets 88 and
96, and that the existing raw capture has `XSurface+88 == XModelSurfs.name` before
the original `DB_AddXAsset` call. We accept that starting evidence here; we do not
repeat the dumper audit or mask fields. The tracked attempt record is
`animation/rig/RIG-RUN-2026-10-12-B.md` (recipe E, retained attempt B).

| Input | Pin / role |
| --- | --- |
| Zone | `sdk_original_rig_probe` |
| FF | 1,064 bytes; `ea7ba4be1d5e6f0878431b51e7b9b1ba9d2b10bf74b1ad21da14d55c414e145d` |
| Profiles | `paris_doom_skin_two_bone_first_a_lod0`, `paris_doom_skin_two_bone_second_a_lod0` |
| ZoneTool source | `fab935826c898806855376662a8a03317b3ad8f1`, reviewed candidate patches retained |
| Candidate executable | `e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04` |
| Candidate PDB | Receipt hash `62b90fd57ec853f6366a768ae43f86186fba8d6b7d4443b9a5ae89221c41a1de`; not rehashed in this lot |

The retained offline verify invocation is `zonetool.exe -headless
-unbuffered-io -strict-content-sources -verifyzone sdk_original_rig_probe`.
This is a reference to the earlier phase, not a launch instruction. Its work
directory has already been restored. Preserve its FF, state, logs and closure
receipts; a future observation needs its own admitted run and restoration record.

## Available debugger and symbol evidence

The installed package is Microsoft.WinDbg `1.2606.22001.0`; its amd64 CDB,
DbgEng and DbgHelp report file version `10.0.29617.1000`. Read-only file checks:

| File | SHA256 |
| --- | --- |
| `cdb.exe` | `5f54abafca3ae5638bbf807d402fabb350a64575c1dfa9fbfc7f5732df5bee67` |
| `dbgeng.dll` | `4352756685e7325288e54abb3281e768637987517be8575ec4450e4b4421842f` |
| `dbghelp.dll` | `ea639fc67cc1430b66b71ef63a2ec72ea92879cca7e665bb10ae33c4468094f9` |

`symbol_identity.py` read 795 bytes of PE metadata and 137,588 bytes of PDB
metadata using seeks. Both report GUID
`aa767c25-a609-474e-a2de-9922d7dc159b`, age 1. PE preferred base is
`0x160000000`, image size 69,607,424 bytes; file sizes are 21,696,512 and
135,532,544 bytes. This confirms the host symbol pair, not its full current
hashes, runtime mapping, loader semantics or stack quality. No symbols were
downloaded or loaded in a debugger. The reader caps total metadata reads at
4 MiB per file and refuses unsupported layouts; it does not read whole files.

Existing Ghidra launchers were not located in the scoped project tool roots
checked. That is not a machine-wide absence claim. CDB already supplies the
bounded disassembly/stack facilities needed for the proposed next investigation;
no installation is justified by this plan.

## Locate the correct loader boundary

Pinned local source gives these **reference virtual addresses**, not validated
live addresses:

| Anchor | Reference | Source under ZoneTool `src/zonetool/` |
| --- | ---: | --- |
| `DB_LoadXAssets` | `0x140A78630` | `zonetool/iw7/functions.hpp` |
| `DB_AddXAsset` detour entry | `0x140A76520` | `zonetool/iw7/zonetool.cpp` |
| `g_streamPos` | `0x145687E30` | `game/iw7/symbols.hpp` |
| XMODEL_SURFS type | 7 | `zonetool/iw7/structs.hpp` |

No reviewed address for `Load_Stream`, `Load_XSurface`, `Postload_XSurface`,
`varXSurface` or the copy-return instruction was found in the scoped symbols.
The header describes XSurface as 256 bytes, and XModelSurfs as 56 bytes with
`name` at +0, `surfs` at +8 and `numsurfs` at +16. Header names such as
`blendVertsBuffer` at +88 and `blendVertsView` at +96 are hypotheses about
meaning, even though the offsets are compiled assertions.

`main.cpp` loads `iw7_ship.exe` through the custom loader. `loader/loader.cpp`
copies sections, imports, TLS and exception metadata and replaces PE headers.
Consequently `lm`, the host preferred base and a matching host PDB do not by
themselves identify the mapped retail code. Do not blindly add an ASLR delta
or force-load the host PDB over retail addresses. Record actual mappings,
retail binary identity, code ranges and a small byte anchor before interpreting
an address or setting an execution breakpoint.

Future discovery, only after a separate native authorization and complete
admission, is bounded to one offline load and at most four code windows of
256 bytes each. First use the local matched PDB to identify host loader and
registration stubs. At the mapped registration entry for asset type 7, validate
the exact allowlisted name with bounded reads; capture six stack frames. Review
the retail caller and its call chain to locate the surface array copy and the
immediate return before pointer fixup/postload or renderer callbacks. Stack
unwind failure is a coverage gap; do not invent caller identities from nearby
addresses. Stop if these windows cannot establish the boundary; no broad scan,
TTD recording, complete memory dump or automatic repeated run is proposed.

Registration is useful for discovery only: the field is already nonzero there.
The earlier store cannot be observed retroactively. A second load for the
actual watchpoint requires the reviewed discovery result and a new run-specific
context; never reset or replay the engine in an existing process to fake it.
If a static small-symbol/code investigation establishes the boundary first,
the discovery run may be unnecessary, but that result is not available now.

The arm-point review must establish all of the following in the real stopped
process, with evidence bound to its exact creation time/path/hash and mapped
retail identity:

- The initial copy of the selected 256-byte XSurface has completed; the selected
  instruction is a real instruction boundary before any relevant fixup/postload.
- The parent name is loaded, count is one, and `XModelSurfs.surfs` points to this
  allocation. Both +0x58 and +0x60 are zero. If these conditions never coexist,
  this capture design is insufficient; do not move the breakpoint after a store.
- The record remains alive throughout the observation, and the bounded earlier
  code path explains its allocation/copy. The supplied code bytes match the
  mapped arm instruction. A name match alone is not provenance.
- All threads are stopped, the debugger is in the exact launch-owned process,
  all discovery breakpoints are removed, and the breakpoint table is empty.
  Verify debugger coverage for the loader thread and possible new threads;
  do not infer a no-write result when thread coverage is uncertain.

## Smallest write capture

`capture.py emit` is a pure file generator. Its context requires the reviewed
phase, literal addresses, 8..32 anchor bytes, pinned FF/tool hashes, process
identity and external admission/ownership/deadline attestations. These fields
record upstream checks; the generator cannot independently prove them. The
checked-in template leaves them unset and is rejected. No runtime addresses or
sample launchable context are shipped.

The generated `arm.cdb` uses explicit MASM evaluation and nested readable-range,
identity, code-byte, array/count, exact NUL-terminated name and zero-field guards.
It reserves only pseudo-registers t0..t3 and breakpoint ID 3 in a fresh session.
It attempts `ba3 w 8 /1` on XSurface+0x58, prints that breakpoint and **stays
stopped**. It emits `BP_PRESENT` only if `@$bp3` equals the exact watch address.
`ARM_ATTEMPT_STOPPED` alone is not proof that CDB accepted the breakpoint:
the supervisor must also require the acknowledgement and absence of debugger errors before issuing `g`.
No resume, native launch/attach, target memory write, kill or detach command is
generated. If any guard fails the process remains stopped.

At the first covered write, the one-shot is removed and commands record PID,
TID, trap RIP, the two record addresses, old/new eight-byte values and name
addresses at arm/hit. They recheck readable records, shape and exact name, then
request `kv 6` and stop. The target is never resumed automatically. A same-value
write also counts as the first write. One hit may therefore be inconclusive
about the later observed nonzero value; this does not authorize another run.
The eight-byte watch location must be aligned, and breakpoint command lists
run after `g`, not stepping. See [Microsoft ba documentation](https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/ba--break-on-access-).

`capture.py report` accepts a maximum 256 KiB UTF-8 capture and exactly one
ordered ARM/WRITE/STACK/STOP sequence. It rejects refusal markers, foreign
nonces, duplicates, truncation, allocation/PID/value discontinuity and stacks
over 8 KiB. Prompt echoes are ignored. It reports only `zero`,
`equals_current_name_address`, `equals_name_address_at_arm` or
`other_nonzero_unclassified`. It always leaves semantic acceptance, verified
stack frames, full FF verification and process-closure verification false. Parsing is evidence
structuring, not evidence authentication; retain the original log/context hashes.

Call the instruction value **trap RIP**, not proven store RIP. Establish the
actual store boundary from the previously mapped function, verify its effective
address and width against the watched bytes, and classify its code owner
(retail loader, ZoneTool detour, renderer hook, unknown). Do not use `RIP-1` or
unanchored backward disassembly as proof. A small reviewed code window after the
stop, together with the stopped thread's bounded register context, can supply
this evidence without dumping assets. Account for possible writes by other
threads before the debugger stops them; the sampled new value alone does not
identify the store's operand. Do not infer a GPU object
or valid engine field from an address equality, module name or stack alone.

## Required supervisor, bounds and closure

A source-only original-job supervisor and concrete CDB/Python qualification
runner now exist; see [SUPERVISION.md](SUPERVISION.md). Its only executable
recipe is an explicitly requested fixture. Retail mode is rejected before launch
and remains unavailable until locator, mapping and stopped-identity bindings are
reviewed. The fixture must validate CDB syntax and original-job behavior under a
future separate GO. Python/PowerShell simulations do not validate CDB parsing,
hardware thread coverage, asynchronous break or Windows job behavior.

| Budget per serialized retail offline observation | Proposal / required behavior |
| --- | --- |
| Physical / commit | **10 GiB / 14 GiB** complete group: existing rig FF 8/11 plus documented debugger 2/3; estimate, not measured peak or admission |
| Admission | One account-wide heavy group; available RAM must fit, no RAM reserve; independent 20% commit reserve with 4 GiB minimum; fresh policy/preflight required |
| Concurrent native work | One CDB-owned ZoneTool target tree; no build/compiler, server, client or parallel discovery run |
| Wall time | 240 s total observation; armed continuation at most 10 s inside that limit; at most 30 s additional bounded drain/closure |
| Evidence storage | 1 MiB hard cap for new context/log/report/code/closure records; raw CDB log 256 KiB, stack 8 KiB, code windows total 1 KiB |
| Stock/symbols | Reuse retained original FF and suitable stock through reviewed staging; no full copy. Local matched PDB only, no network symbol server/cache growth |
| Native hits | One selected surface, one hardware watchpoint, first write only; no automatic rearm/retry |

The 8/11 basis is `animation/rig/CHAIN-PLAN.md`; debugger overhead is
`docs/DEBUGGER.md`. Discovery and capture each require this complete budget and
run sequentially. Tool-image/PDB source verification, staging and capture must
stay inside the future admitted group; no repeat hashing of the frozen stock
outside it. Current estimates cannot be reduced to evade admission. Retained
staging manifests include 71 stock hardlinks and a 77-byte sentinel copy among
79 entries; reuse the reviewed per-file restoration protocol, not a wholesale
workspace copy. Do not modify the original failed run's state or receipts.

The separate Python/CDB protocol fixture has a fixed **4/6 GiB** estimate under
`iw7.rig-watch-python-cdb-fixture/1`. It does not load the retail workload above.
See [the component accounting and unmeasured limits](RESOURCE-PROFILES.md).
This distinction preserves the retail 10/14 estimate and the old refused fixture
Plans; it does not authorize a smaller retail run or any native execution.

The supervisor starts its deadline outside the debuggee, stops logging at the
cap, and owns both debugger and debuggee in a registered job. On a hit, refusal,
timeout, load completion without a hit, exception or output cap: retain the
reason, break only the owned target if needed, remove owned breakpoint ID 3
with the guarded `clear.cdb` while paused, then close the exact owned job through
the existing identity-bound phase helper. The one-shot already removes itself
on a hit; clearing an absent owned ID is harmless but must not be interpreted as
capture success. Never use `bc *`, detach and leave the target running, or issue
an unguarded `q` against an arbitrary attached process. CDB user-mode quit can
terminate its target; see [Microsoft session closure guidance](https://learn.microsoft.com/en-us/windows-hardware/drivers/debugger/ending-a-debugging-session-in-windbg).

Retain PID/creation/path/hash, lease, debugger exit, original root exit where
available, zero active job members and restoration manifest before releasing
admission. If break/close cannot be confirmed, report the ownership/closure
failure and retain the lease; do not restore files still in use. A deadline or
deliberate stop is diagnostic closure, not a successful FF verification. No-hit
without a proven observed interval/thread coverage is inconclusive.

## Source verification and next action

Run the small synthetic tests from the repository root:

```powershell
python -B -m unittest discover -s tools-source/asset-bridge/rig-abi -p test_rig_abi.py -v
```

For future reviewed contexts, the generator interface is `capture.py emit
--context <private-context.json> --out <new-private-directory>`. The parser uses
`capture.py report --context <same-context.json> --log <bounded-cdb.log>`.
Keep outputs in ignored runtime; emitting files never grants native GO.

Capture/identity checks: 20 synthetic tests pass, including malformed PE/PDB tables,
bounded reads, mismatched symbol ages, context/address injection, unresolved
gates, one-hit continuity, replay/truncation refusal and name-value categories.
The initial test run exposed prompt echoes being mistaken for refusal output;
the parser was corrected to match actual refusal lines and that regression passes.
Source review also corrected nested breakpoint-string escaping; its roundtrip
test preserves the inner printf escape, without claiming actual CDB validation.
The documented `r` destination syntax is now `r $t0 = ...`, with `@$t0` retained
only in expressions. The destination correction has a source regression test;
it has not been executed in CDB. See [Microsoft pseudo-register syntax](https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/pseudo-register-syntax).
PE/PDB matching above is a separate current read-only check. CDB has not executed
these fragments. No engine write, rendering, semantic acceptance or gameplay
result is claimed.

Next: parent independent source review and integration. The animations chat owns
the parallel light loader-location investigation in `locator/`; this capture
lot neither duplicates that search nor modifies its files. Resolve the loader
boundary and supervisor gates before any separately authorized native investigation.
Do not promote the ABI, alter strict acceptance or schedule a run from this plan.
