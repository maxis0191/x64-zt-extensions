# Build E: native probes pass, final link fails

One invocation of Plan E ran from source `e42d3ed480efc409fdcc1f950b1ac39e00014935`
in a fresh persistent PowerShell 7 host. Its exact Plan SHA-256 was
`65e4ddc10524e6f6d2e3a596c8a480ca95be7be336555c30a41404597350f2e4`;
the 1083-byte host command was
`ff58ac47d7c873fbf07244f0368a80174d6809beaa74582e72558ccca9ce22d7`.
The failed Plan C / host D output and all original Seal C inputs remain intact.

Thirteen native stages passed: both probe compilations, links and runs; all six
replacement compilations; and the common archive. The repaired `/DNAME` responses
are therefore accepted by the pinned compiler with the existing warning policy.
The actual original C++ probe returned
`78000000000000000000000000000000`, with `matches_original_md5=false`.
The patched probe returned the exact expected
`24fe5af1473ea8f4be33912348210c78`, with `matches_original_md5=true`.
Both reported `field_matches`, `payload_unchanged` and `outside_field_unchanged`
true. These checks use a synthetic envelope; they do not prove native SAB/FF
serialization or playback. Both probes retain `native_ff_tested=false` and
`ready=false`.

The fourteenth stage, `link-candidate`, exited 1158:

```text
LINK : fatal error LNK1158: cannot run 'rc.exe'
```

No final ZoneTool executable or build receipt exists. The exact native PATH
contained only the pinned MSVC x64 bin directory and Windows System32; it omitted
the already installed SDK 10.0.26100.0 x64 bin directory. The existing `rc.exe`
and `rcdll.dll` were found there by read-only inspection. They are not members of
Seal C. A subsequent correction must explicitly bind and protect these new tool
inputs; changing PATH alone must not pretend that the old seal covers them.

The supervisor's final failure is a secondary missing-`build-receipt.json` error
during completion qualification of the original job's remaining `vctip.exe`.
The Python root had already exited 1 because of LNK1158. Success qualification
was refused; normal failure cleanup requested stop on the original job and
confirmed root exit with zero active members. This is a failed run, not an
accepted residual closure or a built candidate.

The complete reservation was 4 GiB RAM / 6 GiB commit. Observed elapsed time was
262797 ms. All 1410 original inputs were guarded and verified before and after;
2207024770 bytes were read and all 1410 input guards were disposed. Twelve new
response sources remained separately protected by bootstrap guards. The final
state reports `TreeClosed=true`, `LeaseReleased=true`, and no retained token.
The 63 retained files total 92224870 bytes, also the observed peak, below the
512 MiB stop threshold. No retry occurred.

The final 3292-byte `supervisor-state.json` SHA-256 is
`8c3068bbb196a75686e70d9145a1f91eb1b69c2f2632e67687119c19302d6be0`.
Before exiting the persistent host, the host itself checked this digest, closure,
lease release and absence of its exact AppDomain quarantine key. It then saved
its outcome outside the candidate and exited normally. Fresh postflight at
2026-10-12 10:54:51 UTC found no lease, no build-heavy process and no surviving
host/native PID. Main's executable/creation identity and UDP 27016 owner were
unchanged. All Plan source and provider pins still matched.

The sanitized [checkpoint](build-e-checkpoint-2026-10-12.json) records every
phase, both probe outputs, closure and output accounting, with hashes for the
state, phase logs, probe executables and rebuilt common archive. Full local
artifacts remain under `runtime/zt-sound-md5-c`; postflight and host outcome are
outside it in the existing ignored Plan directory. Large partial PDBs are counted,
not promoted to valid outputs. The coordinator owns integration and the next
native slot. Next action is a separately reviewed SDK tool/environment correction;
no new build, FF/SAB run or playback is authorized by this checkpoint.
