"""One-material rigid bind-geometry candidate; extraction requires explicit CLI run.

No Blender, scripts, drivers, skin evaluation, FF build or engine calls.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

from inspect_sources import identity, member_name, MAX_MEMBER

NS = {"c": "http://www.collada.org/2005/11/COLLADASchema"}
IDENTITY = [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def numbers(text, maximum, integer=False):
    require(text is not None and len(text) <= MAX_MEMBER, "numeric text absent/oversized")
    tokens = text.split()
    require(len(tokens) <= maximum, "numeric count exceeds bound")
    values = [int(t) if integer else float(t) for t in tokens]
    require(all(math.isfinite(v) for v in values), "nonfinite source number")
    return values


def ref(ids, element, attribute):
    require(element is not None, "required reference absent")
    name = element.get(attribute, "")
    require(name.startswith("#") and name[1:] in ids, "local exact reference required")
    return ids[name[1:]]


def one(elements, reason):
    require(len(elements) == 1, reason)
    return elements[0]


def source_values(ids, input_node, width):
    source = ref(ids, input_node, "source")
    accessor = one(source.findall("c:technique_common/c:accessor", NS), "one source accessor required")
    count = int(accessor.get("count", "0")); stride = int(accessor.get("stride", "0"))
    require(0 < count <= 65535 and stride == width and int(accessor.get("offset", "0")) == 0, "bounded simple accessor required")
    array = ref(ids, accessor, "source")
    require(array.tag == "{"+NS["c"]+"}float_array", "float source required")
    values = numbers(array.text, count * width)
    require(len(values) == count * width == int(array.get("count", "0")), "source count differs")
    return [values[i:i+width] for i in range(0, len(values), width)]


def unit(vector):
    length = math.sqrt(sum(x*x for x in vector))
    require(0.5 <= length <= 2, "normal length outside candidate range")
    return [v/length for v in vector]


def subtract(a,b):
    return [a[i]-b[i] for i in range(3)]


def cross(a,b):
    return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]


def z_up(value):
    return [value[0],-value[2],value[1]]


def convert(data, material_name):
    require(len(data) <= MAX_MEMBER and b"<!DOCTYPE" not in data and b"<!ENTITY" not in data, "bounded DTD-free XML required")
    root = ET.fromstring(data)
    require(root.tag == "{"+NS["c"]+"}COLLADA" and root.get("version") == "1.4.1", "Collada 1.4.1 required")
    require(root.findtext("c:asset/c:up_axis", namespaces=NS) == "Y_UP", "source Y_UP required")
    scale = float(root.find("c:asset/c:unit", NS).get("meter"))
    require(math.isfinite(scale) and 0 < scale <= 1, "finite metre scale required")
    ids = {}
    for e in root.iter():
        if e.get("id"):
            require(e.get("id") not in ids, "duplicate ID refused")
            ids[e.get("id")] = e
    material = one([m for m in root.findall("c:library_materials/c:material", NS) if m.get("name") == material_name], "one exact named material required")
    candidates = []
    for scene in root.findall("c:library_visual_scenes/c:visual_scene", NS):
        for node in scene.findall("c:node", NS):
            for instance in node.findall("c:instance_controller", NS):
                for binding in instance.findall("c:bind_material/c:technique_common/c:instance_material", NS):
                    if binding.get("target") == "#"+material.get("id"):
                        candidates.append((node,instance,binding))
    node,instance,binding = one(candidates, "one direct scene mesh bound to named material required")
    # Current candidate has no inherited scene transforms or posed skeleton.
    translation = [0.,0.,0.]
    for transform in node:
        tag = transform.tag.split("}")[-1]
        if tag == "translate":
            values = numbers(transform.text,3);require(len(values)==3,"translate count");translation=[translation[i]+values[i] for i in range(3)]
        elif tag == "rotate":
            values=numbers(transform.text,4);require(len(values)==4 and abs(values[3])<1e-8,"posed rotation unsupported")
        elif tag == "scale":
            require(numbers(transform.text,3)==[1,1,1],"nonunit scale unsupported")
        else:
            require(tag in ("instance_controller","extra"),"unknown node transform refused")
    controller = ref(ids, instance, "url")
    skin = one(controller.findall("c:skin", NS), "skin controller required for source bind geometry")
    require(numbers(skin.findtext("c:bind_shape_matrix", namespaces=NS),16)==IDENTITY, "nonidentity bind shape unsupported")
    geometry = ref(ids, skin, "source")
    mesh = one(geometry.findall("c:mesh", NS), "one mesh required")
    primitives = [p for p in mesh if p.tag.split("}")[-1] in ("triangles","polylist","polygons","trifans","tristrips","lines")]
    triangle = one(primitives, "one triangle material primitive required")
    require(triangle.tag == "{"+NS["c"]+"}triangles" and triangle.get("material") == binding.get("symbol"), "triangle material binding differs")
    count = int(triangle.get("count","0"));require(0<count<=8192,"triangle count outside rigid candidate bound")
    inputs = triangle.findall("c:input", NS)
    require(len(inputs)==3 and {i.get("semantic") for i in inputs}=={"VERTEX","NORMAL","TEXCOORD"},"exact position/normal/UV inputs required")
    offsets = {i.get("semantic"):int(i.get("offset")) for i in inputs}
    require(set(offsets.values())=={0,1,2},"contiguous unique triangle offsets required")
    vertex_input = next(i for i in inputs if i.get("semantic")=="VERTEX")
    vertices = ref(ids,vertex_input,"source")
    position_input = one(vertices.findall("c:input",NS),"one vertices position input required")
    require(position_input.get("semantic")=="POSITION","vertices POSITION required")
    positions=source_values(ids,position_input,3)
    normals=source_values(ids,next(i for i in inputs if i.get("semantic")=="NORMAL"),3)
    uv_input=next(i for i in inputs if i.get("semantic")=="TEXCOORD")
    require(uv_input.get("set","0")=="0","UV set0 required")
    uvs=source_values(ids,uv_input,2)
    uv_binding=one(binding.findall("c:bind_vertex_input",NS),"one material UV binding required")
    require(uv_binding.get("input_semantic")=="TEXCOORD" and uv_binding.get("input_set")=="0","material UV binding differs")
    p=one(triangle.findall("c:p",NS),"one indexed triangle stream required")
    indices=numbers(p.text,count*9,integer=True);require(len(indices)==count*9,"triangle index count differs")
    used=set(); tuples=[]
    for k in range(0,len(indices),3):
        triplet=tuple(indices[k+offsets[s]] for s in ("VERTEX","NORMAL","TEXCOORD"))
        require(all(0<=index<len(values) for index,values in zip(triplet,(positions,normals,uvs))),"index outside source")
        used.add(triplet[0]);tuples.append(triplet)
    world={i:[v*scale for v in z_up([positions[i][j]+translation[j] for j in range(3)])] for i in used}
    low=[min(p[a] for p in world.values()) for a in range(3)];high=[max(p[a] for p in world.values()) for a in range(3)]
    require(all(abs(v)<=100 for p in world.values() for v in p),"source metre extent outside bound")
    pivot=[(low[a]+high[a])/2 for a in range(3)]
    mapped={};output_vertices=[];output_indices=[]
    for key in tuples:
        if key not in mapped:
            position,normal,uv=key
            require(all(abs(v)<=16 for v in uvs[uv]),"UV magnitude exceeds candidate bound")
            mapped[key]=len(output_vertices)
            output_vertices.append({"position_m":subtract(world[position],pivot),"normal":unit(z_up(normals[normal])),"uv":uvs[uv]})
        output_indices.append(mapped[key])
    require(len(output_vertices)<=65535,"split vertex count exceeds XSurface ushort")
    winding_negative=0;degenerate=0
    for k in range(0,len(output_indices),3):
        a,b,c=[output_vertices[index] for index in output_indices[k:k+3]]
        area=cross(subtract(b["position_m"],a["position_m"]),subtract(c["position_m"],a["position_m"]))
        length=math.sqrt(sum(v*v for v in area))
        if length<=1e-12:
            degenerate+=1;continue
        normal=[sum(v["normal"][i] for v in (a,b,c)) for i in range(3)]
        if sum(area[i]*normal[i] for i in range(3)) < -length*1e-4:
            winding_negative+=1
    require(degenerate==0,"degenerate triangles refused; no silent topology removal")
    require(winding_negative==0,"winding disagrees with source normals; no silent reversal")
    effect=ref(ids,material.find("c:instance_effect",NS),"url")
    profile=one(effect.findall("c:profile_COMMON",NS),"one COMMON effect required")
    texture=one(profile.findall("c:technique/*/c:diffuse/c:texture",NS),"one diffuse texture required")
    require(texture.get("texcoord")==uv_binding.get("semantic"),"diffuse UV semantic differs")
    params={p.get("sid"):p for p in profile.findall("c:newparam",NS)}
    sampler=params.get(texture.get("texture"));require(sampler is not None,"sampler absent")
    surface=params.get(sampler.findtext("c:sampler2D/c:source",namespaces=NS));require(surface is not None,"surface absent")
    image_id=surface.findtext("c:surface/c:init_from",namespaces=NS);require(image_id in ids,"image absent")
    image=ids[image_id].findtext("c:init_from",namespaces=NS);require(image and member_name(image)==Path(image).name,"local basename texture required")
    return {"schema":"iw7.doom-rigid-source/1","ready":False,"mode":"rigid_source_bind_geometry_not_evaluated_pose",
            "selection":{"node_id":node.get("id"),"node_name":node.get("name"),"controller_id":controller.get("id"),"geometry_id":geometry.get("id"),"material_id":material.get("id"),"material_name":material_name,"effect_id":effect.get("id"),"image_id":image_id,"texture_basename":image},
            "transform":{"source_up":"Y_UP","output_up":"Z_UP","axis_map":["x","-z","y"],"determinant_sign":1,"metres_per_source_unit":scale,"node_translation_source":translation,"pivot_policy":"used-position-AABB-center","pivot_world_m":pivot,"source_world_aabb_m":{"min":low,"max":high},"uv_policy":"preserved_no_V_flip"},
            "metrics":{"source_positions":len(positions),"split_vertices":len(output_vertices),"triangles":count,"degenerate_triangles":degenerate,"winding_negative":winding_negative,"uv_outside_0_1":sum(any(v<0 or v>1 for v in row["uv"]) for row in output_vertices)},
            "vertices":output_vertices,"triangle_indices":output_indices}


def main():
    p=argparse.ArgumentParser();p.add_argument("--archive",type=Path,required=True);p.add_argument("--sha256",required=True);p.add_argument("--dae-member",required=True);p.add_argument("--material",default="doomslayer_game_helmet");p.add_argument("--output-root",type=Path,required=True);a=p.parse_args()
    source=identity(a.archive,a.sha256,256*1024*1024)
    with zipfile.ZipFile(a.archive) as archive:
        require(len(archive.infolist())<=128 and len(set(archive.namelist()))==len(archive.namelist()),"bounded unique archive required")
        member=archive.getinfo(member_name(a.dae_member));require(not member.flag_bits&1 and member.file_size<=MAX_MEMBER,"bounded plain DAE member required")
        data=archive.read(member);result=convert(data,a.material)
        texture_name=str(Path(a.dae_member).parent/result["selection"]["texture_basename"]).replace("\\","/")
        image=archive.getinfo(member_name(texture_name));require(not image.flag_bits&1 and 33<=image.file_size<=MAX_MEMBER,"bounded plain PNG required")
        texture=archive.read(image);require(texture[:8]==b"\x89PNG\r\n\x1a\n" and texture[12:16]==b"IHDR","PNG header differs")
        width=int.from_bytes(texture[16:20],"big");height=int.from_bytes(texture[20:24],"big");require(0<width<=8192 and 0<height<=8192,"texture dimensions outside bound")
    result["provenance"]={"archive":source,"dae_member":a.dae_member,"dae_sha256":hashlib.sha256(data).hexdigest(),"texture_member":texture_name,"texture_sha256":hashlib.sha256(texture).hexdigest(),"texture_bytes":len(texture),"texture_dimensions":[width,height]}
    root=a.output_root.resolve();require(not root.exists(),"fresh output root required")
    for ancestor in (root.parent,*root.parents):
        require(not ancestor.is_symlink() and not ancestor.is_junction(),"reparse output ancestry refused")
    root.mkdir(parents=True,exist_ok=False)
    with (root/"albedo-source.png").open("xb") as f:f.write(texture)
    with (root/"rigid-source.json").open("x",encoding="utf-8") as f:json.dump(result,f,indent=2)
    print(json.dumps({"ready":False,"selection":result["selection"],"metrics":result["metrics"],"output_root":str(root)},indent=2))


if __name__=="__main__":main()
