# T7 message observation I

## Evidence boundary

The coordinator authorized analysis of the single completed I capture on
2026-10-12. No new native run, build, binary/payload content read or hash, or
reverse engineering was performed for this analysis. Only the small receipt,
plan, host closure records and already pinned source text were consulted for
the initial interpretation. The coordinator then authorized the narrowly
scoped filename/metadata observation recorded below.
The earlier refused dispatch is a separate attempt and is not runtime I.

The I plan is 10,833 bytes, SHA256
234dc0d788c769e5ddb83cb9d6daa2e9a09d677baf6b4b4aaaef99590e4ff03f.
The runtime receipt is 12,971 bytes, SHA256
1c90706041749a038d6fbb4c788c6efedf648fe032db26738eec72f6393ff540.
Its retained stderr pin is 4,888 bytes, SHA256
56f2538ecb2d2b4c3b31a545f9412d099b1942a101bcca27a743a41f46314dd7.
The stderr hash comes from the receipt; it was not recomputed after release.
The candidate is the unchanged [message build A](BUILD-PLAN.md), SHA256
57168e99d3dd004e83a531905efe5354a8d29e39592786e3f81b5dd4cd5ce05a.

Installation reports installed/error 0 on TID 25272. The buffer reports
ok/error 0 on TID 28892, requested=read=384, length=45, NUL=true. Every emitted
byte is ASCII; the final emitted byte is LF. The terminator is not part of the
45 bytes. No trailing incomplete line exists. The parser reports Observed and
SameThreadBeforeExit; the subsequent exit_hook has TID 28892, code 0 and return
address 0x140AC00C4. This is a complete bounded message, not a truncated prefix.

The engine reports that it cannot find a specifically named startup zone.
The exact message remains in ignored private evidence, including
`runtime/t7-message-i-analysis.local.json` (1,411 bytes), SHA256
a50ee46a2ae1517d53f85f749425d548baccff1edd1ec0106f0d4f06e5e86111.
No message bytes or captured machine code are reproduced in this document.

## Interpretation against the pinned sources

The native source remains pinned at fab935826c898806855376662a8a03317b3ad8f1.
In `src/zonetool/component/t7/zonetool.cpp`, the initialization stub invokes
0x140504170 before calling `zonetool::t7::start()`. The component's post_unpack
also calls `initialize()`. In `src/zonetool/zonetool/t7/zonetool.cpp`, that
function only calls `init_zonetool()`, which emits the initialization-start
message. `start()` separately calls finalize, branding, command registration
and argument handling. The initialization-start log alone therefore does not
prove that start or the catalogue handler was reached.

The I receipt records four aliases: candidate, dedicated engine, Steam DLL and
the requested donor fastfile. There is no startup-zone alias. This matches
`Run-T7Catalogue.ps1` and `T7Catalogue.Profile.ps1`: the runner creates exactly
those four aliases, the validator requires four input metadata records, and
the zone-directory output allowlist contains only the requested donor file.

The observed failure is zone resolution in this runtime environment, correlated
with the natural exit. It does not establish global absence of that file, its
correct search path, compatible version/provenance, or a complete list of
startup dependencies. It also does not prove that supplying this one dependency
will produce a catalogue. No evidence here justifies an engine patch, an error
bypass, a forced return, a changed offset or an anti-tamper diagnosis.

## Authorized filename and metadata observation

One matching file was found in the existing BO3 stock: relative path
`zone/en_core_pre_gfx.ff`, 832 bytes, Archive attribute. Creation was
2026-10-12T10:06:38.5002426Z and last write was 2026-10-12T10:06:38.5195724Z.
The file and every ancestor up to the volume root have no reparse attribute.
The filename search did not follow reparse points. No file content or payload
hash was read, and neither valid content nor version/provenance follows from
this size or these timestamps.

Private evidence `runtime/t7-message-i-startup-metadata-b.local.json` is 1,898
bytes, SHA256
9b2979f0ef9a4520ca5b16f0160ff93a395534d6d672a307d8a0fe45fc5a314a.
The final ancestor check was observed at 17:09:55.1370738 UTC. It explicitly
supersedes the initial report, whose loop inspected only the file and its
direct parent; that incomplete report remains retained.

Pinned T7 source `zone_exists` delegates to `DB_FileExists(zone, 0)`, bound to
0x1401D5C20 in `src/zonetool/zonetool/t7/functions.hpp`. The engine's internal
path search implementation is not present in these sources. `iterate_zones`
selects `zone/` when that directory exists, but this is the tool's enumeration
logic and does not prove the engine search rule. A proposed alias at
`work/zone/en_core_pre_gfx.ff` follows the observed stock layout and existing
donor alias convention. Its suitability remains to be tested in an authorized
runtime; no stronger path claim is justified here.

## Minimal proposed correction, not applied

Qualify only the identified 832-byte file before sealing a new runtime plan.
Under a separately authorized reservation, recheck the exact canonical path,
metadata and absence of reparse points, open it with a retained read guard that
denies writing/deletion, record its file identity and hash through that guarded
stream, and verify identity/metadata again. Compare with an authoritative
existing manifest entry if available; a locally observed hash alone remains
explicitly not depot-verified and does not establish engine compatibility.
Save the bounded qualification receipt, revalidate while guarded, then dispose
guards and close/release the reservation with the usual host closure evidence.
This is a proposed qualification phase; none of these content reads occurred.

A fresh runtime plan can then bind that qualification receipt and exact input
pin, proposed relative path and metadata. Its default validation stays limited
to source/metadata. The actual runtime must reopen/revalidate the new pin under
its own reservation, retaining guards through final revalidation and closure.
Keep the candidate and arguments unchanged; there is no demonstrated reason for
another native build.

The runtime source change must bind the additional input explicitly, extend
the exact metadata/alias/output allowlists, account for its bytes in the output
budget, and retain guarded hashing, source/alias file identity checks and final
revalidation. It must not merely place an unbound file in the old work directory
or weaken the four-input validator. Add focused refusal checks for missing,
duplicate, unexpected or changed startup inputs. Use a fresh sealed plan and
fresh root, independent review, admission and a distinct runtime GO.

I remains Failed/NoCatalogue despite the diagnostic success and natural exit 0.
The receipt records input revalidation, tree closure and lease release, with
no quarantine. Host session 13977 actually exited 0 (tool chunk f4269b).
Independent observation at 17:05:51.4233562 UTC found host 35524, parent 35188
and native root 33572 absent, with zero leases. No retry or correction was run.
