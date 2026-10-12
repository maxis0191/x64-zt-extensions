# BO3 twenty-file catalogue attempt and closed incident

All times below are UTC on 2026-10-12. The attempt ended **Failed / NoCatalogue**.
It did not establish a usable asset catalogue, export, format compatibility or
an exact engine load order. The failed receipt is retained unchanged.

## Inputs and preparation

The existing eight qualified bootstrap files were supplemented by twelve
explicitly selected files. A single admitted group checked those twelve files
with two identity/hash passes: 672,409,216 bytes of inputs, no payload copy.
Its completed receipt is 10,163 bytes, SHA256
`6ea46269d67d74604fbe3477096e06bbbd8fef6934dffc2fe2d3bdf2042a61c4`.
The host actually exited zero and an independent witness at 21:42:17Z confirmed
absence. The result is file identity/hash qualification, not compatibility.

The subsequent catalogue plan used source `caccd698`, the same native candidate
as Q, and the reviewed host contract. Its twenty bootstrap files total
748,135,232 bytes. It binds 73 records (48 text, 25 binary), 24 input metadata
records and 48 expected original/alias file identities. The 51,124-byte plan hash
is `225c5fc9e4302b6a69df33de12f8bb2bb8a53fb7edbe0a580c1c00e15b8e9c5a`.
Independent default validation passed without payload reads or admission.

## Actual failure

Admission started at 21:58:47Z with the unchanged 6/8 GiB profile. The native
process started at 21:58:54Z. The output observer then found an unrecognized
ordinary file at `work/identities/dedicatedpc/LPC/.manifest`, size eight bytes.
The existing `ObservedStartupA` profile permits only the three empty identity
directories, so it rejected this file and requested termination.

The native receipt records exit one, tree closure and lease release, with no
quarantine. `InputsReverified=false` and `EngineOutputsValidated=false` remain
explicit. Stdout reports that the exact donor zone did not finish loading.
The bounded error-message observation was incomplete; no complete engine error
is reconstructed from its partial text. The manifest content was not read.

The failed receipt is 31,409 bytes, SHA256
`68ca0e48a508e3b25657b5b491eb0dbfd5fde64f60da5c4f17973f6d88e99252`.
Later metadata and 48 file-ID checks passed, but they do not replace the missing
payload revalidation. No payload was rehashed after release.

## Distinct incident closure

Normal host finalization correctly refused the missing `InputsReverified`
proof. A separately reviewed, one-shot incident procedure verified the exact
host, failed receipt, source pins, process absence, metadata and file IDs. It
disposed only the 53 retained wrapper text guards, observed all 53 closed and
zero open, and preserved the receipt, state fields and `CanExit=false`.

The host actually exited **2** at 22:05:17Z. An independent witness at
22:06:42.0265108Z confirmed host/parent/native/descendant absence, no leases or
known heavy/client processes, the stopped Main baseline and preserved Python
identity. The witness is 3,331 bytes, SHA256
`74ce5acf77478687ecaea2b32e4c9a6c89ad153cf9c8210644df5ac574961a84`.
Native handle disposal is supported by the pinned implementation and receipt;
it was not freshly enumerated through the returned native owner object.

The run and incident retained 189,069 new bytes across 18 files, excluding 24
hardlinks to existing files. Qualification, preparation and run proofs together
added 322,859 bytes. These are scoped file-length counts, not an OS disk quota
or complete historical allocation measurement.

## Next source correction

Retained provider source does not establish a writer or format for `.manifest`.
Engine initialization is a possible origin, not a proven explanation. Any new
profile must be explicit and opt-in: only the observed path, bounded transient
length, final eight-byte regular-file identity under an admitted read guard,
and no semantic claim. `ObservedStartupA` must retain its original behavior.
The host also needs a distinct failed-incident closure path that preserves the
normal success gates. Neither change authorizes another native attempt.

## Subsequent B attempt: normal closure, no catalogue

After those source changes merged as a21ab024, a new plan retained the same
twenty bootstraps, 24 inputs and native candidate. Only the execution paths,
reviewed source pins and explicit ObservedStartupManifestA profile changed.
Its 51244-byte plan hash is
`7be3417b502fc5e04419029dc9a1970852d6c271230ca559d3f4a2d9eb936c27`.
The declared known-entry count was corrected from 44 to 46: the optional
manifest and the previously omitted generated TLS file. The dynamic cap stayed
64. Independent DEFAULT validation passed before the single authorized run.

Under unchanged 6/8 GiB admission, the native process started at 22:33:36.8297664Z
and exited one after about 5.56 seconds, **without requested termination**.
The result remains Failed / NoCatalogue. InputsReverified,
EngineOutputsValidated, original metadata preservation, native tree closure and
lease release are true; no quarantine remains. The eight-byte manifest was
observed only as opaque file metadata and identity, never read or hashed.
The 31684-byte receipt hash is
`b30e0ddbce9e29ced1afa9c4b02df37580362f73a03b849d12c9e859cb7d6d84`.

The wrapper's normal automatic completion passed: 24 original metadata records,
48 original/alias IDs, no remaining native processes or lease, CanExit=true and
zero retained wrapper guards. No manual Finish or CloseIncident was needed.
The actual host and outer terminal exited one; an independent witness at
22:37:44.6761627Z confirmed their absence, preserved Python and stopped Main.
Its 3805-byte receipt hash is
`2297504f60f48e38f62ebd1b65dae8420deaa16ad12b4295452fcc85ee62d586`.

B retained 250115 new bytes across 18 files, including preparation and both
independent witnesses. The 24 hardlinks represent 808835800 existing logical
bytes and are excluded from that new-data count. These are scoped counts.

The engine still reports that the exact donor zone did not finish loading.
The 683-byte stderr ends mid-record after requested=384/read=; the complete
message and cause of load failure remain unknown. Source inspection identifies
a plausible race between the message worker's publication and CLI quick_exit,
which bypasses the instrumented exit hook. The observed ordering does not prove
that hypothesis. Correct and test bounded diagnostic publication before another
native candidate; do not infer missing message bytes or retry B.
