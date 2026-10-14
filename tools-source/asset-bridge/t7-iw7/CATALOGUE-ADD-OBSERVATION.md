# C2: observe the existing T7 asset-add call

The C `zm_common` experiment is still **Failed / NoCatalogue**. Its 17 observer
records include donor-load entry but no selected public-find call or donor-load
return. The 133-byte fatal reports **RawFile/default-asset resolution** for
`ui/uieditor/widgets/attachmentnamesdisplay.lua`; it does not prove Lua execution.
Neither a missing selected record nor a global phase identifies the cause.
The qualified C source `fa45c39`, plan `627f3aac`, binary `88f2147d` and schema
`iw7.t7-zm-observation/1` remain frozen.

## Primary source and scope

At native revision `fab935826c898806855376662a8a03317b3ad8f1`:

| Existing source | What C2 reuses |
| --- | --- |
| `src/zonetool/zonetool/t7/zonetool.cpp:351` | DB-add stub, existing XAsset and the single original `(type, header)` call |
| `src/zonetool/zonetool/t7/zonetool.cpp:824` | Existing hook at `0x1401D4600`; C2 creates no additional detour |
| `src/zonetool/zonetool/t7/functions.hpp:8` and `:12` | Typed `get_asset_name(XAsset*)` and `DB_GetXAssetName` at `0x14019F080` |
| `src/zonetool/zonetool/t7/zonetool.cpp:373` | Existing current-fastfile pointer at `0x1468FD4A8` |

The supplied structs do not define a RawFile layout. C2 uses one typed name
getter for type 47, guarded in a POD-only SEH leaf, then bounded self-memory
reads. It selects only the exact name, with or without one leading comma,
including its NUL. A getter/read refusal has `target=unknown`; it is not a
selected target call. Other types and readable nonmatching names produce no
call record. The original add executes once with unchanged arguments and
return value, outside SEH. Error guards restore CRT errno before LastError.
No mutex is held across the original call.

The selector is enabled only for exactly `-t7-iw7-catalog zm_common`. `enabled`
means that selector configuration was reached, not proof of hook activation:
the retained hook helper ignores the return of `MH_EnableHook`. C2 does not
silently repair that shared behavior or claim that absence proves API bypass.

## Finite evidence contract

`[T7_ZM_ADD]`, schema `iw7.t7-zm-add-observation/1`, admits one enabled record,
at most one selection refusal and at most four calls, each with one entry and
one return. The bound is **10 rows, 512 bytes per complete row including CRLF,
8 KiB observer and 16 KiB combined stderr**. The unchanged F part still needs
its own 8 KiB validator. Each row is submitted in one WriteFile without retry;
missing, short or interrupted publication remains incomplete evidence.

Call IDs 0..3, TID and reference-prefix state correlate entry/return. Entries
include the observed exact name as hex, caller and asset pointer. No pointer
is dereferenced by the text parser. A return without its unique matching entry,
thread or prefix is refused. An entry without a return remains admissible
incomplete evidence; it is not alone proof that the original failed to return.

Before/after fastfile snapshots copy only its pointer and at most 64 name bytes.
States distinguish pointer unreadable, null, name unreadable, NUL-terminated
read and complete prefix. `ff_atomic=0` is mandatory: the global may change
between reads. It identifies context, not the supplying file or error origin.
No RawFile payload, new DB lookup, extra load, substitute file, default override
or UI suppression is introduced. The parser returns legacy F text byte-for-byte
and never declares catalogue or compatibility success.

## Separate source transition

Build profile and candidate profile are `t7-zombies-catalogue-observation-c2`.
The explicit producer flag is `--zombies-add-observation-c2`, together with
publication, render-only V2 and retained reuse proofs. C/V1 and C2/V2 selectors
are exclusive. The new `ZombiesAddObservationC2` six-field build marker uses
schema `iw7.t7-zm-add-observation-build/1`.

The exact V2 base is **112377 bytes / c63d9552464da674d3b03c35f7edc16385fb9370b113a3925fd7bc4835fb005a**.
The C2 CLI is **119139 bytes / 19af683d0c609d43cefc7c93dd3d7fa6f7ae1a6f5b90d2945d37b1830bda1111**.
Only the known CLI binding maps through this finite transition. The original
three-transition digest, V2/material pins, 66-header dependency facade, 151
bindings (145 text, six binary), 1146 inputs and three fresh stages remain
strict. C2 additionally pins the PR39 streamed-contract tests at 17443 bytes /
`9146f69c84c4178341010f7b6d7c10c4226ce4c7ec524b5fcdf4da742a95ac30`;
the frozen C and V2 binding branches keep their prior test pins. The module and
adapter have separate exact source bindings. No arbitrary
changed-TU reuse is admitted and the older C transition is not relaxed.

This is source preparation. Native compilation, actual observation and a
catalogue are unverified; they require separately reviewed plans and admission.
The local checkpoint passes 36 Python tests (including actual pinned-source
wiring/inversion, matching/refused/interrupted records and the frozen C positive
transition) and 526 PowerShell profile/input checks. These are source/contract
checks, not MSVC compilation or engine execution.
The first source-only preparation from commit `5fb23f9` refused the stale CLI
contract's pre-PR39 test pin before any binary content, lease or run directory.
That source package remains unchanged. The correction updates only the exact
streamed-test snapshot and its C2 binding; it does not rewrite the test or
relax the older profiles.
The corrected source package at `278ea63ef90b7c9acca8edee86f99b8094920846`
verifies 890 exported text files / 8484677 bytes. Its 313411-byte source manifest
has SHA256 `d8c8c4c0b114c3c7d59418a730be6dec0e3ec88381985fef2caa590c043dc65c`.
The real DEFAULT check passes for the 369645-byte plan, SHA256
`c559d838ced188d7ca0628e4dda063f5699d1b499f4d6c9e1b30a3c8244734f9`:
151 bindings, 1146 inputs, no missing pins and main/zonetool11/link stages.
NativeTypesLoaded, BinaryInputsHashed, LeaseAcquired, RunRootCreated and Ready
are all false. This package/plan remains a separate immutable source checkpoint;
the result is not a build receipt or permission to execute.
Next: review the C2 source and coordinate its distinct ops projection before
any build or stock execution.
