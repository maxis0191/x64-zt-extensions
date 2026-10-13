# Recipient I preparation: compiled utility observation

Execution update: the separately authorized I invocation completed and restored
its inputs, but script export found no exact utility name match. `available=0`
counts requested matches, not all loaded ScriptFiles. References
passed; no utility bytes or imports were observed. See the
[I result](native-validation-i-2026-10-12.json) and [failure boundary](README.md#i-references-verified-utility-index-empty-restoration-confirmed).
The preparation below is retained as the reviewed pre-run plan. Its GO is now
exhausted; no retry follows from this document.

Source and Plan only, 2026-10-12. H's single-execution authorization is exhausted.
No script run, retry, source-stock expansion or native rebuild is authorized by
this document. The coordinator owns adoption, the next distinct GO and central
GitHub integration. The local Plan binds the committed reader and fresh absent
`recipient-run-i` root; its machine-specific paths/hashes remain in ignored runtime.

## Minimal operation and unchanged sources

Reuse the reviewed E7 executable and complete stock profile `/3` from
[H](native-validation-h-2026-10-12.json), without changing their contents. E7 is
21,696,512 bytes, SHA256
`e7c956fd713f5d1b1b16cd55ef162aa487031430690ab1394ee60d3d02a13d04`;
its build artifact SHA256 is
`f0d4d7db132d51c789a999e33ab0ce905b2df749db453029f91356b9aa2e2165`.
The retained native source is `fab935826c898806855376662a8a03317b3ad8f1`:

| Source | SHA256 | Relevant behavior |
| --- | --- | --- |
| `src/zonetool/zonetool/iw7/zonetool.cpp` | `f1c9fb861b81727dc7e3882f5116231e6dc0d1a0e6f5838953a62232171059bc` | `dump_enemy_scripts`, lines 2052-2235: requested loaded ScriptFile, metadata checks, serialized full-byte comparison, hash and manifest |
| `src/zonetool/zonetool/shared/assets/scriptfile.hpp` | `5f6b30e5540563c41e8ce5d5d42d388f687e138ba7e5c2dbb30dc7eb720fc823` | name/NUL, three int32 lengths, compressed buffer, bytecode serializer |

These native files were rehashed during preparation. This task changes neither
file nor E7. The existing 12 provider pins and exact SDK request hashes remain
unchanged. The 23-byte script request is exactly `scripts/engine/utility` plus LF,
without `.gsc`; its SHA256 is
`a50b245fff515068331a50818435914a0cb81adcbc74de218753b4218d89d52d`.

The unchanged runner has no script-only mode. Its default Plan is precisely two
sequential native invocations, each in its own original-owned job, within one
stock staging and one account-wide reservation:

```text
zonetool.exe -headless -unbuffered-io -strict-content-sources -enemy-reference-check cp_zmb recipient-material.csv sdk_beacon_recipient_a
zonetool.exe -headless -unbuffered-io -strict-content-sources -enemy-script-dump cp_zmb recipient-scripts.txt paris_enemy_cp_zmb_sdk_beacon_recipient_scripts
```

Do not pass `-ReferencesOnly`. References must pass and their original job close
before the script phase starts. Each CLI exits after its own action, so appending
flags cannot combine them. This Plan repeats the four references in its own
transaction; it does not substitute H's CSV for a current-phase result.

The script phase loads the same ordered 25 zones and exports only the exact
requested module to
`dump/paris_enemy_cp_zmb_sdk_beacon_recipient_scripts/scripts/engine/utility.gscbin`.
The pack-root manifest has exactly the seven columns
`donor_map,pack_name,module,status,path,size_bytes,sha256` and one exact successful
row. Native code constructs the expected serialized bytes from the loaded asset,
compares the complete reread dump to them, then records `dumped` and its SHA256.
The independent Python reader rechecks the representation and that hash.

Success could establish the exported representation's equality to the loaded
utility ScriptFile. It does not decompress/compile/disassemble GSC, prove its
imports or complete consumption, rebuild Beacon, perform an FF readback, or
establish runtime behavior. Native success is not available yet.

## Bounded output reader

`recipient_contract.py` formerly obtained size, header and SHA256 via separate
path operations; the final hash reopen could also read a growing file unbounded.
It now opens one raw descriptor, checks an ordinary-file identity/size/timestamps,
reads and validates its 35-byte header, hashes bounded payload chunks of at most
1 MiB, checks a one-byte EOF sentinel and compares descriptor metadata again.
Short reads accumulate only within the remaining bound. Manifest text and its
digest come from one bounded descriptor snapshot, with no hash reopen.

This Python reader does not acquire a Windows deny-write sharing guard. The
guarantees are the original descriptor, bounded bytes, observed metadata stability
and equality to the native manifest digest; do not equate it with the guarded
Windows complete-inventory reader or a universal concurrent-writer exclusion.

| Item | Fixed limit |
| --- | ---: |
| Name plus NUL plus three signed little-endian int32 lengths | 35 bytes |
| Each declared compressed/source/bytecode length | 0..67,108,864 bytes |
| Serialized file: header + compressed buffer + bytecode | 134,217,763 bytes |
| Python ScriptFile read, including overflow sentinel | declared size + 1, at most 134,217,764 bytes |
| Manifest accepted snapshot / read with overflow sentinel | 16,384 / 16,385 bytes |
| Python payload chunk | at most 1,048,576 bytes |

The source-length field is a scalar; no third 64 MiB source buffer is serialized.
The native comparator materializes both expected and dumped strings, each up to
the serialized-file ceiling, in addition to loaded assets. Actual peak RAM and
native loading I/O remain unmeasured; the existing admission must not be reduced.

47 tiny generated-fixture tests pass: 11 contract, 19 dialog, 7 phase integration,
and 10 new snapshot cases. They cover short reads, growth, truncation, alternate
hash reopen, identity/metadata changes, limits and BOM-inclusive hashing. These
tests read no retail content and execute no native candidate.

## Resource and recovery limits

Use the same `/3` inventory and receipt as H: all 33 reviewed asset PAKs, with
pak1 in the baseline and 32 additions. The inventory SHA256 remains
`683c8a39b6bd289a2acc0a27129a038361d5a217d6ef129d07da739feb6f76bf`;
the stock-observation SHA256 remains
`0d38dd171a0dc03f382f8fba33cca9bcd32a43c6b6132cbef517ec920d04d829`.
See [complete stock scope](COMPLETE-PAK-SCOPE.md) for independent metadata binding.

- Admission stays 8 GiB RAM / 11 GiB commit, fresh full reservation and no foreign
  heavy workload. Source/Plan generation does not reserve that slot.
- Guarded stock content hashes read 5,148,447,113 bytes across 73 identities once
  before staging, reused for both phases. This excludes native loading I/O,
  which happens separately in each process and is not measured by that budget.
- Stage 103 stock hardlinks and the existing 77-byte sentinel copy, plus E7 and
  two request links: 107 managed paths. No PAK payload copy, image PAK, stock
  restoration, client, server or Main modification is added.
- Keep 240 seconds per native phase, 245 seconds per original owner, 5 seconds
  post-root-exit drain, and 600 seconds for the shared active-work deadline.
  The script phase inherits the remaining overall time; it does not reset it.
- Keep 2 MiB per stdout/stderr stream per phase (8 MiB across both phases),
  256 MiB overall generated-output stop threshold and 85% commit-pressure stop.
  Monitoring/cleanup is bounded by the existing observed checks; these limits
  do not promise preemption of a blocked filesystem/system call.
- Fatal-dialog body capture still covers references only. A script-phase hang
  has bounded logs/deadlines and original-job recovery, but no automatic fatal
  body capture. Do not silently extend the observer for this Plan.
- Both original jobs must close with zero members before release. Preserve
  exact failures, restoration of all managed paths, source identities/metadata,
  owner/Main identities and final lease/process observations. No automatic retry.

Only a successful closed run can set `ReferencesVerified` and
`ScriptBytesVerified` and reach `ReferenceAndScriptObservationsVerified`.
`ClosureComplete`, `Ready` and `RuntimeVerified` stay false even then.

## Beacon candidate decision

| Candidate / evidence | What is established | What still requires its own evidence |
| --- | --- | --- |
| H references, usable as stock receiver observations for either Beacon source | The exact material, techset and two images resolve to non-default entries under H's bound cp_zmb stock | Serialized content, further transitive closure, imported references in a rebuilt FF, rendering and package/runtime acceptance |
| Original `sdk_beacon` | The reviewed source and compiled negative control contain two far calls to utility | Current utility bytes from this script phase, then source-bound full-consumption and semantic import audit of the relevant compiled inputs; any additional imports must be evidenced before planning more work |
| Separate `sdk_beacon_self_contained` | Its exact reviewed source replaces those two calls with local flag checks; its separate Creator selector is Plan-only | Full bytecode/stack consumption plus complete semantic import analysis bound to its source/compiler/container/opcode tables; zero observed far calls in a partial historical disassembly does not prove dependency absence |

The utility phase is therefore useful for the **original** Beacon path. It is
not a mandatory dependency of the variant merely because this exporter exists.
The current variant graph reports `unresolvedQualification` without asserting a
utility edge. Qualifying absence can remove that question only for the exact
audited compiled variant; H's four reference rows cannot answer it.

For an actually creatable variant, the coordinator's SDK work must bind the
variant's own identity, preparation, source/compiled input, zone/rawfile and
finalizer route, then validate the resulting candidate's native build/readback
and recipient reference use. Original Beacon receipts cannot be relabeled for
the variant. Its `paris_model_probe`/surfaces/NCS still collide with the original;
no coexistence or transitive asset closure is inferred. These are evidence
boundaries, not authorization for additional exports, native audits or launches.

This distinction follows the current provider SDK `CREATOR.md`,
`examples/beacon-self-contained/README.md`, `gsc-consumption-audit.md` and
`BEACON-FINALIZE.md`, read during preparation. Those SDK files remain owned by the
coordinator/Distribution and were not changed here. Next action: review this
reader commit and the distinct two-phase Plan; choose the original or variant
candidate route before granting any new native action.
