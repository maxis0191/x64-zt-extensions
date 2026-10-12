"""Independent bounded rig native/FF data reader, never a process runner.

The caller must separately bind real writer/FF receipts, hashes and owned-tree
closure. A data pass, including on synthetic tests, never claims those gates.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

# Isolated Python (-I) deliberately omits the script directory. Import only the
# source-bound sibling readers, whose complete paths/hashes the runner guards.
sys.path.insert(0, str(Path(__file__).absolute().parent))
from read_skin_fixture import SIZES, parse, verify_payloads
from read_skin_native import Reader, read_model, read_surface
from verify_clip_rig import read_bounded, verify as verify_clip

PROFILES = ("first", "second")
MODELS = {h: "paris_doom_skin_two_bone_" + h + "_a" for h in PROFILES}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def load_inputs(root):
    require(root.is_absolute() and root.is_dir(), "absolute original input directory required")
    require({p.name for p in root.iterdir()} == set(SIZES) | {"fixture-input.json"}, "exact rig input inventory")
    files = {name: read_bounded(root / name, 16384) for name in SIZES}
    meta = parse(read_bounded(root / "fixture-input.json", 16384))
    verify_payloads(files, meta)
    return files, meta


def reader_refusal(error, payload, kind, hypothesis, stage):
    """Add bounded context after refusal; never normalize or accept a field."""
    detail = ""
    if str(error) == "unexpected native field/padding/dependency":
        try:
            reader = Reader(payload)
            if kind == "xmodel":
                record = reader.array(736, 1)
                offset, field = 272, "XModel.lodInfo[0].surfs"
            else:
                reader.array(56, 1)
                reader.name(expected=MODELS[hypothesis] + "_lod0")
                record = reader.array(256, 1)
                offset, field = 88, "XSurface.blendVertsBuffer (header name)"
            if any(record[offset:offset + 8]):
                detail = (f"; observed {field} offset={offset} "
                          "category=nonzero-8-byte-value; address omitted")
        except (ValueError, struct.error):
            # Diagnostic framing must not hide or replace the original refusal.
            pass
    return ValueError(f"{stage}/{hypothesis}/{kind}: {str(error)[:160]}{detail}")


def read_asset(reader, payload, files, hypothesis, kind, stage):
    try:
        return reader(payload, files, hypothesis)
    except ValueError as error:
        raise reader_refusal(error, payload, kind, hypothesis, stage) from None


def read_stage(files, manifest, pairs, xab, *, ff_roundtrip=False):
    verify_payloads(files, manifest)
    require(set(pairs) == set(PROFILES), "both distinct two-bone model profiles required")
    extracted = dict(files)
    models = {}
    shared_bind = None
    stage = "ff-redump" if ff_roundtrip else "native-data"
    for hypothesis in PROFILES:
        xmb, xsb = pairs[hypothesis]
        require(isinstance(xmb, bytes) and isinstance(xsb, bytes) and
                0 < len(xmb) <= 65536 and 0 < len(xsb) <= 65536, "64 KiB per model/surface limit")
        model, bind = read_asset(read_model, xmb, files, hypothesis, "xmodel", stage)
        surface, blend = read_asset(read_surface, xsb, files, hypothesis, "xsurface", stage)
        require(shared_bind is None or bind == shared_bind, "profile skeleton/bind disagreement")
        shared_bind = bind
        extracted[hypothesis + ".blend.u16.bin"] = blend
        models[hypothesis] = {
            "name": MODELS[hypothesis], "model": model, "surface": surface,
            "xmb_bytes": len(xmb), "xsb_bytes": len(xsb),
            "xmb_sha256": hashlib.sha256(xmb).hexdigest(),
            "xsb_sha256": hashlib.sha256(xsb).hexdigest(),
            "actual_blend_sha256": hashlib.sha256(blend).hexdigest(),
        }
    # Bind and blend inputs here come from the completely read XMB/XSB, not just
    # the original source bundle. The strict readers also check actual geometry.
    for key, payload in zip(("parents.u8.bin", "tag-angles.i16.bin",
                             "tag-positions.f32.bin", "base-mats.f32.bin"), shared_bind):
        extracted[key] = payload
    cpu = verify_clip(extracted, manifest, xab, ff_roundtrip=ff_roundtrip)
    return {"stage": stage, "models": models,
            "clip_rig_cpu": cpu, "complete_model_surface_read": True,
            "writer_provenance_verified": False, "ff_provenance_verified": False,
            "material_resolution_verified": False, "runtime_verified": False, "ready": False}


def verify_chain(files, manifest, native_pairs, native_xab, redump_pairs=None, redump_xab=None):
    require((redump_pairs is None) == (redump_xab is None), "FF model and clip redumps must be supplied together")
    native = read_stage(files, manifest, native_pairs, native_xab)
    redump = None
    if redump_pairs is not None:
        redump = read_stage(files, manifest, redump_pairs, redump_xab, ff_roundtrip=True)
        a, b = native["clip_rig_cpu"], redump["clip_rig_cpu"]
        # Whole-file pointer/script-string IDs may change, but exact reader
        # profiles, decoded keys, actual binds, blends and CPU positions cannot.
        for key in ("channel_to_bone", "parent_distances", "profiles", "root_motion_authored"):
            require(a[key] == b[key], "native-to-FF semantic mismatch: " + key)
        for key in ("name", "normalized_time"):
            require(a["notetrack_data"][key] == b["notetrack_data"][key], "native-to-FF note mismatch")
    return {"schema": "iw7.original-rig-chain-data/1",
            "status": "rig-chain-data-pass" if redump else "rig-native-data-pass",
            "native": native, "redump": redump,
            "native_execution_verified": False, "ff_execution_verified": False,
            "stock_restoration_verified": False, "material_resolution_verified": False,
            "engine_weight_direction_verified": False, "runtime_verified": False, "ready": False}


def load_pairs(root, *, split_profiles=False):
    return {h: (read_bounded((root / h if split_profiles else root) / "xmodel" / (name + ".xmb"), 65536),
                read_bounded((root / h if split_profiles else root) / "xsurface" / (name + "_lod0.xsb"), 65536))
            for h, name in MODELS.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--native-root", type=Path, required=True)
    parser.add_argument("--native-xab", type=Path, required=True)
    parser.add_argument("--redump-root", type=Path)
    parser.add_argument("--redump-xab", type=Path)
    args = parser.parse_args()
    try:
        require((args.redump_root is None) == (args.redump_xab is None), "paired FF paths required")
        files, meta = load_inputs(args.inputs)
        report = verify_chain(files, meta, load_pairs(args.native_root, split_profiles=True), read_bounded(args.native_xab, 65536),
                              load_pairs(args.redump_root) if args.redump_root else None,
                              read_bounded(args.redump_xab, 65536) if args.redump_xab else None)
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError, struct.error) as error:
        print(json.dumps({"status": "invalid-rig-chain-data", "error": str(error)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
