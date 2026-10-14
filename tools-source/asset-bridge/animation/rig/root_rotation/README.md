# Original root-rotation clip: closed source preparation

Root selected a distinct one-channel original clip for the future visible rigid
control. `paris_original_probe_root_rotate` authors X rotation on `tag_origin`
at frames 0/10/20/30 with 0/45/-45/0 degrees. It uses the existing 30-frame,
30-framerate, looped frequency-1 candidate and note data, without translation
streams or delta parts. Pose versus world/root motion, cadence, tree binding,
note delivery and pixels remain runtime hypotheses; no native artifact exists.

`prepare_root_rotation.py` writes only seven fresh text files: a narrowly derived
writer, the unchanged existing ABI assertions, keyed header, unchanged pinned
production XAnim dump body, authoring JSON, one-row source CSV and hash manifest.
It uses the existing preparer's source qualification, quaternion encoder and
dump extraction. The generated writer differs only in its distinct asset name,
one name entry and removal of the unused child-string case. No model writer,
SDK/core49f, old clip/reader, B FF, installed file or Ops55 profile is changed.

The source category vector is `[0,0,1,0,0,0,0,0,1,1]`: no identity-rotation
channels, one quat4 rotation channel, one channel with no translation, one total
name. This is derived from the named `IWXAnim` category order, IW mapping and
the decoder's ordered quaternion stream consumption, not from a guessed DObj
layout. Required streams are four frame bytes, one key-count-minus-one short
equal to 3 and sixteen rotation shorts. Existing real `XAnimParts` 136-byte
assertions are copied unchanged; no replacement native structs are added.

## Pinned source evidence

| Source | Revision / SHA256 | Relevant scope |
| --- | --- | --- |
| ZoneTool IW XAnim / real ABI | `fab935826c898806855376662a8a03317b3ad8f1`, existing source contracts and `probe_native_abi.hpp` | Serializer and field/offset assertions, not runtime tree |
| Existing `prepare_probe.py` / `writer_probe.cpp` / `read_probe.py` | `9246a55a...409be` / `3b9c1f68...9aeb6b` / `1b3630ae...01941` | Frozen helpers/profiles, not widened |
| [Greyhound IW mapping](https://raw.githubusercontent.com/Scobalula/Greyhound/f2d130543fb8a4733d1b27176016ba390e4ffd5d/src/WraithXCOD/WraithXCOD/GameInfiniteWarfare.cpp) | `f2d130543fb8a4733d1b27176016ba390e4ffd5d` / `3ce8dd51025df1cc2d097d7aa4d9bb58b6c8c08157bb1019207e0a33c7929964` | Copies named IW categories and selects DivideBySize rotation decoding |
| [Greyhound IW source structures](https://raw.githubusercontent.com/Scobalula/Greyhound/f2d130543fb8a4733d1b27176016ba390e4ffd5d/src/WraithXCOD/WraithXCOD/DBGameAssets.h) | same revision / `6e86f287debced404ba50b3bee60fe00a476008d2ed15057fd03c06207b28740` | Names/order of the ten categories; no addresses or DObj layout adopted |
| [Greyhound translator](https://raw.githubusercontent.com/Scobalula/Greyhound/d02629b510a2e0be09836bc0bc98f2f4bd1bb8c7/src/WraithXCOD/WraithXCOD/CoDXAnimTranslator.cpp) | `d02629b510a2e0be09836bc0bc98f2f4bd1bb8c7` / `7f9e02358f83ded3a032be78aac2114f69140f16060b6d77585dafea72396334` | Names order, quat4 count/frames/stream size and absence of authored translations |

The actual source text cache is outside Git. The preparer verifies all three
full hashes before writing; existing native-source qualification still requires
the exact ZoneTool revision and interface hashes. The pinned `QuatInt16` encoder
uses 32767, while Greyhound's IW DivideBySize reader uses 32768. The new reader
reports both conventions and keeps engine normalization unverified. Four-key
angle interpretation is data proof and cannot qualify engine timing or motion.

## Source use and validation

```text
python -B tools-source/asset-bridge/animation/rig/root_rotation/prepare_root_rotation.py --source-root <pinned-native-text> --reference-root <pinned-reference-text> --output <fresh-absolute-source-root>
python -B -m unittest discover -s tools-source/asset-bridge/animation/rig/root_rotation -v
```

Preparation has no Run/CPP/writer/FF/Game option. Existing output, reparse ancestry,
source/reference drift, duplicate/nonfinite authoring and any different profile
are refused. Every generated file and current preparer/reader/authoring source
is pinned in its manifest; executable/XAB/FF fields remain absent/null and all
runtime/readiness booleans remain false.

`read_root_rotation.py` reuses only the frozen independent reader's record
primitives. It does not import the writer/preparer. It requires the complete
one-name, quat4, looped profile: exact header/padding/optional-stream absence,
required pointer presence, four keys, packed quaternions, note name/time and
complete consumption. Only explicit `--ff-roundtrip` permits a remapped nonzero
note string ID. Old two-bone clips, aliases, extra channels, null pointers,
truncation, trailing bytes and changed fields fail. Its CLI is a future bounded
asset-read entrypoint and must run under the existing admitted parent recipe;
the current source tests use independent synthetic bytes, not retained assets.

Twelve source/fixture tests pass, including every truncation of the tiny synthetic
stream, incompatible counts/channels, forbidden delta/optional fields, typed
authoring, FF-note scope, old-profile preservation and a synthetic source-provider
preparation transaction. The real source-only preparation also passed against
the pinned text sources. Neither is a native emission or rendering result.
Two causal growth fixtures return a small stat followed by larger source data:
reads stay capped at limit+1 and oversized input is refused before UTF-8 decoding,
hashing or code compilation. The initial review's read-all version fails those
fixtures; source capsule C remains its unchanged pre-correction snapshot.

Next stages remain the [separate minimum plan](../NEXT-ORIGINAL-ANIMATION.md):
review source/pins, positive B DISPLAY, then distinct Root CPP/native-clip GO,
existing FF helper variant/actual readback and SDK4cc's separate opt-in controller
source. No new FF builder is added here. Root has not authorized those executions;
the original six-row B plan, legacy two-bone data and core49f stay immutable.
