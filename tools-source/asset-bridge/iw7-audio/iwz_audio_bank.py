"""Write an IW7 sound bank source (ZoneTool layout) for a usermap or mod, stdlib only.

Every alias starts from a stock IW7 alias row (channel, curves, distances,
bus behaviour come from IW7) and overrides only what the spec says. Audio
comes from a FLAC file (for example a GrayWolf BO3 export) or, for stock
aliases reused as they are, straight out of the stock sound asset banks
(iw7_sab.py), so a usermap can ship cp_zmb ambience without cp_zmb loaded.

    python iwz_audio_bank.py --spec station_zero_audio.json --out <zonetool asset root> [--check-only]

Spec (JSON):
  {"bank": "cp_iwz.all", "zone": "cp_iwz",
   "template_aliases": "<stock dump>/sound/cp_zmb.all.aliases.csv",
   "stock_banks": ["<game>/cp_zmb.sabl", "<game>/code_post_gfx.sabs"],
   "aliases": [
     {"name": "mus_iwz_abracadavre", "template": "mus_zombies_newwave",
      "source": "<dir>/abracadavre.flac", "file": "iwz\\\\mus\\\\abracadavre",
      "set": {"vol_min": 0.5, "vol_max": 0.5, "MusicContent": "music"}},
     {"name": "emt_water_drip_lp", "template": "emt_water_drip_lp", "source": "stock"}]}

Optional "zones" (sound zones: the 2D ambience bed, reverb, mix, filter and occlusion of a place):
  "zones": {"defs": "<stock dump>/sound", "defs_bank": "cp_zmb.all",
            "rows": [{"name": "cp_iwz", "copy": "cp_zmb_basement_lg_room"}, ...]}
copies the stock definition tables (reverbs, mixes, filters, occlusion, ADSR, ...) unchanged, so the
indices of the copied zone rows stay valid, and writes a zone table holding only the listed rows, renamed.
Every zone's Ambience bed must be an alias of this bank ("ambience" in a row replaces the stock bed;
"no_mix": true drops the stock mix of a copied row).
An alias may take "file" (a new asset name, also for stock audio) and "loop_seconds" (a seamless loop of
that length cut from the source, so a long streamed bed can ship loaded). playlocalsound refuses a looping
alias (script runtime error, nothing plays: runs b4/f5 with developer_script 1) and the engine's sound-zone bed
stays silent in a usermap (runs f3/f5), so a per-player 2D bed is a NONLOOPING clip re-triggered by script:
"retrigger_overlap": F appends the first F seconds of the (seamless) loop to its end and fades the clip in over
its first F and out over its last F seconds; started again every (length - F) seconds, the two copies of the
same audio cross-fade back into the loop (alias loop must be "nonlooping").

Output under --out: sound/<bank>.aliases.csv, soundbank/<bank>.json,
sound_assets/<File>.flac, iwz_audio_manifest.json (alias, file, sha256,
seconds, channels, rate) and zone_rows.csv (`soundbank,<bank>` for the zone
CSV). ZoneTool then writes <zone>.sabl (loaded/primed audio) and <zone>.sabs
(streamed audio) next to the fastfile; a usermap ships both in
usermaps/<map>/ and the client redirects them there.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iw7_sab  # noqa: E402

ENUM_COLUMNS = ('vol_mod', 'channel', 'type', 'loop', 'volumefalloffcurve', 'lpfcurve', 'hpfcurve',
                'reverbsendcurve', 'SpeakerMap', 'reverb', 'shape', 'occlusionshape', 'MusicContent',
                'GPadOutput', 'contexttype')
NUMERIC_COLUMNS = ('vol_min', 'vol_max', 'pitch_min', 'pitch_max', 'donut_fadeend', 'dist_min', 'dist_max',
                   'Velocity_Min', 'Probability', 'StartDelay', 'reverb_multiplier', 'far_reverb_multiplier',
                   'lfe_percentage', 'center_percentage', 'envelop_min', 'envelop_max', 'envelop_percentage',
                   'masterPriority', 'masterPercentage', 'masterSlavePercentage')
STREAMED_TYPES = ('streamed', 'primed', 'hybrid_pcm')


def flac_info(path):
    """STREAMINFO of a FLAC file: rate, channels, bits, frames, block sizes."""
    with open(path, 'rb') as f:
        head = f.read(42)
    if head[:4] != b'fLaC' or (head[4] & 0x7F) != 0:
        raise ValueError('%s: not a FLAC file with a leading STREAMINFO block' % path)
    si = head[8:42]
    min_block, max_block = struct.unpack('>HH', si[:4])
    rate = (si[10] << 12) | (si[11] << 4) | (si[12] >> 4)
    channels = ((si[12] >> 1) & 7) + 1
    bits = (((si[12] & 1) << 4) | (si[13] >> 4)) + 1
    frames = ((si[13] & 0x0F) << 32) | struct.unpack('>I', si[14:18])[0]
    return {'rate': rate, 'channels': channels, 'bits': bits, 'frames': frames,
            'seconds': frames / rate if rate else 0.0, 'min_block': min_block, 'max_block': max_block}


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest().upper()


ESCAPES = re.compile(r'\\[tn]')    # the only sequences ZoneTool utils/csv.cpp unescapes


def zonetool_safe_file(name):
    """ZoneTool's CSV reader unescapes \\n and \\t: stock 'cp\\trolley_movement_lp' reads as
    'cp<TAB>rolley...'. Such names use '/' separators instead; the alias and its bank entry are both
    hashed from the parsed name, so they still match (the audio is shipped in the map bank)."""
    return name.replace('\\', '/') if ESCAPES.search(name) else name


def load_template(path):
    with open(path, newline='', encoding='utf-8', errors='replace') as f:
        rows = list(csv.reader(f))
    header = rows[0]
    col = {n: i for i, n in enumerate(header)}
    by_name = {}
    for r in rows[1:]:
        if len(r) == len(header):
            by_name.setdefault(r[col['Name']], []).append(r)
    enums = {k: set(r[col[k]] for rr in by_name.values() for r in rr) for k in ENUM_COLUMNS if k in col}
    return header, col, by_name, enums


def check_row(name, row, col, enums, errors):
    for k, allowed in enums.items():
        if row[col[k]] not in allowed:
            errors.append('%s: %s=%r is not a value stock IW7 uses' % (name, k, row[col[k]]))
    for k in NUMERIC_COLUMNS:
        if k in col and row[col[k]] != '':
            try:
                float(row[col[k]])
            except ValueError:
                errors.append('%s: %s=%r is not a number' % (name, k, row[col[k]]))
    if not row[col['channel']].endswith('_2d') and float(row[col['dist_max']]) <= float(row[col['dist_min']]):
        errors.append('%s: 3D alias needs dist_max > dist_min' % name)
    if float(row[col['vol_max']]) > 1.0 or float(row[col['vol_min']]) > float(row[col['vol_max']]):
        errors.append('%s: volumes must satisfy vol_min <= vol_max <= 1' % name)


def fmt(value):
    return '%.6f' % value if isinstance(value, float) else str(value)


def build(spec, out, check_only=False):
    header, col, stock, enums = load_template(spec['template_aliases'])
    banks = [iw7_sab.Bank(p) for p in spec.get('stock_banks', [])]
    index = [(b, b.by_id()) for b in banks]
    errors, rows, manifest, copies = [], [], [], []
    names = set()
    for a in spec['aliases']:
        name = a['name']
        if name in names:
            errors.append('%s: duplicate alias' % name)
        names.add(name)
        base = stock.get(a.get('template', name))
        if not base:
            errors.append('%s: template alias %s not in %s' % (name, a.get('template', name), spec['template_aliases']))
            continue
        source = a.get('source', 'stock')
        variants = base if source == 'stock' else base[:1]
        for v in variants:
            row = list(v)
            row[col['Name']] = name
            for k in ('StopAliasName', 'Subtitle'):
                row[col[k]] = ''
            if not a.get('keep_duck'):
                row[col['duck']] = ''           # duck assets of the stock bank are not shipped
            row[col['SecondaryAliasName']] = a.get('secondary', '')
            stock_file = row[col['File']]
            if source != 'stock' or a.get('file'):
                row[col['File']] = a.get('file', 'iwz\\' + name)
            for k, value in a.get('set', {}).items():
                if k not in col:
                    errors.append('%s: unknown column %s' % (name, k))
                    continue
                row[col[k]] = fmt(value)
            check_row(name, row, col, enums, errors)
            original = row[col['File']]
            asset = row[col['File']] = zonetool_safe_file(original)
            dest = os.path.join(out, 'sound_assets', *asset.replace('/', '\\').split('\\')) + '.flac'
            if source == 'stock':
                h = iw7_sab.snd_hash_name(stock_file)
                hit = next(((b, ids[h]) for b, ids in index if h in ids), None)
                if not hit:
                    errors.append('%s: stock audio %s is in none of the stock banks' % (name, asset))
                    continue
                copies.append(('stock', hit, dest, (a.get('loop_seconds'), a.get('retrigger_overlap'))))
            else:
                if not os.path.isfile(source):
                    errors.append('%s: missing source %s' % (name, source))
                    continue
                copies.append(('file', source, dest, (a.get('loop_seconds'), a.get('retrigger_overlap'))))
            rows.append(row)
            manifest.append({'alias': name, 'file': asset, 'type': row[col['type']], 'loop': row[col['loop']],
                             'channel': row[col['channel']], 'dist_min': row[col['dist_min']],
                             'dist_max': row[col['dist_max']], 'vol_max': row[col['vol_max']],
                             'source': 'stock:' + a.get('template', name) if source == 'stock' else source,
                             'dest': dest})
    if errors or check_only:
        return {'errors': errors, 'aliases': len(rows)}

    for d in ('sound', 'soundbank'):
        os.makedirs(os.path.join(out, d), exist_ok=True)
    done = {}
    for (kind, src, dest, loop_seconds), m in zip(copies, manifest):
        if dest not in done:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if kind == 'stock':
                b, e = src
                with open(dest, 'wb') as f:
                    f.write(iw7_sab.flac_container(e, b.read(e)))
            else:
                shutil.copyfile(src, dest)
            loop_seconds, overlap = loop_seconds
            if loop_seconds:
                make_loop(dest, float(loop_seconds))
            if overlap:
                make_retrigger(dest, float(overlap))
            info = flac_info(dest)
            if info['bits'] != 16 or info['min_block'] != info['max_block']:
                errors.append('%s: IW7 banks hold fixed-block 16-bit FLAC (%s)' % (dest, info))
            done[dest] = dict(info, sha256=sha256(dest), bytes=os.path.getsize(dest))
        m.update(done[dest])
        if m['type'] not in STREAMED_TYPES and m['seconds'] > 60:
            errors.append('%s: %.0f s of loaded audio; stream it (type streamed)' % (m['alias'], m['seconds']))
        m['dest'] = os.path.relpath(dest, out)
    if errors:
        return {'errors': errors}

    bank = spec['bank']
    with open(os.path.join(out, 'sound', bank + '.aliases.csv'), 'w', newline='') as f:
        csv.writer(f).writerows([header] + rows)
    sb = {'name': bank, 'zone': spec['zone'], 'gameLanguage': 'all', 'soundLanguage': 'all',
          'aliases': ['sound/%s.aliases.csv' % bank]}
    for key in ('sendEffectParams', 'ADSRSettings', 'AmbientDefs', 'AmbientEvents', 'AmbientElements',
                'FilterDefs', 'MixDefs', 'NPCAdsrZoneEntry', 'PLRAdsrZoneEntry', 'OccludeDefs',
                'ReverbDefs', 'TimescaleEntrys', 'ZoneDefs', 'Unks', 'FullOcclusionDefs', 'PlayerBreathStateDefs'):
        sb[key] = []
    if spec.get('zones'):
        zone_result = write_zones(spec['zones'], bank, out, {m['alias'] for m in manifest}, sb)
        if zone_result['errors']:
            return {'errors': zone_result['errors']}
    with open(os.path.join(out, 'soundbank', bank + '.json'), 'w') as f:
        json.dump(sb, f, indent=4)
    with open(os.path.join(out, 'zone_rows.csv'), 'w', newline='\n') as f:
        f.write('soundbank,%s\n' % bank)
    loaded = sum(m['bytes'] for m in manifest if m['type'] not in STREAMED_TYPES)
    streamed = sum(m['bytes'] for m in manifest if m['type'] in STREAMED_TYPES)
    result = {'bank': bank, 'zone': spec['zone'], 'aliases': manifest,
              'sound_zones': zone_result['zones'] if spec.get('zones') else [],
              'expected_files': {'sabl': spec['zone'] + '.sabl', 'sabs': spec['zone'] + '.sabs'},
              'loaded_audio_bytes': loaded, 'streamed_audio_bytes': streamed, 'errors': []}
    with open(os.path.join(out, 'iwz_audio_manifest.json'), 'w') as f:
        json.dump(result, f, indent=1)
    return result


DEF_TABLES = (('sendEffectParams', 'sendEffectParams'), ('ADSRSettings', 'adsr'), ('AmbientDefs', 'ambient'),
              ('AmbientEvents', 'ambientEvent'), ('AmbientElements', 'ambientElement'), ('FilterDefs', 'filters'),
              ('MixDefs', 'mixes'), ('NPCAdsrZoneEntry', 'adsrZoneNPC'), ('PLRAdsrZoneEntry', 'adsrZonePlayer'),
              ('OccludeDefs', 'occlusionFilters'), ('ReverbDefs', 'reverbs'), ('TimescaleEntrys', 'timescales'),
              ('FullOcclusionDefs', 'fullOcclusions'), ('PlayerBreathStateDefs', 'playerBreathStates'))


def make_loop(path, seconds, fade=1.5):
    """Rewrite a FLAC file as a seamless loop of `seconds`: the first `fade` seconds cross-fade with the audio
    that follows the cut (ffmpeg decodes and encodes 16-bit FLAC in 1024-frame blocks like the stock banks; the cross-fade is stdlib Python). A long
    streamed bed shortened this way can ship as loaded audio."""
    import array
    import subprocess
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries',
                            'stream=sample_rate,channels', '-of', 'csv=p=0', path], capture_output=True, text=True, check=True)
    rate, channels = (int(v) for v in probe.stdout.strip().split(',')[:2])
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 's16le', '-acodec', 'pcm_s16le', '-'],
                         capture_output=True, check=True).stdout
    x = array.array('h')
    x.frombytes(raw)
    n, f = int(seconds * rate) * channels, int(fade * rate) * channels
    if len(x) < n + f:
        raise ValueError('%s: %.1f s is too short for a %.1f s loop' % (path, len(x) / channels / rate, seconds))
    out = x[:n]
    frames = f // channels
    for i in range(f):
        w = (i // channels) / frames
        out[i] = max(-32768, min(32767, int(round(x[i] * w + x[n + i] * (1.0 - w)))))
    tmp = path + '.pcm'
    with open(tmp, 'wb') as fh:
        fh.write(out.tobytes())
    try:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 's16le', '-ar', str(rate), '-ac', str(channels), '-i', tmp,
                        '-c:a', 'flac', '-sample_fmt', 's16', '-frame_size', '1024', path], check=True)
    finally:
        os.remove(tmp)


def make_retrigger(path, overlap):
    """Rewrite a seamless loop as a re-trigger clip: loop + its first `overlap` seconds, linear fade-in over the
    first and fade-out over the last `overlap` seconds. Re-started every len(loop) seconds, the outgoing tail and the
    incoming head hold the same samples with complementary gains, so their sum is the loop itself."""
    import array
    import subprocess
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries',
                            'stream=sample_rate,channels', '-of', 'csv=p=0', path], capture_output=True, text=True, check=True)
    rate, channels = (int(v) for v in probe.stdout.strip().split(',')[:2])
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 's16le', '-acodec', 'pcm_s16le', '-'],
                         capture_output=True, check=True).stdout
    x = array.array('h')
    x.frombytes(raw)
    out = retrigger_samples(x, channels, int(overlap * rate))
    tmp = path + '.pcm'
    with open(tmp, 'wb') as fh:
        fh.write(out.tobytes())
    try:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 's16le', '-ar', str(rate), '-ac', str(channels), '-i', tmp,
                        '-c:a', 'flac', '-sample_fmt', 's16', '-frame_size', '1024', path], check=True)
    finally:
        os.remove(tmp)


def retrigger_samples(x, channels, frames):
    """Interleaved 16-bit loop -> re-trigger clip (see make_retrigger)."""
    import array
    f = frames * channels
    if len(x) < 2 * f:
        raise ValueError('loop shorter than twice the re-trigger overlap')
    out = array.array('h', x)
    out.extend(x[:f])
    n = len(out)
    for i in range(f):
        w = (i // channels) / frames
        out[i] = int(round(out[i] * w))
        out[n - f + i] = int(round(out[n - f + i] * (1.0 - w)))
    return out


def write_zones(z, bank, out, aliases, sb):
    """Copy the stock definition tables and write the selected, renamed zone rows (see the module doc)."""
    errors, zones = [], []
    src, stock = z['defs'], z.get('defs_bank', 'cp_zmb.all')
    for key, suffix in DEF_TABLES:
        path = os.path.join(src, '%s.%s.csv' % (stock, suffix))
        if not os.path.isfile(path):
            errors.append('missing stock table %s' % path)
            continue
        shutil.copyfile(path, os.path.join(out, 'sound', '%s.%s.csv' % (bank, suffix)))
        sb[key] = ['sound/%s.%s.csv' % (bank, suffix)]
    unk = os.path.join(src, 'unk', stock + '.json')
    if os.path.isfile(unk):
        os.makedirs(os.path.join(out, 'sound', 'unk'), exist_ok=True)
        shutil.copyfile(unk, os.path.join(out, 'sound', 'unk', bank + '.json'))
        sb['Unks'] = ['sound/unk/%s.json' % bank]
    with open(os.path.join(src, '%s.zone.csv' % stock), newline='', encoding='utf-8') as f:
        rows = list(csv.reader(f))
    header = rows[0]
    col = {n: i for i, n in enumerate(header)}
    by_name = {r[col['Zone_Name']]: r for r in rows[1:] if len(r) == len(header)}
    picked = []
    for row in z['rows']:
        base = by_name.get(row['copy'])
        if not base:
            errors.append('zone %s: stock zone %s not found' % (row['name'], row['copy']))
            continue
        r = list(base)
        r[col['Zone_Name']] = row['name']
        if 'ambience' in row:
            r[col['Ambience']] = row['ambience']
        if row.get('no_mix'):
            for k, v in (('Mix', ''), ('MixIndex', '-1'), ('NumMix', '0')):
                if k in col:
                    r[col[k]] = v
        bed = r[col['Ambience']]
        if bed and bed not in aliases:
            errors.append('zone %s: ambience bed %s is not an alias of this bank' % (row['name'], bed))
        picked.append(r)
        zones.append({'zone': row['name'], 'copy': row['copy'], 'ambience': bed, 'reverb': r[col['Reverb']],
                      'mix': r[col['Mix']], 'filter': r[col['Filter']], 'occlusion': r[col['Occlusion']]})
    with open(os.path.join(out, 'sound', '%s.zone.csv' % bank), 'w', newline='', encoding='utf-8') as f:
        csv.writer(f).writerows([header] + picked)
    sb['ZoneDefs'] = ['sound/%s.zone.csv' % bank]
    return {'errors': errors, 'zones': zones}


def expand(value, env):
    if isinstance(value, str):
        for k, v in env.items():
            value = value.replace('${%s}' % k, v)
        if '${' in value:
            raise SystemExit('unresolved variable in %r (pass --var)' % value)
        return value
    if isinstance(value, list):
        return [expand(v, env) for v in value]
    if isinstance(value, dict):
        return {k: expand(v, env) for k, v in value.items()}
    return value


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument('--spec', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--check-only', action='store_true')
    ap.add_argument('--var', action='append', default=[], help='KEY=VALUE substituted for ${KEY} in spec strings')
    args = ap.parse_args(argv)
    with open(args.spec, encoding='utf-8') as f:
        spec = json.load(f)
    spec = expand(spec, dict(v.split('=', 1) for v in args.var))
    result = build(spec, args.out, args.check_only)
    summary = {k: v for k, v in result.items() if k != 'aliases'}
    summary['aliases'] = len(result['aliases']) if isinstance(result.get('aliases'), list) else result.get('aliases')
    print(json.dumps(summary, indent=1))
    return 1 if result['errors'] else 0


if __name__ == '__main__':
    sys.exit(main())
