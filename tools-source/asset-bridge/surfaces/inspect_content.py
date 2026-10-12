"""Bounded, read-only content dependency preflight for the pinned IW7 source.

This is not a fastfile writer, image decoder, HKS compiler or runtime verifier.
Its JSON schema describes this inspector's evidence, not a game asset format.
"""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import struct
import sys


TECHNIQUE_COUNT = 152  # iw7/structs.hpp at source pin in source_contract.json
LIMIT = 8 * 1024 * 1024
TOTAL_LIMIT = 32 * 1024 * 1024
ITEM_LIMIT = 4096
BYTE_FIELDS = ("gameFlags", "unkFlags", "sortKey", "renderFlags",
               "textureAtlasRowCount", "textureAtlasColumnCount",
               "textureAtlasFrameBlend", "textureAtlasAsArray", "cameraRegion",
               "materialType", "assetFlags")
SOUND_TABLES = ("sendEffectParams", "ADSRSettings", "AmbientDefs", "AmbientEvents",
                "AmbientElements", "FilterDefs", "MixDefs", "NPCAdsrZoneEntry",
                "PLRAdsrZoneEntry", "OccludeDefs", "ReverbDefs", "TimescaleEntrys",
                "ZoneDefs", "Unks", "FullOcclusionDefs", "PlayerBreathStateDefs")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def relative(value):
    require(isinstance(value, str) and 0 < len(value) <= 512, "bounded relative name required")
    value = value.replace("\\", "/")
    parts = value.split("/")
    require(not value.startswith("/") and all(p not in ("", ".", "..") for p in parts),
            "absolute/traversing/empty path component refused")
    require(not any(c in value for c in ':\x00<>\"|?') and
            all(ord(c) >= 32 for c in value), "unsafe path character")
    require(all(not p.endswith((".", " ")) and
                not re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", p)
                for p in parts), "Windows ambiguous path refused")
    return value


def no_links(path):
    for item in (path, *path.parents):
        require(not item.is_symlink() and not item.is_junction(), "linked root/input refused")
    return path


def parse_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    return json.loads(data, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def uint(value, bits):
    return type(value) is int and 0 <= value < 2 ** bits


class Inputs:
    def __init__(self, root):
        self.root = no_links(Path(root).absolute())
        require(self.root.is_dir(), "input root directory required")
        self.total = 0
        self.files = {}

    def path(self, name):
        return no_links(self.root.joinpath(*PurePosixPath(relative(name)).parts))

    def exists(self, name):
        return self.path(name).is_file()

    def read(self, name, limit=LIMIT):
        path = self.path(name)
        require(path.is_file(), "missing file: " + name)
        size = path.stat().st_size
        require(size <= limit and self.total + size <= TOTAL_LIMIT, "input byte budget exceeded")
        require(len(self.files) < ITEM_LIMIT or name in self.files, "input file budget exceeded")
        with path.open("rb") as stream:
            data = stream.read(limit + 1)
        require(len(data) == size, "input changed during read")
        self.total += size
        digest = hashlib.sha256(data).hexdigest()
        if name in self.files:
            require(self.files[name]["sha256"] == digest, "input changed between dependency reads")
        self.files[name] = {"bytes": size, "sha256": digest}
        return data

    def json(self, name, limit=256 * 1024):
        return parse_json(self.read(name, limit))


def verify_contract(zt_root):
    contract = parse_json(Path(__file__).with_name("source_contract.json").read_bytes())
    source = Inputs(zt_root)
    for name, digest in contract["zonetool"]["files"].items():
        require(hashlib.sha256(source.read(name)).hexdigest() == digest,
                "ZoneTool interface differs from pinned contract: " + name)
    return contract


class Inspector:
    def __init__(self, root, zone, references=(), strict_reader_prepared=False):
        self.inputs = Inputs(root)
        self.zone = relative(zone)
        require("/" not in self.zone, "single zone name required")
        self.references = set(references)
        self.findings = []
        self.edges = set()
        self.seen = set()
        self.metadata = {}
        if strict_reader_prepared:
            self.add("pending", "strict_reader_build_required", "reader",
                     "Prepared patch bytes verified; build/roundtrip still required with explicit -strict-content-sources.")
        self.strict_reader_prepared = strict_reader_prepared

    def add(self, level, code, asset, message):
        self.findings.append(dict(level=level, code=code, asset=asset, message=message))

    def external(self, kind, name, owner):
        name = relative(name)
        self.edges.add((owner, kind + ":" + name))
        if (kind, name) in self.references:
            self.add("pending", "recipient_resolution", kind + ":" + name,
                     "Declared recipient inventory reference; non-default DB resolution still needs the target map.")
            return True
        return False

    def guarded(self, kind, name, action):
        key = kind + ":" + name
        if key in self.seen:
            return
        require(len(self.seen) < ITEM_LIMIT, "asset budget exceeded")
        self.seen.add(key)
        try:
            action(name)
        except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError, UnicodeError,
                csv.Error, RecursionError) as error:
            self.add("error", "invalid_input", key, str(error))

    def material(self, name):
        self.guarded("material", name, self._material)

    def _material(self, name):
        name = relative(name)
        asset = "material:" + name
        data = self.inputs.json("materials/" + name.replace("*", "_") + ".json")
        require(isinstance(data, dict), "material object required")
        for key in BYTE_FIELDS:
            require(uint(data.get(key), 8), "material uint8 required: " + key)
        require(uint(data.get("surfaceTypeBits"), 64), "surfaceTypeBits uint64 required")
        technique = relative(data["techniqueSet->name"])
        self.external("techset", technique, asset) or self.add(
            "pending", "techset_binary_uninspected", "techset:" + technique,
            "Requires native .techset/.technique, vertex declaration and VS/HS/DS/PS closure; no opaque binary pass inferred.")
        if not self.zone.startswith("paris_enemy_") and not self.strict_reader_prepared:
            self.add("error", "early_db_material_lookup", asset,
                     "Pinned reader preserves JSON image/techset names only in paris_enemy_ zones; other zones perform early DB lookup.")
        textures = data.get("textureTable")
        constants = data.get("constantTable")
        subs = data.get("subMaterials")
        textures = [] if textures is None else textures
        constants = [] if constants is None else constants
        subs = [] if subs is None else subs
        for table in (textures, constants, subs):
            require(isinstance(table, list) and len(table) <= 255, "material table exceeds uint8 count")
        for row in textures:
            for key in ("firstCharacter", "lastCharacter"):
                require(type(row.get(key)) is int and -128 <= row[key] <= 127, "texture char required: " + key)
            for key in ("semantic", "samplerState"):
                require(uint(row.get(key), 8), "texture uint8 required: " + key)
            require(uint(row.get("typeHash"), 32), "texture typeHash uint32 required")
            image = relative(row["image"])
            if not self.external("image", image, asset):
                self.image(image)
        for row in constants:
            require(isinstance(row.get("name"), str) and "\x00" not in row["name"] and len(row["name"].encode()) <= 12,
                    "constant name must fit fixed char[12]")
            if len(row["name"].encode()) == 12 and not self.strict_reader_prepared:
                self.add("pending", "constant_name_reader_copy", asset,
                         "12-byte constant name reaches pinned strcat terminator past name[12]; strict patch uses bounded copy.")
            require(uint(row.get("nameHash"), 32), "constant nameHash uint32 required")
            require(isinstance(row.get("literal"), list) and len(row["literal"]) == 4 and
                    all(v is None or (type(v) in (int, float) and abs(v) <= 3.4028234663852886e38 and
                                      math.isfinite(v)) for v in row["literal"]), "four float32 constant components required")
        for sub in subs:
            self.edges.add((asset, "material:" + relative(sub)))
            self.add("pending", "submaterial_resolution", asset, "Layer name needs explicit target-material review: " + sub)
        clean = name.replace("*", "_")
        # Require exact names: upstream get_parse_path can borrow another material's sidecar.
        state = f"techsets/state/{technique}/{clean}"
        if "stateFlags" not in data or data["stateFlags"] is None:
            info = self.inputs.json(state + ".stateinfo")
            require(uint(info.get("stateFlags"), 8), "stateinfo stateFlags uint8 required")
        else:
            require(uint(data["stateFlags"], 8), "stateFlags uint8 required")
        bits = self.inputs.read(state + ".statebits", 4096)
        require(len(bits) == TECHNIQUE_COUNT, "statebits requires exactly 152 technique indices")
        mapping = self.inputs.json(state + ".statebitsmap")
        require(isinstance(mapping, list) and 1 <= len(mapping) <= 255, "nonempty bounded statebitsmap required")
        require(all(b == 255 or b < len(mapping) for b in bits), "statebits index exceeds statebitsmap")
        for row in mapping:
            for key, count, width in (("loadBits", 6, 32), ("depthStencilStateBits", 14, 64), ("blendStateBits", 4, 32)):
                require(isinstance(row.get(key), list) and len(row[key]) == count and
                        all(uint(v, width) for v in row[key]), "invalid statebitsmap field: " + key)
            require(uint(row.get("rasterizerState"), 8), "rasterizerState uint8 required")
        if constants:
            cb = f"techsets/constantbuffer/{technique}/{clean}"
            indexes = self.inputs.read(cb + ".cbi", 4096)
            require(len(indexes) == TECHNIQUE_COUNT, "cbi requires exactly 152 technique indices")
            require(len(self.inputs.read(cb + ".cbt", 256 * 1024)) > 0, "empty constant buffer table")
            self.add("pending", "constant_buffer_native_layout", asset,
                     "Exact cbi/cbt present; native array/offset ranges require pinned reader roundtrip, not pointer-layout guesses.")
        self.metadata[asset] = {"texture_count": len(textures), "constant_count": len(constants),
                                "sidecar_policy": "exact_material_only_no_fallback"}

    def image(self, name):
        self.guarded("image", name, self._image)

    def _image(self, name):
        name = relative(name)
        clean = name.replace("*", "_")
        asset = "image:" + name
        candidates = [f"streamed_images/{clean}.iw7Image", f"images/{clean}.iw7Image",
                      f"images/{clean}.dds", f"images/{clean}.tga", f"images/{clean}.iwi"]
        present = [p for p in candidates if self.inputs.exists(p)]
        require(len(present) == 1, "exactly one image representation required; missing or shadowed sources: " + repr(present))
        path = present[0]
        data = self.inputs.read(path)
        if path.endswith(".tga"):
            require(len(data) >= 18, "truncated TGA header")
            ident, cmap, kind = data[:3]
            w, h, bpp, descriptor = struct.unpack_from("<HHBB", data, 12)
            require(cmap == 0 and kind == 2 and bpp in (24, 32), "only uncompressed true-color TGA preflight supported")
            require(0 < w <= 4096 and 0 < h <= 4096 and descriptor & 0xc0 == 0, "TGA dimensions/interleave unsupported")
            require(len(data) >= 18 + ident + w * h * (bpp // 8), "truncated TGA pixels")
            self.metadata[asset] = {"width": w, "height": h, "bits_per_pixel": bpp,
                                    "top_origin": bool(descriptor & 32), "route": "resident_FF_no_PAK"}
        elif path.endswith(".dds"):
            require(len(data) >= 128 and data[:4] == b"DDS " and struct.unpack_from("<I", data, 4)[0] == 124,
                    "invalid DDS header")
            require(struct.unpack_from("<I", data, 76)[0] == 32, "invalid DDS pixel-format header")
            self.add("pending", "dds_decode_required", asset, "DDS container found; DirectXTex mip/format/payload validation remains required.")
        else:
            self.add("pending", "native_image_uninspected", asset,
                     "Native image/IWI source found; pinned reader plus stream descriptors/pixels/SAB-independent PAK closure not parsed here.")

    def shader(self, stage, name):
        require(stage in ("vs", "hs", "ds", "ps", "cs"), "known shader stage required")
        def inspect(value):
            data = self.inputs.read(f"techsets/{stage}/{relative(value)}.cso")
            if stage == "ps" and value == "null.hlsl" and not data:
                self.add("pending", "null_pixel_shader", stage + ":" + value, "Empty retail null shader needs exact pass context.")
                return
            require(len(data) >= 32 and data[:4] == b"DXBC", "missing/corrupt DXBC signature")
            size, chunks = struct.unpack_from("<II", data, 24)
            require(size == len(data) and chunks <= 256 and 32 + chunks * 4 <= size, "DXBC length/chunk table mismatch")
            ranges = []
            for i in range(chunks):
                off = struct.unpack_from("<I", data, 32 + i * 4)[0]
                require(off >= 32 + chunks * 4 and off + 8 <= size, "DXBC chunk offset outside payload")
                end = off + 8 + struct.unpack_from("<I", data, off + 4)[0]
                require(end <= size and all(end <= lo or off >= hi for lo, hi in ranges), "DXBC chunk overlap/truncation")
                ranges.append((off, end))
            self.add("pending", "shader_linkage_required", stage + ":" + value,
                     "DXBC container only; stage, input layout, code constants and selected technique pass need reflection/runtime validation.")
        self.guarded(stage, name, inspect)

    def soundbank(self, name):
        self.guarded("soundbank", name, self._soundbank)

    def _soundbank(self, name):
        name = relative(name)
        asset = "soundbank:" + name
        bank = self.inputs.json(f"soundbank/{name}.json")
        for field in ("name", "zone", "gameLanguage", "soundLanguage"):
            require(isinstance(bank.get(field), str), "soundbank string required: " + field)
        require(bank["name"] == name, "soundbank identity mismatch")
        rows = []
        paths = bank.get("aliases")
        require(isinstance(paths, list) and 0 < len(paths) <= 64, "bounded alias CSV list required")
        contract = parse_json(Path(__file__).with_name("source_contract.json").read_bytes())
        fields = contract["alias_csv_fields"]
        for path in paths:
            self.edges.add((asset, "file:" + relative(path)))
            parsed = csv.reader(io.StringIO(self.inputs.read(path, 2 * 1024 * 1024).decode("utf-8-sig")), strict=True)
            require(next(parsed, None) == fields, "exact pinned positional alias CSV columns required")
            for row in parsed:
                require(len(row) == len(fields), "alias CSV field count mismatch")
                require(len(rows) < ITEM_LIMIT, "alias row budget exceeded")
                rows.append(dict(zip(fields, row)))
        require(rows, "empty alias bank")
        names = {r["Name"] for r in rows}
        require("" not in names, "empty alias name")
        for row in rows:
            for field in ("SecondaryAliasName", "StopAliasName"):
                if row[field]:
                    self.edges.add(("alias:" + row["Name"], "alias:" + row[field]))
                    require(row[field] in names, "unresolved " + field + ": " + row[field])
            if row["duck"]:
                self.inputs.json("sound/ducks/" + relative(row["duck"]) + ".duk")
                self.add("pending", "duck_native_parse", asset, "Duck JSON needs pinned field/range parsing.")
            sample = row["File"]
            if sample:
                path = "sound_assets/" + relative(sample)
                self.edges.add(("alias:" + row["Name"], "sample:" + sample))
                if self.inputs.exists(path + ".flac"):
                    data = self.inputs.read(path + ".flac")
                    require(len(data) >= 42 and data[:4] == b"fLaC" and data[4] & 127 == 0 and
                            int.from_bytes(data[5:8], "big") == 34, "FLAC STREAMINFO signature/length invalid")
                elif self.inputs.exists(path + ".wav"):
                    self.add("error", "wav_sab_unsupported", asset, "Pinned SAB writer explicitly rejects WAV: " + sample)
                else:
                    self.add("error", "missing_sound_sample", asset, "Missing sound_assets/<File>.flac: " + sample)
            else:
                self.add("pending", "alias_without_sample", asset, "Alias has no File; language/secondary/runtime behavior unresolved: " + row["Name"])
        for field in SOUND_TABLES:
            paths = bank.get(field)
            require(paths is None or isinstance(paths, list), "sound table paths must be array/null: " + field)
            for path in paths or []:
                self.inputs.read(relative(path), 2 * 1024 * 1024)
                self.add("pending", "sound_table_native_parse", asset, "Table closure not decoded: " + field)
        self.metadata[asset] = {"alias_lists": len(names), "alias_heads": len(rows), "microphone_transport": "unrelated"}
        self.add("pending", "sab_build_and_playback", asset,
                 "Alias/sample dependency checks only; FLAC decode, alias hash index, SABL/SABS packaging and audible target-map playback remain unverified.")

    def ui(self, module):
        def inspect(name):
            require(re.fullmatch(r"[A-Za-z0-9_-]{1,64}", name), "single UI module name required")
            entry = f"ui_scripts/{name}/__init__.lua"
            data = self.inputs.read(entry, 256 * 1024)
            require(data and not data.startswith(b"\x1b"), "nonempty HKS source required; foreign Lua bytecode refused")
            data.decode("utf-8-sig")
            self.metadata["ui:" + name] = {"entry": entry, "route": "client_HKS", "dedicated_executes": False}
            self.add("pending", "hks_dependency_and_execution", "ui:" + name,
                     "Entry exists only. require(), LUI registrations, materials/fonts, input focus and VM lifecycle need client HKS execution; no regex closure claim.")
            self.add("pending", "client_ui_delivery", "ui:" + name,
                     "Disk ui_scripts or LuaFile FF loader capability must match receiving client. Server HudElem does not supply that capability.")
        self.guarded("ui", module, inspect)

    def report(self):
        errors = sum(f["level"] == "error" for f in self.findings)
        pending = sum(f["level"] == "pending" for f in self.findings)
        return {"schema": "iw7.content-surfaces-preflight/1", "zone": self.zone,
                "status": "invalid" if errors else "incomplete" if pending else "bounded_checks_passed",
                "errors": errors, "pending": pending, "ready": False,
                "runtime_verified": False, "format_scope": "dependency_preflight_not_full_asset_decoder",
                "findings": self.findings, "edges": [list(x) for x in sorted(self.edges)],
                "metadata": self.metadata, "files": self.inputs.files,
                "bytes_read": self.inputs.total}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--zt-source", type=Path, required=True)
    parser.add_argument("--zone", required=True)
    parser.add_argument("--reader-patch", type=Path, help="verified prepared patch; records native build as pending")
    parser.add_argument("--references", help="root-relative recipient inventory CSV (type,name); declarations only")
    for key in ("material", "image", "soundbank", "ui", "shader"):
        parser.add_argument("--" + key, action="append", default=[])
    args = parser.parse_args()
    try:
        contract = verify_contract(args.zt_source)
        if args.reader_patch:
            from prepare_reader_patch import verify_prepared
            verify_prepared(args.zt_source, args.reader_patch)
        check = Inspector(args.root, args.zone, strict_reader_prepared=bool(args.reader_patch))
        require(any(getattr(args, k) for k in ("material", "image", "soundbank", "ui", "shader")), "at least one asset required")
        if args.references:
            rows = csv.reader(io.StringIO(check.inputs.read(args.references, 256 * 1024).decode("utf-8-sig")), strict=True)
            for row in rows:
                require(len(row) == 2 and row[0] in ("image", "techset", "material"), "reference CSV requires type,name rows")
                check.references.add((row[0], relative(row[1])))
        for kind in ("material", "image", "soundbank", "ui"):
            for name in getattr(args, kind):
                getattr(check, kind)(name)
        for shader in args.shader:
            stage, name = shader.split(":", 1)
            check.shader(stage, name)
        report = check.report()
        report["source_contract"] = {"zonetool_pin": contract["zonetool"]["revision"], "interfaces_match": True}
        print(json.dumps(report, indent=2, ensure_ascii=True))
        return 1 if report["errors"] else 2 if report["pending"] else 0
    except (ValueError, OSError, UnicodeError, csv.Error, RecursionError) as error:
        print(json.dumps({"schema": "iw7.content-surfaces-preflight/1", "status": "invalid", "ready": False, "error": str(error)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
