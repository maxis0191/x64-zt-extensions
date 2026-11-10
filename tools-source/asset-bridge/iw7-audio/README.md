# iw7-audio: IW7 sound banks for usermaps and mods

Stdlib-only tools that read stock IW7 sound asset banks and write ZoneTool IW7
sound bank sources, so a usermap (or a mod) can ship its own sounds and reuse
stock IW7 sounds without loading the zone they come from.

| Tool | Role |
| --- | --- |
| `iw7_sab.py` | Reads `.sabl` (loaded) / `.sabs` (streamed) banks: `list` entries (id, name, size, seconds, channels, rate, loop), `extract` entries as FLAC by alias asset name (`--name`) or by alias (`--names-from <aliases.csv> --alias ...`), `hash` a name with the engine's sound hash. Output follows ZoneTool's `sound_assets/<File>.flac` layout. |
| `iwz_audio_bank.py` | Writes a bank from a JSON spec: every alias starts from a stock alias row (channel, curves, distances, bus behaviour stay IW7's), the spec overrides only listed columns, audio comes from a FLAC file (e.g. a GrayWolf BO3 export) or straight out of the stock banks (`"source": "stock"`). Validates enum columns against values stock IW7 uses, 3D falloff ranges, volumes, fixed-block 16-bit FLAC, and refuses more than 60 s of loaded (non-streamed) audio. Writes `sound/<bank>.aliases.csv`, `soundbank/<bank>.json`, `sound_assets/`, `iwz_audio_manifest.json` and `zone_rows.csv`. |
| `test_iw7_audio.py` | Synthetic tests (bank reader/extractor round trip, spec validation). `python -m unittest test_iw7_audio` |

## How a usermap ships sounds

1. The zone CSV gets `soundbank,<bank>` (e.g. `soundbank,cp_iwz.all`); the bank JSON's `zone` is the map
   name. ZoneTool's soundbank builder then writes `zone/<map>.sabl` (loaded and primed audio) and
   `zone/<map>.sabs` (streamed audio) beside `<map>.ff`.
2. The usermap folder carries all three: `usermaps/<map>/<map>.ff`, `<map>.sabl`, `<map>.sabs`. The
   iw7-mod client redirects the engine's `<map>.sabl/.sabs` opens into `usermaps/<map>/`
   (`fastfiles.cpp` `find_usermap`, server docs/USERMAPS.md).
3. Alias rows reference audio by the hash of their `File` column (`iw7_sab.py hash`). Stock aliases
   copied into the map bank need their audio copied too (`"source": "stock"` does it): a usermap does
   not load `cp_zmb.sabl`. Stock streamed level audio (music, ambience beds) lives in the global
   `code_post_gfx.sabs`, not in `cp_zmb.sabs` (4096-byte empty header); `iw7_sab.py` reads both.
4. Long audio (songs, beds) must be `streamed`; short effects `loaded`. IW7 banks hold FLAC only (ZoneTool
   refuses WAV): fixed block size 1024, 16-bit, any rate the stock banks use (22050..48000).

```
python iwz_audio_bank.py --spec <map spec>.json --out <zonetool asset root of the map> \
    --var IW7_DUMP=<stock dumps> --var GAME=<IW7 game root> --var BO3_EXPORT=<GrayWolf exports>
python iw7_sab.py list <game>/code_post_gfx.sabs --grep amb_cp_zmb
```

Station Zero's spec, easter-egg GSC and capture/measurement tools are in iw7-creator-sdk
`tools-source/iwzmap/audio/`. The BO3 weapon-sound route (`t7-weapons/t7_weapon_sound.py`) maps BO3
weapon alias roles onto stock rows the same way.
