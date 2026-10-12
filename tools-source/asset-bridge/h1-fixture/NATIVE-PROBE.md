# Prepared production-parser -> production-converter observation

**Source-only. No compilation or native execution has occurred for this probe.**
The existing full ZoneTool EXE has not been launched or changed. The original
H1 XMB/XSB fixture and its light checks are described in [README.md](README.md).

## Concrete route

`prepare_native.py` prepares one small C++ translation unit and includes from
the checked `fab935826c898806855376662a8a03317b3ad8f1` source, plus the exact
reviewed H1 surface correction. It does not change the shared source checkout.
It hashes 21 source files and fails on drift. The patch is applied in memory;
its target, hunk context/counts, patch hash and complete resulting source hash
must match. The local patch is an exact LF copy of the model owner's
`zonetool-fab9358-h1-xsurface.patch`, SHA-256
`e50c7f18b9e3b8904b441ddf10bb32a3315442d22afec7d174bda699f9db26a0`.

The future native flow is:

1. Open the two original fixture files read-only while denying write/delete
   sharing, reject reparse paths and compare **all bytes** with the positive
   input embedded at preparation. Keep both handles until observation ends.
   Malformed-input Python tests are not fed into the permissive production
   C++ reader. This is not a general untrusted-asset importer.
2. Restrict the production filesystem search paths to the fixture root. Create
   the real `zone_memory` with a 1 MiB pool. Call exact production
   `h1::xmodel::parse` and `h1::xsurface::parse` bodies on the two files.
3. Inspect parsed fields, the material/LOD names and `tag_origin` retained by
   the production string-table methods. Leave its numeric token **zero**.
4. Pass the returned objects directly to the exact production
   `h1::converter::iw7::xmodel::convert` and patched
   `h1::converter::iw7::xsurface::convert`. Use the real allocator methods and
   ordinary-vertex/self-visibility codec, with no reactive-motion shortcut.
5. Check actual ABI offsets, counts, bounds, all 24 vertex field transfers,
   self-visibility against a literal oracle, triangle/rigid aliases, optional
   streams, bone-array aliasing and named references. Print one compact JSON
   result only after all observations succeed. No pointer addresses or machine
   paths are emitted. No dump, FF, material conversion, renderer or engine is
   called; allocator lifetimes encompass every observed alias.

## What is exact, and the one declaration adapter

The generated fragment manifest hashes each selection. Function bodies are
byte-identical to LF-normalized production source, or to the reviewed patched
surface source, including their original error paths:

- `h1::xmodel::{add_script_string,get_script_string,parse}`;
- `h1::parse_subdiv` and `h1::xsurface::parse`;
- both converter bodies, blend validator/packer and converter macros;
- full `filesystem.cpp` namespace body, the two referenced directory helpers,
  allocator methods, half-float and self-visibility codec namespaces.

The real H1/IW7 structs, `assetmanager::reader`, `zone_memory`, filesystem class
and allocator headers are included from the existing checkout. No SDK or
game files are copied. There is no Python-created C++ object standing in for
the production parser and no replacement reader, allocator or converter.

The asset class headers normally include `h1/zonetool.hpp`, which pulls hooks,
engine DB, command/scheduler integration, every asset and virtual interfaces.
The preparation therefore extracts the original fields and parse/string-method
signatures into **declaration-only class envelopes** without `asset_interface`
or the unrelated virtual methods. Their access is public in this envelope to
observe the real string table. The parser bodies are unchanged. This probes
those exact production methods and their real serialization/support routines;
it does not validate the original class vtable, full ZoneTool initialization,
stock DB fallback, command dispatch or whole-application linkage. Logging alone
is adapted to `fprintf(stderr, ...)`. Compilation/linkage remain unverified.

## String and material limits remain explicit

`tag_origin` is honestly resolved **as the string stored by the parser**, not
as a live engine script-string ID. No guessed ID is assigned. No `prepare`,
`SL_GetString`, `SL_ConvertToString` or IW7 dump call is included. A later dump
requires a separately reviewed real engine/string-table integration; this
probe intentionally cannot emit an IW7 XMB. A successful in-memory conversion
would not close that gap.

H1 `read_asset<Material>()` creates only the named reference. The probe reads
only its name, never uses the stub as a full Material, and does not call the
material converter. XModel conversion creates an IW7 name stub; its null
technique remains an explicit check. The converted LOD also remains a named
reference, not linked geometry. Complete material/technique/shaders, dependency
closure and recipient binding remain with their owners. A passing synthetic
probe would not establish retail-H1 import, FF loading or rendered appearance.

## Preparation and proposed admitted work

Only the following source preparation and Python tests are authorized now:

```powershell
python -B tools-source/asset-bridge/h1-fixture/test_native_preparation.py `
  --source-repo <existing-pinned-x64-zt-directory>
python -B tools-source/asset-bridge/h1-fixture/prepare_native.py `
  --source-repo <existing-pinned-x64-zt-directory> `
  --output <absolute-fresh-preparation-directory>
```

Prepared source and receipts must stay below **1 MiB**. Output is create-only
and reparse ancestry is refused. `preparation.local.json` records source,
fragment and output hashes plus proposed compile arguments; it launches no
compiler. Revalidate that receipt, the source headers and original fixture
hashes immediately before a future admitted native run.

Use the same preparation command with `--verify` for a read-only preflight:
it regenerates the expected source in memory, checks every prepared source
byte and fragment/source hash, and still grants no execution authorization.

Review correction: `raw_bounded` no longer performs `stat` followed by an
unlimited `read_bytes`. It opens one unbuffered handle, requests at most
1 MiB + 1 byte, rejects excess length and checks regular-file identity/state
before and after reading against the current pathname. Tests perform a real
concurrent append after `fstat` (both oversized and within the cap), and a real
path replacement before open. An initial check exposed differing Windows
Python 3.12 `ctime` semantics in `lstat` and `fstat`; identity/birth/mtime are
compared across APIs and `ctime` within each API. This remains a cooperative
file guard, not protection against an attacker restoring every metadata field.

Proposed future budget, subject to the parent's plan/GO and live scheduler:

| Group | RAM / commit estimate | Bound |
| --- | --- | --- |
| One MSVC x64 compile + link | 4 GiB / 6 GiB | One compiler, no `/MP`, no PCH, 120 seconds; <=32 MiB new obj/EXE/logs |
| Separate probe execution | 0.25 GiB / 0.25 GiB | 1 MiB parser pool, two files/2,260 bytes, 15 seconds |

These estimates are **not measured peaks or current leases**. The current
reviewed scheduler/owned-job wrapper must own the whole active group, enforce
timeouts/output monitoring, observe closure and release admission. Preserve
all diagnostics if compile/link/assertions fail. Do not reduce estimates to
bypass a refused admission or invoke the planned commands directly. A full
ZoneTool rebuild, engine/game loading or donor extraction is not part of this
route; a coupling failure requires a revised source plan before expanding it.

No private PR is opened by this sub-lot; the coordinating branch owns its
integration, exact-head checks and merge.
