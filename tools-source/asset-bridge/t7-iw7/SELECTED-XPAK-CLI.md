# Selected XPAK raw payload CLI

This Windows tool copies one explicitly selected BO3 XPAK object into an owned
CPU buffer without loading T7, an engine cache or a map. Inputs are a finite
list of local absolute package paths, their observed Win32 file identities and
lengths, the exact lower-case 64-bit key, and the expected decoded byte count.
The caller supplies those facts; the tool does not discover packages or infer a
key from an opaque engine descriptor.

## Command

From a terminal whose environment has the already qualified executable:

    selected-xpak.exe --key 0123456789abcdef --expected-bytes 18624 --out C:\private\mesh.bin --package C:\stock\zone\donor.xpak AABBCCDD:0000000000000001 1048576

The key, identity and size above are synthetic placeholders in a usage example,
not a qualified game input. Replace all three with independently observed
values. Repeat the four-token package option for another admitted package,
up to eight distinct paths and identities. Quote paths containing spaces.

The output parent must already exist. Extraction creates mesh.bin and
mesh.bin.json with CREATE_NEW and never overwrites either. Reparse ancestry,
resolved-path aliases, device filenames and output inside the input package
directory are refused. For packages in a zone directory, its parent game root
is also protected. The caller must choose private storage outside any other
game installation; the tool does not inventory all installed games.

    selected-xpak.exe --inspect --key 0123456789abcdef --expected-bytes 18624 --package C:\stock\zone\donor.xpak AABBCCDD:0000000000000001 1048576

Inspection decodes the same bounded selected object and prints its provenance.
It is not a header/index-only mode. It writes no payload or metadata files.
Help performs no input or output IO.

## Contracts

| Boundary | Limit |
| --- | --- |
| Inputs | 1–8 distinct packages, each 120 bytes through 16 GiB |
| File admission | Exact Win32 VolumeSerial8hex:FileIndex16hex and byte length |
| Index | Aggregate declared Hash24 section size at most 8 MiB |
| Selected encoded extent | 1–262144 bytes, unique key after validating every admitted index |
| Decoded bytes | Exact caller expectation, 1–262144 |
| Framing/codecs | Existing reader: 128-byte groups, Count 1–30, at most 128 groups, raw0/LZ4 3 |
| Input IO | Retained READ/shareREAD handle, exact resolved path, size/mtime checks around reads |
| Output | Local absolute file, portable basename ≤64 characters, create-only payload and JSON |

The new public raw-payload entry point shares the existing reader implementation.
The original selected-mesh API still requires exactly 18624 decoded bytes; E3
uses that strict API. The CLI does not loosen the geometry export profile.

The JSON records the admitted package scope, actual provider identity/length,
key as hexadecimal text, selected offsets/extent, packed size as decimal text,
indexed record bytes, codecs, opaque command-header offsets and decoded SHA-256.
Only the decoded output buffer is hashed with Windows CNG. No whole package hash
is computed. Buffer ownership lasts through extraction. Packages remain sealed
through output creation; there is no OS sandbox or proven atomic source snapshot.

Both fresh output handles are reserved before bytes are written. On a handled
failure, the tool marks only its own new partial files for deletion through
those retained handles. An abrupt process/system failure can still leave an
incomplete pair; preserve it and choose a new output name. The pair is not a
filesystem transaction. An existing output is never deleted or overwritten.

Raw bytes and metadata remain private local artifacts. They do not establish
asset licensing, model geometry, materials, FF compatibility or gameplay.
Never add extracted game bytes, file identities or machine-specific requests
to Git or a public distribution.

## Source, build and qualification

The CLI uses the existing selected reader and LZ4 1.10.0 source pinned at
1b0fc692949cf474eb0d89db5f0dfa3698e9aa56. It vendors no decoder. SHA-256 uses
bcrypt.lib supplied by Windows/VS; no extra package is downloaded.

Use the established native compiler/job pipeline and its ordinary reservation
and closure checks. With a previously qualified LZ4 object and an initialized
VS2022 environment, the compile recipes are:

    cl /nologo /std:c++20 /EHsc /O2 /MT /W4 /WX /I LZ4_INCLUDE /Foselected_xpak_cli.obj /Feselected-xpak.exe selected_xpak_cli.cpp QUALIFIED_LZ4_OBJECT
    cl /nologo /std:c++20 /EHsc /O2 /MT /W4 /WX /Focli_options_test.obj /Fecli-options-test.exe test_selected_xpak_cli_options.cpp

LZ4_INCLUDE and QUALIFIED_LZ4_OBJECT denote the existing exact qualified inputs,
not fallback versions. The original synthetic reader fixture is extended with
generic min/max decoded lengths, early bound refusal, exact-length mismatch,
truncated framing, invalid signed LZ4 output and unchanged strict-mesh refusal.
The parameter fixture checks canonical key/identity/decimal parsing, overflow,
missing/duplicate options, inspection/output exclusivity and the eight-file cap.

Current checkpoint: source prepared only. No new native compilation, generic
fixture execution, CLI output creation or real selected payload decode is
qualified yet. Historical reader PR12/C receipts remain historical evidence;
they do not qualify this new executable. Next action is independent source
review, then one authorized small native batch using the existing pipeline,
followed by the already identified selected 18624-byte donor input.
