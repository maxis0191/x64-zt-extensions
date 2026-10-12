# T7 diagnostic before absolute patches

2026-10-12. The coordinator selected an earlier diagnostic stage than the
catalogue: observe layout, page protections and bounded code windows at the
first intercepted `SetProcessDPIAware` after entrypoint, before component
`post_unpack` / Arxan or other absolute-address patches, then exit. The engine
worker owns that bounded helper and its contract; the T7 worker owns integration
into the existing build preparation. This checkpoint prepares only the local
environment. It starts no process and does not qualify a candidate or hook.

## Environment actually prepared

The new ordinary `runtime/t7-prepatch-a` tree contains `work`, `evidence` and
`temp` directories. Its `work` directory contains exactly two NTFS hardlinks:

| Local filename | Existing source | Bytes | Previously verified SHA256 |
| --- | --- | ---: | --- |
| `BlackOps3_UnrankedDedicatedServer.exe` | Durable one-file Steam acquisition | 21,737,352 | `3df511d71e3690b14517379783bbfb713f6fe2ed2f2e73b445b4878216686156` |
| `steam_api64.dll` | Owner's installed BO3 dependency matching the manifest | 235,600 | `71af8666392acad2080a816b9f1196fe9ccb950e1db8a549f8312c4d231f55a8` |

Source/destination file IDs match for each link. Source length, attributes and
last-write timestamp remained unchanged; all checked ancestors/entries were
free of reparse points. Read-sharing-only source handles were held during link
creation and released afterwards. Hashes are inherited from the verified prior
receipts, not remeasured by this preparation. Reopen retained input guards and
verify exact hashes under the separately admitted runtime stage before use.

There is no candidate, `zone`, `../zone`, FF, FD or XPAK in this tree. No payload
was copied, native provider loaded or resource lease obtained. Exact paths and
file IDs remain private. [The sanitized observation](prepatch-environment-20261012.json)
binds the local preparation receipt by hash. The prepared environment is not
ready to execute until the final helper contract and instrumented candidate
are bound. An uninstrumented D2/E7 candidate must never be substituted.

## Runtime boundary to preserve

No zone/catalogue/export command belongs in this diagnostic. The final argument
and output contract must come from the actual reviewed helper integration;
none is invented here. Bind its final EXE hash, source/build receipt, exact
command, working directory, output location/caps and expected exit codes before
the coordinator's separate GO. Reuse the witnessed NativeJob, common scheduler
and original-handle closure through the existing small profile, with no new
supervision framework.

The entrypoint runs before the intercepted call and may access files or have
other effects. The absence of zone aliases does not prove zero engine I/O or
an OS sandbox. Stop clearly on missing files; preserve the first failure and
do not automatically add assets, Steam DLLs, BATs, playlists or guessed bootstrap
FFs. Failure to reach the hook, a native crash or a deadline is not compatible
layout evidence. No later ZoneTool init at `0x140504170` or absolute patch may
run in the witness path, including on diagnostic failure.

Keep the conservative planned engine admission separate from static inspection:
6 GiB physical / 8 GiB commit is an estimate, not a measured requirement. Pin
the reviewed stage deadlines/output caps in its final runtime plan. Existing
85% commit pressure, explicit stop request, exact original job stop, fresh
root/ActiveProcesses closure and lease quarantine rules remain. Do not shrink
budgets to bypass an occupied slot or interrupt Main/the owner's client.

The aliases are currently retained as prepared evidence. The dedicated EXE's
read-only attribute is shared across its hardlinks: do not clear it through an
alias or use a cleanup that silently changes original attributes. Any future
removal must use exact destination/file-ID checks and a reviewed file-level
method preserving the source attributes; otherwise retain the small aliases.
Do not recursively remove stock. No source/profile/configuration restore is
needed from this preparation because none was overwritten, but external writes
from a future run must be checked before claiming restoration complete.

After this diagnostic is qualified, the separate catalogue still needs its
actual engine/zone compatibility and startup stock decisions. A memory-window
receipt by itself proves neither a real model name nor conversion or rendering.
