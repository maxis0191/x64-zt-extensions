# Multisurface build preparation A: blocked before Run, 2026-10-13

Preparation A at repository commit `709f11aa7abc6ad26880fc0f1b7ed1aa3f89b0f6`
passed the default source/metadata check but omitted the transitive headers
introduced by the explicit IW7 surface writer include. No native compilation,
admission, binary read/hash, candidate execution or export occurred. The plan,
envelope and default evidence remain frozen; **A must not run**. Its default
success does not prove that a later compiler dependency record would pass.

## Frozen evidence

All paths below are relative to `runtime/t7-multisurface-build-plan-a/` in the
producer worktree. The 15-file scope is **517988 logical bytes**, within the
16 MiB preparation allowance. This is not an NTFS allocation measurement.

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `build-plan.local.json` | 304851 | `2a8c4ca3c03c5216cf07cd319150488aa2dac1562db27281d7d292055df3f297` |
| `commands.local.json` | 5166 | `e003cbcbe4a4630a231fc52d450283ea2545227f370612ae68353bbd9ecc26e6` |
| `default-validation.local.json` | 4055 | `69b60c367db6aa1bd4abe78cf2ee2870f8e84dd2dd07852c4c2e5fafbfa91078` |
| `preparation-proof.local.json` | 25736 | `7a717d4911d364b9be6f02e6f2d088f5d2278e6926c337093cb92ea2b30caf5c` |

Preparation tool chunk `2114d3` exited zero; default chunk `af3e58` exited zero.
The source runner was 25995 bytes, SHA256
`f2b5152b1e18f8a17c1a73e1c5845c9ac535f15958f28048e1dfe5875b7936f9`.
No persistent build host PID was recorded and no native build process ran.
The later proof explicitly blocks
the envelope's proposed future command; that command was never authorized.

The 1080 input rows exactly match the JSON values in diagnostic build A.
There are 69 text bindings and six binary metadata bindings. Exactly
main, CLI and the adapter changed among the prepared sources. All four response
files match diagnostic A after preparation/run-root normalization. The intended
stages remain main, CLI and link, with 411 retained objects and two fresh ones.
The intended run directory `runtime/zt-t7-multisurface-a` remains absent.

## Missing closure and source correction

The P2 triangle-ownership correction uses the real IW7 writer declaration:

- `src/zonetool/zonetool/iw7/assets/xsurface.hpp`: 735 raw bytes,
  SHA256 `5b71c1049114cc9b06168576a845fe80596d1973e87f9d731cf47ecf539228a8`.
- Its direct include `src/zonetool/zonetool/iw7/zonetool.hpp`: 3159 raw bytes,
  SHA256 `612de0e4a64fceb5ec1b762fd5825d66c40f231e290c684d71896f50441f165a`.

The second header includes the wider IW7 facade. The sealed E7 dependency
journal, 15206288 bytes with SHA256
`d9cdd533796a9fe14e0d5140d8adcbf5cbc932fafd4c06e18a615d15199a2185`,
records 150 dependencies for `src/zonetool/zonetool/iw7/assets/xsurface.cpp`.
Compared with A, the difference is **66 headers / 87204 bytes**, plus the known
E7 PCH. The header maximum is 12403 bytes. The PCH is excluded because the
prepared commands use `/Y-`; the baseline already includes the original
`std_include.cpp` dependency closure.

`prepare_build.py` now contains an exact, pinned 66-header allowlist enabled
only by `--resident-multisurface-v2`. It checks the sealed E7 read and compiler
journals, verifies equality of writer/CLI compiler context except the source
and object destinations, and requires the exact additional header set. It
reads only those bounded text headers and requires every byte count/hash.
Missing, extra, duplicate, overlapping or changed inputs are refused. Each
header enters both Inputs and the default-checked text Bindings. There is no
glob collection, new native patch, ABI change, PCH reuse or opaque payload read.

The existing 1080 inputs and three source transitions stay intact. The expected
next plan has **1146 inputs**, 135 text bindings and six binary bindings.
That next plan has not been prepared. The 4/6 GiB admission estimates,
120/600/5-second limits and 256 MiB native output allowance remain unchanged.

Validation: 56 source/recipe tests passed, none skipped, including real pinned
E7/header reads in memory, refusal of every one of the 66 missing and
same-length mutated headers, closure/context mutants and previous recipe
tests. No native compilation or runtime acceptance is claimed.

Next: independent source review and coordinator integration, then a distinct
preparation B under a separate preparation authorization. Build, export,
fastfile and game execution still require their own gates.
