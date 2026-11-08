# env-model: environment models for IW7 usermaps (BO3 ports and Blender-authored parts)

One command turns a list of Black Ops III environment models (or any glTF, e.g. from Blender) into IW7 model
sources that `kit_import.py` (iw7-creator-sdk, branch codex/iwzmap-hero-train) links into a usermap zone:

```
python t7_env_port.py --manifest port.json --out <dump root> [--graywolf <GrayWolf.exe>]
```

| File | Does |
| --- | --- |
| `iw7_zt_stream.py` | ZoneTool assetmanager record streams (.xmb/.xsb), reader and writer |
| `iw7_xmodel_io.py` | IW7 XModel / XModelSurfs schemas: parse, edit, write (byte-identical on 5383 xsb + 3093 xmb of cp_disco) |
| `iw7_model_author.py` | rigid IW7 models from triangle meshes: packing, tangents, winding, normals check/rebuild, LODs, 65535-vertex split |
| `mesh_glb.py` | glTF reader to game space (inches, Z up); GrayWolf skins and Blender exports |
| `t7_env_material.py` | BO3 materials (GrayWolf materials.json) baked to IW7 model materials: layered micro tiles, tints, reveal masks, decals, glass, emissive; IW7 packed images passed through |
| `collision_boxes.py` | clip boxes from a surface voxelisation (openings stay open) for the map generator |
| `t7_env_port.py` | the one-command port (manifest: models composed of parts with offset / yaw / repeat, LOD part lists, overrides) |
| `iw7_model_to_glb.py` | an IW7 model dump back to glTF (what the engine reads), for inspection |
| `blender/blender_preview.py` | headless Blender renders of glTF files |
| `blender/track_kit.py` | procedural rails (AREMA-like profile), ballast prism, third rail on porcelain insulators, LOD1, materials.json |
| `test_env_model.py` | unit tests (`python -m unittest test_env_model`) |

Conventions measured on stock dumps are documented at the top of `iw7_model_author.py`. Known traps handled:
reversed LOD order (refused), random normals (rebuilt when < 90 % agree with the faces), origin (manifest
`origin: base`), BO3 images not in IW7 paks (embedded `.dds`), glass/decal templates (blend with packed_a).

Blender: 4.5.15 LTS portable from download.blender.org (zip sha256
52dd02fd74877fa08e74b67d7854cf32468a232c02aaa19b6844c91285574f8d), run as
`blender -b --factory-startup -P <script> -- <args>`.
