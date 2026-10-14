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
was skipped. The new 66 PowerShell profile/binding controls and existing
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

Next: peer review, private PR/exact-head checks/merge, immutable source package
and fresh DEFAULT qualification, then coordinator GO for one main/link build
and one prepatch probe. Native compilation, mapped windows, ABI/reference
interpretation and a working Zombies catalogue remain pending.
