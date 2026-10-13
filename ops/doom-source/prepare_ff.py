"""Prepare a minimal Doom rigid FF from a measured independent writer run.

No tool launch, game clone, retail material/image copy or geometry conversion.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from prepare_writer import PIN, unlinked, require

MATERIAL = "mopw/character_park_clown_zombie_shoes"


def bounded_json(path, maximum=1024*1024):
    path = unlinked(path)
    require(0 < path.stat().st_size <= maximum, "bounded regular JSON required")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def candidate_metadata(value):
    return (type(value.get("lod0_dist")) is int and value["lod0_dist"] == 1000000
            and value.get("has_lods") is True
            and type(value.get("shadow_cutoff_lod")) is int and value["shadow_cutoff_lod"] == 6
            and type(value.get("collision_lod")) is int and value["collision_lod"] == 255)


def stage(writer_run, output):
    run, output = unlinked(writer_run), unlinked(output)
    require(not output.exists(), "fresh Doom FF preparation required")
    provenance_path = run / "writer-provenance.json"
    provenance = bounded_json(provenance_path)
    source = provenance.get("Source", {})
    roundtrip = provenance.get("Roundtrip", {})
    name = source.get("candidate_name", "")
    require(re.fullmatch(r"paris_doom_[a-z0-9_]{1,48}", name) is not None, "bounded Doom asset name required")
    metrics = source.get("metrics", {})
    require(provenance.get("Schema") == "iw7.doom-rigid-writer-build/1" and provenance.get("SourcePin") == PIN
            and source.get("schema") == "iw7.doom-rigid-writer-source/1" and source.get("source_pin") == PIN
            and source.get("material_reference") == MATERIAL and provenance.get("InputSnapshotsMatch") is True
            and provenance.get("FFBuilt") is False and provenance.get("PixelsVerified") is False
            and provenance.get("Ready") is False, "measured immutable rigid writer required")
    require(roundtrip.get("schema") == "iw7.doom-rigid-roundtrip/1"
            and roundtrip.get("geometry_roundtrip_verified") is True and candidate_metadata(roundtrip)
            and roundtrip.get("bones") == 1 and roundtrip.get("surfaces") == 1 and roundtrip.get("lods") == 1
            and roundtrip.get("ready") is False and roundtrip.get("pixels_verified") is False
            and roundtrip.get("ff_built") is False and roundtrip.get("iw7_normal_encoding_verified") is False,
            "measured one-root single-surface roundtrip required")
    for key, limit in (("vertices", 65535), ("triangles", 8192)):
        require(type(metrics.get(key)) is int and 0 < metrics[key] <= limit
                and type(roundtrip.get(key)) is int and roundtrip[key] == metrics[key], "measured mesh counts differ")
    manifest_path = run / "writer-source.json"
    manifest_payload = manifest_path.read_bytes()
    require(len(manifest_payload) <= 64*1024
            and hashlib.sha256(manifest_payload).hexdigest().upper() == provenance.get("SourceManifestSHA256", "").upper()
            and bounded_json(manifest_path, 64*1024) == source, "writer source/provenance differs")
    writer_path = unlinked(run / "doom-writer.exe")
    require(0 < writer_path.stat().st_size <= 16*1024*1024
            and hashlib.sha256(writer_path.read_bytes()).hexdigest().upper() == provenance.get("WriterSHA256", "").upper(),
            "measured reader binary changed")
    assets = (f"xmodel/{name}.xmb", f"xsurface/{name}_lod0.xsb")
    entries = provenance.get("Artifacts", [])
    require(len(entries) == 2 and {entry.get("Path") for entry in entries} == set(assets), "exact two-asset rigid inventory required")
    payloads = {}
    for entry in entries:
        path = unlinked(run / "artifacts" / entry["Path"])
        require(type(entry.get("Bytes")) is int and 0 < entry["Bytes"] <= 4*1024*1024
                and path.stat().st_size == entry["Bytes"], "bounded measured rigid asset required")
        payload = path.read_bytes()
        require(hashlib.sha256(payload).hexdigest().upper() == entry.get("SHA256", "").upper(), "writer asset changed")
        payloads[entry["Path"]] = payload
    # ZoneTool's paris_enemy_ custom-dependency rule is explicit. Asset names
    # remain paris_doom_*; a zone name does not claim an enemy actor exists.
    zone = "paris_enemy_" + name.removeprefix("paris_")
    recipient_csv = f"zone_source/{zone}_recipient.csv"
    zone_csv = f"zone_source/{zone}.csv"
    ncs_name = "ncs_mdl_" + name
    payloads[recipient_csv] = ("material," + MATERIAL + "\n").encode()
    payloads[zone_csv] = (f"ignore,{zone}_recipient\nxmodel,{name}\nnetconststrings,{ncs_name}\n").encode()
    payloads[f"netconststrings/{ncs_name}.json"] = (json.dumps({"stringType": 0, "sourceType": 2, "stringList": [name]}, indent=2)+"\n").encode()
    plan = {"schema": "iw7.doom-rigid-ff-plan/1", "source_pin": PIN, "asset_name": name, "zone": zone,
            "recipient": "cp_zmb", "material_reference": MATERIAL, "material_payload_copied": False,
            "writer_provenance_sha256": hashlib.sha256(provenance_path.read_bytes()).hexdigest(),
            "reader_sha256": provenance["WriterSHA256"], "metrics": metrics,
            "lod0_dist": 1000000, "has_lods": True, "shadow_cutoff_lod": 6, "collision_lod": 255,
            "source_files": {key: hashlib.sha256(value).hexdigest() for key, value in payloads.items()},
            "expected_inventory": ["material,,"+MATERIAL, "xmodelsurfs,"+name+"_lod0", "xmodel,"+name,
                                   "netconststrings,"+ncs_name, "rawfile,"+zone],
            "offline_context_required": "runtime cp_zmb must resolve the retail material reference",
            "geometry_roundtrip_verified": True, "normal_encoding_runtime_verified": False,
            "ff_built": False, "pixels_verified": False, "ready": False}
    output.mkdir(parents=True, exist_ok=False)
    for relative, payload in payloads.items():
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(payload)
    with (output / "doom-ff-plan.json").open("x", encoding="utf-8") as stream:
        json.dump(plan, stream, indent=2)
    return plan


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--writer-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    print(json.dumps(stage(arguments.writer_run, arguments.output), indent=2))
