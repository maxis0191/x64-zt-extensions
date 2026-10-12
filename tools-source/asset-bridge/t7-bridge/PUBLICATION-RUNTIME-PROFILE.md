# Catalogue admission for the two-TU publication build

`t7-catalog-message-publication` is a distinct candidate profile. Its build
contract comes from `91eee780a6315e56713350203147a2b3f35fbb32` and
`847ce016fda8f9b31e5cafbbf5285cce0857f4bb`; the response destination correction
is `bc89481edffd9ef2278f38e70f9e4afcccaee5fe`. This runtime delta does not
prepare a real build/catalogue plan, compile a candidate or authorize a run.

The catalogue qualifier requires the exact new name in both the guarded build
plan and its successful, closed, unexecuted receipt. It preserves the existing
D2/reuse provenance and diagnostic schemas, and also requires
`PublicationSchema=iw7.t7-message-publication-build/1`. The old message profile
cannot accept this receipt or a CLI recompilation marker.

All six new profile pins must agree between build, receipt and guarded catalogue
text bindings: publication generator, publication source, prepared CLI and the
three response files. Their canonical paths and existing size bounds are checked.
The receipt must be the new build root's receipt, bound by its own reviewed hash;
there is no invented fixed hash for a future executable.

The exact stage order is `main`, `zonetool11`, `link`, with two successful closed
Compile proofs and one Link proof for this build-plan hash. Both compile stages
must list their object, private PDB and dependency JSON; the Link stage lists its
EXE, PDB, LIB and EXP. These binary entries are metadata, never opened by this
qualifier. Both guarded dependency reports must identify the corresponding
prepared source. Only the qualified XPAK stage remains in the reuse roots.

The text responses must use the expected compiler/linker and their pinned paths.
Every `/Fo`, `/Fd`, `/sourceDependencies`, `/OUT`, `/PDB` and `/IMPLIB` destination
must occur once and identify its fresh stage. Quoted and unquoted duplicates,
alternate option case/prefixes, nested responses and ambiguous quote syntax are
refused. The existing `PDBCompress` flag takes no destination. Exactly 413 unique
direct object rows must link both new objects once and the exact retained XPAK
object; a stale CLI or main object is refused. These checks independently repeat
the reviewed build contract using only guarded text.

The profile adds exactly six catalogue bindings: five new profile pins (the link
response was already bound) and the CLI dependency JSON. An equivalent twenty-file
V3 collection with eight individual and twelve shared qualifications therefore
has 79 bindings instead of the historical 73. Old profiles keep their original
counts. Payload budgets, resource estimates, deadlines and output entry caps do
not change. The optional opaque manifest remains an independently selected
engine-output profile; it is not a message or build receipt.

Publication still uses the existing MSG `/1` parser and 8192-byte stderr bound.
Absent, partial and malformed records retain their existing outcomes; the new
profile cannot reconstruct a truncated record or establish catalogue success from
a completed build. Actual native publication, donor loading and compatibility
remain unproved until separately reviewed, admitted attempts.

`Test-T7CataloguePublication.ps1` uses invented in-memory build/receipt metadata
and small original response/diagnostic text fixtures. It covers missing stages,
stale objects, pin disagreements and bounds, provenance/schema changes, both TU
dependency reports, duplicate/redirected compiler/linker destinations, unchanged
legacy admission, qualified binding counts and partial MSG parsing. It creates no
operational plan and reads/hashes no EXE, OBJ, PDB, game asset or historical opaque
file. Existing trace, message, catalogue and bootstrap suites remain regression
checks. No historical A/B plan, receipt, alias or cached object is modified.

Next: independent source review and coordinated private integration of the build
and runtime changes, followed by a separately authorized two-TU build. The later
catalogue must bind the actual new plan, receipt, sources and output pins; closed
A/B attempts are never relabeled or rerun.
