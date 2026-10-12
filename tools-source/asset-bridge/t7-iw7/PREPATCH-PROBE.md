# Single T7 observation before post_unpack patches

This is source preparation, following the [disk observation](executable-static-observation-20261012.json).
`native_prepatch_probe.inc` has not been compiled or run at this checkpoint.
The separate CLI owner controls main.cpp wiring/build; the coordinator controls
review and native GO. No build, launch or compatible ABI is implied by this file.

## Exact contract

From a private ignored stage prepared by the existing native runner:

```text
<reviewed-instrumented-zonetool.exe> -t7-prepatch-probe
```

Exactly two argv entries: executable and that exact flag. No zone, output
argument or extra flag. The fixed report is `t7-prepatch-probe.local.json`, at
most262144 bytes, in the initial stage CWD. Validation binds its absolute path
before load_binary; a changed CWD, existing output or missing early binding is
refused. No overwrite or alternate output fallback. Raw output stays ignored.

Include the helper once after engine-name macros. Its API in namespace
`zonetool::t7_prepatch_probe` is:

- `bool requested() noexcept`: existing flag detection; a flag-parser exception
  enters the refusal path rather than falling back to normal mode.
- `bool validate_invocation() noexcept`: call before selecting/loading an
  engine; false must terminate exit2. Require the dedicated file and T7 mode
  through the existing boot guard. It reads no payload bytes.
- `int capture() noexcept`: call once at the start of the intercepted
  SetProcessDPIAware, using `exit_hook(capture())`. The caller must never reach
  component_loader::post_unpack or normal continuation in this mode, on either
  success or failure. Loading failure or entrypoint returning without capture
  must also terminate2, without normal-mode fallback or a blocking MessageBox.

The existing create-new writer performs exclusive publication, flush and exact
readback. Exit0 means a complete capture for offline review; exit2 means partial,
refused or failed capture. Publication failure can yield no usable report.
An existing/truncated/malformed output must never become CaptureComplete.

## What is captured

Only the actual already-mapped named module is read. GetModuleHandleW does not
load it. Every read is checked against image bounds, VirtualQuery allocation
ownership/MEM_IMAGE, committed non-guarded pages and the **4 MiB cumulative
requested-byte cap**. ReadProcessMemory uses GetCurrentProcess only; partial
reads fail. The helper never changes protections, opens another process, loads
a DLL/zone, calls a DB function, patches an address or starts a worker thread.

PE headers/sections and at most2 MiB of `.pdata` are read; the full `.pdata` is
not published. Overlapping function ranges are refused. The report contains
only applicable function records plus their first four unwind bytes, explicitly
without claiming the unwind format is validated. The12 windows total1536 bytes:
the initial5 disk windows,2 copy-info sites, image-loader call and4 integrity
sites. A portable contract test checks exact correspondence with the static list.

Mapped PE flags and VirtualQuery page protections are distinct observations.
These are sequential reads, not an atomic process snapshot. Earlier import
hooks, post_load and the payload entrypoint have already run. This probe cannot
promise zero prior file access/effects or prove that unpacking has completed.
It stops before the absolute post_unpack patches and initZoneTool.

## Machine-readable evidence

Schema `iw7.t7-prepatch-memory-observation/1`, phase
`first_dpi_before_component_post_unpack`. The report always initializes
`capture_complete`, `requested_bytes`, `returned_bytes`, `window_count=12`,
`window_observations` and `windows`. Status is `captured_for_offline_review` or
`incomplete_stop`. Available provenance includes PID, thread ID, process creation
FILETIME as a decimal string, actual module path/base and mapped PE metadata.
The runner must bind these to its own process generation and input pins.

Each window carries site/RVA/window bounds, region state/protection, observed
bytes and an optional runtime-function record, or an error. CaptureComplete
requires exit0, a valid bounded fresh report with exact phase/process identity,
all12 windows and full reads. Exit2 with valid partial JSON is CapturePartial;
missing JSON is NoCapture. A complete capture can still reveal incompatible
sites: `boot_authorized`, `abi_proven` and `runtime_compatibility_proven` are
always false. Review the observed code/metadata offline before choosing any
subsequent native experiment. No automatic retry, unpack assumption or fallback
to ordinary boot is permitted by this contract.

Validation at preparation:10 stdlib source-contract checks pass, including fixed
window correspondence, non-mutating API surface, caps, output binding and
fail-closed entry/exit requirements. They neither compile the C++ nor prove
Win32 behavior. Native compile and runtime remain separate future gates.
