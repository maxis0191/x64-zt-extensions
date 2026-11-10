#!/usr/bin/env python3
"""Weapon sound audit: will this weapon's sounds load, and are they set up the way stock weapons are?

Reads facts from files only (sfxpkg, sound alias tables, sound_assets, soundbank JSON, compiled banks) and from the
stock dump passed at run time. Levels are MEASURED from the sample files (ffmpeg volumedetect) and never estimated.
What the player hears is the engine's to confirm: those findings carry proof='engine' and an engine question.

    python -I iw7_weapon_sound_audit.py TREE --stock DUMP/cp_zmb [--bank mod.sabl --loads-as mod] [--json out.json]

Rules (codes): SND-BANK-ZONE, SND-BANK-JSON-ZONE, SND-BANK-UNREADABLE, SND-SAMPLE-MISSING, SND-PCMHEAD-MISSING,
SND-FIRE-LEVEL, SND-FIRE-QUIET, SND-LEVEL-NOT-MEASURED, SND-LAYERS-ONE-CHANNEL, SND-FIRE-TYPE-RARE,
SND-ALIAS-MISSING, SND-ALIAS-NOT-IN-DUMP, SND-FIRE-VOLUME-POSITION, SND-NO-STOCK, and the shared SND-TEMPLATE-*.
"""
import argparse
import glob
import math
import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import iw7_audit_common as common  # noqa: E402

TOOL = 'weapon-sound-audit'
PREFIX = 'SND'
GROUPS = ('sound profile',)

BANK_STRUCT = '<8I3Q16s512sQQ64s8s3sII5s'
BANK_MAGIC = 0x23585532
BANK_VERSION = 4
BANK_ZONE_FIELD = 15
FIRE_SLOTS = ('fireSoundPlayer', 'fireLastSoundPlayer')
QUIET_DB = 6.0               # a player's shot chain this far below its reference is worth a listen
RARE_SHARE = 0.05            # a stock share under this is "rare"
AGGREGATE_OVER = 10          # more missing files than this in one alias table are written as one finding
SAMPLE_EXTENSIONS = ('.flac', '.wav')
NOT_AUDIO_SLOTS = ('name',)


# ------------------------------------------------------------------ compiled banks
def read_bank_header(path):
    """(zone name, version) of a compiled .sabl/.sabs. ValueError when it is not a bank."""
    size = struct.calcsize(BANK_STRUCT)
    with open(path, 'rb') as handle:
        raw = handle.read(size)
    if len(raw) < size:
        raise ValueError('only %d bytes, a bank header is %d' % (len(raw), size))
    fields = struct.unpack_from(BANK_STRUCT, raw)
    if fields[0] != BANK_MAGIC:
        raise ValueError('magic is 0x%08x, not 0x%08x' % (fields[0], BANK_MAGIC))
    if fields[1] != BANK_VERSION:
        raise ValueError('bank version is %d, not %d' % (fields[1], BANK_VERSION))
    zone = fields[BANK_ZONE_FIELD].split(b'\0', 1)[0].decode('ascii', 'replace')
    return zone, fields[1]


# ------------------------------------------------------------------ measuring
_FFMPEG_CACHE = {}


def channel_count(layout):
    """Channels from an ffmpeg layout word: mono, stereo, 5.1, '4 channels'; None when unknown."""
    if layout in ('mono', 'stereo'):
        return 1 if layout == 'mono' else 2
    named = re.match(r'^(\d+) channels', layout)
    if named:
        return int(named.group(1))
    dotted = re.match(r'^(\d)\.(\d)', layout)
    return int(dotted.group(1)) + int(dotted.group(2)) if dotted else None


def ffmpeg_measure(path):
    """(mean level in dBFS, channels) of a sample through ffmpeg volumedetect; None when it cannot be measured."""
    if path in _FFMPEG_CACHE:
        return _FFMPEG_CACHE[path]
    result = None
    try:
        run = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af', 'volumedetect', '-f', 'null', '-'],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        text = run.stderr.decode('utf-8', 'replace')
        mean = re.search(r'mean_volume:\s*(-?[0-9.]+|-inf)\s*dB', text)
        stream = re.search(r'Stream #\d+:\d+.*?Audio:.*?Hz,\s*([^,]+),', text)
        if run.returncode == 0 and mean and mean.group(1) != '-inf':
            layout = stream.group(1).strip().lower() if stream else ''
            channels = channel_count(layout)
            result = (float(mean.group(1)), channels)
    except (OSError, subprocess.SubprocessError, ValueError):
        result = None
    _FFMPEG_CACHE[path] = result
    return result


# ------------------------------------------------------------------ files of the tree
def clean_file(value):
    return (value or '').replace('\\', '/').strip('/')


def sample_path(zone_dir, file_value):
    """Path of the sample behind an alias row's File, or None (absent, or a path that leaves sound_assets)."""
    rel = clean_file(file_value)
    if not rel or '..' in rel.split('/'):
        return None
    base = os.path.join(zone_dir, 'sound_assets')
    for ext in SAMPLE_EXTENSIONS:
        full = os.path.join(base, *rel.split('/')) + ext
        if os.path.isfile(full):
            return full
    return None


def pcmhead_path(zone_dir, file_value):
    rel = clean_file(file_value)
    if not rel or '..' in rel.split('/'):
        return None
    return os.path.join(zone_dir, 'sound_assets', *rel.split('/')) + '.pcmhead'


def db(volume):
    return 20.0 * math.log10(max(volume, 1e-6))


# ------------------------------------------------------------------ stock
class StockSound:
    """Everything the audit needs from the stock alias tables and sfxpkg files, read once per run."""

    def __init__(self, stock):
        self.rows = []
        for zone in sorted(stock.zones):
            self.rows.extend(common.alias_rows(stock.zones[zone]))
        self.index = common.alias_index(self.rows)
        self.pairs = {(row['Name'], clean_file(row.get('File'))) for row in self.rows}
        self.named = set()                  # every alias name any stock sfxpkg points at
        roots = {}
        for _, _, doc in stock.docs('sfxpkg'):
            sounds = doc.get('sounds') if isinstance(doc, dict) else None
            if not isinstance(sounds, dict):
                continue
            for key, value in sounds.items():
                if key not in NOT_AUDIO_SLOTS and isinstance(value, str) and value:
                    self.named.add(value)
            for slot in FIRE_SLOTS:
                if isinstance(sounds.get(slot), str) and sounds[slot]:
                    roots[sounds[slot]] = True
        self.chains = []                    # [chain] of every stock player fire chain, one per root alias
        for root in sorted(roots):
            chain = common.alias_chain(self.index, root)
            if chain and chain[0][1]:
                self.chains.append(chain)
        self.type_counts, self.volumes = {}, []
        for chain in self.chains:
            for row in chain[0][1]:
                kind = row.get('type', '')
                if kind:
                    self.type_counts[kind] = self.type_counts.get(kind, 0) + 1
                volume = common.number(row.get('vol_max'))
                if volume is not None:
                    self.volumes.append(volume)
        self.multi = [chain for chain in self.chains if len(chain) >= 2]
        self.sharing = sum(1 for chain in self.chains if shared_channels(chain))
        self.sharing_multi = sum(1 for chain in self.multi if shared_channels(chain))

    def type_share(self, kind):
        total = sum(self.type_counts.values())
        return (self.type_counts.get(kind, 0) / total) if total else None


def row_channels(rows):
    return {row.get('channel', '') for row in rows if row.get('channel')}


def shared_channels(chain):
    """{channel: [alias names]} of every channel used by two different aliases of one fire chain."""
    users = {}
    for name, rows in chain:
        for channel in row_channels(rows):
            users.setdefault(channel, []).append(name)
    return {channel: names for channel, names in users.items() if len(names) >= 2}


# ------------------------------------------------------------------ the audit
def _aggregate(report, severity, code, asset, items, message_one, message_many, notice):
    """One finding per item up to AGGREGATE_OVER, else a single one with the first examples."""
    if not items:
        return
    if len(items) <= AGGREGATE_OVER:
        for text, evidence in items:
            report.add(severity, code, asset, message_one % text, notice=notice, **evidence)
    else:
        report.add(severity, code, asset, message_many % (len(items), ', '.join(t for t, _ in items[:5])),
                   notice=notice, count=len(items), examples=[t for t, _ in items[:5]])


def audit_banks(report, zone_dir, banks, loads_as):
    for bank in banks:
        name = os.path.basename(bank)
        try:
            zone, _ = read_bank_header(bank)
        except (OSError, ValueError) as error:
            report.add('error', 'SND-BANK-UNREADABLE', name, 'cannot read the bank header: %s' % error,
                       notice='the game cannot load this bank: none of its sounds will play', path=bank)
            continue
        expected = loads_as or os.path.splitext(name)[0]
        if zone != expected:
            report.add('error', 'SND-BANK-ZONE', name,
                       'bank header says "%s" but the game asks for "%s": no sound of this bank will play' % (zone, expected),
                       notice='every custom sound of this bank is silent', header=zone, expected=expected)
    if loads_as:
        for path in sorted(glob.glob(os.path.join(zone_dir, 'soundbank', '*.json'))):
            try:
                doc = common.load_json(path)
            except (OSError, ValueError) as error:
                report.add('error', 'SND-BANK-UNREADABLE', os.path.basename(path), 'does not parse: %s' % error,
                           notice='the sound bank description is broken', path=path)
                continue
            zone = doc.get('zone') if isinstance(doc, dict) else None
            if zone != loads_as:
                report.add('error', 'SND-BANK-JSON-ZONE', os.path.basename(path),
                           'soundbank zone is "%s" but the game asks for "%s": a bank built from it gets the wrong name'
                           % (zone, loads_as), notice='every custom sound built from this description is silent',
                           zone=zone, expected=loads_as)


def audit_samples(report, zone_dir, rows, stock_sound):
    """S2 and S3: the files behind the tree's own alias rows."""
    if not os.path.isdir(os.path.join(zone_dir, 'sound_assets')):
        return
    missing, headless = {}, {}
    for row in rows:
        file_value = clean_file(row.get('File'))
        if not file_value:
            continue
        if stock_sound and (row['Name'], file_value) in stock_sound.pairs:
            continue
        sample = sample_path(zone_dir, file_value)
        table = row['_list']
        if sample is None:
            text = '%s (line %d)' % (row['Name'], row['_line'])
            missing.setdefault(table, []).append((text, {'alias': row['Name'], 'file': file_value, 'line': row['_line']}))
        elif row.get('type') == 'hybrid_pcm':
            head = pcmhead_path(zone_dir, file_value)
            if not os.path.isfile(head) or os.path.getsize(head) == 0:
                text = '%s (line %d)' % (row['Name'], row['_line'])
                headless.setdefault(table, []).append((text, {'alias': row['Name'], 'file': file_value, 'line': row['_line']}))
    for table in sorted(missing):
        _aggregate(report, 'error', 'SND-SAMPLE-MISSING', table, missing[table],
                   'sample file of alias %s is absent from sound_assets',
                   '%d aliases name a sample that is absent from sound_assets, first: %s',
                   'these sounds cannot be built: they are silent or the build fails')
    for table in sorted(headless):
        _aggregate(report, 'error', 'SND-PCMHEAD-MISSING', table, headless[table],
                   'hybrid_pcm alias %s has no .pcmhead (or it is empty)',
                   '%d hybrid_pcm aliases have no .pcmhead (or it is empty), first: %s',
                   'the start of the sound is cut or silent')


def fire_roots(sfxpkg):
    sounds = sfxpkg.get('sounds') if isinstance(sfxpkg, dict) else None
    sounds = sounds if isinstance(sounds, dict) else {}
    out = []
    for slot in FIRE_SLOTS:
        value = sounds.get(slot)
        if isinstance(value, str) and value and value not in out:
            out.append(value)
    return out


def merged_index(tree_index, stock_sound):
    """Alias rows by name: the tree's own rows win, stock rows fill in names the tree does not define."""
    if not stock_sound:
        return tree_index
    merged = dict(stock_sound.index)
    merged.update(tree_index)
    return merged


def alias_level(rows, zone_dir, measure):
    """(level dB, [channels]) of one alias: the average of its variants, None when any variant cannot be measured."""
    levels, channels = [], []
    for row in rows:
        sample = sample_path(zone_dir, row.get('File'))
        volume = common.number(row.get('vol_max'))
        if sample is None or measure is None or volume is None:
            return None, channels
        got = measure(sample)
        if not got:
            return None, channels
        levels.append(got[0] + db(volume))
        channels.append(got[1])
    return (sum(levels) / len(levels), channels) if levels else (None, channels)


def chain_level(chain, zone_dir, measure):
    """(power-summed level of the chain, per-layer facts); the level is None unless every layer was measured."""
    total, layers, whole = 0.0, [], True
    for name, rows in chain:
        level, channels = alias_level(rows, zone_dir, measure)
        layers.append({'alias': name, 'variants': len(rows), 'channels': sorted(row_channels(rows)),
                       'types': sorted({r.get('type', '') for r in rows}), 'sample_channels': channels,
                       'level_db': None if level is None else round(level, 2)})
        if level is None:
            whole = False
        else:
            total += 10 ** (level / 10.0)
    return (10.0 * math.log10(total) if whole and total > 0 else None), layers


def audit(zone_dir, stock, intent, items=None, banks=(), loads_as=None, fire_reference_db=None, measure=None):
    """Return a common.Report for the tree. measure=None runs ffmpeg, measure=False measures nothing."""
    report = common.Report(TOOL, zone_dir)
    intent.report_problems(report)
    if measure is None:
        measure = ffmpeg_measure
    elif measure is False:
        measure = None
    audit_banks(report, zone_dir, banks, loads_as)

    rows = common.alias_rows(zone_dir)
    tree_index = common.alias_index(rows)
    stock_sound = StockSound(stock) if stock else None
    if stock_sound is None:
        report.add('info', 'SND-NO-STOCK', os.path.basename(zone_dir),
                   'no stock dump given: the shot-layer, root-type and volume comparisons are skipped, '
                   'missing aliases cannot be told from stock ones',
                   notice='nothing is compared with the sounds of the original game')
    else:
        report.facts['stock'] = {
            'alias_rows': len(stock_sound.rows), 'player_fire_chains': len(stock_sound.chains),
            'chains_with_layers': len(stock_sound.multi), 'chains_sharing_a_channel': stock_sound.sharing,
            'multi_layer_chains_sharing_a_channel': stock_sound.sharing_multi,
            'root_type_counts': dict(sorted(stock_sound.type_counts.items()))}
    audit_samples(report, zone_dir, rows, stock_sound)
    index = merged_index(tree_index, stock_sound)

    facts, levels, chains_seen, unmeasured = {}, {}, {}, set()
    volumes = common.Population(stock_sound.volumes) if stock_sound else None
    for item in (items or common.weapon_names(zone_dir)):
        judge, documents, templates = common.judge_weapon(zone_dir, item, intent, stock)
        facts[item] = common.template_facts(templates)
        judge.report(report, PREFIX, only=GROUPS)
        sfxpkg = documents.get('sfxpkg')
        if not isinstance(sfxpkg, dict):
            continue
        _alias_existence(report, item, sfxpkg, index, tree_index, stock_sound)
        for root in fire_roots(sfxpkg):
            chain = common.alias_chain(index, root)
            level, layers = chain_level(chain, zone_dir, measure)
            chains_seen.setdefault(item, {})[root] = layers
            if level is None:
                unmeasured.add(item)
            else:
                levels.setdefault(item, {})[root] = round(level, 2)
            _fire_rules(report, item, root, chain, stock_sound, volumes)
    report.facts['templates'] = facts
    report.facts['fire_chains'] = chains_seen
    report.facts['fire_levels'] = levels

    _levels(report, zone_dir, levels, unmeasured, measure, fire_reference_db)
    return report


def _alias_existence(report, item, sfxpkg, index, tree_index, stock_sound):
    """S8: every alias the package names, and every layer reached from them, exists somewhere."""
    sounds = sfxpkg.get('sounds') if isinstance(sfxpkg.get('sounds'), dict) else {}
    missing, elsewhere = [], []
    seen = set()
    for slot in sorted(sounds):
        value = sounds[slot]
        if slot in NOT_AUDIO_SLOTS or not isinstance(value, str) or not value:
            continue
        previous = None
        for name, rows in common.alias_chain(index, value):
            owner_is_tree = previous is None or (previous in tree_index and (stock_sound is None or any(
                (r['Name'], clean_file(r.get('File'))) not in stock_sound.pairs for r in tree_index[previous])))
            previous = name
            if rows or name in seen:
                seen.add(name)
                continue
            seen.add(name)
            # a layer that hangs off an unchanged stock row belongs to the stock zone that defines the chain: not ours to judge
            named_by_stock = stock_sound is not None and (name in stock_sound.named or not owner_is_tree)
            (elsewhere if named_by_stock or stock_sound is None else missing).append((slot, name))
    for slot, name in missing:
        # a warning, not an error: absence from a dump is never proof (the dump may lack the zone that defines it)
        report.add('warn', 'SND-ALIAS-MISSING', item,
                   'sfxpkg names alias "%s" (%s) but no alias list of the tree or of the stock dump given defines it, '
                   'and no stock package uses that name' % (name, slot),
                   notice='if no loaded zone defines it, this sound of the weapon is silent', proof='engine',
                   source='stock', alias=name, slot=slot)
        report.ask('hear', item, 'is the sound %s (%s) heard?' % (name, slot),
                   'no file given to the audit defines that alias', alias=name, slot=slot)
    if elsewhere:
        names = ', '.join(sorted({n for _, n in elsewhere})[:5])
        if stock_sound is None:
            report.add('info', 'SND-ALIAS-NOT-IN-DUMP', item,
                       '%d aliases are in no alias list of the tree and no stock dump was given, so they cannot be '
                       'checked (%s)' % (len(elsewhere), names), count=len(elsewhere))
        else:
            report.add('info', 'SND-ALIAS-NOT-IN-DUMP', item,
                       '%d aliases are in no alias list of the tree or of the dump, but stock packages use them: they '
                       'belong to a stock zone that is not in the dump (%s)' % (len(elsewhere), names),
                       count=len(elsewhere))


def _fire_rules(report, item, root, chain, stock_sound, volumes):
    """S5, S6, S9 for one player fire chain."""
    rows = chain[0][1] if chain else []
    if not rows or stock_sound is None:
        return
    shared = shared_channels(chain)
    if shared:
        total = len(stock_sound.chains)
        share = stock_sound.sharing / total if total else 0.0
        channel, names = sorted(shared.items(), key=lambda kv: -len(kv[1]))[0]
        text = '%s: %d layers of the shot, %d of them on channel %s (%s); %d of %d stock chains (%.1f %%) share a channel' % (
            root, len(chain), len(names), channel, ', '.join(names), stock_sound.sharing, total, 100 * share)
        notice = 'the layers of the shot cut each other off: only one is heard'
        evidence = dict(alias=root, channel=channel, layers=names, stock_chains=total,
                        stock_sharing=stock_sound.sharing, stock_multi_layer_chains=len(stock_sound.multi),
                        stock_multi_layer_sharing=stock_sound.sharing_multi)
        if total and share < RARE_SHARE:
            report.add('warn', 'SND-LAYERS-ONE-CHANNEL', item, text, notice=notice, proof='engine', source='stock',
                       **evidence)
            report.ask('hear', item, 'are all layers of the player shot of %s heard, or does one cut off the rest?' % root,
                       'several layers of the shot use the channel %s and stock almost never does that' % channel,
                       alias=root, channel=channel)
        else:
            report.add('info', 'SND-LAYERS-ONE-CHANNEL', item, text, source='stock', **evidence)
    for kind in sorted({r.get('type', '') for r in rows if r.get('type')}):
        share = stock_sound.type_share(kind)
        if share is not None and share < RARE_SHARE:
            report.add('warn', 'SND-FIRE-TYPE-RARE', item,
                       '%s: the root shot row is type %s; %.1f %% of stock player shots are (%s)' % (
                           root, kind, 100 * share, ', '.join('%s %d' % kv for kv in sorted(stock_sound.type_counts.items()))),
                       notice='the shot loads differently from stock shots: its start may come late or be cut',
                       proof='engine', source='stock', alias=root, type=kind, stock_share=round(share, 4))
            report.ask('hear', item, 'does the first shot of %s start at once?' % root,
                       'the root row type %s is rare among stock shots' % kind, alias=root, type=kind)
    if volumes is not None and volumes.n:
        volume = max((common.number(r.get('vol_max'), 0.0) for r in rows), default=0.0)
        report.add('info', 'SND-FIRE-VOLUME-POSITION', item,
                   '%s: root vol_max %s; %s; position %s' % (root, common.fmt(volume), volumes.describe(),
                                                            volumes.position(volume)),
                   source='stock', alias=root, value=volume, stock_median=volumes.median,
                   stock_min=volumes.min, stock_max=volumes.max, position=volumes.position(volume))


def _levels(report, zone_dir, levels, unmeasured, measure, reference):
    """S4: record, compare, and say plainly what could not be measured."""
    for item in sorted(levels):
        shown = ', '.join('%s %.1f dBFS' % (alias, value) for alias, value in sorted(levels[item].items()))
        report.add('info', 'SND-FIRE-LEVEL', item, 'player shot level (mean sample level plus alias volume, layers '
                   'summed): %s' % shown, levels=levels[item])
    loudest = max((v for per in levels.values() for v in per.values()), default=None)
    for item in sorted(levels):
        for alias, value in sorted(levels[item].items()):
            reasons = {}
            if reference is not None and value < reference - QUIET_DB:
                reasons['below_reference_db'] = round(reference - value, 1)
            if loudest is not None and value < loudest - QUIET_DB:
                reasons['below_loudest_db'] = round(loudest - value, 1)
            if not reasons:
                continue
            parts = []
            if 'below_reference_db' in reasons:
                parts.append('%.1f dB below the reference %.1f' % (reasons['below_reference_db'], reference))
            if 'below_loudest_db' in reasons:
                parts.append('%.1f dB below the loudest shot of this tree (%.1f)' % (reasons['below_loudest_db'], loudest))
            report.add('warn', 'SND-FIRE-QUIET', item, '%s: player shot level %.1f dBFS, %s' % (
                alias, value, ' and '.join(parts)),
                notice='the weapon fires much quieter than the reference: it may sound weak or missing',
                proof='engine', alias=alias, level_db=value, reference_db=reference, loudest_db=loudest, **reasons)
            report.ask('hear', item, 'is the shot of %s as loud as the other weapons?' % alias,
                       'its measured level is far below the reference', alias=alias, level_db=value)
    if unmeasured:
        why = ('measuring was switched off' if measure is None else
               'a sample is absent, not readable, or the stock alias has no file in this tree')
        report.add('info', 'SND-LEVEL-NOT-MEASURED', os.path.basename(zone_dir),
                   'shot level not measured for %d weapons (%s)' % (len(unmeasured), why),
                   notice='nothing is claimed about how loud these shots are', weapons=sorted(unmeasured))


def main(argv=None):
    ap = argparse.ArgumentParser(description='Weapon sound audit: do the sounds load, and are they set up like stock?')
    ap.add_argument('tree', help='zonetool source tree of the mod (folder holding weapons/, sound/, ...)')
    ap.add_argument('--item', action='append', default=[], help='only this weapon (repeatable)')
    ap.add_argument('--bank', action='append', default=[], metavar='FILE', help='compiled .sabl or .sabs (repeatable)')
    ap.add_argument('--loads-as', metavar='NAME', help='the zone name the game asks for (for example mod)')
    ap.add_argument('--fire-reference-db', type=float, metavar='DBFS',
                    help='level of a shot you consider right; a player shot 6 dB below it is flagged')
    ap.add_argument('--no-measure', action='store_true', help='do not run ffmpeg; levels are then not measured')
    common.add_common_args(ap)
    args = ap.parse_args(argv)
    zone_dir = common.locate_zone_dir(args.tree)
    stock = common.stock_from_args(args)
    intent = common.Intent.load(args.intent) if args.intent else common.Intent()
    report = audit(zone_dir, stock, intent, items=args.item or None, banks=args.bank, loads_as=args.loads_as,
                   fire_reference_db=args.fire_reference_db, measure=False if args.no_measure else None)
    return common.finish(report, args, intent=intent)


if __name__ == '__main__':
    sys.exit(main())
