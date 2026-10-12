# Bounded message publication before the two catalogue CLI exits

Source-only correction prepared on 2026-10-13 from project main
`a21ab02475edaf85e02e60bb1ab5a26e198dd3dd`. Historical message instrumentation,
build plans, providers, compiled objects and receipts remain unchanged.

## Evidence and diagnosis boundary

The coordinator's catalogue20 B run completed naturally with exit 1 and no
catalogue. This task read only the two small logs and retained source text:

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| catalogue20 B `evidence/stdout.log` | 485 | `8851fb480c2014672c0b280e0b3f7b26622f08ec1c61f13a79a8ce23ef4bc110` |
| catalogue20 B `evidence/stderr.log` | 683 | `40901ae27d793c285ece24e6217c39df26a9cf86e79c03e2c8546c805af07ff8` |
| message build A `prepared/main.cpp` | 38500 | `a601ef1449eaa4c3ec2c85ea561ed4cc5c1aa75769a4ad1def002d348a971e68` |
| ordinary build D2 `prepared/zonetool.cpp` | 35974 | `106ccdb4aec584184132c309c117f778d504ca9e64e8a821d23bfecc83bc8635` |

Stdout contains initialization completion and then the refusal `Exact donor
zone did not finish loading`. Stderr's message record on thread 23136 ends at
`requested=384 read=`. The message formatter and argument list are consistent.
The log does not reveal the missing numeric field, payload or underlying cause;
none is reconstructed here.

The retained main marks `catalog_message_seen` before reading or printing the
message (`main.cpp:327-354`). The CLI invokes `fflush(nullptr)` and then
`quick_exit` on its success/failure paths (`zonetool.cpp:1036-1044`), outside the
engine exit hook. Terminating the process while the other thread is publishing
is a plausible race, not a proven event ordering. The correction addresses that
source-level gap without claiming to identify the donor-load failure.

## Separate overlay

`prepare_message_publication.py` renders the exact existing CLI/message source
from the pinned retained source at
`fab935826c898806855376662a8a03317b3ad8f1`, then overlays only:

- `main.cpp`: single-record publication and bounded CLI-close wrapper;
- `zonetool.cpp`: declarations and the two existing success/failure CLI exits.

It rejects changed/multiple anchors. The original helper call, its return
value, `LastError` restoration, read bounds, install guards and engine
`exit_hook` remain unchanged. Neither the old generators nor the historical
patch/providers are edited. The output is **not a build plan** and cannot be
used as a qualification receipt.

The new native body is `native_message_publication.inc`. The old formatter's
whole line is first formatted into `char record[1024]`; a negative, empty or
truncated formatting result is refused. At most 1023 bytes are submitted in one
`WriteFile` to the existing standard-error handle. Only API success **and exact
byte count** qualify as written. There is no streaming `fprintf` for the captured
buffer and no retry on a failed/short write. This proves only OS acceptance of
that write, not durable storage or a complete downstream transcript.

The existing message schema remains `/1`. At maximum field widths the record is
948 bytes; the existing install/context/caller upper bound remains 7994 of the
8192-byte stderr contract. No new diagnostic line or file is added. A short or
missing record remains inadmissible to the existing parser; its bytes are never
filled in from expected messages or source strings.

## State and bounded closure

The interlocked phase has four values: `idle`, `capturing`, `published`,
`closing`. Capture is admitted only by compare/exchange from idle to capturing.
The separate publication result starts pending and becomes written, format
failure, write failure or short write. A successful write publishes its counts
and result through an interlocked barrier, then changes capturing to published
only if closing has not already won. A failed writer consumes the single claim
and cannot admit a second capture.

Before either CLI exit, closing is exchanged atomically into the phase,
preventing any new capture. The closer then checks the publication result with
both a 100 ms elapsed-time budget and a maximum of 100 polls. Each pending poll
checks the deadline before requesting `Sleep(1)`; even a nonadvancing clock
cannot create an unbounded loop. The closer performs **no I/O, flush, stream
lock, allocation, wait-for-thread, cancellation or join**. It never waits for a
blocked output handle to become writable.

The bound is on the code's wait budget and finite poll count. OS scheduling can
delay a resumed thread beyond the deadline; this is not a hard real-time promise
that process exit always occurs within exactly 100 wall-clock milliseconds.
There is no potentially blocking sink operation in the close path that could
turn the explicit deadline into a wait for output.

The terminal internal result distinguishes no capture, published, publication
failure and incomplete. It is stored in `catalog_message_close_result` and is
not overwritten by a later successful writer. A late writer also cannot reopen
the closing gate. Both the close function and the CLI wrapper restore their
entry `LastError`; the original `EXIT_SUCCESS` or `EXIT_FAILURE` is passed
unchanged to `quick_exit`. The non-catalogue CLI retains its original flush.
Other engine exits are not hooked, delayed or rewritten.

**Internal result versus published evidence:** on timeout, bad handle, short
write or a stalled sink there may be no complete stderr diagnostic at all.
The closer intentionally does not try another synchronous print/flush to report
that failure. The atomic result is available to a debugger, not asserted to be
an output artifact. The outer observer must continue rejecting absent/partial
records; successful publication is not inferred from exit code or internal
intent. Unrelated engine termination can still interrupt a capture, because
this correction only covers the two CLI exit paths.

## Preparation and future build requirement

```powershell
python tools-source/asset-bridge/t7-iw7/prepare_message_publication.py `
  --source <retained-pinned-source> --output <fresh-absolute-directory>
```

The generator reads pinned source text only. It writes two C++ sources, one
overlay patch and `source-report.json`, with a total bound of 1 MiB and a fresh
non-reparse destination. The report binds source/overlay hashes, marks
`BuildPlanCreated`, `NativeExecuted`, `CandidateCreated`, `RuntimeVerified` and
`Ready` false, and requires fresh stages **main, zonetool11, link**.

Source preparation A is retained in the owning checkout at
`runtime/t7-message-publication-source-a/`:

| Output | Bytes | SHA-256 |
| --- | ---: | --- |
| `main.cpp` | 42948 | `b96e145dd96558ff6307854748d25ea43638b258d4f97b630c99f8f0c68d4c38` |
| `zonetool.cpp` | 36028 | `280e301f8be1b61133b0c6d86644a7d0ce0fb676fc41abc261ae206ad8b44524` |
| `publication-overlay.patch` | 7161 | `289f4483f9de06c8240dbfcdb2de2ecaca2a001025cfcb006fa8146064b6f5a1` |
| `source-report.json` | 1538 | `b0a6cfa9f95129842450ffa766c6c34230afc7a9731f1912562208798fc0daf8` |

Total 87675 bytes; metadata and patch together 8699 bytes. No executable, PDB,
object, manifest or asset payload was opened or created by this task.

The historical `--catalog-message` plan recompiles only main and reuses the old
CLI object. It is explicitly incompatible with this correction. Its existing
source-equality check refuses the changed CLI, verified by a light test. The
future coordinator must supply a separately reviewed plan/provider profile that
requires **both** new objects and binds the corresponding sources before link;
simply rebuilding main cannot apply the two-exit correction. That new build
profile and heavy-work admission are outside this source handoff.

## Validation and handoff

With `IW7_T7_SOURCE` pointing to the retained pinned source:

- `test_message_publication.py`: **16 passed**, covering eight competing capture
  threads, close-before-capture, a blocked writer, late publication, write failure,
  short write, formatting failure, fixed-clock/poll bounds, source ordering,
  exact two-exit wiring and refusal to reuse the old CLI object.
- `test_catalog_*.py`: **54 passed**, including the unchanged historical generated
  source identities, original helper forwarding and existing output bounds.
- `prepare_cli.py --check`: passed; historical CLI patch remains exactly the
  rendered 19890 bytes.
- Source preparation A completed within its size cap, without native execution.

The concurrency tests execute a Python behavioral model plus source assertions;
they are **not native MSVC/Win32 execution** and do not measure real scheduling,
stderr durability or engine behavior. Native compilation, code review by the
coordinator, an admitted execution and complete-record observation remain required.
No new catalogue/export is claimed and no missing diagnostic cause is invented.
The coordinator owns private PR/CI/merge and the later two-TU build plan.
