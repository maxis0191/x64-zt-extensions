# Separate input sealing: prepared, not run

The coordinator requested an independently admitted read-only seal before the
native build Plan. `Seal-ChecksumInputs.ps1` defaults to Plan; only `-Seal` enters
the existing scheduler. No compiler, librarian, linker, native probe, job owner
or new native supervisor is used by this stage. The scheduler retains its existing
memory implementation. No sound sealing GO has been exercised at this checkpoint.

The metadata inventory contains 1410 exact existing files, 1103512385 bytes:

| Category | Files | Bytes |
| --- | ---: | ---: |
| Objects | 421 | 535713583 |
| Libraries | 42 | 341599252 |
| Includes | 814 | 34314052 |
| PDB inputs | 22 | 83451904 |
| Toolchain/interpreter images | 73 | 78936416 |
| Source and bindings | 38 | 29497178 |

The 421 objects are 408 unchanged E7 link inputs plus thirteen original common
objects used to compare archive member payloads. The libraries include the
recorded VC/SDK dependencies as well as eighteen project libraries. PDBs are
recorded linker inputs; E7's final PDB is not included. The shared 277938176-byte
PCH is excluded because all six replacement compilations use `/Y-`.

The include inventory comes from the five affected E7 translation units, their
PCH creator's dependency record and the common bit-buffer dependency record.
All nine explicit standard-library includes in the original C++ probe already
appear in those records. Narrow file listings add the fixed x64 compiler's
adjacent DLLs and English resource DLLs; there is no recursive Windows SDK scan.
The dependency/command records, source archives, patched private overlay, original
probe and qualified providers are also bound. Future compiler include reporting
must still reject an input absent from the seal; these old records alone do not
prove that a fresh `/Y-` compilation will consume exactly this closure.

The metadata inventory is local, 560366 bytes, SHA-256
`c97bbd45fd9b7d5284ca329db215e27210149d1869810d9bf9f9543a34cc12c3`.
It lives under `runtime/content-surfaces/original-sound-checksum-seal-plan-a`.
Current Recipe C is `seal-recipe-c.local.json`, 2457 bytes, SHA-256
`62bc96ad05af9f111ff63928be7d1c74ff2786e2309d3f4147441b77ee7cef1c`.
The short entry is `seal-command-c.local.ps1`, 565 bytes, SHA-256
`ce0ab2bb0204ab0633d9ffce250768f77856adc9f7e13d15d893eb9967b85cc5`.
It starts a fresh PowerShell 7.6.5 host with `-NoProfile -NonInteractive`, the exact
recipe path/hash and `-Seal`. This command is prepared for coordinator review;
its presence is not authorization to invoke it.

The proposed output is the currently absent
`runtime/content-surfaces/original-sound-checksum-seal-a`. Admission is Analysis,
1 GiB RAM / 2 GiB commit. Each file is read sequentially in 256 KiB chunks, twice:
2207024770 declared input bytes. Existing source-hash expectations are checked on
the first pass. Handles deny write/delete sharing and stay retained through the
second independent path read and completion of all file proofs. Metadata is
checked around the reads. Sources, objects, libraries, E7 and shared PDBs are
never modified or copied. All new output must fit 16 MiB.

The 120-second observed deadline is checked before and after each blocking read,
after pressure polling and during final receipt writes. It cannot preempt a
blocked filesystem call; a late return fails and records the observed read bytes.
The existing 85% committed-memory stop remains, sampled at most once per second.
Failures dispose input guards and release this read-only reservation; failed guard
disposal or refused release leaves the retained token explicit. A failed receipt
cannot qualify a manifest merely because its file was already written. Build
preparation must require the final `Sealed` state and released lease as well as the
manifest hash. Final accounting includes the serialized state itself.

Eight actual PowerShell source/mock cases pass 35 assertions: JSON integer
round-tripping, real FileStream write denial, two-pass byte accounting including
an empty file, metadata/digest drift, a slow read, a slow final state write,
read failure, duplicate refusal and release failure. No real reservation or
native type is used. An actual default Recipe C Plan also passed with Add-Type,
admission, CIM, process creation and reusable-input hashing trapped; native types
and the output directory remained absent.

Recipe A remains an obsolete, unexecuted preparation. Default Plan exposed that
PowerShell JSON reads attributes as Int64; the bounded attribute contract now
accepts Int32 or Int64, and the success test round-trips its fixture through JSON.
No input hashing, native build or native probe occurred during that correction.

Independent review then found that B checked source/recipe hashes before opening
its guards and importing the core. C opens recipe, entry and core read-sharing
handles before the first hash/parse. After discovering the inventory/helper paths
from the guarded recipe, it opens those handles before their hash/parse/import.
Hashing and JSON reads use the same retained streams. All guards remain open
through either Plan output or sealing completion and are disposed in one finally
block. No default-Plan exception releases them before import or output.

The added `test_seal_entry_guards.ps1` passes eleven assertions on disposable
copies. Seven attempted mutation intervals are denied: recipe/core at recipe
parse, core/inventory after successful hashing but before core import, and all
three at Plan output. The source stays unchanged, the Plan creates no output,
and a subsequent write succeeds only after Plan has returned and disposed its
guards. It uses no native type, reservation or large input. Recipes A and B stay
preserved, obsolete and unexecuted; the exact native-input inventory is unchanged.
