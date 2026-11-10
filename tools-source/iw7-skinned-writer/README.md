# iw7-skinned-writer: skinned character models, hero materials and outfits

Reads and writes the game's skinned models byte for byte (model, surfaces, up to four bone influences, LOD chain),
turns a Blender or glb mesh into a game model, packs authored maps into the hero material layout and ships a hero
set. Python 3.12, standard library only; Blender is needed for the export and packing steps.

```
blender -b --factory-startup <file>.blend -P tools-source/iw7-skinned-writer/blender_export.py -- --out o.json
python -I tools-source/iw7-skinned-writer/build_model.py o.json --base-xmodel <stock>.xmb --name <name> --out <kitdump>
python -I tools-source/iw7-skinned-writer/ship_heroes.py --config tools-source/iw7-skinned-writer/ship_heroes.example.json --out <dir>
python -B -m unittest discover -s tools-source/iw7-skinned-writer
```

Inputs you provide (none is tracked): a ZoneTool dump of a stock map, fitted meshes, Blender, texconv.
`ship_heroes.example.json` names them through the environment variables `IWZ_DUMP`, `IWZ_HEROES`, `IWZ_BLENDER`
and `IWZ_TEXCONV`. The scripts under `ops/` stage a zone and run a private proof on a bench root with the tools of
the server repository; they take every path as a parameter.

What was proven, in which run, and what is still open: [NOTES.md](NOTES.md). The table of all creation tools:
`docs/CREATION-TOOLS.md`. The tests use synthetic data; what they do not cover is listed in `docs/CHECKS.md`.
