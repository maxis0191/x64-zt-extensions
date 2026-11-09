"""Write an IW7 sound bank source for BO3 weapon sounds (stdlib only).

Input: a GrayWolf BO3 alias table (CSV with Name, FileSpec, Secondary,
VolMin, VolMax...), the exported FLAC files, and a dumped stock IW7 alias
table. Each BO3 alias takes the stock row of its role (channel, type,
distance and curves come from IW7), keeps its BO3 secondary-alias chain, and
scales the stock volume by its BO3 volume relative to the role's reference.

Roles: given per alias with --role alias=role (the port takes them from the
WeaponDef slot that names the alias; secondaries inherit the role of their
chain), otherwise from the BO3 alias name:
  player fire (*_plr with fire/act/flux)  weap_plr_fire_* channels, one per chain layer
  npc fire    (*_npc)                     weap_npc_* channels, one per chain layer
  foley       (reload/raise)              scn_fx_unres_2d row
  projectile  (*loop)                     projectile_loop_close row
  impact      (*exp*)                     explo_*_3d channels, one per chain layer

A chain puts each layer on its own channel, as stock IW7 chains do
(weap_acr_fire_plr -> _mech -> _lyr -> _lfe on overlap, fire_2, fire_3,
fire_lfe; NPC chains on main, mech, lfe, mid; explosions on explo_1, 2, 3):
the layer at depth d of any chain takes LAYER_CHANNELS[role][d], an *lfe*
layer the role's LFE channel. Layers sharing a channel started about 1.2 s
late (measured in game). Every layer keeps the stock row of its role's root
channel (distances, curves, volume); an LFE layer takes the stock LFE row.
A layer reached from chains of two roles (a BO3 flux in the player and the
NPC fire chain) is written once per role, the NPC copy named <alias>_npc.

Player fire layers are hybrid_pcm, as every stock IW7 player fire sound: the
game starts them from an uncompressed head (the first 512 frames as 16-bit PCM,
sound_assets/<prefix>/<alias>.pcmhead, decoded with ffmpeg) while the FLAC
decodes. Stock LFE layers stay loaded.

Output under --out (a ZoneTool IW7 asset root, e.g. zonetool/<zone>):
  sound/<bank>.aliases.csv, soundbank/<bank>.json,
  sound_assets/<prefix>/<alias>.flac (+ .pcmhead for hybrid layers)
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
import subprocess

ROLES = (
    ('impact', lambda n: '_exp' in n, 'explo_1_3d'),
    ('projectile', lambda n: n.endswith('_loop'), 'projectile_loop_close'),
    ('foley', lambda n: 'reload' in n or 'raise' in n, 'scn_fx_unres_2d'),
    ('npc', lambda n: n.endswith('_npc'), 'weap_npc_main_3d'),
    # BO3 fire sounds are chains of layers (Ray Gun: fire, rear, act, flux left, flux right) that play
    # together. Two layers of one chain never share a channel, as in stock chains (on weap_plr_fire_1_2d
    # each layer stopped the one before and the shot was silent): see layer_channel.
    ('player', lambda n: n.endswith('_plr'), 'weap_plr_fire_overlap_2d'),
)
# Stock layer channels by depth in a chain (the root on the role's channel), and LFE channels.
LAYER_CHANNELS = {
    'player': ('weap_plr_fire_overlap_2d', 'weap_plr_fire_2_2d', 'weap_plr_fire_3_2d', 'weap_plr_fire_4_2d',
               'weap_plr_fire_alt_2_2d', 'weap_plr_fire_alt_3_2d', 'weap_plr_fire_alt_4_2d'),
    'npc': ('weap_npc_main_3d', 'weap_npc_mech_3d', 'weap_npc_mid_3d', 'weap_npc_dist_3d'),
    'impact': ('explo_1_3d', 'explo_2_3d', 'explo_3_3d', 'explo_4_3d'),
}
LFE_CHANNELS = {'player': 'weap_plr_fire_lfe_2d', 'npc': 'weap_npc_lfe_3d', 'impact': 'explo_lfe_3d'}
ROLE_CHANNELS = {role: channel for role, _, channel in ROLES}
BO3_REFERENCE_VOLUME = 75.0   # fallback when a BO3 row has no volume
HYBRID_ROLES = ('player',)     # stock: every player fire sound is hybrid_pcm
HYBRID_PCM_FRAMES = 512        # stock head: 1024 bytes mono, 2048 stereo


def flac_channels(path):
    """Channel count from a FLAC's STREAMINFO block."""
    with open(path, 'rb') as f:
        data = f.read(4 + 4 + 34)
    if data[:4] != b'fLaC' or (data[4] & 0x7F) != 0:
        raise SystemExit('%s is not a FLAC with STREAMINFO first' % path)
    v = int.from_bytes(data[8 + 10:8 + 18], 'big')
    return ((v >> 41) & 7) + 1


def pcm_head(path, ffmpeg='ffmpeg'):
    """The first HYBRID_PCM_FRAMES frames of a FLAC as interleaved 16-bit PCM (zero padded)."""
    size = HYBRID_PCM_FRAMES * flac_channels(path) * 2
    out = subprocess.run([ffmpeg, '-v', 'error', '-i', path, '-f', 's16le', '-acodec', 'pcm_s16le', '-'],
                         capture_output=True)
    if out.returncode:
        raise SystemExit('ffmpeg could not decode %s: %s' % (path, out.stderr.decode(errors='replace')[:200]))
    return out.stdout[:size].ljust(size, b'\x00')


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


def layer_channel(role, name, depth):
    """The channel of a layer of a role at a depth of its chain(s)."""
    if role not in LAYER_CHANNELS:
        return ROLE_CHANNELS[role]
    if 'lfe' in name:
        return LFE_CHANNELS[role]
    table = LAYER_CHANNELS[role]
    if depth >= len(table):
        raise SystemExit('%s chain of %s is deeper than the %d stock layer channels' % (role, name, len(table)))
    return table[depth]


def chain_depths(names, secondary, own_channel=lambda name: False):
    """Deepest position of each alias over every chain it is part of: along any chain the depth grows,
    so no two layers of one chain share a depth (a PaP root may chain into the base weapon's root).
    A layer with a channel of its own (LFE) takes no depth: the layer after it may reuse it."""
    depth = {name: 0 for name in names}
    for _ in range(len(depth)):
        for name in names:
            nxt = secondary(name)
            step = 0 if own_channel(name) else 1
            if nxt and depth[nxt] < depth[name] + step:
                depth[nxt] = depth[name] + step
    return depth


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
    ap.add_argument('--ffmpeg', default='ffmpeg', help='decodes the uncompressed head of hybrid layers')
    ap.add_argument('--zone', default='bo3wpn')
    ap.add_argument('--prefix', default='bo3wpn')
    ap.add_argument('--alias', nargs='+', required=True, help='BO3 aliases to include (secondaries are followed)')
    ap.add_argument('--gain-db', type=float, default=0.0,
                    help='added to every alias volume (stock rows cap at 1.0): matches a port to stock loudness')
    ap.add_argument('--role', action='append', default=[],
                    help='alias=role, role in %s (default: from the alias name)' % ', '.join(ROLE_CHANNELS))
    args = ap.parse_args(argv)

    with open(args.bo3_aliases, newline='', encoding='utf-8', errors='replace') as f:
        bo3 = list(csv.reader(f))
    bcol = {n: i for i, n in enumerate(bo3[0])}
    source = {r[0]: r for r in bo3[1:] if r}
    header, col, by_channel = template_rows(args.template)
    roles = dict(r.split('=', 1) for r in args.role)

    wanted, queue, unresolved = [], list(args.alias), []
    while queue:
        name = queue.pop(0)
        if name in wanted or name in unresolved or not name:
            continue
        if name not in source:
            # In none of the exported alias tables (a generic alias kept in a zone the port does not read):
            # reported and left silent, so the weapon references nothing missing.
            unresolved.append(name)
            continue
        wanted.append(name)
        queue.append(source[name][bcol['Secondary']])

    os.makedirs(os.path.join(args.out, 'sound'), exist_ok=True)
    os.makedirs(os.path.join(args.out, 'soundbank'), exist_ok=True)
    out = [header]
    report = [{'alias': name, 'silent': True, 'unresolved': True} for name in unresolved]
    built = {name for name in wanted if source[name][bcol['FileSpec']]}

    def audible_secondary(name):
        """The next alias of a chain that is built: a silent or unresolved link is skipped, so no row names
        an alias the bank lacks (the Mark II fire chain pointed at its silent rear layer)."""
        seen = set()
        nxt = source[name][bcol['Secondary']]
        while nxt and nxt not in built and nxt not in seen:
            seen.add(nxt)
            nxt = source[nxt][bcol['Secondary']] if nxt in source else ''
        return nxt if nxt in built else ''
    def role_in(name, chain_root):
        given = roles.get(name) or roles.get(chain_root)
        if given:
            if given not in ROLE_CHANNELS:
                raise SystemExit('unknown role %s for %s' % (given, name))
            return given
        return role_of(name)[0]

    # One bank alias per (BO3 alias, role): a layer both the player and the NPC chain end in (the DG-2's
    # flux layers) gets a copy per role with its own name and FLAC, so the player chain keeps distinct player
    # channels (two links on weap_npc_main_3d delayed the DG-2 shot by about 1.2 s) and the copies' hybrid
    # and loaded types never share a bank entry.
    instances, layers, links, chain_root = {}, [], {}, {}

    def instance(name, role, start):
        if (name, role) not in instances:
            inst = name if name not in {i for i in instances.values()} else '%s_%s' % (name, role)
            instances[(name, role)] = inst
            layers.append((inst, name, role))
            chain_root[inst] = start
        return instances[(name, role)]
    for start in args.alias:
        if start not in source:
            continue
        name, seen, prev = start if start in built else audible_secondary(start), set(), None
        while name and name not in seen:
            seen.add(name)
            inst = instance(name, role_in(name, start), start)
            if prev and prev not in links:
                links[prev] = inst
            prev, name = inst, audible_secondary(name)
    depth = chain_depths([inst for inst, _, _ in layers], lambda inst: links.get(inst, ''), lambda inst: 'lfe' in inst)
    report += [{'alias': name, 'silent': True} for name in wanted if name not in built]
    for inst, name, role in layers:
        r = source[name]
        channel = layer_channel(role, inst, depth[inst])
        lfe = channel == LFE_CHANNELS.get(role)
        base = channel if lfe else ROLE_CHANNELS[role]
        if base not in by_channel:
            raise SystemExit('template has no %s row' % base)
        row = list(by_channel[base])
        row[col['channel']] = channel
        flac = resolve_flac(args.flac_root, r[bcol['FileSpec']])
        if flac is None:
            raise SystemExit('missing FLAC %s under %s' % (r[bcol['FileSpec']], args.flac_root))
        # Forward slashes: ZoneTool's alias CSV reader turns a backslash followed by t or n into a tab or
        # newline, so t7\tesla_gun_zm\... and t7\thundergun_zm\... named no file and every DG-2 and
        # Thundergun sound was missing from the zone.
        rel = '%s/%s' % (args.prefix.replace('\\', '/').strip('/'), inst)
        dest = os.path.join(args.out, 'sound_assets', *rel.split('/')) + '.flac'
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(flac, dest)
        # BO3 volumes are in dB-like units; keep each chain's relative balance
        # (the chain root plays at the stock volume of its role).
        reference = float(source[chain_root[inst]][bcol['VolMax']] or BO3_REFERENCE_VOLUME)
        gain = 10 ** ((float(r[bcol['VolMax']] or reference) - reference + args.gain_db) / 20.0)
        for key in ('vol_min', 'vol_max'):
            row[col[key]] = '%.6f' % min(1.0, float(row[col[key]]) * gain)
        row[col['Name']] = inst
        row[col['SecondaryAliasName']] = links.get(inst, '')
        row[col['StopAliasName']] = ''
        row[col['Subtitle']] = ''
        row[col['File']] = rel
        if role in HYBRID_ROLES and not lfe:
            row[col['type']] = 'hybrid_pcm'
            with open(dest[:-len('.flac')] + '.pcmhead', 'wb') as f:
                f.write(pcm_head(dest, args.ffmpeg))
        else:
            row[col['type']] = 'loaded'
        # Stock references to duck files are not in the mod's sources.
        for key in ('duck',):
            if key in col:
                row[col[key]] = ''
        out.append(row)
        report.append({'alias': inst, **({'copy_of': name} if inst != name else {}), 'role': role, 'channel': channel, 'secondary': row[col['SecondaryAliasName']],
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
