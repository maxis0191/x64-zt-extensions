# Multisurface build preparation B: default refused, 2026-10-13

B was prepared at repository commit `732951a41db6816c8eeeac0582500ea605f14f03`
after PR199 added the transitive writer headers. It has 1146 unique Inputs and
141 unique Bindings (135 text, six binary metadata). Default validation refused
the runner's historical 128-binding limit before opening those bindings,
loading providers or acquiring admission. B remains frozen and must not run.

## Preserved preparation evidence

Files are under `runtime/t7-multisurface-build-plan-b/` in the producer worktree.

| File | Bytes | SHA256 |
| --- | ---: | --- |
| `build-plan.local.json` | 365638 | `23b93e754c725b81b438e12498fac8c93257aa43368889fecc22e3ff1fefa3dc` |
| `commands.local.json` | 5716 | `cef0613349708d13179a496ba2241e995d9e6dfe2d20ef9842918cc65bab42ce` |
| `default-validation.local.json` | 846 | `f0ebb7f2a8baaf43b07b1c88eda4353cc9496a42a7582848aeb6c31c1c361c14` |
| `preparation-proof.local.json` | 26746 | `eb27c18f82e385f47d8ac7930601d7d1807e61e5db29501ba45a2879a7bd0f07` |

Preparation chunk `96ddcb` exited zero. Actual DEFAULT chunk `fe1593` exited one
in 0.5399948 seconds with `Input set bound/uniqueness differs.` at the former
runner line 215. Its source was 25995 bytes, SHA256
`f2b5152b1e18f8a17c1a73e1c5845c9ac535f15958f28048e1dfe5875b7936f9`.

The 1080 baseline Inputs match A exactly; the 66 added header pins total 87204
source bytes. All seven prepared sources match A byte-for-byte, and all four
response files match after preparation/run-root normalization. The three v2
transitions and retained C/D2/E7 proof are unchanged except for the explicit
header closure. The intended build still has two fresh objects, 411 retained
objects, 18 libraries and one resource. Both A and B run roots remain absent.

A is unchanged at 15 files / 517988 bytes. B has 15 files / 577126 bytes. Their
combined **30 files / 1095114 logical bytes** fit the existing 16 MiB preparation
allowance, within the same 272 MiB overall allocation. No native products were
created; no existing budget was freed or enlarged. These are logical file sizes,
not measured NTFS allocation or global disk growth.

## Narrow runner correction

`Assert-T7InputBindings` now runs at the original early bound check. Legacy
profiles keep the 128-binding maximum. The 141-binding exception requires the
publication profile, explicit v2 proof, 1146 unique Inputs, 135 text bindings
and the exact retained six-tool binary metadata inventory. Marking an EXE or
other opaque build artifact as text is refused before any binding is opened.

The gate verifies the complete 66-header inventory using the canonical sorted
relative-path, raw byte-count and SHA256 rows already defined in
`MULTISURFACE_HEADER_PINS`: 7676 UTF-8 bytes, SHA256
`5ee7ea0b46848bca9f4d365d0035cf070b2f57c6723019ab1288a54a93a7297b`.
Every row must match exactly one Input and one text Binding. The six binary
metadata rows and three source transitions also have exact canonical inventory
pins. Their contents are not opened by this check. Existing C dependency JSON,
E7 journals, prepared v2 sources and compiler-context/PCH evidence must match
their reviewed pins and bindings. No automatic input discovery was added.

Tests exercise the runner's actual validator and its placement before binding
access, binary metadata, providers and admission. The full profile test reports
**409 checks**, including 44 new checks for nominal v2, missing/mutated/extra
headers, missing proof, mixed profiles, classification swaps, changed retained
proof and legacy 128/129 boundaries. The Python recipe suite passes all 56 tests.

Four additional calls use the real DEFAULT entry without `-Run`: nominal v2
passes; missing proof, swapped header/binary classification and legacy 129 fail
at their expected early gates. These use a single temporary JSON fixture derived
from B with only the current runner pin updated before each case's deliberate
mutation. The fixture is bounded to 512 KiB and removed individually afterwards.
B is verified unchanged. This is source/metadata testing, not preparation C or
build admission. No EXE/OBJ/PDB/asset content is read or hashed.

Next: independent review and coordinator integration of the runner correction,
then separately authorized preparation C. Its runner source and plan must be
freshly pinned. A/B are not patched or reused as runnable plans. Native build,
export, fastfile, rendering and owner acceptance remain pending.
