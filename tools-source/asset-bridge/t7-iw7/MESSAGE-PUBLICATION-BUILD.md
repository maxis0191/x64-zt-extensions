# Future two-TU publication build profile — source delta, 2026-10-13

This change depends on source overlay commit
`91eee780a6315e56713350203147a2b3f35fbb32`. It adds the preparation/runner contract
needed to compile both corrected translation units. **No executable build plan,
native build, new binary, catalogue or asset extraction was produced.** The next
heavy slot remains assigned by the coordinator; this source change supplies no
T7 execution authorization.

## Ownership and historical boundaries

The delta owns `prepare_build.py`, `Run-T7Build.ps1`, their Python/PowerShell tests
and this document. The overlay body/generator, `T7Build.Profile.ps1`, H1 ownership
and compiler providers, cached objects, old prepared roots and historical
plans/receipts remain untouched. The runner source changes for the new profile;
an old plan is not rewritten to point at a new provider hash or reclassified as
a new successful build.

The new selector is `--catalog-message-publication`, mutually exclusive with
the existing diagnostic selectors. Its build-profile name is
`t7-catalog-message-publication`, with schema
`iw7.t7-message-publication-build/1`. Historical profiles retain their existing
main/link or link-only paths, and reject the new CLI rebuild marker even if it
is falsely set to a string or false value. The old message profile still cannot
silently consume a changed CLI source.

## Mandatory new compilation and pins

Preparation first verifies the same ordinary D2 and retained successful compile
proofs, then applies the reviewed publication overlay to both source strings.
Both main and CLI must differ from their retained sources; every other reused
source/header must remain byte-identical. The new reuse descriptor requires
the Boolean values `RecompiledMain=true` and `RecompiledZonetool=true`.

The new profile binds all existing trace/message fields and D2 proofs, plus:

| Pin | Required source/output |
| --- | --- |
| `PublicationWiring` | `prepare_message_publication.py` |
| `PublicationSource` | `native_message_publication.inc`, at most 16 KiB |
| `PreparedCLI` | the new prepared `zonetool.cpp` |
| `MainResponse` | prepared-root parent `main.obj.rsp` |
| `CLIResponse` | prepared-root parent `zonetool11.obj.rsp` |
| `LinkResponse` | prepared-root parent `link.rsp`, at most 256 KiB |

`PreparedMain` and the legacy trace wiring remain separately bound. Each pin
must match one text binding's exact path, size and hash. The runner locks and
verifies these text bindings before reading the response contents or acquiring
admission. These are plan-bound hashes, not invented fixed hashes for an
unbuilt executable.

The required stage sequence is exactly **main, zonetool11, link**. Each stage
must use its one pinned response file and expected compiler/linker image.
Main and CLI each guard their object, private compile PDB and dependency JSON;
link guards its EXE, PDB, import library and exports. Missing/extra artifact
guards are refused.

The runner independently inspects the guarded response text for this profile:

- Each compile command has one `/Fo`, `/Fd` and `/sourceDependencies` target
  in its own fresh stage and ends with the exact prepared source path.
- Link `/OUT`, `/PDB` and `/IMPLIB` each occur exactly once and name the exact
  `link/zonetool-t7.exe`, `.pdb` and `.lib` stage artifacts.
- Multiline compile commands and nested response-file arguments are refused.
- The link contains exactly 413 unique direct quoted object rows. Main and
  `zonetool11` must each occur once at their new stage path. Old objects, missing
  rows, duplicate basenames, extra objects in the flags or nested response files
  are refused.
- The only retained dependency stage among the three replaced TUs is `xpak`,
  whose linked object must match that retained root. The root itself is checked
  against the original prior plan before any native action.

The existing compiler ABI/flags, ordered E7 link inputs, original-job ownership,
closure/quarantine handling and source/binary pin guards remain in force. These
new checks do not replace manual review of the final plan and exact source pins.

### Independent-review P2 correction

The initial profile commit `847ce016` passed 102 source checks but accepted an
expected quoted `/Fo` plus a second unquoted `/FoC:\outside\stolen.obj`. It also
accepted `/OUT:C:\outside\stolen.exe` with the exact 413 link objects. Text hashes
could bind these incorrect responses; artifact checks after execution were too
late to prevent the redirected writes. Both cases were replayed against the
original validator (accepted) and the corrected validator (refused).

The correction parses the entire response into arguments before checking output
options. Spaces/tabs delimit arguments outside quotes; quoted segments can occur
inside arguments. The output scan recognizes `/` and `-`, case variants, attached
or separate values and optional colons. Duplicate destinations are refused even
when both values are correct. Missing or mismatched paths are refused before any
admission. The existing filename-free `/PDBCompress` flag remains supported.

This is a deliberately bounded parser for the generated response syntax, not a
general MSVC command interpreter. Escaped, doubled or unclosed quotes, control
characters and response indirection are refused. It follows the quoted-segment
and space/tab rules documented by [Microsoft's argument parsing reference](https://learn.microsoft.com/en-us/cpp/c-language/parsing-c-command-line-arguments?view=msvc-170)
for the accepted subset; the optional colon/space form of `/Fo` is documented in
the [MSVC output option reference](https://learn.microsoft.com/en-us/cpp/build/reference/fo-object-file-name?view=msvc-170).
No profile schema, pin name, binding or stage contract changes in this correction.

## Reuse and estimated growth

The 413-object link will consist of **411 reused objects** (410 original E7
objects plus the qualified `xpak.obj`) and **two newly compiled objects**. The
18 project libraries and one resource remain reused. The fixed `ReusedObjects`
field remains 410 because it counts original E7 inputs, not additional retained
T7 compilation. The qualified 51-check name-helper proof is retained; the helper
is not rerun by this three-stage profile.

The previous main/link profile reused both CLI and XPAK stage outputs. This
profile removes the old CLI object/PDB/dependency pins from its reused-artifact
set; the prior receipt is still retained as historical compile evidence.

Size estimates below come only from small retained receipt metadata, without
opening or rehashing their binaries:

| Historical reference | Object | Compile PDB | Dependencies | Total |
| --- | ---: | ---: | ---: | ---: |
| message A main | 572842 B | 1732608 B | 62096 B | 2367546 B |
| original successful CLI stage | 3630389 B | 3559424 B | 76744 B | 7266557 B |

Relative to another main/link build, recompiling the CLI adds an indicative
**7266557 bytes (6.93 MiB)** plus its logs and any size change from the new source.
Message A's four link artifacts total 158219173 bytes. Reusing that historical
link size with the two historical compile totals gives about **160.08 MiB** of
new build artifacts, before logs and unmeasured compiler/link growth. This is an
estimate, not a measured future run or a guaranteed fit.

The overlay source itself adds 4448 bytes to the prior message main and 54 bytes
to the ordinary CLI. Existing source preparation A is preserved. No new game
stock or cache copy is needed for this source/build-profile work.

The existing admission estimate remains 4 GiB physical and 6 GiB commit, with
sequential stages, 120 seconds per compile/link, 600 seconds for the group,
256 MiB output cap and 1 MiB metadata reserve. The estimates are not silently
reduced and native input checks still occur only under the future reservation.
Actual growth/resource observations belong to that later admitted run.

## Validation and remaining gate

- Python build preparation/reuse tests: **20 passed**, including three tests
  reading only the exact retained CL/link command logs, plus stale/missing/
  duplicate CLI object and changed-source refusals.
- Publication overlay source/scheduling-model tests: **16 passed** unchanged.
- Actual PowerShell profile/response validators, extracted without executing
  the runner: **366 checks passed** after the P2 correction, including historical
  profile cases, pins/stages/artifact guards, both review reproductions, every
  output option across quoted/unquoted/colon/separate/case/prefix forms,
  duplicates, redirected/missing values, malformed quotes and paths with spaces.
- Retained main/CLI/link RSP text passed the actual corrected validator with the
  retained CLI object path adapted only in memory to the expected fresh path.
  All original flags, including manifest quoting and `/PDBCompress`, were kept.
- Python build preparation/reuse tests were replayed after the P2 correction:
  **20 passed with no skips**, reading only retained source and command text.
- Existing deadline/finalization fixture: **3 passed**, no native types loaded,
  zero child processes and no lease.

The first Python pass skipped the three retained-command tests until their
existing source/log locations were supplied; the final pass ran all 20 with no
skip. Tests manipulate source strings and original synthetic metadata, not a
launchable real build plan. No native compatibility, executable hash, measured
performance or real diagnostic publication is claimed.

Next: coordinator review/integration of overlay plus this dependent delta.
Only after separate authorization should it prepare and inspect an exact new
plan, confirm both new object paths and all pins, admit the group, compile/link,
and then schedule a separate catalogue run. The previous candidates and receipts
remain the historical record throughout.

The catalogue runtime's candidate-profile admission also needs a separate
reviewed extension for this new build-profile name. This delta does not change
`t7-bridge` or disguise a publication-build receipt as the old message profile.
