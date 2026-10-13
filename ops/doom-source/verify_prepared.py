"""Recompute generated header/metrics without writing outputs or compiling."""
import argparse
import json
from pathlib import Path
from prepare_writer import geometry_header, require, unlinked


def verify(root):
    root=unlinked(root)
    manifest_path=root/"writer-source.json"
    require(manifest_path.stat().st_size<=65536,"bounded manifest required")
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    geometry_path=root/"geometry.source.json"
    require(geometry_path.stat().st_size<=8*1024*1024,"bounded geometry required")
    data=json.loads(geometry_path.read_text(encoding="utf-8"))
    header,metrics=geometry_header(data,manifest["candidate_name"],manifest["material_reference"],manifest["metrics"]["height_engine_units"])
    require(metrics==manifest["metrics"],"prepared metrics differ from exact intermediate")
    require((root/"rigid_geometry.hpp").read_bytes()==header.encode(),"prepared header differs from exact intermediate")
    return metrics


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--prepared",type=Path,required=True)
    print(json.dumps(verify(p.parse_args().prepared),sort_keys=True))
