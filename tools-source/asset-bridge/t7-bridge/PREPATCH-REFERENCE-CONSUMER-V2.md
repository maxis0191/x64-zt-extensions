# Fixed reference prepatch V2 consumer

`Run-T7PrepatchReferenceV2.ps1` and `T7PrepatchReferenceV2.Profile.ps1` consume
only the separate V2 producer. V1, C1/C2 and RunCatalogue remain unchanged.
The native command is exactly `-t7-prepatch-reference-v2`, with report
`t7-prepatch-reference-v2.local.json` and observation schema
`iw7.t7-prepatch-reference-observation/2`. No zone or address selector exists.
The report must contain DB_AddXAsset RVA 0x1D4600/2048 bytes and
Load_SimpleAsset RVA 0x1DB2B0/256 bytes in that order.

The producer cohort is immutable: source `2f74c974`, recipe SHA256 `0aca63cb`,
closed receipt 16885 bytes/`77e7fecf`, six-closure index 1867 bytes/`cfb6f523`
and executable 21777408 bytes/`f11c683b`. These tuples come from the original
admitted compilation; source preparation never rehashes the executable/PDB.
The consumer requires the original main/link closure, exact twelve-field
build profile, ten-field source marker and six guarded closure JSON records.
Singleton arrays cannot substitute for strings, integers or lifecycle booleans.

The assigned Main baseline is Stopped, with cause Unknown. Before and after
the probe, its original PID/image and UDP 27016 must be absent. PID reuse,
an inaccessible same-name image or a port owner refuses the operation.
Read-only file and bank directory metadata must match the local reviewed
snapshot; bank contents are not read. Machine paths, bank names and snapshots
belong in the ignored operational plan, not this repository.

H1 still owns admission, original creation handles, registration, deadlines,
telemetry, confirmed teardown, quarantine and receipts. The 6/8 GiB estimates
are observations under the existing telemetry-only scheduler, not capacity
minima. The V2 profile retains a 200-second group, 120-second native deadline,
2 MiB .pdata bound, 4 MiB total capture reads and 256 KiB report. It validates
only the two reported ranges and their memory/.pdata metadata; it performs
no disk PE scan, disassembly or callee following.

DEFAULT validates source/text pins and binary metadata without a lease,
provider load, binary hash or native launch. PowerShell 7.5+ JSON decoding
preserves literal UTC strings explicitly. A fresh NoProfile DEFAULT must
qualify the real entrypoint and its final plan before the coordinator's GO.
Run requires the exact fresh NoLogo/NoProfile/NoExit command. Same-host
postflight exposes CanExit only after original tree closure, lease release,
zero wrapper guards, native absence and preserved Main metadata. Actual PTY
exit and a subsequent independent absence witness remain separate obligations.

Source tests cover fixed/scalar selectors, closed build fields, exact argv,
complete/partial/missing reports, window and region bounds, guarded output,
literal UTC JSON and stopped Main/port/bank conflicts. No test starts a
candidate or loads the native provider. Native capture and interpretation
still require a separate GO; ABI, provider ownership, boot and catalogue
compatibility are never inferred from source checks or CaptureComplete.
