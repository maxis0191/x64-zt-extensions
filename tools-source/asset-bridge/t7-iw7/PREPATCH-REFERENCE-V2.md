# T7 reference resolver: fixed prepatch V2

The actual C2 stock run reached DB_AddXAsset with RawFile type 47 and the
reference `,ui/uieditor/widgets/attachmentnamesdisplay.lua`. The observed
caller was `0x1401DB2C5`. No matching return was published; a default-RawFile
fatal message followed on the same thread. The source at native revision
`fab935826c898806855376662a8a03317b3ad8f1` names `0x1401DB2B0`
Load_SimpleAsset. The caller is its entry plus 0x15, subject to mapped-code
verification. This evidence has not identified the dependency fastfile or
established a hook/init defect. See CATALOGUE-PLAN.md for the failed C2 run.

V2 supplies the missing original-code observation for this question: what
signature and reference/default branch does DB_AddXAsset use, and what call
does Load_SimpleAsset actually make? Its selection is fixed:

| Function | RVA | Bytes |
| --- | --- | ---: |
| DB_AddXAsset | 0x1D4600 | 2048 |
| Load_SimpleAsset | 0x1DB2B0 | 256 |

The helper preserves V1's PE validation, MEM_IMAGE/readability checks, complete
ReadProcessMemory results, ordered .pdata validation, 2 MiB .pdata bound,
4 MiB total-read bound, 256 KiB report bound and exclusive fresh-file writer.
It captures at the first DPI rendezvous before component post_unpack and
immediately invokes the existing exit hook. It does not follow callees or load
fastfiles. Its observation remains offline evidence requiring interpretation.

The distinct profile is `t7-prepatch-reference-v2`, with sole argument
`-t7-prepatch-reference-v2`, report `t7-prepatch-reference-v2.local.json` and
schema `iw7.t7-prepatch-reference-observation/2`. Build preparation requires
`--prepatch-reference-v2`, a paired ten-field `ReuseCompile.PrepatchReferenceV2`
marker (`iw7.t7-prepatch-reference-build/2`), and exactly main/link stages.
CLI/catalogue/export markers, other arguments, address selectors and changed
source tuples are refused. V1's helper and wiring remain byte-identical.

The immutable V2 helper is 15785 bytes / SHA-256
`0309b81376d3708cc8de43d297b43fbdfbdd535120e0ad054c157735c2c7457a`.
Wired main is 14524 bytes /
`e719365c5a7f407218a7218bd9c7090421934042c34a9f163d9a8e3d42ee1e28`.
The separate source-contract section records the helper/wiring pins without
adding bindings to frozen C1/C2 or V1 builds.

To retain a two-stage build, this profile alone reads the six exact non-main
text payloads of retained plan C (292575 bytes /
`422e79898fa2b16defc8193182fe146e2db5d73aeb4516c2bd2aaf87c409c4de`)
and its receipt (26199 bytes /
`af6beecf7a8892e16266a7641d2799f665f86fa8ad7c40c61561b782534f7897`).
The existing reuse checks retain the successful closed CLI/xpak sub-stages
and preserve the enclosing group's Failed status. Current plain main and
retained main have separate pins; the historical converter is not qualified
for a new export by this diagnostic.

Source verification on 2026-10-14: 79 Python checks passed using the actual
pinned native source and E7 text journals; one historical C1 snapshot check
was skipped. The new 100 PowerShell profile/binding controls and existing
526 profile / 132 binding controls passed. The real DEFAULT plan B had
79 bindings (73 text, six binary metadata), 1083 inputs and no missing pins.
It returned exit 0 with NativeTypesLoaded, BinaryInputsHashed, LeaseAcquired,
RunRootCreated and Ready all false. This was a
source/metadata check with no admission or native execution.

Preparation corrections are retained: current converter/header text could
not silently replace retained C inputs, so the profile now pins its six
historical text payloads; the first real DEFAULT also caught an incorrect
object-shaped assumption about string SourcePlan/Receipt paths. The corrected
fresh plan passed. An earlier abbreviated `-Plan` invocation failed parameter
binding; the exact parameter is `-PlanPath`.
Qualification review then found that singleton arrays could satisfy PowerShell
text comparisons. V2 now requires scalar strings before I/O; 34 added controls
verify the exact type-boundary refusal for profile, marker, reuse and pin fields.

Source merged in [PR 57](https://github.com/maxis0191/x64-zt-extensions/pull/57)
as `2f74c9745f95d90455591591638d3c013e7a069b`, after peer source review and
qualification approval of exact final head `be27a38b9b51b98dd57dbf90ea4309f7eef4112f`.
All four exact-head hosted checks had direct billing/spending-limit refusal
annotations, runner_id=0 and empty steps. The owner's existing conditional
exception applied; hosted checks did not pass. Canonical main was synchronized
and clean after the merge.

## Actual main/link build, 2026-10-14

The fresh merged source package contained 899 text files / 8721070 bytes.
Its source-workspace.json was 316668 bytes /
`49a3be5cd65302b0ee40b20bcc8d9f5090b5280b95595abef28a4c728f254653`.
Fresh plan B was 303783 bytes /
`0aca63cb09e8ecfc96dee34e1fdf94f8cb66e400f8a190ffdefd38bec3a2c549`.
The actual DEFAULT returned exit 0 (tool chunk ef647c), with the same 79
bindings / 1083 inputs and five false flags listed above. Initial preparation
failed before output creation because the fresh runtime parent was absent;
the exact parent was created and a new B path used, preserving the failed A.

One separately authorized build ran in original bundled PowerShell host PID
11832, created 04:56:21.0362886Z. The real tool session 1957 returned exit 0,
chunk 0216e5. Receipt status Passed covered exactly main Compile and link Link,
both exit 0, elapsed 18704.001299999654 ms, finishing 04:56:44.7255449Z.
InputsReverified, TreeClosureConfirmed and LeaseReleased were true;
Quarantined, CandidateExecuted and Ready remained false. Receipt: 16885 bytes /
`77e7fecfbf47217cee2fb5f4e371e76350961b759007130d1d4980488168b9f8`.

| Artifact | Bytes | SHA-256 from original leased receipt |
| --- | ---: | --- |
| EXE | 21777408 | f11c683b5379e08cca4e881a7a412a2a8a45b5f872acb690ac62218fce6717f5 |
| PDB | 136998912 | e761bd9f6e54a5ee7d99b60aa00918e1c61d3d7d6cbaec8306b921226b5a9de6 |

The original main compiler PID18912 and linker PID26400 each had one VCTIP
child (32668 and 32948). Two observations established each child's original-job
membership, image/creation identity and expected parent. After original-job
termination, active counts were zero and member lists empty. The original host
completion confirmed closed context, absent lease and zero guards. Fresh
05:01:17.0561151Z postflight found all five recorded identities absent, with
no heavy processes or leases. These are lifecycle observations at their dates.

The six JSON closure pins are retained locally: entry 1198 bytes, original
completion 669, tool return 320, inventory 1429, derived build completion 8528
and closed bundle 2359. Their outer index is 1867 bytes /
`cfb6f523336ad0fd163c2ffcdeaf4ff5b31b83fc5fa17321662bce89c61353d0`.
The compiled EXE/PDB were not reread or rehashed after admission was released.
The immutable build source remains merge 2f74; later documentation heads do
not relabel its binary or receipts.

Next: the separately owned V2 consumer and coordinator-qualified probe plan,
then one explicit probe GO. Mapped windows, ABI/reference interpretation,
dependency/cause identification and a working Zombies catalogue remain pending.
