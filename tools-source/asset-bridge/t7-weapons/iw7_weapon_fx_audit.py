#!/usr/bin/env python3
"""Weapon effect audit: which effects does each weapon really play, do they exist, were they converted
completely, and is any of them a stock effect in disguise? Stdlib only.

It reads the particle systems (.iw7VFX, decoded by iw7_vfx) a weapon names and compares them with the stock
effects of a local dump. It never predicts how an effect looks: a trail whose settings are a copy of a stock
trail is a FACT, whether it looks wrong is a question for the running game (proof 'engine' + an engine question).

Findings (prefix FX):
    FX-UNREFERENCED     info  effect files no audited weapon reaches
    FX-MISSING          warn  a named effect is in no file of the tree or of the dump and no stock asset uses the name
                              (absence from a dump is never proof: the engine or the build log settles it)
    FX-NOT-IN-DUMP      info  a named effect or reference is not in the dump but stock itself uses the name
    FX-STOCK-COPY       warn  a ribbon / beam / tail (or a whole effect) has the settings of a stock one (engine)
    FX-STOCK-COPY-OTHER info  other element types that equal a stock element
    FX-SIZE-EXTREME     warn  an element is bigger than any stock element of its type (engine)
    FX-LIFE-EXTREME     warn  a particle lives longer than any stock particle of its type (engine)
    FX-SIZE-RANGE       info  elements outside the central stock band of their type
    FX-LIFE-RANGE       info  same for particle life
    FX-PARITY-SKIPPED   warn  --port: the converter left elements of the original out (engine)
    FX-PARITY-COUNT     warn  --port: the report says N emitters, the file in the tree has another count
    FX-PARITY-NO-COUNTERPART warn --port: the port names an effect that neither the report nor the tree holds
    FX-REF-MISSING      warn  a material / model / child effect is in no file given (same rule)
    FX-REF-NOT-IN-DUMP  info  same, but stock effects use the name
    FX-NO-CHILD-LINKS   info  no effect of the tree links a child effect
    FX-BAD-FILE         error an effect file does not decode
    FX-NO-STOCK         info  no stock dump: copy and size rules were skipped

How a stock copy is told. Every emitter ("element") is reduced to its decoded settings with every asset name
(material, model, child effect, light, sound) removed. A port keeps the skeleton of the stock template it was made
from and only overwrites the look (colours, sizes, intensity graphs, spawn range), so two hashes are kept:
  full      the whole element; equal = the element IS the stock element apart from names
  settings  the element without INIT_ATTRIBUTES, colour/size/intensity/emission graphs, spawn range and seed;
            equal = timing, life, spawn, ribbon geometry, velocity and gravity are the stock ones
A tree effect whose file is byte-equal to the stock file of the same name is stock itself and is not judged.
"""
import argparse
import hashlib
import json
import os
import sys
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import iw7_audit_common as common  # noqa: E402
import iw7_vfx  # noqa: E402

TOOL = 'weapon-fx-audit'
PREFIX = 'FX'
GROUPS = ('effects',)

EXT = '.iw7VFX'
ELEMENT_PREFIX = 'PARTICLE_ELEMENT_TYPE_'
MODULE_PREFIX = 'PARTICLE_MODULE_'
# element types where a copy of a stock element matters visually, with the noun used in messages
COPY_TYPES = {'GEO_TRAIL': 'ribbon', 'BEAM': 'beam', 'TAIL': 'tail'}
SIZED_TYPES = ('BILLBOARD_SPRITE', 'ORIENTED_SPRITE', 'TAIL', 'GEO_TRAIL')
# names of the asset slots of the linked-asset unions, by what they point at
REF_KIND = {'material': 'material', 'material0': 'material', 'material1': 'material', 'material2': 'material',
            'model': 'model', 'particleSystem': 'effect'}
NAME_KEYS = frozenset(('material', 'material0', 'material1', 'material2', 'model', 'particleSystem', 'lightDef',
                       'sound', 'vectorField', 'physicsFXPipeline', 'physicsFXShape', 'particleSim'))
# modules that carry the look a port overwrites (colour, size, intensity); not part of the settings hash
LOOK_MODULES = frozenset(MODULE_PREFIX + n for n in (
    'INIT_ATTRIBUTES', 'COLOR_GRAPH', 'COLOR_LERP', 'INTENSITY_GRAPH', 'EMISSION_GRAPH', 'EMISSIVE_GRAPH',
    'SIZE_GRAPH', 'SIZE_LERP'))
LOOK_EMITTER_KEYS = ('spawnRangeSq', 'randomSeed')
LIST_LIMIT = 6
MATCH_LIMIT = 8


# ------------------------------------------------------------------ decoded effect -> facts
def _short(text, prefix):
    return text[len(prefix):] if isinstance(text, str) and text.startswith(prefix) else text


def _norm(node, look=False, emitter=False):
    """The decoded node without pointers, asset names (and, with look, the overwritten look)."""
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            if key.endswith('@ptr') or key in NAME_KEYS:
                continue
            if look and emitter and key in LOOK_EMITTER_KEYS:
                continue
            out[key] = _norm(value, look)
        return out
    if isinstance(node, list):
        if look:
            node = [x for x in node if not (isinstance(x, dict) and x.get('moduleType') in LOOK_MODULES)]
        return [_norm(x, look) for x in node]
    return node


def _hash(node):
    return hashlib.sha1(json.dumps(node, sort_keys=True, default=str).encode()).hexdigest()


def _num(value):
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _emitter_size(emitter):
    """Crude peak size: largest INIT_ATTRIBUTES size and largest SIZE_GRAPH value times its scale."""
    size = 0.0
    for state in emitter.get('stateDefs') or []:
        for group in state.get('moduleGroupDefs') or []:
            for module in group.get('moduleDefs') or []:
                kind = module.get('moduleType')
                if kind == MODULE_PREFIX + 'INIT_ATTRIBUTES':
                    sizes = [_num(x) for x in (module['initAttributes'].get('m_sizeMax') or [])[:3]]
                    size = max([size] + [x for x in sizes if x is not None])
                elif kind == MODULE_PREFIX + 'SIZE_GRAPH':
                    for curve in module['sizeGraph'].get('m_curves') or []:
                        scale = _num(curve.get('scale'))
                        scale = 1.0 if scale is None else scale
                        values = [_num(p.get('value')) for p in curve.get('controlPoints') or []]
                        values = [x for x in values if x is not None]
                        if values:
                            size = max(size, max(values) * scale)
    return size


def analyse(model):
    """Facts of one decoded effect: {'flags', 'whole', 'emitters': [...], 'refs': {kind: [names]}}."""
    system = model['system']
    emitters, refs = [], {'material': set(), 'model': set(), 'effect': set()}
    for index, emitter in enumerate(system.get('emitterDefs') or []):
        states = emitter.get('stateDefs') or []
        etype = _short(states[0].get('elementType'), ELEMENT_PREFIX) if states else None
        mine = {'material': [], 'model': [], 'effect': []}
        for state in states:
            for group in state.get('moduleGroupDefs') or []:
                for module in group.get('moduleDefs') or []:
                    for field, name in iw7_vfx.linked_assets(module):
                        kind = REF_KIND.get(field)
                        if kind and isinstance(name, str) and name:
                            mine[kind].append(name)
                            refs[kind].add(name)
        life = _num((emitter.get('particleLife') or {}).get('max'))
        emitters.append({'index': index, 'type': etype if isinstance(etype, str) else None,
                         'full': _hash(_norm(emitter, False, True)), 'settings': _hash(_norm(emitter, True, True)),
                         'size': _emitter_size(emitter), 'life': life, 'refs': mine})
    flags = system.get('flags')
    return {'flags': flags, 'emitters': emitters, 'refs': {k: sorted(v) for k, v in refs.items()},
            'whole': _hash([flags, [e['full'] for e in emitters]])}


def decode_file(path):
    with open(path, 'rb') as handle:
        return iw7_vfx.decode(handle.read())


# ------------------------------------------------------------------ stock
class StockFx:
    """Everything the audit needs from the stock dump, computed once per run from the dump itself."""

    def __init__(self, stock):
        started = time.time()
        self.files = {}                      # effect name -> path of the first zone that has it
        self.copies = {}                     # effect name -> every path (several zones may hold one name)
        self.settings, self.full, self.whole = {}, {}, {}
        self.referenced = set()              # names stock effects point at (materials, models, children)
        self.used_effects = set()            # effect names stock weapons / packages / stock effects name
        self.unreadable = 0
        sizes, lives = {}, {}
        for _, name, path in stock.paths('particlesystem', EXT):
            self.files.setdefault(name, path)
            self.copies.setdefault(name, []).append(path)
        for name, path in sorted(self.files.items()):
            try:
                facts = analyse(decode_file(path))
            except Exception:                # a truncated dump file must not stop the audit
                self.unreadable += 1
                continue
            for kind in facts['refs']:
                self.referenced.update(facts['refs'][kind])
            self.used_effects.update(facts['refs']['effect'])
            self.whole.setdefault(facts['whole'], []).append(name)
            for emitter in facts['emitters']:
                key = (name, emitter['index'])
                self.full.setdefault(emitter['full'], []).append(key)
                self.settings.setdefault(emitter['settings'], []).append(key)
                etype = emitter['type']
                if etype in SIZED_TYPES:
                    sizes.setdefault(etype, []).append(emitter['size'])
                    if emitter['life'] is not None:
                        lives.setdefault(etype, []).append(emitter['life'])
        for folder in ('weapons', 'vfxpkg'):
            for _, _, doc in stock.docs(folder):
                self.used_effects.update(effect_strings(doc))
        self.sizes = {t: common.Population(v) for t, v in sizes.items()}
        self.lives = {t: common.Population(v) for t, v in lives.items()}
        self.seconds = round(time.time() - started, 1)

    def uses(self, name):
        return name in self.used_effects or name in self.referenced


def effect_strings(doc):
    """{effect name: [dotted path]} of every string leaf that names an effect (vfx/...)."""
    out = {}
    for path, value in common.leaves(doc).items():
        if isinstance(value, str) and value.startswith('vfx/'):
            out.setdefault(value, []).append(path)
    return out


# ------------------------------------------------------------------ tree
def stems(base):
    """Names (relative path without extension, '/' separated) of the files below a folder."""
    out = set()
    for here, _, names in os.walk(base):
        for name in names:
            out.add(os.path.relpath(os.path.join(here, os.path.splitext(name)[0]), base).replace(os.sep, '/'))
    return out


class FxTree:
    def __init__(self, zone_dir):
        self.zone_dir = zone_dir
        self.files = {}
        base = os.path.join(zone_dir, 'particlesystem')
        for here, _, names in os.walk(base):
            for name in sorted(names):
                if name.endswith(EXT):
                    full = os.path.join(here, name)
                    self.files[os.path.relpath(full, base).replace(os.sep, '/')[:-len(EXT)]] = full
        self._stems, self._models, self._facts = {}, {}, {}

    def has(self, folder, name):
        if folder not in self._stems:
            self._stems[folder] = stems(os.path.join(self.zone_dir, folder))
        return name in self._stems[folder]

    def model(self, name):
        """(decoded model, None) or (None, error text)."""
        if name not in self._models:
            try:
                self._models[name] = (decode_file(self.files[name]), None)
            except Exception as error:
                self._models[name] = (None, str(error))
        return self._models[name]


class StockNames:
    """Existence of stock files by folder (materials and models are only known when the dump holds them)."""

    def __init__(self, stock):
        self.stock, self._stems = stock, {}

    def has(self, folder, name):
        if folder not in self._stems:
            found = set()
            for zone in self.stock.zones.values():
                found |= stems(os.path.join(zone, folder))
            self._stems[folder] = found
        return name in self._stems[folder]


# ------------------------------------------------------------------ wiring of a weapon
def named_effects(zone_dir, item, documents, weapons, behaviours):
    """{effect name: [role]} the weapon plays: its file, its package, behaviours.txt, and the weapons it names."""
    out = {}

    def add(doc, label):
        for effect, paths in effect_strings(doc).items():
            for path in paths:
                role = path[:-3] if path.endswith('.fx') else path
                out.setdefault(effect, []).append((label + ' ' if label else '') + role)

    for kind in ('weapon', 'vfxpkg'):
        if isinstance(documents.get(kind), dict):
            add(documents[kind], '')
    for entry in behaviours.get(item, ()):
        for key, effect in sorted((entry.get('effects') or {}).items()):
            if isinstance(effect, str) and effect:
                out.setdefault(effect, []).append('behaviours.txt ' + key)
    for value in common.leaves(documents.get('weapon') or {}).values():
        if isinstance(value, str) and value in weapons and value != item:
            other = common.load_json(os.path.join(zone_dir, 'weapons', value + '.json'))
            add(other, 'via ' + value)
            pkg = common.package_refs(other).get('vfxpkg')
            path = os.path.join(zone_dir, 'vfxpkg', pkg + '.json') if pkg else None
            if path and os.path.isfile(path):
                add(common.load_json(path), 'via ' + value)
    return out


def behaviours_by_weapon(zone_dir):
    path = os.path.join(zone_dir, 'behaviours.txt')
    try:
        # read_behaviours wants an indexed Tree; only its 'loose' file table is used, so a stand-in avoids walking
        # every folder of the zone
        entries = common.read_behaviours(types.SimpleNamespace(loose={'behaviours.txt': path}))             if os.path.isfile(path) else []
    except (OSError, ValueError):
        entries = []
    out = {}
    for entry in entries:
        out.setdefault(entry.get('weapon'), []).append(entry)
    return out


def basename(name):
    return name.rsplit('/', 1)[-1]


def listing(names, limit=LIST_LIMIT):
    names = list(names)
    text = ', '.join(names[:limit])
    return text + (' and %d more' % (len(names) - limit) if len(names) > limit else '')


# ------------------------------------------------------------------ the audit
def audit(zone_dir, stock, intent, items=None, ports=(), **options):
    """Return a common.Report for the tree. No printing, no exit."""
    started = time.time()
    report = common.Report(TOOL, zone_dir)
    intent.report_problems(report)
    tree = FxTree(zone_dir)
    weapons = set(common.weapon_names(zone_dir))
    behaviours = behaviours_by_weapon(zone_dir)
    facts, wiring = {}, {}
    for item in (items or common.weapon_names(zone_dir)):
        judge, documents, templates = common.judge_weapon(zone_dir, item, intent, stock)
        facts[item] = common.template_facts(templates)
        judge.report(report, PREFIX, only=GROUPS)
        wiring[item] = named_effects(zone_dir, item, documents, weapons, behaviours)
    report.facts['templates'] = facts

    sfx = StockFx(stock) if stock else None
    stock_names = StockNames(stock) if stock else None
    if sfx is None:
        report.add('info', 'FX-NO-STOCK', os.path.basename(zone_dir),
                   'no stock dump given: copy and size comparisons were skipped and a missing name cannot be told '
                   'from a stock one', notice='nothing here says whether an effect is the stock one in disguise')
    else:
        report.facts['stock'] = {'effects': len(sfx.files), 'unreadable': sfx.unreadable, 'seconds': sfx.seconds,
                                 'elements': sum(len(v) for v in sfx.full.values())}

    # ---- reachability (X1) and X2: missing named effects
    reach, decoded_errors = {}, set()
    for item, effects in sorted(wiring.items()):
        seen, stack = set(), sorted(effects)
        while stack:
            name = stack.pop()
            if name in seen:
                continue
            seen.add(name)
            if name in tree.files:
                model, error = tree.model(name)
                if error:
                    decoded_errors.add(name)
                else:
                    stack.extend(analyse(model)['refs']['effect'])
        reach[item] = seen
        _missing(report, item, effects, seen, tree, sfx, stock)
    report.facts['effects'] = {item: sorted(names) for item, names in reach.items()}
    reached = set().union(*reach.values()) if reach else set()
    loose = sorted(set(tree.files) - reached)
    if loose:
        report.add('info', 'FX-UNREFERENCED', os.path.basename(zone_dir),
                   '%d effect file(s) of the tree are reached by no audited weapon (first %d: %s)' % (
                       len(loose), min(10, len(loose)), ', '.join(loose[:10])),
                   notice='these effects are built into the mod but never played by the audited weapons',
                   count=len(loose), first=loose[:10])
    for name in sorted(decoded_errors):
        report.add('error', 'FX-BAD-FILE', name, 'the effect file does not decode: %s' % tree.model(name)[1],
                   notice='the game cannot load this effect')

    # ---- the effects of the tree itself
    own = {}
    for name in sorted(reached & set(tree.files) - decoded_errors):
        if sfx is not None and any(_same_bytes(tree.files[name], p) for p in sfx.copies.get(name, ())):
            continue                                     # byte-equal to a stock file of that name: it IS stock
        own[name] = analyse(tree.model(name)[0])
    report.facts['own_effects'] = sorted(own)
    child_links = 0
    for name, info in own.items():
        child_links += len(info['refs']['effect'])
        _references(report, name, info, tree, sfx, stock, stock_names)
        if sfx is not None:
            _stock_copy(report, name, info, sfx)
            _size_and_life(report, name, info, sfx)
    child_total = child_links + sum(len(analyse(tree.model(n)[0])['refs']['effect'])
                                    for n in reached & set(tree.files) - decoded_errors if n not in own)
    report.facts['child_links'] = child_total

    # ---- port parity (X5) and the child links
    converted_unreached = set()
    for port in ports or ():
        converted_unreached |= _parity(report, port, tree, sfx, reached)
    if not child_total and own and converted_unreached:
        report.add('info', 'FX-NO-CHILD-LINKS', os.path.basename(zone_dir),
                   'no effect of the tree links another effect, yet the port converted %d effect(s) that no audited '
                   'weapon reaches (%s): they were probably child effects of the originals' % (
                       len(converted_unreached), listing(sorted(converted_unreached), 4)),
                   notice='a secondary effect of the original weapon (for example a ring around a trail) is built '
                          'but never played',
                   unreached=sorted(converted_unreached))
    report.facts['seconds'] = round(time.time() - started, 1)
    return report


def _same_bytes(a, b):
    try:
        if os.path.getsize(a) != os.path.getsize(b):
            return False
        with open(a, 'rb') as x, open(b, 'rb') as y:
            return x.read() == y.read()
    except OSError:
        return False


def _missing(report, item, effects, reached, tree, sfx, stock):
    """X2: a named effect that is neither a tree file nor a stock file."""
    gone, unknown = [], []
    for name in sorted(effects):
        if name in tree.files or (sfx is not None and name in sfx.files):
            continue
        (unknown if sfx is not None and sfx.uses(name) else gone).append(name)
    for name in sorted(reached - set(effects)):          # a child effect link that leads nowhere
        if name not in tree.files and not (sfx is not None and name in sfx.files):
            (unknown if sfx is not None and sfx.uses(name) else gone).append(name)
    roles = {n: effects.get(n, ['child effect link']) for n in gone + unknown}
    if gone:
        # with a dump: a warning for the engine, not an error (the dump may lack the zone that holds the effect)
        severity = 'warn' if sfx is not None else 'info'
        why = '' if sfx is not None else ' (no stock dump: a stock effect cannot be told from a missing one)'
        report.add(severity, 'FX-MISSING', item,
                   '%d effect(s) named by the weapon are neither in the tree nor in the stock dump given, and no stock '
                   'asset uses the name: %s%s' % (
                       len(gone), '; '.join('%s (%s)' % (n, roles[n][0]) for n in gone[:LIST_LIMIT]), why),
                   notice='if no loaded zone holds the effect, nothing shows where the weapon plays it',
                   proof='engine' if sfx is not None else 'data', effects=gone)
        if sfx is not None:
            for name in gone[:LIST_LIMIT]:
                report.ask('see', item, 'does the effect %s (%s) show?' % (name, roles[name][0]),
                           'no file given to the audit holds that effect', effect=name)
    if unknown:
        report.add('info', 'FX-NOT-IN-DUMP', item,
                   '%d effect(s) are not in the dump but stock uses the name, so another stock zone holds them: %s' % (
                       len(unknown), listing(unknown)), effects=unknown)


def _references(report, effect, info, tree, sfx, stock, stock_names):
    """X6: materials, models and child effects an effect of the tree names."""
    folders = {'material': ('materials', 'material'), 'model': ('xmodel', 'model'),
               'effect': (None, 'child effect')}
    for kind, (folder, noun) in folders.items():
        gone, unknown = [], []
        for name in info['refs'][kind]:
            if kind == 'effect':
                if name in tree.files or (sfx is not None and name in sfx.files):
                    continue
            elif tree.has(folder, name) or (stock_names is not None and stock_names.has(folder, name)):
                continue
            (unknown if sfx is not None and sfx.uses(name) else gone).append(name)
        if gone:
            report.add('warn' if sfx is not None else 'info', 'FX-REF-MISSING', effect,
                       '%d %s(s) named by the effect are neither in the tree nor in the stock dump given: %s%s' % (
                           len(gone), noun, listing(gone),
                           '' if sfx is not None else ' (no stock dump: cannot tell a stock name from a missing one)'),
                       notice='if no loaded zone holds them, part of the effect is invisible or shows the default '
                              'checker image',
                       proof='engine' if sfx is not None else 'data', kind=kind, names=gone)
            if sfx is not None:
                report.ask('see', effect, 'does the whole effect show, with its own %s(s)?' % noun,
                           'no file given to the audit holds %s' % listing(gone), reference=kind, names=gone)
        if unknown:
            report.add('info', 'FX-REF-NOT-IN-DUMP', effect,
                       '%d %s(s) are not in the dump but stock effects use the name: %s' % (
                           len(unknown), noun, listing(unknown)), kind=kind, names=unknown)


def _stock_copy(report, effect, info, sfx):
    """X3: elements (and whole effects) that equal a stock one."""
    twins = [n for n in sfx.whole.get(info['whole'], ()) if n != effect]
    if twins and info['emitters']:
        report.add('warn', 'FX-STOCK-COPY', effect,
                   'the whole effect is identical to the stock effect %s (every element, setting for setting)' %
                   listing([basename(n) for n in twins], 4),
                   notice='this effect looks and behaves exactly like a stock effect', proof='engine',
                   stock=twins[:MATCH_LIMIT], level='whole effect')
        report.ask('see', effect, 'does %s look like something made for this weapon rather than the stock %s?' % (
            basename(effect), basename(twins[0])), 'the whole effect equals a stock effect', effect=effect,
                   stock=twins[0])
        return
    other_same = other_total = 0
    for element in info['emitters']:
        matches = [k for k in sfx.settings.get(element['settings'], ()) if k[0] != effect]
        etype = element['type']
        if etype in COPY_TYPES:
            if not matches:
                continue
            exact = [k for k in sfx.full.get(element['full'], ()) if k[0] != effect]
            names = []
            for stock_effect, _ in exact + matches:
                if stock_effect not in names:
                    names.append(stock_effect)
            noun = COPY_TYPES[etype]
            if exact:
                how = 'identical in every setting'
            else:
                how = 'same timing, life, spawn, shape and velocity; only colours, sizes and materials differ'
            report.add('warn', 'FX-STOCK-COPY', effect,
                       'the %s (element %d) of %s is setting-for-setting the stock %s %s (%s)' % (
                           noun, element['index'], effect, 'trail' if etype == 'GEO_TRAIL' else noun,
                           listing([basename(n) for n in names], 4), how),
                       notice='the %s was not designed for this weapon: it behaves exactly like the stock one, '
                              'which is how a stray beam or ribbon can appear' % noun,
                       proof='engine', element=element['index'], element_type=etype, stock=names[:MATCH_LIMIT],
                       level='identical' if exact else 'settings')
            report.ask('see', effect, 'does the %s of %s read as this weapon\'s own effect, with no stray line or '
                                      'beam, in the hand and in flight?' % (noun, basename(effect)),
                       'its %s settings are a copy of the stock %s' % (noun, basename(names[0])),
                       effect=effect, element=element['index'], stock=names[0])
        else:
            other_total += 1
            other_same += 1 if matches else 0
    if other_same:
        report.add('info', 'FX-STOCK-COPY-OTHER', effect,
                   '%d of %d other element(s) (sprites, lights, ...) have the settings of a stock element' % (
                       other_same, other_total), count=other_same)


def _size_and_life(report, effect, info, sfx):
    """X4: crude peak size and longest particle life against the stock population of the same element type."""
    for metric, populations, code, label in (('size', sfx.sizes, 'SIZE', 'peak size'),
                                             ('life', sfx.lives, 'LIFE', 'particle life')):
        extreme, outside = [], []
        for element in info['emitters']:
            population = populations.get(element['type'])
            value = element[metric]
            if population is None or not population.n or value is None:
                continue
            position = population.position(value)
            row = (element['index'], element['type'], value, population)
            if position == 'above-all':
                extreme.append(row)
            elif position in ('high', 'low', 'below-all'):
                outside.append((row, position))
        if extreme:
            worst = max(extreme, key=lambda r: r[2] / (r[3].max or 1.0))
            index, etype, value, population = worst
            report.add('warn', 'FX-%s-EXTREME' % code, effect,
                       '%s of element %d (%s) is %s, above every stock %s (%s)' % (
                           label, index, etype.lower(), common.fmt(value), etype.lower(), population.describe()),
                       notice='bigger or longer-lived than anything the game itself uses for this kind of element',
                       proof='engine', element=index, value=value, stock_max=population.max,
                       stock_median=population.median, count=len(extreme))
            report.ask('see', effect, 'is %s of %s as big/long as intended (element %d, %s)?' % (
                label, basename(effect), index, common.fmt(value)),
                       'the value is above the stock maximum for its element type', effect=effect, element=index)
        elif outside:
            highs = [r for r, p in outside if p in ('high',)]
            lows = [r for r, p in outside if p != 'high']
            lead = max(highs, key=lambda r: r[2]) if highs else None
            text = '%d element(s) outside the central stock band of their type for %s' % (len(outside), label)
            if lead:
                text += '; highest: element %d (%s) %s, %s' % (
                    lead[0], lead[1].lower(), common.fmt(lead[2]), lead[3].describe())
            report.add('info', 'FX-%s-RANGE' % code, effect, text, high=len(highs), low=len(lows),
                       value=lead[2] if lead else None, stock_median=lead[3].median if lead else None)


def _parity(report, port_dir, tree, sfx, reached):
    """X5: compare the converter's own report with the tree. Returns the effects it converted that nothing reaches."""
    path = os.path.join(port_dir, 'fx_report.json')
    name = os.path.basename(os.path.normpath(port_dir))
    try:
        entries = common.load_json(path)
    except (OSError, ValueError) as error:
        report.add('error', 'FX-PARITY-NO-REPORT', name, 'no readable fx_report.json in the port folder: %s' % error,
                   notice='the conversion cannot be compared with the original')
        return set()
    if not isinstance(entries, list):
        report.add('error', 'FX-PARITY-NO-REPORT', name, 'fx_report.json is not a list of effects')
        return set()
    listed, unreached = set(), set()
    for entry in entries:
        effect = entry.get('effect') if isinstance(entry, dict) else None
        if not isinstance(effect, str):
            continue
        listed.add(effect)
        skipped = entry.get('skipped') or []
        built = entry.get('emitters')
        if effect not in tree.files:
            report.add('warn', 'FX-PARITY-NO-COUNTERPART', effect,
                       'the port report lists this effect (%s emitters) but the tree holds no file for it' % built,
                       notice='an effect the converter built is not in the mod')
            continue
        if effect not in reached:
            unreached.add(effect)
        if skipped:
            parts = ['element %s: %s' % (s.get('element', '?'), s.get('reason', '?')) for s in skipped
                     if isinstance(s, dict)]
            report.add('warn', 'FX-PARITY-SKIPPED', effect,
                       '%d element(s) of the original were not converted (%s); %s emitters were built' % (
                           len(skipped), '; '.join(parts[:LIST_LIMIT]), built),
                       notice='part of the original effect is missing in game', proof='engine',
                       skipped=skipped, emitters=built)
            report.ask('see', effect, 'does %s still read as the original effect with %d element(s) missing?' % (
                basename(effect), len(skipped)), 'the converter skipped part of the original', effect=effect)
        model, error = tree.model(effect)
        if model is not None:
            count = len(model['system'].get('emitterDefs') or [])
            if isinstance(built, int) and built != count:
                report.add('warn', 'FX-PARITY-COUNT', effect,
                           'the port report says %d emitters were built, the file in the tree has %d' % (built, count),
                           notice='the effect in the mod is not the one the converter reported',
                           report_emitters=built, file_emitters=count)
    named = {}
    for spec in ('spec.json', 'spec_upgraded.json'):
        try:
            doc = common.load_json(os.path.join(port_dir, spec))
        except (OSError, ValueError):
            continue
        for role, entry in ((doc.get('fx') if isinstance(doc, dict) else None) or {}).items():
            if isinstance(entry, dict) and isinstance(entry.get('iw7'), str):
                named.setdefault(entry['iw7'], '%s %s' % (spec, role))
    try:
        with open(os.path.join(port_dir, 'behaviour.txt'), encoding='utf-8', errors='replace') as handle:
            for line in handle:
                parts = line.rstrip('\n').split('|')
                if len(parts) >= 4:
                    for pair in parts[3].split(','):
                        key, _, effect = pair.partition('=')
                        if effect.startswith('vfx/'):
                            named.setdefault(effect, 'behaviour.txt %s' % key)
    except OSError:
        pass
    for effect, where in sorted(named.items()):
        if effect in listed or effect in tree.files or (sfx is not None and effect in sfx.files):
            continue
        report.add('warn', 'FX-PARITY-NO-COUNTERPART', effect,
                   'the port names this effect (%s) but neither its report nor the tree holds it' % where,
                   notice='the weapon is meant to play an effect that was never built')
    return unreached


def main(argv=None):
    ap = argparse.ArgumentParser(description='Which effects does each weapon play, do they exist, were they '
                                             'converted completely, and is any a stock effect in disguise?')
    ap.add_argument('tree', help='zonetool source tree of the mod (folder holding weapons/, particlesystem/, ...)')
    ap.add_argument('--item', action='append', default=[], help='only this weapon (repeatable)')
    ap.add_argument('--port', action='append', default=[], metavar='DIR',
                    help='port folder holding fx_report.json (repeatable): checks the conversion for skipped elements')
    common.add_common_args(ap)
    args = ap.parse_args(argv)
    zone_dir = common.locate_zone_dir(args.tree)
    stock = common.stock_from_args(args)
    intent = common.Intent.load(args.intent) if args.intent else common.Intent()
    report = audit(zone_dir, stock, intent, items=args.item or None, ports=args.port)
    return common.finish(report, args, intent=intent)


if __name__ == '__main__':
    sys.exit(main())
