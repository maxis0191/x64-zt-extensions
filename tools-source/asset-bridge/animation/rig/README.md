# Original two-bone rig and four-key clip binding

The original preparation below was a source-only recovery and CPU checkpoint.
The later [attempt B](RIG-RUN-2026-10-12-B.md) built and dumped the FF but remains
historically `FailedRestored`. The explicit CPU-only follow-up below has its own
scope and does not change that result. The original ribbon contains
8 vertices, 6 triangles, one surface, `tag_origin` and child `tag_probe`. Its
channel order matches the passed `paris_original_probe_bend` clip. No compiler,
native writer, FF builder, stock transaction or game ran for this rig tranche.
The existing animation FF result remains separate.

## CPU-only FF readback - 2026-10-13

`read_rig_chain.py --cpu-only-ff-readback` selects a separate FF data scope.
The authored native records still use the strict reader. In the redumps, it
requires a present `XModel.lodInfo[0].surfs` numeric value equal to the paired
`XModelSurfs.surfs`, and preserves `XSurface.blendVertsBuffer` as an opaque
eight-byte value. It reports the value category and observed numeric equality
to the outer name value without printing or dereferencing either. It does not
validate buffer production, GPU objects, lifetimes or the retail field ABI.
All other unsupported pointer/stream/padding rules remain enforced.

The actual retained B pairs and native/final clip passed this new reader:
22 small original-data inputs, 15,143 bytes, byte/hash unchanged before/after;
output status `rig-chain-cpu-ff-data-pass`. All nine recorded native/redump
assets matched the historical B hashes. Both numeric LOD links matched; both
buffer-slot values were nonzero and equaled their captured outer-name values.
That equality remains an observation of opaque numbers. Actual geometry, tags,
bind matrices, blend bytes, channel mapping and decoded CPU poses matched
between native and FF data. The largest analytical pose error was
0.004260786588817347 units. This proves CPU data preservation for the original
two-bone fixture, not visible skinning or a BO3 import.

The full local report SHA256 is
`ec2c6f0b0d6bb7d906b43dd7d549e4a2c98f340bfa5201082a1272ec2311b0d8`.
The 23 chain tests and 16 strict native-reader tests pass. New cases cover
mismatched/absent LOD links, unsupported fields, corrupted geometry/blends,
truncation, preservation of the strict native stage and explicit FF selection.
No native tool, compiler, stock staging or game was launched for this read.
The next proof is the protected two-bone playback described in
[RUNTIME-CONTRACT.md](RUNTIME-CONTRACT.md), after the real BO3 prop demonstration.

## Reused original sources

The twelve files in [recovered-source.json](recovered-source.json) were recovered
byte-for-byte from retained `doom-source-pipeline/ops/doom-source`: the real-header
native writer, complete independent XMB/XSB reader, CPU oracle, input/source
preparers and 69 existing tests. No historical file was edited and no native
process wrapper was imported. Source comments describing the initial unbuilt
checkpoint are preserved as part of that history.

The recovery receipt is an immutable October 12 snapshot, not a promise that
every active source file will keep those bytes forever. The October 13 CPU-only
FF reader change in PR4 advanced only `read_skin_native.py` among its twelve
files, from 11,783 to 12,239 bytes. [source-lineage.json](source-lineage.json)
records the exact before/after SHA256, Git blobs and reviewed source commit.
Current source checks preserve the original receipt, verify the eleven
unchanged files and require that one exact reviewed reader revision. Corruption,
rehashed forged lineage or another unrecorded change still fails. No historical
receipt, native/FF capsule or runtime result is rewritten by this source fix.

Names remain `paris_doom_skin_two_bone_first_a` and
`paris_doom_skin_two_bone_second_a`, each with `_lod0` surfaces. These are original
procedural geometry, not a Doom asset or the one-bone Beacon. Keeping their exact
names preserves correspondence with the October 7 native artifacts already read
by the model workstream. Its recorded native evidence is not a new native
execution here, nor an FF or rendered-skinning pass.

The writer references the existing material name
`mopw/character_park_clown_zombie_shoes`; it emits no material or retail bytes.
Resolution on a future map/FF remains required. An original material substitution
needs a reviewed new profile/name and independent reader expectation, with the
material owner's dependency closure. Do not silently alter the retained profiles
or copy a guessed donor asset.

## Geometry, bind and weight contract

Coordinates are Z-up engine units. The ribbon lies at X=0, spans Y=-4..4 and
Z=0..16. Root global bind is identity at (0,0,0); child global bind is identity
at (0,0,8). Parent distance is byte 1. The local child quaternion is int16
(0,0,0,32767), translation (0,0,8); both positive global `baseMat` records have
identity quaternion and `transWeight=2`. The oracle computes inverse binds for
skinning; inverse binds are not stored in the model's `baseMat`.

| Vertex rows in serialized order | Child weight | Purpose |
| --- | ---: | --- |
| Z=0, Y=-4/+4 | 0 | Root-weighted control stays still |
| Z=16, Y=-4/+4 | 1 | Child-only points establish pivot/rotation |
| Z=4, Y=-4/+4 | 0.25 | Asymmetric dual weights |
| Z=12, Y=-4/+4 | 0.75 | Opposite asymmetry detects reversed weight convention |

The surface has four mono and four dual vertices, 48 blend bytes, no rigid list,
zero client bones and no optional GPU/reactive/subdivision/collision streams.
Pinned converters establish raw IW7 bone IDs, two/four ushort words per mono/dual
vertex and byte-range weights in ushorts. They do not establish which dual bone
receives the stored weight. The profiles keep bone order and geometry identical
while storing 64/191 under opposite explicit hypotheses. CPU success does not
choose an engine convention.

`skin_native_abi.hpp` binds the writer to actual pinned ZoneTool types:
XModel=736, XModelSurfs=56, XSurface=256, GfxPackedVertex=32, Face=6,
DObjAnimMat=32 and XBlendInfo=2 bytes. `read_skin_native.py` independently reads
all records, pointers as presence markers, exact streams and EOF. It rejects
unsupported pointers/flags/dependencies and blob aliases. Synthetic tests do not
stand in for a new writer execution.

Flags 0x86, partBits C0000000, normal/tangent words E0080000/200FFE00,
selfVisibility 01FE0100, planar bounds and negative tangent handedness remain
engine/shader/culling checks. The format contract uses ZoneTool pin
`fab935826c898806855376662a8a03317b3ad8f1`; do not substitute H1 structs or rename
H1 files. Eleven physical source hashes were rechecked during preparation and
are retained in [validation-2026-10-12.json](validation-2026-10-12.json).

## Current lightweight evidence

[verify_clip_rig.py](verify_clip_rig.py) imports no writer. It consumes the
independently verified input bundle and exact-profile XAB reader, then computes
matrix skinning from the four decoded quaternions. A separate closed-form
rotation about Z=8 supplies ideal positions, including the negative bend.
The CLI requires the measured native or B redump hash; synthetic test bytes
cannot masquerade as that evidence.

With the real B redump, both hypotheses pass their corresponding CPU
interpretation. Neutral frames 0/30 reproduce bind geometry; root-weighted
points stay fixed. Maximum combined packed-quaternion/weight error is
**0.0042607866 units**, versus **2.1605451221 units** for opposite weight
interpretation. This assumes normalized quaternions and linear blend skinning;
it does not prove interpolation, engine weight direction or visible deformation.
The note remains data at 0.5, not a delivered gameplay event.

The initial checkpoint passed 79 light tests: the recovered 69 and ten new tests
for four-key binding,
negative pose, explicit note remapping, channel/geometry/parent/weight mutations,
neutral bind, retained hashes, byte limits and exact recovery provenance. Real
source preparation generated and re-read only raw inputs, C++ source/header
and JSON receipts. From the repository root:

```powershell
python -B -m unittest discover -s tools-source/asset-bridge/animation/rig -v
```

Explicit absolute local path arguments keep preparation separate from native work:

```powershell
python -B tools-source/asset-bridge/animation/rig/prepare_skin_fixture.py --source $PinnedZoneTool --output $FreshInputDirectory
python -B tools-source/asset-bridge/animation/rig/read_skin_fixture.py --input $FreshInputDirectory
python -B tools-source/asset-bridge/animation/rig/prepare_skin_writer.py --inputs $FreshInputDirectory --source $PinnedZoneTool --output $FreshPreparedSourceDirectory
python -B tools-source/asset-bridge/animation/rig/prepare_skin_writer.py --verify-prepared --inputs $FreshInputDirectory --source $PinnedZoneTool --output $FreshPreparedSourceDirectory
python -B tools-source/asset-bridge/animation/rig/verify_clip_rig.py --inputs $FreshInputDirectory --xab $ActualBRedump --ff-roundtrip
```

Preparers refuse existing output directories and modified/unpinned source,
generate no XMB/XSB/FF and never invoke a compiler. Do not use retained historical
native launch scripts. Future native/FF/runtime work requires separate coordinator
GO and current resource/ownership/restoration helpers. The next recipe and real
GSC route are in [RUNTIME-CONTRACT.md](RUNTIME-CONTRACT.md).

The [chain adapter and specialized runner](CHAIN-PLAN.md) now implement the
complete native/FF sequence with an independent reader using actual model/surface
binds and blends. The initial source checkpoint passed 108 Python tests, including
four PowerShell suites (187 internal checks). One authorized attempt then passed
native compile, both model emissions and independent native reading, before an
FF log-directory collision stopped the chain. The failed attempt was restored;
see [the preserved run and correction](RIG-RUN-2026-10-12-A.md).
The corrected runner uses separate compiler artifacts and phase logs, retaining
bootstrap errors even without `phase.json`. One separately authorized recipe E
then passed native reading and FF build/verify/dump, but the strict final reader
refused two loaded pointer fields. The attempt is failed/restored, with its raw
outputs preserved; see [attempt B / recipe E](RIG-RUN-2026-10-12-B.md).
Default remains inert Plan, and a new Run needs separate coordinator GO.
Measured AnimationFF/shared providers and recovered source bytes are unchanged.
Every engine weight, cadence, material and rendered-output convention remains open.
