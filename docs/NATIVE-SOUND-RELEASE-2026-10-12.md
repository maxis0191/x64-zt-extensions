# Native sound-observer Release checkpoint — 2026-10-12

The r3 Release x64 build completed and its retained package passed a separate
static qualification. This establishes a compiled candidate, not engine sound
lookup, playback, audibility or owner acceptance. Earlier failures and the r3
observer interruption remain recorded.

Source: `caccd6981578d96aee44a288108b80956053be48`, the PR #177 merge.
This advances the compiled-client prerequisite left open after PR #174 and the
[sound SDK contract](SOUND-SDK-CONTRACT.md). The existing native cache was reused
through its explicit canonical path; no new checkout or clean build is claimed.

## Retained output identity

Measurements are from admitted qualification; cache outputs and archived symbols matched.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Release executable | 6,097,920 | `958613F3ADE0347F991071A0A8A8502CFB66C816C5C084C5214F05078F7B0296` |
| Matching PDB | 55,119,872 | `64A0DED22E3CC8CE9CE1C7CBA32E59FE791BD28A4F5EA6C46342A7461E30B812` |
| Build manifest | 15,561 | `969F4AF7B49826FDACA9C83774D39849BF0446ADB311049BDC81E34A371145A8` |

All 34 declared sources matched byte-for-byte. The compiled transformed fixture hash is
`F8CA6C7890E02C3C9A8D8486801F478819144D198B60B6D39DF341B5E9C59581`.
The receipt confirms Release/x64, debugger disabled and the private-test
heartbeat suppression overlay. `CleanBuildAttested` and `NativeRuntimeVerified`
remain false; the provider does not attest every build-copy snapshot.

## Build result and recovered closure

The retained stdout records fixture compilation and final package preparation.
It includes 707 native PTT provenance checks, 147 PTT source/copy checks with the
eight real SDK source pins, 24 capacity-overlay checks, and 121 recorder-cleanup
checks whose kernel/NTFS dependencies were mocked. Wire, reconnect, simulated
WAN, recording and ownership checks also report success. These are build/test
results, not in-game or real WAN/audio acceptance; no aggregate count is inferred.
The file-symlink case lacked elevation; junction checks executed. Build stderr is empty.

At 21:47:11Z, the observer stopped on an incompletely identified receiver probe.
The original retained builder handle subsequently established actual exit **0**
at **21:47:54.4958056Z**. Recovery used that handle, an explicitly authorized
identity-targeted VCTIP stop, six closure snapshots, disk metadata accounting and
source/cache/binding revalidation. The build host's actual terminal exit **1**
is retained separately from the builder's success. Independent build closure at
21:53:19Z found no remaining observed identities or leases.

Polling ended before the builder exited. `WholeDescendantClosureProven=false`
remains explicit: no Job Object or atomic coverage of every short-lived child
is retroactively claimed by this recovery.

## Separate qualification and release

`qualification-01` took its own Analysis admission of **4 GiB RAM / 6 GiB commit**
at 21:54:59Z, without recompilation. Output read guards, source and manifest
bindings, fixture identity, build time window and Release definitions passed.
The closed receipt records success, restored priority and ended cache assignment.
The qualification terminal exited **0**; the independent witness at
**21:56:05.6070137Z** confirmed host/parent absence, closed source handles, no
remaining observed workers or leases, and the stopped-Main baseline. The
coordinator subsequently released the administrative source freeze and cache.
No payload was read or hashed after admission release.

Final file-length accounting measured **79,844,523 bytes** of positive growth across
three scoped roots, within the reserved **4 GiB native allocation**.
This is not complete historical global-growth accounting or an enforced OS quota.

The private r3 evidence set retains these independently readable receipt pins:

| Receipt | SHA-256 |
| --- | --- |
| `build-closed.json` | `30EEDFB07BA8094B768EFCC301F3385D15DEDD8AAEFB3E2B941F6C6EDCCC8372` |
| `qualification-01/evidence.json` | `BB34203734412BEAB96E7A29EB27E29E17D3642261537046190B2644C2ED77CF` |
| `qualification-01/closed.json` | `D68FCF5C4355E17B64C44A26E95F234F142C6B6AAB3C7D0B9E477C5FFB097AF2` |
| `qualification-01/independent-closure.json` | `72DF1C62D353266581941775AC5BB188AE93A2D5A0CB56F2FB1D7F60425FC860` |
| `qualification-01/disk-final.json` | `681823A59199158D0D9FEA3EC57582C9961D053AF30350D65CC6C8647D3B2974` |

Next: produce and qualify the actual StandardMod sound package under its own
reviewed plan/admission, then use this exact native candidate for a separately
authorized protected private runtime test. Preserve pending lookup, playback,
audibility and owner acceptance until those tests provide their own evidence.
