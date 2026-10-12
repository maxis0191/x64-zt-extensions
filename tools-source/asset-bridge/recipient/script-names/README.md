# Two-key ScriptFile observer: source candidate only

This candidate answers the naming question left by [Recipient I](../SCRIPT-INDEX-ANALYSIS.md).
It preserves canonical `scripts/engine/utility` and numeric `2626` as two separate
requested keys. A source token table links them historically; no current native
observation yet establishes either live name or any alias relationship.

No compiler, linker, harness or native candidate has been executed for this
observer. E7, shared native sources, objects, libraries and PDBs remain unchanged.
The private build and subsequent engine witness require separate reviewed Plans
and authorization. This directory contains source, a checked patch, pure Python
validation and a **prepared but unexecuted** C++ harness.

## Observation behavior

The proposed fixed CLI is:

```text
zonetool.exe -headless -unbuffered-io -strict-content-sources -recipient-script-name-check cp_zmb
```

The new branch requires exactly one terminal donor argument, fixed to `cp_zmb`.
It clears dump/csv/verify mode, uses the same synchronous source-zone load helper
as Recipient I and never invokes the script exporter. It does not accept an
arbitrary name list, token map, payload export or fallback request.

`recipient_script_names.hpp` collects these small observations:

- Before filtering: callback, null-header, null-name, named, decimal-name and
  unmatched counts. After filtering: occurrences of each of the two exact names.
- Only for matching enum entries and direct lookups of those same two keys:
  raw content/database names, three declared lengths, type and default status.
- Process-local header identity **ordinals**, without pointer addresses. The
  same observed pointer must retain the same metadata; a second distinct pointer
  for one enum key refuses the report. Repeated occurrence of the same pointer
  is counted, without confusing it with an ambiguous distinct asset.

Both keys retain their own enum/direct slots even if a live lookup later reports
the same header. `token_alias_inferred` stays false. No name conversion, header
rewrite, serializer change or acceptance of `2626` as the existing utility export
contract is introduced. Negative/oversize lengths, inconsistent metadata, wrong
direct-entry type, missing metadata names and ambiguous matches fail closed.

The metadata interface has no compressed-buffer or bytecode pointer. The native
wrapper accesses only header names and scalar lengths; it does not read, hash,
decompress or serialize script buffers. `payload_bytes_read=0` describes these
observer operations, not the engine's normal zone-loading I/O. Unmatched entries
do not call the metadata factory; no global name sample is written.

Names accept at most 240 printable ASCII bytes and inspect at most one additional
termination byte. At most 4096 enum callbacks may read names/metadata. A later
callback captures a refusal and disables further observation reads; the engine
enumerator itself may still issue callbacks until it returns. Exceptions are
captured inside that callback and rethrown after the engine returns, avoiding
unwinding through the enum implementation. This is a read cap, not a guarantee
of aborting/preempting engine traversal or a proof arbitrary pointers are valid.

Independent review found the initial wrapper evaluated `script->name` before
entering the counter guard, so callback 4097 could still read that pointer.
The corrected API takes a lazy raw-name factory and invokes it only after
callback admission and the null-identity guard. The C++ harness now counts raw
name-factory calls across 4096 non-null callbacks, then requires the 4097th to
refuse without incrementing either name or metadata reads. Null identities also
must not call the name factory. This harness remains uncompiled/unexecuted.

The JSON output is at most 4096 bytes, at
`enemy-catalog/sdk_beacon_script_names.json`. Directory validation and the existing
exclusive `CREATE_NEW` writer/readback are reused. The `.csv` sibling check from
the reused path helper is conservative; final `.json` existence is enforced by
`CREATE_NEW`. The report contains no content hashes and always leaves script
bytes, closure and readiness false. Failure produces a bounded future phase log,
not a fabricated partial-success JSON.

## Pure tests and source check

The 27 Python checks pass with the explicit retained source path: 18 output
contract cases plus six source/preparer guards and three source-bound patch
checks. They cover canonical/numeric distinctions, populated-but-unmatched
enumeration, duplicate occurrences, conflicting identities, rejection of multiple
enum rows, name/type/length/count bounds, exact two-key ordering, duplicate JSON
fields, and refusal of payload/alias/readiness claims. These fixtures validate
the **reader**, not native enum or engine behavior.
The additional source guard checks admission-before-factory ordering and the
lazy wrapper call; runtime enforcement still needs the prepared native harness.

`test_recipient_script_names.cpp` exercises the actual header with invented
identities, canonical/numeric names, same/distinct pointers, null/unmatched
entries, lazy metadata calls, ambiguity and refusal bounds. It uses explicit
checks instead of release-disabled `assert`. It has not been compiled or run;
neither its runtime behavior nor the wrapper's engine ABI is qualified.

The source preparer checks the exact native source SHA and replaces only three
unique anchors: one include, one observer function, one CLI branch. Tests preserve
the complete original script index/export function text. `git apply --check`
passed against the clean retained native checkout; no patch was applied there.
The parent/native source pin is `fab935826c898806855376662a8a03317b3ad8f1`.
`source-contract.json` binds the candidate source files and rendered patch.

## Proposed private incremental build

Only `src/zonetool/zonetool/iw7/zonetool.cpp` needs replacement. The actual E7
compile tlog binds it to **`obj/zonetool9.obj`**, currently 8,027,786 bytes. The
link tlog contains 413 object inputs: reuse the other **412** read-only, preserve
all five earlier E7 overlays, and add one private replacement. Reuse the 18
project libraries and original resource input unchanged; no common library
rebuild is indicated by this header/function-only change.

The source compile record retains `/MT`, `/O1`, `/Zi`, `/W4`, `/WX`, `/bigobj`,
`/fp:precise`, `EXPERIMENTAL_IW7` and `/std:c++23preview`. Preserve the original
MSVC x64 ABI/definitions and original include directories. Use a private patched
source plus its sibling observer header, with the original IW7 source directory
as an include root so quoted `zonetool.hpp` and `../utils/gsc.hpp` still resolve.
Disable PCH use for this replacement (`/Y-`, remove `/Yu` and `/Fp`), and use
private `/Fo`, `/Fd` and dependency-report paths. Preserve `/fp:precise` when
removing the case-distinct PCH flag. Do not copy or update E7's PCH/compile PDB.
New header includes and the `/Y-` include closure require sealing and compiler
dependency verification; a source-level proposal is not that evidence.

Use the original link order/flags, substituting only `zonetool9.obj`; keep
`/INCREMENTAL:NO` and private EXE/PDB/import-library/temp paths. Do not invoke
the E7 MSBuild project or the 413-unit full-build retry loop. Preserve E7's
generated version include unchanged; identify the candidate by its distinct
receipt/source/patch/binary hashes, not by claiming a new upstream version.

The local **partial metadata** inventory is 432 files / 840,132,922 bytes:
412 objects, 18 project libraries, one resource and the E7 compile PDB. No bytes
from these binary inputs were read or hashed during preparation. This is not a
complete dependency seal: VC/SDK libraries, additional debug references, includes,
compiler/linker DLLs and source/provider bindings still need explicit qualification.
The earlier metadata draft accidentally counted `/IMPLIB` output as an input;
the retained `v2` inventory excludes it and is the only count used here.

The sound `native-checksum/SealInputs.Core.ps1` workflow is a reusable pattern
for bounded read-only sealing; its completed Seal C belongs to a different
input set and cannot qualify this candidate automatically. Reuse its admission,
guards, deadline/accounting concepts after pinning exact helpers and inputs.

For compilation, H1's current original-handle job supervision and verified
compiler/telemetry-child closure are relevant. Its `native_probe.exe` artifact
names, 30 MiB per-artifact checks and compiler-only result policy are specific
to that harness. They cannot be relabeled as this ZoneTool linker outcome.
An adapter must bind this candidate's artifacts, retain the original handles,
separate root exit from job closure, and refuse unknown residual processes.
Linker jobs require their own explicit completion checks. Do not adopt a PID or
weaken the telemetry gate to reuse the H1 entrypoint.

Proposed admission remains 4 GiB RAM / 6 GiB commit for sequential harness,
one replacement compile and one link, with 256 MiB generated-output stop and
120 seconds per compile/link stage, 600 seconds for the entire active group.
These are proposed conservative limits, not measured outcomes or an executable
Plan. Input-seal totals and budget are incomplete and must be reviewed first.
No automatic retry, full rebuild or budget increase follows a refusal.

The engine observation would be a later distinct 8/11 GiB transaction using
the existing complete stock profile. The current Recipient runner intentionally
accepts only E7 and its existing CLI phases; it cannot execute this new candidate
unchanged. Its guards must remain intact. A separately reviewed phase binding,
absent run root, stock hash budget, output accounting and exact restoration list
are still required before any native GO. No new runnable build/Run command was
created during this source preparation.
