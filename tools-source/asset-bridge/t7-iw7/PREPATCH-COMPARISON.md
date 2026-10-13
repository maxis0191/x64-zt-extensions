# First-DPI comparison and next experiment

The single diagnostic capture on 2026-10-12 removes the nine **observed disk
discrepancies** as reasons to reject this candidate at the first-DPI rendezvous.
It does not prove compatibility of the whole T7 ABI. The
[sanitized evidence](prepatch-comparison-20261012.json) links the exact saved
reports, runner receipt and Plan C. No executable was reopened for this comparison.

## Findings

- All 12 windows changed: **1,530 of 1,536 bytes** differ from inspection-a.
  This establishes a transformation before the capture point, without attributing
  every change to a particular loader or proving that all unpacking has finished.
- All eight specified instruction/signature checks match the pinned source:
  `boot_call` is a direct CALL to `0x140504170`; `image_loader_call` is a direct
  CALL to `0x1407DB4C0`; both copy-info sites start on short branches; all three
  intact-integrity patterns and the split-integrity pattern match.
- Every observed site/window page has `PAGE_EXECUTE_READWRITE` (`0x40`). The
  third intact-integrity site remains in a mapped PE section whose header flags
  are non-executable, but its actual saved VirtualQuery page is executable.
  Section flags and current page permissions must not be conflated.
- The mapped base is the expected `0x140000000`. Image size, timestamp,
  entrypoint, DLL characteristics and `.pdata` record count match the disk report.
- Seven sites have a containing `.pdata` record. Six records begin inside their
  windows: DB find/load, boot CALL, server-thread RET and both copy-info patches.
  Capstone 5.0.7 forward-decoded **883 saved bytes** from those six begins. All six
  sites, plus both NOP edges `0x1401D87AE` and `0x1401D87B3`, are decoded instruction
  boundaries. No instruction crossing those eight boundaries was observed.
- The image-loader record begins before its captured window. SL and the four
  integrity sites have no containing record. The probe saves only four unwind
  header bytes; it does not validate the full unwind format or calling convention.
  Forward decoding is conditional on the saved begin address, not a complete ABI proof.

The static baseline retains its 9 conflicts and 37 unknowns as historical evidence
(25 unwind-header, 7 instruction-anchor, 5 non-file-backed globals). Runtime
observations supersede the corresponding disk-only conclusions; the comparator
does not erase those baseline records or claim that the other 26 windows were read.
These coverage limits do **not** automatically require another probe.

## Smallest next useful engine experiment

Source review found no new concrete refusal in these observations. A separately
reviewed, isolated **single-zone catalogue** may proceed as an experiment that can
fail, after the runner owner selects a real zone and its bounded bootstrap stock:

```text
zonetool-t7.exe -t7-iw7-catalog <exact-selected-zone>
```

Do not combine it with `-t7-prepatch-probe`, which exits before the needed patches.
The existing catalogue captures model names and header counts (no mesh, surface
or bone-array export), limits names to 1,024/256 KiB, and caps its JSON at 512 KiB.
It refuses an already-loaded zone, excess data or an existing output root. No
zone is selected by this document. A tiny FF's filename/size alone does not prove
that it is a donor, that it will still be unloaded, or that bootstrap can complete.

Reviewed ordering at native source `fab935826c898806855376662a8a03317b3ad8f1`:
`component/t7/zonetool.cpp::post_unpack` applies the boot CALL/RET/branch/image
patches and calls `initialize`, installing DB-add/DB-finish hooks and the reviewed
five-byte NOP. Scheduler and command components add their own hooks. Later the
boot stub invokes original init `0x140504170` **before** `t7::start`/`handle_params`.
Thus original init may request files before catalogue code runs. No required
bootstrap FF list is named by this C++ path; none is inferred from the capture.
The catalogue then uses `load_zone(zone, true, false)` and the existing DB wait.
The reviewed source has no internal timeout for those waits: the next runner
must bound the entire boot, DB wait, output and job closure, not only publication.
Unobserved patch/function sites are explicit residual risk of that experiment,
not evidence that they are wrong. No new native run is authorized by this report.

## Reproduce from saved JSON only

`compare_prepatch_reports.py` uses the existing inspector's site list and pattern
checks. It reads at most 1 MiB per static/receipt/plan JSON and 256 KiB for the
capture, rejects duplicate keys/non-finite JSON and checks exact window shapes.
It never opens files named by the input documents, attaches to a process or
rehashes the dedicated binary. It verifies only saved links; the pinned runner
supplies process ownership, binary verification and closure evidence.

```text
python -B compare_prepatch_reports.py <inspection-a.json> <capture.json>
  --static-sha256 <static hash from evidence>
  --receipt <receipt.json> --receipt-sha256 <receipt hash from evidence>
  --plan <plan.json> --plan-sha256 <plan hash from evidence>
  --decode-anchors --output <new-comparison.json>
```

The command is shown wrapped for readability. `--decode-anchors` is optional and
uses existing Capstone; the base comparison needs only stdlib (`python -B -S`).
Without receipt/plan and both expected hashes, results remain uncorrelated.
Output contains hashes/counts/boundary checks, no raw windows or disassembly.
Exit 0 means a comparison was produced, never permission to boot or an ABI pass.
Fourteen synthetic tests cover changed CALL targets, relocation, page/section
differences, malformed windows/regions/JSON, provenance mismatch and incomplete
closure. The existing ten helper source-contract tests also pass.
