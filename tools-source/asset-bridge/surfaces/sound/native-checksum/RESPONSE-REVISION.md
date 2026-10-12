# D8004 response correction: Plan E preparation record

Update: the single subsequently authorized Plan E invocation is recorded in
[BUILD-E-RESULT.md](BUILD-E-RESULT.md). All eight compilations passed, both native
checksum probes passed, and the final link failed with LNK1158. The preparation
and pre-execution validation below are retained as historical evidence.

The failed Plan C / host D attempt is committed separately in `ac93d18` before
this correction. Its response files, Seal C manifest, logs and 1872-byte failed
output remain immutable. No compiler was invoked to investigate or test the fix.

The first native `cl` diagnostic was D8004: `'/D' requires an argument`. Its
response file placed each `/D` on a separate line from its macro. The same
serialization occurs in all eight compile responses: eleven definitions in
each probe/common compilation and twelve in each of the five ZoneTool consumers.
`response_revision.py` joins each definition to the option on the same line,
producing `/DNAME`. It preserves the exact macro spelling/order and every other
compiler option, including `/WX`, `/W4`, `/O1`, `/MT`, `/fp:precise` and `/Y-`.
The `EXPERIMENTAL_IW7` definition remains exclusive to the five ZoneTool units.

Because the previous native output now contains evidence, all private output
references move from `runtime/zt-sound-md5-b` to the still-absent
`runtime/zt-sound-md5-c`. The twelve fresh response files contain exactly 93
definition joins and 33 output-path relocations. Link/library responses only
change the private output paths. No original source, shared object, library,
PDB, PCH, warning policy or runtime asset is changed.

The small preparation lives under
`runtime/content-surfaces/original-sound-checksum-build-review-b`:

| Item | Bytes | SHA-256 |
| --- | ---: | --- |
| Twelve revised responses | 81758 | Individual hashes in the revision manifest |
| `response-revision.local.json` | 11026 | `ef4cb1e65d3f7394d2b18b71a692cf1b80a46b9f08f9f652ee4161e9ca74bb17` |

Preparation binds the original command review and Seal C hashes. It re-reads
only the small old/new response sources, reconstructs the permitted transformation
and requires exact byte equality. A missing macro, another option used as its
argument, duplicate macro, unexpected count or additional byte change fails.
It does not create the native candidate or hash any large retained input.

These twelve new sources are explicitly **not members of Seal C**. Plan E lists
them as `response_pins` and also as ordinary bootstrap `source_pins`. The entry
therefore opens their read guards before hash/import and retains those guards
through the whole build lifecycle, including AppDomain quarantine if required.
The PowerShell and Python contracts require exactly one matching guarded source
and command per new response; unknown, duplicate, old-seal or mismatched paths
fail. The worker checks exact length and digest before each compiler/linker/
librarian invocation. The 1410 original sealed inputs remain separately guarded
and verified before/after a future admitted run. No old manifest is relabelled
or altered, and no new full sealing run occurred.

The future Plan and persistent-host command live under the existing
`runtime/content-surfaces/original-sound-checksum-build-plan-a` directory:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `build-plan-e.local.json` | 36830 | `65e4ddc10524e6f6d2e3a596c8a480ca95be7be336555c30a41404597350f2e4` |
| `build-command-e.local.ps1` | 1083 | `ff58ac47d7c873fbf07244f0368a80174d6809beaa74582e72558ccca9ce22d7` |

The command is prepared only. A future explicit GO must load it in a fresh PS7
`-NoLogo -NoProfile -NoExit` host, which remains alive until original-job closure,
released admission and absent quarantine are confirmed. It must not be invoked
from the old ephemeral wrapper. Fourteen native stages, the 4/6 GiB admission,
512/768 MiB output budgets, one-hour observed global deadline and unchanged
two-second qualified drain remain as reviewed. The original/corrected C++ probe
expectations and all FF/SAB/playback gates remain unchanged.

Source verification passes: four new Python tests exercise byte-exact response
repair, LF/CRLF preservation, unchanged warning/options and new-source binding
refusals; all eleven checksum-build Python tests pass. Seven PowerShell response
contract cases pass. Default Plan E passes in PowerShell and Python. The entry
test now denies fifteen writes, including a copied revised response, and proves
seven fixture files become writable after return. Existing thirteen lifecycle
cases / 72 assertions still pass. No native type or actual reservation is used.

This is a source correction proposal. It has not yet established that MSVC
accepts the revised response syntax, that either native probe passes or that the
checksum fix works in SAB/FF output. Next action is independent Plan E/source
review and a separate coordinator GO. No retry is authorized by this document.
