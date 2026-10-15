# Generated private-pair report and raw byte checks

`neutral_pair_inputs.py` consumes the generated Native60 `neutral-clone.json`
contract from `iw7-mod-components` Source
`5fbc198395fe67da75c8e927dbcf587cfbab72ae`,
`ops/raygun/prepare_iw7_clone.py`. It does not import or vendor that producer,
and does not confuse this output report with its input retail capture manifest.
No captured U1/T2 or stock body was opened for this implementation/testing.

The module exports two pure helpers. Neither opens a path, starts a process,
loads a native type, constructs an arena/parser/zone, emits builder rows or
creates an authorization token. The strict reference policy remains unchanged.

`validate_private_pair_report(raw_report, expected_bytes, expected_sha256)` first
requires immutable `bytes`, a positive bounded integer length and canonical
lowercase SHA256 supplied outside the report. The raw report is capped at 64 KiB;
its exact length/hash must match before UTF-8/JSON decode. There is no self-hash,
normalized JSON hash, coercive length or trust derived solely from report text.
Duplicate keys, trailing data, nonfinite/overflow numbers, invalid UTF-8 or
surrogates and bounded-tree failures refuse.

The decoded schema has exactly 30 keys: the fixed generated-report/profile and
private identities, uncoerced integer base 1/PAP 0, literal mechanics-preserved
true, all 13 literal qualification flags false, two Source enum labels, producer
diagnostic strings, one of six known PAP slots, three provenance hashes and
exactly three unique `path`/`bytes`/`sha256` file rows. The generated bundle has
four files: two definitions, the CSV and this report. The report's own external
pin is not a fourth row or new envelope. Provenance hashes bind local metadata;
they do not authenticate assets or cause the helper to reopen earlier inputs.

Only the literal weapon/attachment/CSV relative paths are accepted. Each JSON
pin is positive and at most 2 MiB. The CSV pin and bytes are the exact 66-byte
two-owned-row output. File-row order is immaterial to this data check; this is
not an operational dependency CSV or reference-only enforcement mechanism.
Generic JSON tree limits remain 32,768 nodes, depth 64 and 8,192 entries per array;
they are not an aggregate native allocation or full native shape proof.

`verify_private_pair_bytes(raw_report, expected_bytes, expected_sha256,
weapon_raw, attachment_raw, csv_raw)` re-runs the first helper on the original
immutable raw report and external pin, then checks all three original immutable
buffers against its exact lengths/hashes and fixed CSV bytes. It does not accept
a previously decoded mutable report as authority. It never decodes either
definition body and returns `None` on success. Arbitrary owned bytes can pass
these byte checks if their trusted report pins match; native JSON validity and
native parser eligibility do not follow.

The caller owns acquisition and authorization. It must close the report before
acquiring real payloads, retain original file/byte guards, and separately prove
four distinct ordinary file identities/ancestry and closed bundle inventory.
After byte checks, a complete native body key/shape/count/range/allocation gate
must still precede arena construction. Actual parser opens must refer to the
same held validated files **before their first read**, with CWD/search paths
sealed and restored. Keep both parser objects/maps, roots, arena and guards alive
in the required destruction order. These physical I/O, native schema, routing
and durable owner gates remain unimplemented; no parse/CLI/builder is wired.
See [NEUTRAL-INVENTORY.md](NEUTRAL-INVENTORY.md) for the separate descriptive
inventory and its absence of builder authority.

Twenty tests use owned synthetic report/raw buffers, never captured definitions.
They exercise actual helpers, hash-before-decode order, closed/nested schema,
flags/types, duplicates/aliases, UTF-8/numbers/tree budgets, report revalidation,
body/CSV mutations, zero I/O and the deliberate absence of body parsing. The
prior CPP F result qualifies only its recorded earlier native Source; this
Python-only lot adds no C++/FF/runtime qualification or new runtime permission.

```powershell
python -B -m unittest -v test_neutral_pair_inputs
```
