# Authored ModelFF Source namespace and native path preflight

This is the Source correction following the
[closed D5 failure](../../docs/AUTHORED-PLATFORM-FF-D5-2026-10-15.md).
It rejects a known long effective path before admission and diagnoses material
JSON mismatches before required sidecar copying. It does not prove that MAX_PATH
caused D5, qualify an FF, or authorize another operation.

## Source sidecar before admission

The authored route now requires deferred original-project staging with
`-OutputNamespacePlan <path> -OutputNamespacePlanSHA256 <lowercase SHA256>`.
The sidecar is private operation Source metadata, separate from the author-input
and SDK schemas. Its exact fields are:

```json
{
  "Schema": "iw7.model-ff-output-files/1",
  "Files": ["work/fixture.pak", "source/model-ff-plan.json"],
  "StockInputs": ["fixture.pak"]
}
```

This abbreviated fictional example is not a complete runnable manifest.
`Files` must declare every additional file in the complete future RunRoot:
staged Source and writer evidence, copied author files/templates, stock aliases,
Work inputs/native dump, roundtrip and possible backup files. The namespace
constructor separately adds its fixed reports, seven phase-log pairs, two
receipts and pending names, then derives their parent directories. SourceRoot
must be inside the globally counted RunRoot. No empty-directory exception is
inferred from an observed run.

Compile this declaration from the pinned Source recipes, original descriptor
and existing bounded writer/stock metadata before running. Do not inventory an
opaque output tree to choose a passing allowance. `StockInputs` declares the
exact future Work-relative input set; each must also appear as `work/<relative>`
in `Files`. Copy/link mode, current identity and content checks remain the
existing admitted stock policy, including PR187's qualified-alias validation.

The parser reads at most one MiB through one actual Source metadata handle,
checks its SHA256, decodes strict UTF-8, rejects duplicate keys and unexpected
fields/types, and accepts only unique ordinary relative paths. Separators are
forward slashes; traversal, rooted paths, reserved Windows names and trailing
dots/spaces are refused. Returned file lists are read-only. No game/tool/blob is
read, output directory created, native owner imported or reservation acquired.

Every declared file's effective full path must contain fewer than 260 UTF-16
characters, including room for the terminating null. The same check covers the
constructor's added paths before admission. This is a conservative native
narrow-stdio path contract; it does not change Windows or the native writer.
A future short immutable Source package can satisfy the existing RunRoot
containment rule without a junction or path-policy relaxation.

## Bind actual results to the sealed declaration

The namespace and its counter closure are constructed before admission and
attached to the actual ModelFF root as those same objects. The sidecar itself
is then hash-guarded under the original admission before SDK staging.

After the SDK job, its actual plan and original writer recipe must describe
exactly the Source-prefixed files in the declaration. A bounded metadata walk
also checks the actual staged file/directory tree, refusing missing or extra
files, unexpected empty directories and reparse points before FF construction.
After current stock discovery, its actual relative input set must exactly equal
`StockInputs` before provider hashing, aliases and FF work. No mismatch expands
the sealed namespace. The complete-tree publication policy is implemented by
the separate namespace helpers in `ModelFF.Core.ps1`; generic H1 remains intact.

## Material JSON before required sidecars

Following native re-dump, both material JSONs must be present and at most 256 KiB
each. The entry enrolls them through `Add-ModelFFHeldInput` in the same original
context guard/pin lists. The diagnostic reads those two actual FileStreams,
resets their positions, and leaves their handles for the existing final closer.
It creates no owner, context, guard list or eighth native phase.

Strict JSON parsing rejects duplicate properties and nesting beyond 32. The
literal `techniqueSet->name` must be a nonempty string in both documents. Every
Source field must have the same semantic value in the dump: object order and
numeric formatting do not matter; constants, texture entries and their
semantics remain compared. Extra top-level native fields are allowed, as in the
existing independent verifier. A mismatch reports the differing field before
the original required-sidecar loop runs.

`MetadataMatch` is a diagnostic result. Material readback, image bytes, native
CBT semantics, recipient/normal/shader ABI, pixels, physics and Ready remain
unqualified until their separate readers/evidence. The original dump-file copy
list is unchanged: a missing required CBI still fails, and a Source sidecar is
never substituted for native dump evidence.

The Source tests use small fictional files and held streams. A new immutable
capsule, exact-tuple review/admission and independent FF readers are still
required. D5's frozen package, outputs and known failure remain unchanged.
