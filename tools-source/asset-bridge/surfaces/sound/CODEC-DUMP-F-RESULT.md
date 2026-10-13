# Native dump F: strict FFmpeg decode failed, ownership closed

One authorized invocation of codec Plan B ran on 2026-10-12 from source
`28ee8dbb52d79529292451ad88800389c259f887`. The exact 8692-byte plan SHA-256 is
`8cf5e60187cef1f5a3f5ba7e144e705267e4801ab317ae4b3cb406239194be09`;
the 1105-byte persistent-host command SHA-256 is
`ce81b637942132e624f442ffc7da0a9659a4461af212da07528f3740491a7402`.
The unchanged `NativeDumpF` input and original WAV were guarded and hashed under
the complete 512 MiB RAM / 1 GiB commit reservation before the worker launched.

FFmpeg 8.1.2 reported `blocksize 4096 > 1024`, then `decode_frame() failed` and
`Invalid data found when processing input`. This directly exposes the native
dump's declared 1024-sample maximum versus its unchanged 4096-sample frames.
The codec returned Windows exit 3199971767 (signed error -1094995529), and the
worker root returned 2. The output WAV has length zero; no PCM comparison passed.
The guarded source checks did not relax the decoder or repair the input header.
No retry, native source change, new build, stock staging or game followed.

The worker's small receipt records normal return of both bounded pipe drains,
EOF and no drain exception. The outer supervisor rejected root exit 2 before
accepting a successful worker receipt, so its `Worker` field remains null. The
separate worker trace is diagnostic evidence, not a success qualification.
At the 372 ms root observation, the original root had exited and its job had zero
active processes. Cleanup requested job stop and confirmed closure in 1 ms;
disposal completed. All guarded inputs were revalidated before release.

Final state records `InputHashesMatch`, `InputsUnchanged`, `JobClosed`,
`JobDisposeCompleted` and `ReadGuardsReleased` true, with no retained lease or
quarantine. The host checked this safe failure closure and the exact final state
hash, then exited normally with code zero. That host exit is distinct from the
failed codec and worker exit codes. A separate 16:11:01 UTC postflight confirmed
the two host processes, worker and codec absent, with no heavy/lab/codec process
or lease. Main remained stopped under the reviewed `5707abd` helper, with no
restart; the unrelated Python process retained its original creation identity.

| Small retained trace | Bytes | SHA-256 |
| --- | ---: | --- |
| `state.local.json` | 1443 | `b9564651a739854680eac567db55766b9f591c5ffc0d9da524dcca872ddb62ea` |
| `worker-receipt.json` | 725 | `53feaf47992f334214b3dc8ad5085dac2a0310bdbf55d5068384d6ab1c6af0e0` |
| `stderr.log` | 4017 | `a781c3dd3060b3a786abe87f325f7fc341a88331873a254a0cbd5ba72d05cb05` |
| `stdout.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

The five retained files total 6185 bytes by a postflight file-length snapshot.
The WAV was neither read nor hashed after release, including despite its zero
length. Only small state/worker/log traces, plan/command and pre/postflight/host
metadata were read for the [sanitized checkpoint](dump-codec-checkpoint-2026-10-12.json).
No executable, input audio, SAB/FF payload or original F state was rehashed or
reread after release. Complete local evidence stays under ignored
`runtime/content-surfaces/original-sound-dump-codec-a`.

The preceding SAB/FF checksum proof remains valid within its recorded scope:
it decoded SAB frames using the original metadata and explicitly excluded
standalone dump validation. This failed experiment does not establish
standalone FLAC conformance, native alias-index correctness, the writer's
`checksumChecksum` semantics, delivery or audible playback. All those acceptance
flags remain false. Next action is source-only review of the smallest justified
native metadata correction; any implementation/build/run requires its own
review and authorization, and the retained F dump must stay unchanged.
