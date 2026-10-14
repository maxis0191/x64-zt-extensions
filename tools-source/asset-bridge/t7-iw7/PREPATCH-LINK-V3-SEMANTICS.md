# Link entry and returned-header interpretation

The closed V3 text capture was decoded once on 2026-10-14. The complete
`DB_LinkXAssetEntry` interval explains why a registration caller must distinguish
its input entry, the entry returned by Link, and the header returned by Add.
This is an interpretation of captured code and pinned declarations. It does not
qualify a nested material image pointer, the contents of a live pool, availability,
lifetime, the complete ABI, or runtime compatibility.

## Evidence and decoding boundary

| Retained private text | Bytes | SHA-256 |
| --- | ---: | --- |
| Closed capture review card | 6162 | a0db6155569d57b3b3ce791bdd61a2091806a9fd9d8960acf0a2722c7d7a2e70 |
| V3 mapped report | 38323 | 95d489a706885eec2723a4fcbeeb30c2686abc82cc0010151d02c0aa94a7e4e1 |
| Linear decoder journal | 55736 | 8b40772f129721a3fb7e63177e0e194aa03dfa60edd1f24307b0c016f720cf53 |
| Decoder summary | 35381 | b1c78bca37f62109069ee9561feb7322616e5ae8987bb00714e98169be3ead61 |
| Admitted decode receipt | 2462 | aee7b9e0f408e99029fadd56e30a16d09b6d7ae2d323961ce485c9404e4cdd55 |

Only the following named `.pdata` intervals were decoded from the existing
band. There was no new capture, scan, callee-code read, live-memory read, game
invocation, or PE/PDB input. The source/runtime phase remains first DPI before
component post-unpack. Raw captured bytes and the decoder journal stay private
and untracked; this document contains no opcode dump.

| Function | RVA interval | Bytes |
| --- | --- | ---: |
| Link | [0x1D7960, 0x1D7CDD) | 893 |
| Find | [0x1D5FB0, 0x1D6529) | 1401 |
| IsDefault | [0x1D7260, 0x1D742B) | 459 |

The 2753 bytes produced **743 linear decoder records**, not 743 established
executable instructions. Find ends its code at RET 0x1D64D2 and a NOP at
0x1D64D3. Its inline data intervals are [0x1D64D4, 0x1D64DC), two RVA entries,
and [0x1D64DC, 0x1D6529), 77 index bytes. Instructions at 0x1D63F0 and
0x1D63F8 reference these tables. Their apparent instructions in the linear
journal are data, not evidence of executable behavior. Find/IsDefault and their
G3 consequences have separate ownership in
[the material recipient notes](../t7-bridge/MATERIAL-PARTS-RECIPIENT.md);
the analysis below concerns Link.

Python 3.12 and Capstone 5.0.7 were reused. Their binary guards were measured
only under the separately admitted Analysis reservation. One original Python
process exited zero, the existing scoped original-handle helper confirmed its
exit, and the original NoExit host retained context until owners/guards were
empty and the lease released. The true original PTY exited zero; fresh parent,
host and Python identities were absent and the shared registry was empty.
The helper supplies no Job or proof of descendants. Total run outputs were
93736 bytes. The first postflight looked for the wrong registry filename;
source inspection corrected it to `leases.json`, without replaying the decode.
The earlier preparation capsule with an OrderedDictionary summation error
remains preserved and was never executed.

## Pinned source contract

[BOIII load declarations at 5aa7fac](https://github.com/Ezz-lol/boiii-free/blob/5aa7fac39c51438d9c1e312b99534b7fef3bff44/src/client/game/symbols/db/load.hpp)
associate 0x1401D7960 with Link, an entry-pointer return, an entry-pointer first
argument and a second `qboolean` named `allowOverride`. The same file names
0x1401D4FE0 as delayed copy. The
[asset symbols](https://github.com/Ezz-lol/boiii-free/blob/5aa7fac39c51438d9c1e312b99534b7fef3bff44/src/client/game/symbols/db/xasset/core.hpp)
identify the name getter at 0x14019F080. These are source bindings; unlisted
callees below retain anonymous addresses and have not been decoded or called.

The pinned
[entry layout](https://github.com/Ezz-lol/boiii-free/blob/5aa7fac39c51438d9c1e312b99534b7fef3bff44/src/client/game/structs/db/xasset/core.hpp)
declares a 32-byte entry: type at zero, header at +8, zone index at +0x10,
in-use byte at +0x11, hash/type/override indices at +0x14/+0x18/+0x1C.
Bytes +0x12 and +0x13 are padding in that source. Link tests them, but their
semantic names remain unknown. Agreement with code offsets supports this
interpretation; it is not a blanket retail-layout or ABI certificate.

## Name lookup and pool index provenance

Link saves the incoming entry in R14 and the second argument in R13d. It calls
the name getter at 0x1D7986, tests the first character for a comma at 0x1D798D,
and advances the effective name pointer once at 0x1D799F for a reference.
The type comes from the entry's first dword at 0x1D79A2.

The hash uses the type as its seed and multiplier 0x1003F. Character callee
0x140ABA544 remains unqualified; the explicit subsequent substitution converts
backslash to slash. The reduction selects one of 0x26400 bucket positions in
the table at 0x146904070. At 0x1D7A10–0x1D7A16 a nonzero UInt32 index becomes
an entry address using base 0x1469BB270 and a 32-byte stride. Candidate type
must match, and name comparison target 0x140581300 must return zero.
The loop follows the index at entry +0x14, with zero as its end marker.

These addresses and operations are code-derived. No table/pool contents,
capacity, valid index bounds, allocation lifetime, or resident asset were read.
This entry index arithmetic is not evidence for a mask or handle encoding in
a nested image pointer.

## Branches that determine the returned entry

| Captured condition | Behavior visible within Link | Return provenance |
| --- | --- | --- |
| Second argument zero; comma reference; matching entry | 0x1D7A4F branches directly to 0x1D7CC2 | Existing RSI entry |
| Second argument zero; comma reference; no match | 0x1D7A5B calls 0x1401D4E20 with type and effective name, then jumps to the common epilogue | Callee RAX; callee/default semantics unqualified here |
| Second argument zero; ordinary name | 0x1D7A6E calls 0x1401D4700 with type and dword from 0x1469BB268; 0x1D7A87 calls 0x1401D4C60 with original input, returned entry, and 1 | Subsequent branches use the callee-produced entry as R14 |
| No matching entry after the ordinary/flag path | 0x1D7AA1–0x1D7AC0 inserts hash/type links and publishes `(R14 - poolBase) >> 5` | R14 at 0x1D7AC4 |
| Existing entry, same zone on the path reaching 0x1D7B97 | 0x1D7BAD calls 0x1401D4C60 with incoming entry, existing entry, and 6; 0x1D7BB9 passes incoming type/header +8 to 0x1401D69B0; counters decrement and incoming entry is put on a free list | Existing RSI |
| Existing entry; path through 0x1D7C23; second argument zero | 0x1D7CBD invokes the source-named delayed-copy callee on incoming entry | Existing RSI |
| Other existing-entry paths | Tests and calls select/splice +0x1C override indices; selected paths call 0x1401D4C60 with 6 | Existing RSI |

The no-match publication uses a type-head table at 0x14699D070, storing the
previous head at entry +0x18. Override insertion at 0x1D7C81–0x1D7C8E stores
the previous selected index at incoming +0x1C and publishes the incoming pool
index. Another path at 0x1D7C93–0x1D7CB3 links incoming after the existing head
and calls the anonymous copy target before returning the existing head.

The visible same-zone free-list head is 0x1469BB260; the decremented counters
are 0x14690203C and 0x146902030. Their units/capacity/ownership are not inferred.
Entry bytes +0x12/+0x13, zone-record bits/masks, target 0x1401D8DB0, and the
other unnamed calls remain raw conditions. Their priority, replacement,
diagnostic, fatal-return, and deep-copy semantics are not established. In
particular, no claim that a logging-looking callee cannot return is made.

## Reusable caller consequence and next bounded observation

[The retained V2 caller analysis](PREPATCH-LINK-V3.md) establishes that Add
constructs an input entry, invokes Link with the second argument zero, then
extracts the **returned entry's** header at +8. SimpleAsset stores that Add
return in its caller's header slot. Link does not promise to return its input
entry or the same header: it may return an existing entry, a callee result, or
an allocated entry. Observation must distinguish:

1. The input header passed into Add.
2. Link's entry return, if that specific call is observed.
3. Add's header return, already extracted at +8 by Add.

Adding +8 again to an Add return would confuse these contracts. This document
does not claim that the current G3 observer has that bug or authorize a patch
without source evidence. A comma reference selecting an existing entry also
does not prove a provider, non-default status, or nested-image validity.

The minimal proposed observation is provenance for the existing exact MODEL
registration callback and post-load lookup, using the already selected first
slot, binding 4 and name hash 0xA0AB1041. Keep separate input MODEL header and
actual Add-return MODEL header, with ordinal/thread/phase association. Add's
return is a header already; do not apply the Link-entry +8 extraction twice.
If the return differs from the input, record `HeaderChanged` and do not label
both samples as the same object. For each qualified selected field, retain the
MODEL/material/table/slot association with its raw image value.

The two selected epochs are canonical Add return and the same post-load MODEL
lookup. Keep the incoming header only as a scalar provenance value; no image
body is read before Add. Reuse existing bounded selected-field reads on the
returned/lookup MODEL headers, and query only region metadata for the existing
fixed image candidate span:
state, protection, type and extent. Do not read image bytes/pixels, transform a
pointer, invent a handle, retain an image, or add IMAGE registration/lookup/name
getter calls. A missing or unqualified selected-field/header association refuses
the sample. Raw equality alone proves neither lifetime nor readability;
inequality alone selects no alternate layout or tag mask. This is a joint
source-only proposal, not a new probe implementation or a runtime result. Its
exact phases, bounds and refusal behavior need separate review and coordinator
GO. Existing failed G3 evidence and these private outputs remain immutable.
