"""Prepare only an independent rigid prop writer; does not compile or run it."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import subprocess

PIN="fab935826c898806855376662a8a03317b3ad8f1"
INTERFACES=["utils/io/assetmanager.hpp","utils/io/filesystem.hpp","utils/memory.hpp","iw7/structs.hpp","iw7/assets/xmodel.cpp","iw7/assets/xsurface.cpp","iw7/assets/gfximage.cpp","iw7/assets/material.cpp","h1/converter/iw7/assets/xmodel.cpp","h1/converter/iw7/assets/xsurface.cpp","iw7/converter/h1/assets/xsurface.cpp"]


def require(condition,message):
    if not condition:raise ValueError(message)


def unlinked(path):
    path=path.absolute()
    for p in (path,*path.parents):require(not p.is_symlink() and not p.is_junction(),"linked source/output refused")
    return path


def vector(value,size):
    require(isinstance(value,list) and len(value)==size and all(type(v) in (float,int) and math.isfinite(v) for v in value),"finite vector required")
    return [float(v) for v in value]


def unit(value):
    length=math.sqrt(sum(v*v for v in value));require(math.isfinite(length) and length>1e-10,"nonfinite/zero tangent/normal refused")
    return [v/length for v in value]


def single(value):
    return struct.unpack("<f",struct.pack("<f",value))[0]


def literal(value):
    text=format(single(value),".9g")
    if "." not in text and "e" not in text:text+=".0"
    return text+"f"


def geometry_header(data,name,material,height):
    require(re.fullmatch(r"paris_doom_[a-z0-9_]{1,48}",name) is not None,"unique bounded Doom candidate name required")
    require(material=="mopw/character_park_clown_zombie_shoes", "stage1 exact measured retail material only")
    require(type(height) in (float,int) and math.isfinite(height) and 8<=height<=64,"explicit prop height8..64 engine units required")
    require(data.get("schema")=="iw7.doom-rigid-source/1" and data.get("ready") is False and data.get("mode")=="rigid_source_bind_geometry_not_evaluated_pose","rigid source-only intermediate required")
    transform=data["transform"]
    require(transform["output_up"]=="Z_UP" and transform["determinant_sign"]==1 and transform["uv_policy"]=="preserved_no_V_flip","exact source transform contract required")
    vertices=data["vertices"];indices=data["triangle_indices"]
    require(isinstance(vertices,list) and 0<len(vertices)<=65535 and isinstance(indices,list) and 0<len(indices)<=8192*3 and len(indices)%3==0,"bounded mesh counts required")
    require(all(type(i) is int and 0<=i<len(vertices) for i in indices),"indices outside final vertices")
    positions=[vector(v["position_m"],3) for v in vertices];normals=[unit(vector(v["normal"],3)) for v in vertices];uvs=[vector(v["uv"],2) for v in vertices]
    require(all(abs(v)<=100 for p in positions for v in p) and all(abs(v)<=16 for uv in uvs for v in uv),"source extents/UV out of bound")
    metre_height=max(v[2] for v in positions)-min(v[2] for v in positions);require(metre_height>1e-5,"nonzero metre height required")
    scale=height/metre_height;require(0<scale<=100000,"bounded explicit engine scale required")
    xyz=[[single(x*scale) for x in p] for p in positions]
    require(all(abs(x)<=256 for p in xyz for x in p),"engine prop extent exceeds256 units")
    tangents=[[0.,0.,0.] for _ in vertices];mirrored=0
    for offset in range(0,len(indices),3):
        i,j,k=indices[offset:offset+3];a,b,c=xyz[i],xyz[j],xyz[k]
        e1=[b[d]-a[d] for d in range(3)];e2=[c[d]-a[d] for d in range(3)]
        area=[e1[1]*e2[2]-e1[2]*e2[1],e1[2]*e2[0]-e1[0]*e2[2],e1[0]*e2[1]-e1[1]*e2[0]]
        require(sum(v*v for v in area)>1e-12,"engine triangle degenerate")
        u1=uvs[j][0]-uvs[i][0];v1=uvs[j][1]-uvs[i][1];u2=uvs[k][0]-uvs[i][0];v2=uvs[k][1]-uvs[i][1]
        determinant=u1*v2-u2*v1;require(abs(determinant)>1e-12,"degenerate UV triangle: tangent encoding not proven")
        mirrored+=int(determinant<0)
        tangent=[(e1[d]*v2-e2[d]*v1)/determinant for d in range(3)]
        for index in (i,j,k):tangents[index]=[tangents[index][d]+tangent[d] for d in range(3)]
    for i,tangent in enumerate(tangents):
        dot=sum(normals[i][d]*tangent[d] for d in range(3));tangents[i]=unit([tangent[d]-normals[i][d]*dot for d in range(3)])
    low=[min(p[d] for p in xyz) for d in range(3)];high=[max(p[d] for p in xyz) for d in range(3)]
    mid=[single((low[d]+high[d])/2) for d in range(3)];half=[single((high[d]-low[d])/2) for d in range(3)]
    radius=single(max(math.sqrt(sum(x*x for x in p)) for p in xyz))
    rows=["    {"+", ".join(literal(x) for x in xyz[i]+normals[i]+uvs[i]+tangents[i])+"}" for i in range(len(vertices))]
    tris=["    {"+", ".join(str(x) for x in indices[i:i+3])+"}" for i in range(0,len(indices),3)]
    result="#pragma once\n#include <cstddef>\n"
    result+="inline constexpr const char* probe_model_name="+json.dumps(name)+";\ninline constexpr const char* probe_surfs_name="+json.dumps(name+"_lod0")+";\ninline constexpr const char* probe_material_name="+json.dumps(material)+";\n"
    result+=f"inline constexpr unsigned probe_vertex_count={len(vertices)}, probe_triangle_count={len(tris)};\n"
    result+="inline constexpr float probe_engine_units_per_metre="+literal(scale)+", probe_radius="+literal(radius)+";\n"
    result+="inline constexpr float probe_bounds_mid[3]={"+", ".join(literal(x) for x in mid)+"}, probe_bounds_half[3]={"+", ".join(literal(x) for x in half)+"};\n"
    result+="struct ProbeVertex { float xyz[3], normal[3], uv[2], tangent[3]; };\ninline constexpr ProbeVertex probe_vertices[probe_vertex_count]={\n"+",\n".join(rows)+"\n};\ninline constexpr unsigned short probe_triangles[probe_triangle_count][3]={\n"+",\n".join(tris)+"\n};\n"
    return result,{"vertices":len(vertices),"triangles":len(tris),"source_height_m":metre_height,"height_engine_units":height,"engine_units_per_metre":scale,"bounds_mid_engine":mid,"bounds_half_engine":half,"radius_engine":radius,"mirrored_uv_triangles":mirrored,"tangent_handedness_runtime_verified":False}


def prepare(intermediate,source,output,name,material,height):
    intermediate,source,output=map(unlinked,(intermediate,source,output));require(not output.exists(),"fresh prepared root required")
    require(subprocess.check_output(["git","-C",str(source),"rev-parse","HEAD"],text=True).strip()==PIN,"exact ZoneTool pin required")
    require(not subprocess.check_output(["git","-C",str(source),"status","--porcelain","--untracked-files=all"],text=True).strip(),"changed shared ZoneTool must be preserved")
    require(intermediate.stat().st_size<=8*1024*1024,"intermediate byte limit")
    payload=intermediate.read_bytes();data=json.loads(payload);header,metrics=geometry_header(data,name,material,height)
    own=Path(__file__).parent;files={"writer.cpp":(own/"writer_rigid.cpp").read_bytes(),"half_uv.hpp":(own/"half_uv.hpp").read_bytes(),"rigid_geometry.hpp":header.encode(),"geometry.source.json":payload}
    refs={name:hashlib.sha256((source/"src/zonetool/zonetool"/name).read_bytes()).hexdigest() for name in INTERFACES}
    refs["../game/shared.cpp"]=hashlib.sha256((source/"src/zonetool/game/shared.cpp").read_bytes()).hexdigest()
    manifest={"schema":"iw7.doom-rigid-writer-source/1","source_pin":PIN,"interface_hashes":refs,"prepared_hashes":{name:hashlib.sha256(value).hexdigest() for name,value in files.items()},"candidate_name":name,"material_reference":material,"metrics":metrics,"compiled":False,"ff_built":False,"pixels_verified":False,"ready":False}
    output.mkdir(parents=True,exist_ok=False)
    for filename,payload in files.items():
        with (output/filename).open("xb") as f:f.write(payload)
    with (output/"writer-source.json").open("x",encoding="utf-8") as f:json.dump(manifest,f,indent=2)
    return manifest


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--intermediate",type=Path,required=True);p.add_argument("--source",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--name",required=True);p.add_argument("--height-engine-units",type=float,default=16);p.add_argument("--material",default="mopw/character_park_clown_zombie_shoes");a=p.parse_args()
    print(json.dumps(prepare(a.intermediate,a.source,a.output,a.name,a.material,a.height_engine_units),indent=2))
