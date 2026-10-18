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

The caller owns acquisition and authorization. It must validate the report before
acquiring real payloads, retain original file/byte guards, and separately prove
four distinct ordinary file identities/ancestry and closed bundle inventory.
After byte checks, a complete native body key/shape/count/range/allocation gate
must still precede arena construction. Actual parser opens must refer to the
same held validated files **before their first read**, with CWD/search paths
sealed and restored. Keep both parser objects/maps, roots, arena and guards alive
in the required destruction order. These physical I/O, actual native admission, routing
and durable owner gates remain unimplemented; no parse/CLI/builder is wired.
The separate [pure body preflight](NATIVE-BODY-SCHEMA.md) now validates the
pinned consumed dialect and ordered demand/alignment model on original byte
buffers. This does not add native body admission, physical routing or owners,
and does not change either report/raw-byte helper's scope.
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

The inactive C++ `native_pair_report.hpp` now supplies a void report-only check
on the same const `OwnedInput`: externally copied raw report pin first, strict
primary JSON with decoded-key duplicate rejection and event bounds, then the
closed thirty-key schema and three rows bound to the same owned bytes/pins,
including exact CSV66. It does not decode bodies or change the three-case Source
address gate, PR216 eligibility, provenance or external-ingress permission.
`test_pair_report.cpp` contains eight authored groups, uncompiled and unexecuted
at this Source preparation; its real standard-new fault targets the report SHA
rehash before decode and is not parser-allocation or fatal-allocator evidence.
Only the new targeted Python Source checks were run. New standalone C++
compile/link/probe requires separate exact review, admission, Root GO and known
closure; J8E does not qualify these new files. No CLI/FF/Game/ABI/Ready promotion.

## J9 report-only CPP and known closure, 2026-10-18

One separately authorized J9 invocation compiled exact Source
`919b36d79dc44f9a7d87bca6d514a541d3213631`, tree
`0dd9b370b24cb35badf9983583b1a708bd768758`, with explicit Native provider Source
`efe6761bc6a96581140767bde9f82816af579375`. The primary JSON Source remains
`484483acad6d562306efc9b3c6d413404f1b1f8a`; its admitted raw identity and
LF-normalized Source identity were checked before compiler activation. The
reviewed 280642-byte plan is SHA256
`f1bef0862fd87ccb622db7d8840e0875727272ebd6d57ea02a3510b339a2ac1f`.
A later DOC head or merge is not this compiled identity. Nothing was replayed.

All three original stage trees closed with exit0:

| Stage | Observed result | Stage elapsed ms |
| --- | --- | ---: |
| report-compile | standalone fixture compiled | 3024.0457 |
| report-link | this cohort's one fresh object linked | 976.7406 |
| report-test | all eight exact-output groups | 188.8604 |

The eight observed groups are same_owned_report_only,
external_pins_before_decode, closed_keys_early_duplicates, literal_schema_numbers,
framing_event_bounds, closed_roles_csv66, changed_owner_binding_only and
primary_exception_standard_memory. The raw stdout is 271 bytes, SHA256
`83419a70eea18bb4c62a7c75e36d6b3aafe6a6930782560f3802213bf3bd59a0`.
The retained raw bytes were checked before explicit CRLF-to-LF normalization
and ordinal comparison with all eight fixed PASS lines and
`IW7_PAIR_REPORT=8`. This is not raw-byte equality with the LF Source literal.
All three stage stderr files were empty. The allocation-failure group remains
an ordinary standard-allocation exception at report SHA rehash before JSON
decode, not parser-allocation or fatal-allocator closure evidence.

Root personally read the own receipts/stdout and SAME original preexit facts:
six Root witnesses, seven External witnesses, identical context/guard/saved
arrays, 32 Source records,499 input records and three publication records.
The 534 original FileStreams/saved SFHs and all three original owners were
closed; the inner guard list was empty, lease null and CanExit true. The 491
compiler declarations plus four opaque parent declarations are not a claim of
495 unique physical inputs or a reclassification of those 499 observed records.
Full input reverify, measured/final readbacks and the final deadline check were
true. Maximum output 28388995 bytes was measured under the original lease;
no opaque artifact was reopened to recalculate it. The original clock was not
reset: preexit elapsed 115984.9368ms is that observation, not total PTY wall time.

Own receipts under the distinct J9 runtime root:

| Receipt | Bytes | SHA256 |
| --- | ---: | --- |
| `measured-before-release.json` | 27759 | `5d7923ecc7c5e80fbb6e337a7095232568f2f31583070fe825d786374e79ed59` |
| `closure-before-release.json` | 14177 | `612f99d1be4a2dda7ac695d2ac4d393ba520e10a1e5421372a39594d9ce68f3b` |
| `final-closure.json` | 14364 | `65380581144b0618d7d341702c26a68fb5f8fd58294e176c9ee6916f099e7e16` |

The final disk receipt honestly retains
`ClosedReleasedGuardsHeldPendingPostflight`, GuardsDisposed=false and 534 held
guards. Later same-context preexit proves their subsequent closure; the earlier
receipt is not rewritten. `J9-ACTUAL-PREEXIT.local.json` is 15590 bytes, SHA256
`235065a67d349a682fb022c1ecada8875bcc65b5be0f97a2ecd509bdece3c33d`.
Its false TrueExitObserved/CPPQualificationGranted fields remain the honest
preexit observation, not a denial or prediction of the later terminal event.

The external Source stream and host saved SFH remained held until Root's
distinct terminal GO. That same Source was rechecked and closed, then the
original Process was disposed at the known-closure gate. The original roots
were retained until process death; no claim that both roots became null is
made. Kernel CloseHandle's return was not measured separately. Root observed
true exit0 at 06:58:54 UTC, terminal chunk `a2b58f`; that session is terminal and
must never be polled or replayed. The terminal tool call's 0.0000339-second
latency is not total PTY duration, which was not measured.

Root's fresh 06:59:23.3431656 UTC observation found all seven captured identities
absent, only the preserved Main with its same identity, and an empty Version1
lease registry before releasing the slot. The closed proof
`root-j9-cpp-closed-20261018T065923343Z-30434fc800d1489198103607e057249a.json`
is 727 bytes, SHA256
`f807e3e69310855f76923fac2fee5c88b918d66dfcd9d881830c34ae27446834`.
Only Source and own metadata/stdout were read after release; no SDK, OBJ, EXE,
PDB or opaque native output was reopened for this documentation.

Before actual authorization, the Source preparation retained its initial
92-check/16-failure result: six real local-contract omissions and separate
test-instrumentation errors. The corrected whole-contract/entry tests passed 144
Source assertions. Publication tests passed 250 using authored fakes and owned
Source files; those are not C++ results. Complete RSP and independently pinned
compiler/job/environment checks were corrected before operative Source emission.
Historical controls, refusals and incomplete before-write tests remain intact.

J9 qualifies this standalone authored report-only check and known closure. It
does not decode weapon/attachment bodies, validate a real pair or captured
U1/T2/stock data, change the three-case binding gate, or establish PR216 native
eligibility, provenance, arena/fatal closure, engine ABI/lifetime, FILE/routes,
CLI/FF, weapon grant, physics, PAP or Game. Ready remains false. No new actual
authorization or compiled credit to this DOC revision follows.
