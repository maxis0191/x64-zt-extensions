# Original keyed probe: native serializer and independent readback passed

On 2026-10-12 the bounded native writer compiled against the pinned SDK and
produced a 281-byte original XAB. Independent readback passed. FF parsing,
FF serialization, rendered animation and event callbacks remain untested.
The sanitized [native validation record](native-validation-2026-10-12.json)
binds the source, prepared include, compiler, executable, output and diagnostics
by SHA-256. It contains no game assets or machine paths.

The successful run used the runner hash recorded in that historical evidence.
Subsequent review found process-tree cleanup and final-receipt budget defects.
The [source corrections](RUNNER-CORRECTIONS.md) add an atomic Windows Job owner
and reserve final metadata space. The helper subsequently passed the separate
[three-case native ownership witness](NATIVE-JOB-WITNESS.md). The full revised
animation runner has not been rerun; its historical 281-byte proof still belongs
to the earlier runner hash, and untested failure paths remain explicitly open.

This source tranche prepares `paris_original_probe_bend` for the existing original
`tag_origin` / `tag_probe` rig. It authors four X-axis rotation keys:
frame0=0°, frame10=45°, frame20=-45°, frame30=0°, with `probe_contact` at normalized
time0.5. Framerate30, numframes30, loop flag1; no translations, delta, IK, additive
or viewmodel streams. Meshes/materials and the original two-bone writer are untouched.

`prepare_probe.py` verifies the retained ZoneTool pin and ten source hashes, then
generates the packed input header, original authoring JSON, one-XAnim zone CSV and
`probe_dump.inc`. This include contains the complete production
`xanim_parts::dump` method body from `iw7/assets/xanim.cpp`, unchanged except CRLF
normalization and a local class/namespace declaration. It does not contain a new
implementation of the serializer. `writer_probe.cpp` calls that method with the
real `XAnimParts` type and real `assetmanager::dumper`; only filesystem IO and
the three original script-string identities are supplied locally. No game VM is
needed for this serialization. Static assertions cover the actual ABI and were
executed by the successful native compilation.

## Source support and remaining uncertainty

The pinned local ZoneTool `t7/structs.hpp:1153` gives bucket order;
`t7/converter/iw7/assets/xanim.cpp:97-111` handles key-count-minus-one and quat4
samples; `game/shared.cpp:302-313` provides float32*32767 truncation. Our packed
samples follow that encoder exactly. This is a new original IW7 clip, not an H1
animation converter or evidence that arbitrary H1 motion already works.

Two targeted Greyhound references were downloaded to an ignored local directory
(125046 bytes combined, no binaries). The pinned
[IW7 adapter](https://raw.githubusercontent.com/Scobalula/Greyhound/f2d130543fb8a4733d1b27176016ba390e4ffd5d/src/WraithXCOD/WraithXCOD/GameInfiniteWarfare.cpp)
maps IW7 to integer quaternion decoding. The pinned
[translator](https://raw.githubusercontent.com/Scobalula/Greyhound/d02629b510a2e0be09836bc0bc98f2f4bd1bb8c7/src/WraithXCOD/WraithXCOD/CoDXAnimTranslator.cpp)
locates byte-sized frame indices in dataByte, keys-minus-one in dataShort and
quat4 samples in randomDataShort; zero-rotation bones precede rotated bones.
Its older process-reader branch divides by32768 while its buffer-reader branch
uses approximately1/32767. The writer follows ZoneTool's32767 encoder; readback
reports norm and angle rather than claiming measured engine normalization.
Exact revisions/hashes are in [probe-source-contract.json](probe-source-contract.json).

Frequency is no longer an unresearched placeholder. A bounded read of **142 bytes
each** from two already-retained Rhino XABs gives:

| Header | numframes | fps | frequency | flags |
| --- | ---: | ---: | ---: | ---: |
| alien_queen_idle | 60 | 30 | 0.5 | 3 (loop + delta) |
| alien_drone_attack_jump_level_l45hand | 14 | 30 | 2.142857074737549 | 2 (delta) |

Both match float32(fps/numframes), not fps/(numframes-1). Thus the original
30/30 probe uses **candidate frequency1**, explicitly supplied to the writer.
[Header observations](frequency-observations.json) preserve lengths, values and
prefix hashes without raw pointers or asset bytes. The two headers both have
delta enabled; their correlation does not prove timing of the new no-delta clip.
The runtime hypothesis to test is a1-second cycle with the note at0.5 seconds.

## Reproduce preparation, then compile only after the parent's GO

Use the already installed Python3.10+ standard library. `SOURCE` is the retained
`modular-agent-platform/tools/x64-zt-enemy` checkout at `fab935826...`; `REFS`
contains the two exact reference files above. `PREPARED` must be a fresh absolute
directory beneath an existing ignored runtime directory. No assets are copied.

```powershell
python -B tools-source/asset-bridge/animation/prepare_probe.py `
  --source-root <SOURCE> --reference-root <REFS> --output <PREPARED>
python -B -m unittest discover -s tools-source/asset-bridge/animation -v
```

The first real preparation refused because the pinned source ends without a final
LF. It created no output. The extraction now accepts either terminal-LF form,
keeps the method body and passes a dedicated regression. Preparation then
succeeded against the actual pinned source. That preparation checkpoint proved
generated source/input only. The retained earlier `runtime/probe-prepared-v1` predates the
frequency observations and is superseded by `runtime/probe-prepared-v2`.

After the parent's limited GO, the historical `Run-NativeProbe.ps1` used the current merged
resource helper, a fresh atomic 4 GiB physical / 6 GiB commit admission and
BelowNormal priority. It rehashes the prepared inputs and SDK against
`prepared.json` and preserves process PID/creation time, compiler identity,
arguments, exits and diagnostics in ignored runtime receipts. Output must be a
fresh directory below this worktree's runtime, with no reparse ancestry.
The revised source also loads its C# job helper inside the reservation, keeps
unresolved owners quarantined and checks both final receipts before publication.
Reusing that source requires the validation gate described above.

```powershell
pwsh -NoProfile -File tools-source/asset-bridge/animation/Run-NativeProbe.ps1 `
  -SourceRoot <SOURCE> -PreparedRoot <PREPARED> `
  -OutputRoot <fresh-runtime-build> -PythonExe <installed-python.exe>
```

This is a sequential compiler → writer → reader job, with no `/MP`, MSBuild,
FF build or game launch. The x64 MSVC/Windows SDK compiler argument recipe is:

```text
cl.exe /nologo /std:c++20 /EHsc /MD /O1
  /I <SOURCE>/src/zonetool /I <PREPARED> /I <animation-directory>
  <animation-directory>/writer_probe.cpp
  /Fo<fresh-build>/writer_probe.obj /Fe<fresh-build>/writer_probe.exe
  /link /INCREMENTAL:NO
```

Within that same owned build job, emission and independent readback are:

```text
writer_probe.exe <fresh-absolute-native-output> 1
python -B read_probe.py <native-output>/xanim/paris_original_probe_bend.xab --expected-frequency 1
```

The native writer allows only its single expected file, CREATE_NEW output and
64 KiB total writes. It refuses existing output or reparse ancestry. No FF,
model, game file, bank or configuration is opened. The one-row `probe-zone.csv`
can later enter the normal ZoneTool recipe with that native-produced XAB in its
`zonetool/<pack>/xanim` source tree. The real ZoneTool parser and FF serializer
still need a separately admitted build/roundtrip. This CSV contains no `.atr`,
agent or automatic playback route; connect those only in the isolated fixture.

## Independent decoded readback and exact next witness

`read_probe.py` imports neither writer nor preparer. It checks the full136-byte
header including padding/absent optional streams, all record lengths/names,
four frame indices, key count, every packed quaternion, note identity/time and
EOF. It decodes only this original quat4 profile, yielding angular error below
0.01° and norm error below0.0001. It refuses other animation profiles rather
than posing as a general decoder. Synthetic bytes passing this reader do not
prove that the native serializer has emitted anything; bind actual output to its
native receipt when available. Runtime status always remains false.

39 lightweight tests pass, including14 new codec/preparation/readback cases plus
the frequency-observation check (15 new total), all byte truncations, every
nonpointer header-byte mutation and every payload-byte mutation, and real CLI
checks. These remain independent of the native run and do not replace it.

## Native run and retained correction

The native run used source commit `4c0f00d` (including reviewed baseline
`24d5c4f`), MSVC 14.44.35207 and Windows SDK 10.0.26100.0. All actual IW7
size/offset assertions compiled. The sole compiler warning is C4996 for
`strcpy` in pinned `assetmanager.hpp:580`; the upstream header was unchanged.

The first attempt hit a runner error while checking the empty output directory:
`Measure-Object` exposed no `Sum` property under StrictMode. No native artifacts,
compiler diagnostics or child identity survived that attempt, so it has no
claimed native outcome. A fresh check found no cl/link/writer process and no
lease. The runner now sums file lengths from zero and preserves diagnostics and
the receipt on failure. Attempt `b` succeeded; both attempt directories are
retained under ignored runtime.

| Stage | Exit | Elapsed | Result |
| --- | ---: | ---: | --- |
| Compile/link | 0 | 1571 ms | Real pinned dumper and IW7 ABI compiled |
| Original writer | 0 | 18 ms | One 281-byte XAB, create-only |
| Independent reader | 0 | 70 ms | Header, keys, note and EOF exact |

The decoded angles are 0, +44.9997642627, -44.9997642627 and 0 degrees at
frames 0/10/20/30. `tag_origin` remains identity. `probe_contact` is present at
normalized time 0.5, frequency remains the explicit candidate 1. The XAB SHA-256
is `1284b72cf501ae42f77958579610dbcaf692b9153cd06ff66dcf2d1d11eeda7d`.
Pointer bytes in native dump headers can vary between executions; the reader
checks nonzero presence and the exact nonpointer header rather than treating
that full-file hash as a universal reproducibility target.

Final disk accounting, including the failed-attempt record and successful
receipts, is recorded in the validation JSON and remains below 0.4 MiB versus
the 32 MiB cap. Peak working set was unavailable from the process objects after
exit and is not claimed. The post-run registry was empty and a fresh process
inventory found no compiler or writer. No FF, Blender, game, asset extraction,
Main configuration or client was involved.

Next: the separately admitted tiny FF parser/serializer roundtrip must consume
this actual native XAB. Then the existing two-bone skin fixture should show
the0/+45/-45/0 bend, correct fixed pivot and weight interpretation,1-second loop,
and one `probe_contact` per cycle. Record engine animation time and the observer
pose separately. Only after that consider attack-state/damage-window/replication.
Potential failure questions are concrete: bone rotation relative to bind versus
absolute local pose, actual loop endpoint normalization, frequency scaling,
quaternion renormalization and event callback routing. None is claimed resolved.

This tranche adds only small source/original data. Source references use125046
bytes; generated preparation is under8 KiB before its small manifest. Cap a
writer build/output/log group at32 MiB until the parent re-evaluates it;
use the existing4 GiB physical/6 GiB commit build admission policy, not a new
parallel reservation. Disk growth is now measured; process peak memory is not.
