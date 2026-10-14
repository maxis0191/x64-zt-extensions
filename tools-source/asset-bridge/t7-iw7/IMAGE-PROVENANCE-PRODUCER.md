# Source-only image provenance producer wiring

The existing `prepare_build.py` now has an explicit `--image-provenance-v1`
selection. It requires the retained E5 publication recipe, selected render-only
V2 family and both prior compile proofs. Other observations, material-parts,
prepatch modes and explicit catalogue diagnostics are excluded before any
preparation IO. The frozen f2 API, source contract, fixture and renderer are
unchanged.

The producer applies the existing pinned image-provenance overlay after the
E5 source transition. It records a separate `ImageProvenance` marker and binds
both adapter sources, the header, entry, source contract and fixture. The
generated main/CLI source pair is still 43370/13052a66 and 130246/15d03375.
The main, zonetool11 and link recipe stays within the existing producer; H1
ownership, compiler/VCTIP closure, resource policy and `T7Build.Profile.ps1`
are unchanged. The explicit source payload bound is 288 KiB, as for parts.
The finite dated TZRES qualification remains the only accepted OS pin change.

`SourceOnlyPending` is mandatory for this new profile. The runner refuses
`-Run` before the source providers, input loop, scheduler, types, reservation
or child creation. Its source-only DEFAULT reports a null candidate and false
NativeTypesLoaded, BinaryInputsHashed, ZoneHashObserved, LeaseAcquired,
FilesCreated and Ready. It does not qualify the complete recipe or a binary.
There is no candidate EXE/PDB hash in this change and the old E/cce8 candidate
cannot be relabeled as provenance.

Local source checks execute the real selector and renderer transition, reject
conflicting profiles before preparation IO, compare the exact frozen f2 output
pair, and test the source contract/transition guard. They also execute the real
source-pending gate and confirm its ordering before imports/admission. The
historical parts guard remains covered. The first authored PowerShell check
found an incorrect contract field sort order; it was corrected. A legacy
extracted-AST test then found a new variable dependency in the streamed-pin
block; the block now derives the marker from its existing reuse object.

The real F fixture's 53 C++ assertions are still unexecuted. PR112 stays open
until they pass under its separate Root GO and original host/job closure is
confirmed. This dependent producer branch must not merge or deploy that API
implicitly. A later reviewed change must supply measured fixture provenance
and enable the full-CLI recipe under a new CPP GO. That full build, its artifact
and closure receipts, then a fresh native plan/ordinary DEFAULT and separate
native GO are distinct gates. Authentic textures, image body admission,
runtime ABI, pointer lifetime and owner gameplay remain unqualified.

Worker 51 owns producer/API wiring; 688 owns the existing Catalogue launcher,
allowlists and host guard; 5d owns the closed JSON result consumer. This change
adds neither a launcher nor a second capture pipeline. Existing owner client
and Main are preserved; these checks launch no game and read no SDK, binary,
stock or tlog bytes.
