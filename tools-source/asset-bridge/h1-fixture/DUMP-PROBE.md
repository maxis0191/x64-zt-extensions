# Original H1 fixture: exact IW7 dump preparation

2026-10-12: the source/light preparation below was followed by one separately
authorized **Compile A, passed**. The dump executable has not run. Compile B and
its separate 111-check Probe remain the earlier parser/converter checkpoint.
Neither compilation nor that earlier checkpoint is a native dump witness.

## Production fragments and adapters

`prepare_dump.py` reuses `prepare_native.py` and the same pinned checkout
`fab935826c898806855376662a8a03317b3ad8f1`. Parser declarations, complete H1
parser bodies, reviewed converters, production filesystem/allocator support and
original input bytes are identical to the B preparation. The separate profile
adds these verbatim production functions:

- `iw7/assets/xmodel.cpp`: complete `xmodel::dump`.
- `iw7/assets/xsurface.cpp`: `dump_subdiv`, `dump_shprobesimplexdata` and complete
  `xsurface::dump`.
- `iw7/common/havok.cpp`: version/header definitions, `validate_header` and
  complete `dump_havok_data`, with the real absent-data early return. Its header
  is included directly. This fixture rejects optional Havok before calling dump.
- The existing `assetmanager.hpp` dumper performs all serialization. There is no
  replacement native serializer. The existing `filesystem.cpp` writes the files.

`dump-source-contract.json` pins the four additional/reused source files by LF
hash; the resulting preparation binds **24 distinct production files**. Exact
fragments and generated inputs have individual hashes in its local receipt.
Minimal IW7 class declarations omit unrelated asset interfaces, as the existing
H1 declarations already do. This remains an extracted-body harness, not the
whole ZoneTool CLI, vtable or game database route.

The new hook runs after every existing parser/converter assertion. Its fixture
string bridge accepts only the original unresolved **token 0**, with the exact
source bone-array address, live H1 parser table and retained text `tag_origin`.
It rejects another token, wrong text or a second call. The token is unchanged
before and after dump. `bone_engine_token_resolved=false` remains mandatory;
`fixture_string_adapter=true` distinguishes this local bridge from engine SL
integration. This follows the animation probe's explicit local-string-adapter
approach, using the actual parser table rather than inventing an engine ID.

The exact filesystem targets `probe/dump/h1_original`. All four output
directories must be newly created and are held against rename/deletion during
dump. Only the original `.xmb` and `.xsb` names are allowed, each nonempty and
at most 64 KiB. Production `wb` IO is retained: this is fresh-directory isolation,
not a hostile-writer filesystem sandbox or proof that production IO checks every
write. Independent readback is required after the native stage.

## Independent readback

`inspect_dump.py` imports neither generator nor converter/preparer. It reuses
the independent H1 geometry/UV reader and the rig reader's bounded typed-name
OFFSET rule. Arrays must be unaliased for this exact profile; general pointer
graphs, subdivision, skinned streams and arbitrary H1 assets are outside scope.

It requires the exact original H1 input hashes, validates their cube geometry,
then reads every IW7 record in the production dump order. It checks model
metadata, required-pointer presence, absent optional fields/padding, root bits,
one LOD, bounds, bind pose, material/LOD/bone names, all 24 vertex field transfers,
the self-visibility word, 12 triangles and rigid coverage. Raw addresses are
ignored beyond required presence; they are process-dependent, not asset IDs.

The CLI accepts `--dump-root` and `--fixture-root` and reads at most 64 KiB per
file. Its report deliberately keeps `native_provenance_verified=false`: bind its
output hashes to `DumpArtifacts` in the actual admitted Probe receipt before
describing a native readback pass. Synthetic fixtures are only reader tests.

The new tests pass: 10 Python cases, including every byte truncation of both
synthetic outputs, bad tags/counts/aliases, pointer absence, field/dependency/
geometry changes, source drift/extra prepared files, and exact-body extraction;
21 pure PowerShell assertions for observation scope and locked artifact hashes.
The modified Plan tests pass 13 assertions. The existing runner's 24 assertions
and native preparation's 12 Python cases also pass. No native provider was loaded.
The first extraction check correctly rejected the assumed final newline; the
pinned files end in a namespace brace without that newline. The corrected bound
removes only that final namespace brace and retains all function bytes.

## Complete two-stage Plan, not execution authorization

Local preparation: `runtime/h1-dump-prepared-20261012-a`, **9 files / 78,842 bytes**.
Preparation receipt SHA-256:
`efae2f397fe228be05829fb5d79cd4c1a9179ad232b187dd7dd1690ab61cfc1d`.
Local Plan: `runtime/h1-dump-plan-20261012-a.local.json`, **68 bindings / 23,135 bytes**.
Plan SHA-256:
`328d765786859e435eaa0766153ca7a1b01802d55efbcdd50aea802c67e0abb2`.
`plan_native.py --dump` selects this profile. The Plan binds the new preparer,
adapter, reader, source contract and prepared fragments as well as the existing
compiler/job/scheduler/observer inputs. Read-only `Run-H1Native.ps1` verification
passed all 68 bindings. Its proposed `runtime/h1-dump-observation-20261012-a`
root was absent at this preparation checkpoint. The separately authorized
Compile A below subsequently created its compile stage; Probe remains absent.

| Stage | Reservation | Deadline | Acceptance |
| --- | --- | --- | --- |
| Compile, separate GO | 4 GiB physical / 6 GiB commit | 120 s | Existing reviewed compiler/telemetry closure on the original job, locked EXE/OBJ/PDB, zero root exit, closed tree and released lease |
| Probe, another GO | 256 MiB physical / 256 MiB commit | 15 s | Successful Compile receipt for this exact Plan/EXE, original fixture locks, all inherited checks, exact dumps and scope assertions, closed tree and released lease, two output hashes |
| Independent Python readback | Light, four inputs <=64 KiB each | Expected under 1 s; stop if anomalous | Full profile check and output hashes matched against actual Probe receipt; no native run |

Both native stages retain 5 s cleanup, 1 MiB parser pool, one compiler without
PCH or `/MP`, 85% system commit ceiling, and **32 MiB combined output** including
1 MiB metadata reserve. Reservations are estimates, not measured peak usage or
kernel memory quotas. Earlier B consumed 18,008,273 output bytes; additional dump
template/debug data can change that, so the 32 MiB check stays mandatory.
New source/preparation/Plan files together are far below the 30 MB preparation
cap. No clones, downloads, new framework or stock were needed.

Use the same `Run-H1Native.ps1 -PlanPath <absolute plan> -PlanSHA256 <hash>` for
read-only verification. Only a new coordinator GO may add `-Stage Compile -Run`.
After inspection of that receipt, another GO is required for `-Stage Probe -Run`.
Then run `inspect_dump.py --dump-root <run>/probe/dump/h1_original --fixture-root
<original generated root>` and record hashes alongside the Probe receipt. A
failure preserves its outputs and receipt; do not overwrite or rerun that root.

B's prepared files still pass their original read-only preflight. Its Compile
receipt, Probe receipt and stdout hashes were rechecked unchanged. Historical
Plan F is retained as evidence; the runner source has evolved, so its old source
bindings are not authorization to rerun the current runner. No evidence file or
shared native E7 input was rewritten.

## Dependency handoff toward an FF

The proposed dump keeps `paris_h1_original_material` as a **name-only reference**.
The LOD names `paris_h1_original_cube_lod0`; its matching file is emitted but the
converted model's in-memory LOD stub still has no linked geometry. Neither fact
establishes material completion, FF dependency resolution or rendering.

Reuse the existing Beacon authoring and rig/FF workflow after a native readback
witness. The existing surface is `community_beacon_material_a`, original color
image `community_beacon_color_a`, technique
`mopw_l_sm_replace_i0c0s0o0n0p0`, with recipient normal-image dependency
`park_clown_zombie_shoes_n_3e46d100_packed_nog`. Those recipient names require
fresh strict dependency resolution in the chosen FF context; they are not H1
material conversion. The existing surface preparer uses `-strict-content-sources`.

Root/model ownership must define an explicit new material-binding profile or
reviewed material-name alias before packaging this model. Do not silently rename
the original reference, substitute arbitrary material bytes, or edit a binary
dump to pass a reader. A changed binding needs corresponding source/reader/Plan
evidence. Reuse the current dedicated/FF tools with separate admission, then
build, verify, re-dump and independently read the actual FF output as in the rig
workflow. Game/appearance acceptance remains a later, separate boundary.

## Authorized Compile A, 2026-10-12 09:43 UTC

The coordinator independently reviewed source commit
`65b31627fe15cefa46cdadf9d1f5f485cf8d0730`, then authorized exactly one Compile
phase of the Plan above. Fresh preflight verified all 9 prepared files, 24
production sources and 68 bindings, clean source, absent output and zero leases.
Main retained its existing identity/hash. The current origin/main resource
workflow was fetched and read before admission.

The exact planned `Run-H1Native.ps1` invocation with `-Stage Compile -Run`
passed with exit 0. Admission started `2026-10-12T09:43:05.8431723Z`;
acceptance took 3,196.0946 ms and the receipt finished at
`2026-10-12T09:43:09.2505238Z`. Reservations stayed 4 GiB physical / 6 GiB
commit, 120 s, 32 MiB output and 5 s cleanup. These are budgets, not measured peaks.

The original compiler PID 14784 was created at `09:43:05.9507343Z`. Its exit
was 0. Two captures at `09:43:08.8643618Z` and `09:43:08.9352827Z` identified
only vctip PID 32148, creation `09:43:07.4982677Z`, parent 14784, in the
original job. The existing reviewed closure terminated only that job, observed
root exit 0 / ActiveProcesses 0, captured an empty member list, then independently
polled root exit 0 / ActiveProcesses 0 again at `09:43:08.9542653Z`.
Tree closure and lease release passed; no quarantine or retry occurred.

Compile receipt: 6,229 bytes, SHA-256
`f0438da3dca9dbf13ba18e1d60a94c2520bde098cdddc56a91dc6bfba9e6e9a0`.
Executable: 1,331,200 bytes, SHA-256
`15aeb2e9da13a96e1b61045ee4c4f275113ff680af945ce48c0b764f0d7080d6`.
Six compile files total **19,024,147 bytes**. Stdout is 1,248 bytes with the
two existing production `strcpy` C4996 warnings; stderr is empty. All OBJ/PDB/log
hashes and sanitized closure evidence are in
[dump-compile-observation-2026-10-12.json](dump-compile-observation-2026-10-12.json).

At `09:43:23.6223220Z`, a fresh inventory found zero leases and no probe,
compiler, linker, telemetry, ZoneTool or CDB residue. Main was the sole game
process, PID 27784 / creation `00:52:28.7133740Z`; its image hash was rechecked
unchanged. Read-only Probe Plan verification subsequently passed all 68 bindings
and the successful Compile receipt without loading types or acquiring a lease.
The Probe directory is absent. **No Probe, native dump/readback, FF or game test
was authorized or run.** The unique Compile GO is consumed; a separate Probe
GO is still required. This source/evidence belongs to the tranche after PR154.
