"""Write an IW7 sound bank source for BO3 weapon sounds (stdlib only).

Input: a GrayWolf BO3 alias table (CSV with Name, FileSpec, Secondary,
VolMin, VolMax...), the exported FLAC files, and a dumped stock IW7 alias
table. Each BO3 alias takes the stock row of its role (channel, type,
distance and curves come from IW7), keeps its BO3 secondary-alias chain, and
scales the stock volume by its BO3 volume relative to the role's reference.

Roles: given per alias with --role alias=role (the port takes them from the
WeaponDef slot that names the alias; secondaries inherit the role of their
chain), otherwise from the BO3 alias name:
  player fire (*_plr with fire/act/flux)  weap_plr_fire_overlap_2d row
  npc fire    (*_npc)                     weap_npc_main_3d row
  foley       (reload/raise)              scn_fx_unres_2d row
  projectile  (*loop)                     projectile_loop_close row
  impact      (*exp*)                     explo_1_3d row

Output under --out (a ZoneTool IW7 asset root, e.g. zonetool/<zone>):
  sound/<bank>.aliases.csv, soundbank/<bank>.json,
  sound_assets/<prefix>/<alias>.flac
Add `soundbank,<bank>` to the zone CSV; ZoneTool writes mod.sabl/mod.sabs.

    python t7_weapon_sound.py --bo3-aliases zm_common.csv --flac-root <dir>
        --template <stock>.aliases.csv --out <asset root> --bank bo3wpn.all
        --zone bo3wpn --prefix bo3wpn/raygun --alias wpn_rgun_fire_plr ...
"""
import argparse
import csv
import json
import math
import os
import shutil

ROLES = (
    ('impact', lambda n: '_exp' in n, 'explo_1_3d'),
    ('projectile', lambda n: n.endswith('_loop'), 'projectile_loop_close'),
    ('foley', lambda n: 'reload' in n or 'raise' in n, 'scn_fx_unres_2d'),
    ('npc', lambda n: n.endswith('_npc'), 'weap_npc_main_3d'),
    # BO3 fire sounds are chains of layers (Ray Gun: fire, rear, act, flux left, flux right) that play
    # together; on weap_plr_fire_1_2d each layer stopped the one before and the Ray Gun shot was silent
    # (witness 2026-11-08). Stock IW7 layered fire chains (G18 + _mech) use the overlap channel.
    ('player', lambda n: n.endswith('_plr'), 'weap_plr_fire_overlap_2d'),
)
ROLE_CHANNELS = {role: channel for role, _, channel in ROLES}
BO3_REFERENCE_VOLUME = 75.0   # fallback when a BO3 row has no volume


def resolve_flac(root, spec):
    """A BO3 FileSpec under an export root. GrayWolf writes every sound under all/, while alias
    tables name some files with that prefix and some without."""
    parts = [p for p in spec.replace('/', '\\').split('\\') if p]
    if parts:
        parts[-1] = os.path.splitext(parts[-1])[0] + '.flac'   # tables also name .opus/.wav; exports are FLAC
    for cand in (parts, ['all'] + parts, parts[1:] if parts[:1] == ['all'] else None):
        if cand:
            path = os.path.join(root, *cand)
            if os.path.isfile(path):
                return path
    return None


def role_of(name):
    for role, match, channel in ROLES:
        if match(name):
            return role, channel
    raise SystemExit('no role for alias %s' % name)


def template_rows(path):
    with open(path, newline='', encoding='utf-8', errors='replace') as f:
        rows = list(csv.reader(f))
    header = rows[0]
    col = {n: i for i, n in enumerate(header)}
    by_channel = {}
    for r in rows[1:]:
        # First audible stock row of each channel.
        if len(r) == len(header) and r[col['channel']] not in by_channel and float(r[col['vol_max']] or 0) > 0:
            by_channel[r[col['channel']]] = r
    return header, col, by_channel


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    ap.add_argument('--bo3-aliases', required=True)
    ap.add_argument('--flac-root', required=True, help='folder the BO3 FileSpec paths resolve against')
    ap.add_argument('--template', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--bank', default='bo3wpn.all')
    ap.add_argument('--zone', default='bo3wpn')
    ap.add_argument('--prefix', default='bo3wpn')
    ap.add_argument('--alias', nargs='+', required=True, help='BO3 aliases to include (secondaries are followed)')
    ap.add_argument('--role', action='append', default=[],
                    help='alias=role, role in %s (default: from the alias name)' % ', '.join(ROLE_CHANNELS))
    args = ap.parse_args(argv)

    with open(args.bo3_aliases, newline='', encoding='utf-8', errors='replace') as f:
        bo3 = list(csv.reader(f))
    bcol = {n: i for i, n in enumerate(bo3[0])}
    source = {r[0]: r for r in bo3[1:] if r}
    header, col, by_channel = template_rows(args.template)
    roles = dict(r.split('=', 1) for r in args.role)

    wanted, root, queue, unresolved = [], {}, [(a, a) for a in args.alias], []
    while queue:
        name, chain = queue.pop(0)
        if name in wanted or name in unresolved or not name:
            continue
        if name not in source:
            # In none of the exported alias tables (a generic alias kept in a zone the port does not read):
            # reported and left silent, so the weapon references nothing missing.
            unresolved.append(name)
            continue
        wanted.append(name)
        root[name] = chain
        queue.append((source[name][bcol['Secondary']], chain))

    os.makedirs(os.path.join(args.out, 'sound'), exist_ok=True)
    os.makedirs(os.path.join(args.out, 'soundbank'), exist_ok=True)
    out = [header]
    report = [{'alias': name, 'silent': True, 'unresolved': True} for name in unresolved]
    for name in wanted:
        r = source[name]
        if not r[bcol['FileSpec']]:
            # BO3 keeps empty aliases for silent roles (the Thundergun's projectile loop): nothing to play.
            report.append({'alias': name, 'silent': True})
            continue
        given = roles.get(name) or roles.get(root[name])
        if given:
            if given not in ROLE_CHANNELS:
                raise SystemExit('unknown role %s for %s' % (given, name))
            role, channel = given, ROLE_CHANNELS[given]
        else:
            role, channel = role_of(name)
        if channel not in by_channel:
            raise SystemExit('template has no %s row' % channel)
        row = list(by_channel[channel])
        flac = resolve_flac(args.flac_root, r[bcol['FileSpec']])
        if flac is None:
            raise SystemExit('missing FLAC %s under %s' % (r[bcol['FileSpec']], args.flac_root))
        # Forward slashes: ZoneTool's alias CSV reader turns a backslash followed by t or n into a tab or
        # newline, so t7\tesla_gun_zm\... and t7\thundergun_zm\... named no file and every DG-2 and
        # Thundergun sound was missing from the zone.
        rel = '%s/%s' % (args.prefix.replace('\\', '/').strip('/'), name)
        dest = os.path.join(args.out, 'sound_assets', *rel.split('/')) + '.flac'
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(flac, dest)
        # BO3 volumes are in dB-like units; keep each chain's relative balance
        # (the chain root plays at the stock volume of its role).
        reference = float(source[root[name]][bcol['VolMax']] or BO3_REFERENCE_VOLUME)
        gain = 10 ** ((float(r[bcol['VolMax']] or reference) - reference) / 20.0)
        for key in ('vol_min', 'vol_max'):
            row[col[key]] = '%.6f' % min(1.0, float(row[col[key]]) * gain)
        row[col['Name']] = name
        row[col['SecondaryAliasName']] = r[bcol['Secondary']]
        row[col['StopAliasName']] = ''
        row[col['Subtitle']] = ''
        row[col['File']] = rel
        row[col['type']] = 'loaded'
        # Stock references to duck files are not in the mod's sources.
        for key in ('duck',):
            if key in col:
                row[col[key]] = ''
        out.append(row)
        report.append({'alias': name, 'role': role, 'channel': channel, 'secondary': r[bcol['Secondary']],
                       'vol': row[col['vol_max']], 'flac_bytes': os.path.getsize(dest)})
    with open(os.path.join(args.out, 'sound', args.bank + '.aliases.csv'), 'w', newline='') as f:
        csv.writer(f).writerows(out)
    bank = {'name': args.bank, 'zone': args.zone, 'gameLanguage': 'all', 'soundLanguage': 'all',
            'aliases': ['sound/%s.aliases.csv' % args.bank]}
    for key in ('sendEffectParams', 'ADSRSettings', 'AmbientDefs', 'AmbientEvents', 'AmbientElements',
                'FilterDefs', 'MixDefs', 'NPCAdsrZoneEntry', 'PLRAdsrZoneEntry', 'OccludeDefs',
                'ReverbDefs', 'TimescaleEntrys', 'ZoneDefs', 'Unks', 'FullOcclusionDefs', 'PlayerBreathStateDefs'):
        bank[key] = []
    with open(os.path.join(args.out, 'soundbank', args.bank + '.json'), 'w') as f:
        json.dump(bank, f, indent=4)
    print(json.dumps({'bank': args.bank, 'aliases': report}, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
