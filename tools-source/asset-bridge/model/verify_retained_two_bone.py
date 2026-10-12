"""Re-read the existing October 7 XMB/XSB pair with its independent reader.

Explicit local paths; no copying, dumping, native writer execution or build.
Compare converted original H1-layout examples with both actual IW7 blend blobs.
The old reader validates the whole XMB/XSB and bind, not just the blend bytes.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import struct
import sys

from blend_bridge import convert_h1, read_bounded, require, verify_correspondence

EXPECTED = {
    "first": ("c979c54ac158dcc9ad648efe2542831f4250b13805b8232e218866a15ac0d856",
              "aef640e642c7e0eeef0d5cf2a483a8d349a4e5514c4528c8ac77998794ba4fdc"),
    "second": ("67fc685e892dff9f46c10923e0c2c9819ed38f9cec502bdfb6349b3d2ff7a620",
               "118343bf0f75df1fe4bc3be71d93b9d895f4f899fb5301f5dee0f157767574ae"),
}


def verify(reader_path, inputs_dir, build_dir):
    # The caller selects the retained trusted repository reader. This is Python
    # source execution, not a sandbox for arbitrary third-party reader scripts.
    read_bounded(reader_path, 65536)
    sys.path.insert(0, str(reader_path.parent))
    try:
        spec = importlib.util.spec_from_file_location("retained_skin_reader", reader_path)
        reader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(reader)
        reader.read_inputs(inputs_dir)
        inputs = {name: read_bounded(inputs_dir / name, 65536) for name in (
            "positions.f32.bin", "uv.f32.bin", "triangles.u16.bin", "parents.u8.bin",
            "tag-angles.i16.bin", "tag-positions.f32.bin", "base-mats.f32.bin")}
        results = []
        for hypothesis in ("first", "second"):
            inputs[hypothesis + ".blend.u16.bin"] = read_bounded(inputs_dir / (hypothesis + ".blend.u16.bin"), 65536)
            root = build_dir / ("artifacts-" + hypothesis)
            name = "paris_doom_skin_two_bone_" + hypothesis + "_a"
            xmb = read_bounded(root / "xmodel" / (name + ".xmb"), 65536)
            xsb = read_bounded(root / "xsurface" / (name + "_lod0.xsb"), 65536)
            native = reader.verify_outputs(xmb, xsb, inputs, hypothesis)
            require((native["xmb_sha256"], native["xsb_sha256"]) == EXPECTED[hypothesis],
                    "retained October 7 artifact hashes differ")
            _, actual_blend = reader.read_surface(xsb, inputs, hypothesis)
            # Original, fixed H1-layout examples, not inverse conversion of the
            # output under test. Both hypotheses preserve their opaque words.
            low, high = (191, 64) if hypothesis == "first" else (64, 191)
            words = [0, 0, 64, 64, 0, 64, low, 0, 64, low, 0, 64, high, 0, 64, high]
            h1 = struct.pack("<16H", *words)
            meta = {"schema": "iw7.asset-bridge.h1-blend/1", "blend_vert_counts": [4, 4, 0, 0, 0, 0, 0, 0],
                    "vertex_count": 8, "bone_count": 2, "rigid_vert_list_count": 0}
            converted = convert_h1(h1, meta)
            require(converted == actual_blend == inputs[hypothesis + ".blend.u16.bin"],
                    "H1 conversion differs from actual writer blend")
            results.append({"hypothesis": hypothesis, "retained_native_read": native,
                            "bridge_readback": verify_correspondence(h1, converted, meta)})
        return {"schema": "iw7.asset-bridge.retained-two-bone-check/1", "profiles": results,
                "native_writer_rerun": False, "native_compilation": False,
                "game_run": False, "weight_direction_engine_verified": False}
    finally:
        sys.path.pop(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reader", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--build-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.reader, args.inputs, args.build_dir), indent=2))
