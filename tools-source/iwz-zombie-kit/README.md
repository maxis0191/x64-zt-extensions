# iwz-zombie-kit: an authored mesh fitted to the stock zombie parts

Fits one authored mesh to the stock zombie (six body parts, five damaged parts, caps), writes the models and
materials with the skinned writer (`../iw7-skinned-writer`) and clones the stock scriptable with the new part names.
Offline only so far: nothing was built into a zone or run in the game (see NOTES).

```
python -I tools-source/iwz-zombie-kit/run_zombie.py --config tools-source/iwz-zombie-kit/configs/zombie_M1.json
python -B -m unittest discover -s tools-source/iwz-zombie-kit
```

Inputs you provide through environment variables (none is tracked; a missing one stops the run with its name):
`IWZ_HEROES` (local heroes work folder; its `tools/fit` holds `fit_hero.py`, a local file that is not in this
repository), `IWZ_BLENDER` (blender.exe), `IWZ_DUMP` (ZoneTool dump root with `cp_zmb` and `techsets_cp_zmb`),
`IWZ_TEXCONV` (texconv.exe). Optional: `IWZ_FIT_DIR`, `IWZ_WRITER`.

State, measurements and open points: [NOTES.md](NOTES.md). The table of all creation tools: `docs/CREATION-TOOLS.md`.
