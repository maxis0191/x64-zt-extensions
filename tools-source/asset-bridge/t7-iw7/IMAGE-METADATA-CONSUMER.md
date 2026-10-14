# Selected image metadata consumer

`image_metadata_consumer.py` validates an existing JSON record from the fixed
`iw7.t7-selected-image-provenance/1` producer. It performs no capture, memory
query, header read, asset lookup, extraction or runtime preparation. The source
producer interface is the f2 revision `f2ee0df49352e8414c4998ea0e50657ad23cab82`;
this consumer does not qualify that revision's C++ fixture or an executable.

The selector remains `mp_freerun_04` / `p7_fre_platform_cap_02`, LOD 0, material
slot 0, texture binding 4, uint32 name hash `A0AB1041` (2695565377). It never
substitutes the first image or interprets that hash as a 64-bit XPAK key.

| Recorded value | Interpretation |
| --- | --- |
| H_in, registration `incoming_model_header_hex` | Scalar provenance only. No dereference or offset. |
| H_return, registration `selected_model_header_hex` | Add returns the header already. Do not apply entry + 8 again. |
| H_lookup, lookup `selected_model_header_hex` | A separately recorded post-load header. |
| Equal image fields | Equal numeric values only; object identity and lifetime remain unproven. |
| Complete query over 264 bytes | Coverage metadata at that query, with at most two raw MBI regions. No retained allocation or atomic snapshot. |
| Complete but unreadable/free range | A valid metadata observation; it does not admit an image header. |

The loader/source distinction between an XAssetEntry and its returned header
comes from the retained V3 Link analysis. It does not supply a nested-image
pointer transform, an image ABI proof or a lifetime guarantee. The consumer
checks recorded scalars; it does not cast them to pointers.

`consume(report)` requires the exact producer fields, typed booleans and bounded
integers, canonical nullable hex strings, the two epoch phases, consistent
association/comparisons and counters. Complete rechecked queries must have
consistent region coverage and readability flags. An unobserved binding must
have all query flags false and no regions. A failed final binding
recheck can retain the producer's earlier observed fields and query metadata;
those remain refused association evidence. The output omits raw addresses and
keeps the epochs' refusal flags and error text.

`strict_json(raw_bytes)` enforces strict UTF-8, a 32 KiB JSON limit and unique
keys. Duplicate keys, nonfinite numbers, schema extensions, fabricated image
fields, positive body/payload bytes and promoted proof flags are refused.
`classify(report, original_exit_code)` distinguishes `NoReport`,
`ProvenanceMetadataRefused`, `ProvenanceMetadataObserved` and
`ValidMetadataFromFailedProcess`. A refused capture with exit zero contradicts
the producer contract. Complete metadata with a nonzero exit remains a failed
process. Calling `classify(None, exit_code)` records absence; it creates no
producer report. A missing CLI input file is an error with no output report.
The CLI accepts only a nonempty regular `.json` file of at most 32 KiB. It checks
the suffix, size and every path component for reparse metadata before opening,
then rechecks the opened file's identity and size before a bounded read. The
pure bytes/dict API remains the interface for a record selected from stdout.

The existing Catalogue/H1 owner remains responsible for selecting exactly one
stdout marker, guarding and pinning the closed log, bounds on stdout/stderr,
the original job/host/lease and true process closure. This module neither
implements nor replaces those responsibilities. Operational integration must
review its existing dispatch and receipt paths separately; the CLI below is a
source inspection utility for a JSON already obtained through that workflow.

```powershell
python -B tools-source/asset-bridge/t7-iw7/image_metadata_consumer.py existing-report.json --native-exit-code 0
python -B -m unittest discover -s tools-source/asset-bridge/t7-iw7 -p test_image_metadata_consumer.py -v
```

The earlier G3 refusal occurred before its image memcpy:
`range is not committed readable memory`. That compound guard does not identify
which condition failed (commit, guard or protection), nor prove a freed pointer.
No BO3 image name, format, dimensions, stream key, pixel bytes or extraction
authorization was obtained from that refusal. This consumer adds no fallback.

M7's separate existing recipient reference is material
`mopw/character_park_clown_zombie_shoes` in `cp_zmb`: one named row, verified=1,
missing=0, default=0. The retained CSV SHA-256 is
`b691b56baf8b9db5f887d9ce6d2005c9bc1c1bc0527c7756bc8b792b9bd6230c`.
It proves that named IW7 reference only. Material payload, BO3 texture,
rendering and collision are unqualified; the future slot-0 diffuse proposal
must preserve the other four recipient material slots. Machine receipts and
game data remain outside Git.

Validation on 2026-10-14: 25 targeted Python tests pass using authored JSON
cases, including complete MEM_FREE, two-region coverage, null image, missing
registration, duplicate/search refusal, late recheck failure and failed native
exit. No native producer, memory query, engine or game was run by these tests.
Independent review identified and corrected an invalid nonobserved binding
that could claim complete/readable query metadata. The causal test now refuses
each query flag or region in that case, while preserving a real observed
binding's query metadata after a failed recheck.
The later CLI review found a missing metadata gate before file opening. A
follow-up correction rejects authored opaque suffixes, oversized JSON,
directories and reparse metadata before any open; opened growth/replacement
also refuses. These cases use authored files and metadata mocks, never an
actual executable, SDK, game asset or producer.
Next gates remain separate: real producer fixture, reviewed producer merge,
launcher/result source integration, newly qualified full CLI build, fresh
ordinary DEFAULT preparation, then an explicit native GO. Every consumer
result keeps body admission, extraction, pointer transformation, lifetime,
object identity, authentic BO3 texture and Ready false.
