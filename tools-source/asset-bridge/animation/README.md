# Animation envelope and skeleton preflight

Run with Python 3.10+ and the standard library. No installation, native compiler,
game process, asset extraction, network access or output files are needed.

```powershell
python -B -m unittest discover -s tools-source/asset-bridge/animation -v
python -B tools-source/asset-bridge/animation/xab_preflight.py <existing-small.xab> --game iw7
python -B tools-source/asset-bridge/animation/xab_preflight.py <existing-small.xab> --game h1 --skeleton <rig.json>
```

The explicit game selects a source-derived ABI; `.xab` has no universal game
magic/version. H1's 216-byte header and IW7's 136-byte header are not interchangeable.
`source-contract.json` pins the interfaces inspected, not a tested native build.
The fixtures are original synthetic data. The `.xab` generator in the tests is
an envelope oracle, **not an asset writer suitable for engine consumption**.

Exit 0 prints JSON `status: envelope-pass`. It checks typed record lengths,
pointer/count presence, exact channel names, normalized notetrack times, delta
structure/frame lengths and key indices, complete input consumption and optional
skeleton name/topology binding. Pointers are opaque presence markers, never
addresses to read. Input and optional JSON are each capped at 4 MiB. Names are
bounded ASCII. String aliases can refer only to an earlier string at index zero.

Exit 2 prints `invalid` or `unsupported`. This initial profile explicitly refuses
blob aliases and H1 IK/extra bone buckets/secondary/alternative/blend-shape/viewmodel
extensions. A refusal may mean a valid asset exceeds this deliberately narrow
profile. Null records for nonzero counts, nonnull pointers for zero counts,
nonfinite values, extra trailing bytes and unmapped channels also refuse. Event
order is preserved; equal-time or repeated events are not automatically removed.

No packed channel samples, rotations or translations are decoded. No root-motion
distance, sampling, quaternion validity, flags semantics, animation duration,
bind pose, weights, axes, retarget, IK, ASM, damage window or network correctness
is established by exit 0. In particular, compressed arrays with internally invalid
track data can pass their envelope. `runtime_verified` and
`compressed_tracks_decoded` are always false.

The optional `iw7.skeleton-binding/1` document has `num_client_bones: 0` and a
`bones` array containing only `{name, parent}` objects. `parent` is null for roots
or an earlier zero-based index. All roots must precede children; 1..255 regular
bones are allowed by this profile. Names are matched exactly, case sensitively.
The output includes candidate `parent_list_u8` distances and `channel_to_bone`,
without reordering channels or changing compressed data. Missing channels fail;
unanimated model bones are listed for explicit review. This is a topology plan,
not a binary XModel writer. See `fixtures/two-bone.skeleton.json` for the
`tag_origin` / `tag_probe` topology shared with the retained Doom skin fixture.

The next decisive experiment and dependency map are in
[ANIMATION-AI-BRIDGE.md](../../../../docs/ANIMATION-AI-BRIDGE.md).
