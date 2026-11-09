#!/usr/bin/env python3
"""Preflight of an assembled IW7 mod zone source tree: seconds, before ZoneTool and before any launch (stdlib only).

    python iw7_mod_preflight.py <zonetool/<zone>> --csv <zone_source/<zone>.csv>
        [--common <csv> ...] [--map NAME=CSV[;CSV] ...]      map-only references (iw7_mod_reference_audit)
        [--state <file>] [--accept [WEAPON ...]]             which weapons changed since they last passed in game
        [--json <file>] [--no-binary]

One pass over the whole tree answers two questions that used to cost a build and a game launch each:

1. Is anything in this tree already known to fail in the game? It runs the existing binary checks on every file
   (iw7_xanim_layout: the long-animation client crash; iw7_xsurface_check: the black model) and adds cross-asset
   rules no single-file tool can see: a zone csv line with no source, a source nothing builds, a weapon field
   naming an asset that is neither in the tree nor in a stock reference list, a catalog or behaviour line naming
   something that is not built, a sound alias with no audio file or absent from the bank, a model wearing a
   two-UV (camo) material on surfaces with no second UV set.
2. Which weapons do I have to look at again? Every catalog entry gets a content hash over everything it reaches
   (weapon, upgrade, attachments, packages, animations, models, surfaces, materials, images, effects, sound rows
   and audio). Compared with the state accepted after the last in-game pass, an unchanged weapon needs no launch.

Nothing here knows a weapon by name: the rules read the tree, the zone csv, catalog.txt and behaviours.txt.
Exit 1 when an error is found, else 0. A warning is a fact to read, not a failure.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = 'iw7.mod-preflight/1'
STATE_SCHEMA = 'iw7.mod-preflight-state/1'
# zone csv type -> (source folder, extension)
TYPES = {
    'weapon': ('weapons', '.json'), 'attachment': ('attachments', '.json'), 'animpkg': ('animpkg', '.json'),
    'sfxpkg': ('sfxpkg', '.json'), 'vfxpkg': ('vfxpkg', '.json'), 'soundbank': ('soundbank', '.json'),
    'material': ('materials', '.json'), 'xmodel': ('xmodel', '.xmb'), 'xanim': ('xanim', '.xab'),
    'vfx': ('particlesystem', '.iw7VFX'), 'image': ('images', '.dds'),
}
FOLDER_TYPE = {folder: kind for kind, (folder, _) in TYPES.items()}
# Weapon definition fields whose value is an asset of a known type (the IW7 weapon schema, not a weapon).
WEAPON_FIELDS = {
    'szXAnims': 'animpkg', 'vfxPackage': 'vfxpkg', 'sfxPackage': 'sfxpkg', 'gunXModel': 'xmodel',
    'worldModel': 'xmodel', 'defaultViewModel': 'xmodel', 'defaultWorldModel': 'xmodel',
    'camoViewModelMaterialOverride': 'material', 'camoWorldModelMaterialOverride': 'material', 'fx': 'vfx',
}
PRINTABLE = re.compile(rb'[\x21-\x7e]{4,}')
ORDER = {'error': 0, 'warn': 1, 'info': 2}


def rel_name(path, base):
    return os.path.splitext(os.path.relpath(path, base).replace(os.sep, '/'))[0]


class Tree:
    """Index of a ZoneTool zone source folder. A key is (folder, name); the name has no extension."""

    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.files = {}
        self.by_name = {}
        self.loose = {}
        self._techsets = None
        self._json = {}
        self._hash = {}
        for entry in sorted(os.listdir(self.root)):
            path = os.path.join(self.root, entry)
            if os.path.isfile(path):
                self.loose[entry] = path
            elif not entry.startswith('techsets'):   # dumped stock techniques: tens of thousands of files, looked up by name
                for base, _, names in os.walk(path):
                    for name in sorted(names):
                        full = os.path.join(base, name)
                        self.files.setdefault((entry, rel_name(full, path)), []).append(full)
        for key in self.files:
            self.by_name.setdefault(key[1], []).append(key)

    def has_techset(self, name):
        if self._techsets is None:
            self._techsets = set()
            folder = os.path.join(self.root, 'techsets')
            if os.path.isdir(folder):
                with os.scandir(folder) as entries:
                    self._techsets = {e.name[:-8] for e in entries if e.name.endswith('.techset')}
        return name in self._techsets

    def json(self, key):
        """Parsed JSON of a key, None when it has none, ValueError text when it does not parse."""
        if key not in self._json:
            value = None
            for path in self.files.get(key, ()):
                if path.endswith('.json'):
                    try:
                        with open(path, encoding='utf-8') as handle:
                            value = json.load(handle)
                    except (OSError, ValueError) as error:
                        value = ValueError(str(error))
            self._json[key] = value
        return self._json[key]

    def digest(self, key):
        if key not in self._hash:
            sha = hashlib.sha256()
            paths = list(self.files.get(key, ()))
            if key[0] == 'techsets':
                base = os.path.join(self.root, 'techsets', key[1] + '.techset')
                paths = [p for p in (base, base + '.txt') if os.path.isfile(p)]
            for path in sorted(paths):
                sha.update(os.path.basename(path).encode())
                with open(path, 'rb') as handle:
                    for block in iter(lambda: handle.read(1 << 20), b''):
                        sha.update(block)
            self._hash[key] = sha.hexdigest()[:20]
        return self._hash[key]


def read_zone_csv(path):
    """(entries [(type, name)], directives [(require|ignore, zone)], duplicates [(type, name, line)])."""
    entries, directives, duplicates, seen = [], [], [], set()
    with open(path, encoding='utf-8', errors='replace') as handle:
        for number, line in enumerate(handle, 1):
            line = line.strip()
            if not line or line.startswith('//') or line.startswith('#'):
                continue
            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 2 or not parts[-1]:
                continue
            kind, name = parts[0], parts[-1]
            if kind in ('require', 'ignore'):
                directives.append((kind, name))
                continue
            if (kind, name) in seen:
                duplicates.append((kind, name, number))
            seen.add((kind, name))
            entries.append((kind, name))
    return entries, directives, duplicates


def read_stock(csv_path, directives):
    """Names the zone csv tells ZoneTool to take from the base game: {type: names}, lists read, lists not found."""
    stock, loaded, missing = {}, [], []
    folder = os.path.dirname(os.path.abspath(csv_path))
    for kind, name in directives:
        if kind != 'ignore':
            continue
        path = os.path.join(folder, name + '.csv')
        if not os.path.isfile(path):
            missing.append(name)
            continue
        loaded.append(name)
        with open(path, encoding='utf-8', errors='replace') as handle:
            for line in handle:
                parts = [p.strip() for p in line.strip().split(',')]
                if len(parts) >= 2 and parts[0] and parts[-1] and not parts[0].startswith('//'):
                    stock.setdefault(parts[0], set()).add(parts[-1])
    return stock, loaded, missing


def read_aliases(tree):
    """Sound alias rows of the per-weapon lists: {alias: [(list key, row text, audio file)]}."""
    aliases = {}
    for key in sorted(tree.files):
        path = tree.files[key][0]
        if key[0] != 'sound' or not path.endswith('.csv'):
            continue
        with open(path, newline='', encoding='utf-8', errors='replace') as handle:
            rows = list(csv.reader(handle))
        if not rows or 'Name' not in rows[0] or 'File' not in rows[0]:
            continue
        name_at, file_at = rows[0].index('Name'), rows[0].index('File')
        for row in rows[1:]:
            if len(row) > max(name_at, file_at) and row[name_at]:
                aliases.setdefault(row[name_at], []).append((key, ','.join(row), row[file_at].strip().replace(chr(92), '/')))
    return aliases


def bank_lists(tree):
    """List files each built sound bank names: {bank key: [path relative to the zone folder]}."""
    out = {}
    for key in sorted(tree.files):
        data = tree.json(key) if key[0] == 'soundbank' else None
        if isinstance(data, dict):
            out[key] = sorted(v for v in strings_of(data) if v.lower().endswith('.csv'))
    return out


def named(table):
    """A package table without its own name field."""
    return {k: v for k, v in table.items() if k != 'name'} if isinstance(table, dict) else table


def strings_of(data):
    stack = [data]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
        elif isinstance(item, str) and item:
            yield item


def typed_refs(folder, data):
    """(asset type, name, field) for the fields of a source JSON whose asset type is known."""
    out = []
    if not isinstance(data, dict):
        return out
    if folder == 'weapons':
        stack = [('', data)]
        while stack:
            field, item = stack.pop()
            if isinstance(item, dict):
                stack.extend(item.items())
            elif isinstance(item, list):
                stack.extend((field, v) for v in item)
            elif isinstance(item, str) and item:
                kind = WEAPON_FIELDS.get(field) or ('attachment' if re.fullmatch(r'attachments\d*', field) else None)
                if kind:
                    out.append((kind, item, field))
    elif folder == 'animpkg':
        out += [('xanim', s, 'anims') for s in strings_of(data.get('anims'))]
    elif folder == 'vfxpkg':
        out += [('vfx', s, 'vfx') for s in strings_of(named(data.get('vfx')))]
    elif folder == 'sfxpkg':
        out += [('alias', s, 'sounds') for s in strings_of(named(data.get('sounds')))]
    elif folder == 'materials':
        if isinstance(data.get('techniqueSet->name'), str) and data['techniqueSet->name']:
            out.append(('techset', data['techniqueSet->name'], 'techniqueSet->name'))
        for entry in data.get('textureTable') or []:
            if isinstance(entry, dict) and isinstance(entry.get('image'), str) and entry['image']:
                out.append(('image', entry['image'], 'textureTable'))
    return out


def binary_names(path):
    with open(path, 'rb') as handle:
        return {m.decode('ascii') for m in PRINTABLE.findall(handle.read())}


class Preflight:
    def __init__(self, zone_dir, csv_path):
        self.tree = Tree(zone_dir)
        self.csv_path = csv_path
        self.entries, self.directives, self.duplicates = read_zone_csv(csv_path)
        self.stock, self.stock_lists, self.stock_missing = read_stock(csv_path, self.directives)
        self.stock_all = set().union(*self.stock.values()) if self.stock else set()
        self.aliases = read_aliases(self.tree)
        self.findings = []
        self.listed, self.roots = set(), set()
        self._edges = {}

    # ---------------------------------------------------------------- helpers
    def add(self, severity, code, asset, message):
        self.findings.append({'severity': severity, 'code': code, 'asset': asset, 'message': message})

    def in_tree(self, kind, name):
        if kind == 'techset':
            return self.tree.has_techset(name)
        if kind == 'alias':
            return name in self.aliases
        return (TYPES[kind][0], name) in self.tree.files

    def in_stock(self, kind, name):
        return name in self.stock.get(kind, ()) or name in self.stock_all

    def edges(self, key):
        """Everything a source file names that this tree also holds."""
        if key in self._edges:
            return self._edges[key]
        out = set()
        folder, name = key
        if folder == 'alias':
            for _, _, audio in self.aliases.get(name, ()):
                if ('sound_assets', audio) in self.tree.files:
                    out.add(('sound_assets', audio))
        elif folder in FOLDER_TYPE:
            names = set()
            data = self.tree.json(key)
            if isinstance(data, (dict, list)):
                names = set(strings_of(data))
                if folder == 'materials' and isinstance(data, dict):
                    techset = data.get('techniqueSet->name')
                    if isinstance(techset, str) and self.tree.has_techset(techset):
                        out.add(('techsets', techset))
            elif folder in ('xmodel', 'particlesystem'):
                for path in self.tree.files.get(key, ()):
                    names |= binary_names(path)
            for value in names:
                for other in self.tree.by_name.get(value, ()):
                    if other != key and other[0] != 'sound' and other[0] != 'soundbank':
                        out.add(other)
                if value in self.aliases and folder in ('sfxpkg', 'weapons', 'attachments'):
                    out.add(('alias', value))
        self._edges[key] = out
        return out

    def closure(self, roots):
        seen, stack = set(), [r for r in roots]
        while stack:
            key = stack.pop()
            if key in seen:
                continue
            seen.add(key)
            stack.extend(self.edges(key) - seen)
        return seen

    def node_digest(self, key):
        if key[0] == 'alias':
            rows = sorted(text for _, text, _ in self.aliases.get(key[1], ()))
            return hashlib.sha256('\n'.join(rows).encode()).hexdigest()[:20]
        return self.tree.digest(key)

    # ---------------------------------------------------------------- catalog and behaviours
    def catalog(self):
        """[{weapon, upgrade, attachments, fire_alias, line}] from catalog.txt, or one entry per weapon file."""
        out = []
        path = self.tree.loose.get('catalog.txt')
        if not path:
            return [{'weapon': name, 'upgrade': None, 'attachments': [], 'fire_alias': None, 'line': name}
                    for folder, name in sorted(self.tree.files) if folder == 'weapons']
        with open(path, encoding='utf-8', errors='replace') as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith('//') or line.startswith('#'):
                    continue
                alias, _, right = line.rpartition('=')
                fields = [f.strip() for f in right.split(':')]
                out.append({'weapon': fields[0], 'upgrade': fields[1] if len(fields) > 1 and fields[1] else None,
                            'attachments': [f for f in fields[2:] if f], 'fire_alias': alias.strip() or None,
                            'line': line})
        return out

    def behaviours(self):
        """[{weapon, namespace, effects {key: vfx}, sounds [alias], line}] from behaviours.txt."""
        out = []
        path = self.tree.loose.get('behaviours.txt')
        if not path:
            return out
        with open(path, encoding='utf-8', errors='replace') as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith('//') or line.startswith('#'):
                    continue
                fields = (line.split('|') + [''] * 5)[:5]
                effects = dict(item.split('=', 1) for item in fields[3].split(',') if '=' in item)
                out.append({'weapon': fields[0].strip(), 'namespace': fields[1].strip(), 'effects': effects,
                            'sounds': [s.strip() for s in fields[4].split(',') if s.strip()], 'line': line})
        return out

    # ---------------------------------------------------------------- checks
    def check_csv(self):
        for kind, name, number in self.duplicates:
            self.add('warn', 'CSV_DUPLICATE', '%s,%s' % (kind, name), 'listed twice in the zone csv (line %d)' % number)
        for name in self.stock_missing:
            self.add('warn', 'STOCK_LIST_MISSING', name,
                     'the zone csv ignores this list but %s.csv is not beside it; stock names from it are unknown' % name)
        listed = set()
        for kind, name in self.entries:
            if kind not in TYPES:
                continue
            key = (TYPES[kind][0], name)
            listed.add(key)
            if key not in self.tree.files:
                self.add('error', 'CSV_NO_SOURCE', '%s,%s' % (kind, name),
                         'the zone csv lists it and the tree holds no %s/%s%s' % (TYPES[kind][0], name, TYPES[kind][1]))
            elif self.in_stock(kind, name):
                self.add('warn', 'SHADOWED_BY_STOCK', '%s,%s' % (kind, name),
                         'an ignored stock list carries the same name: the game may keep its own asset, not this one')
        return listed

    def check_json(self):
        for key in sorted(self.tree.files):
            data = self.tree.json(key)
            if isinstance(data, ValueError):
                self.add('error', 'JSON_INVALID', '/'.join(key), 'does not parse: %s' % data)
            elif key[0] in ('weapons', 'attachments') and isinstance(data, dict):
                inner = data.get('szInternalName')
                if isinstance(inner, str) and inner != key[1]:
                    self.add('error', 'NAME_MISMATCH', '/'.join(key),
                             'file is %s but szInternalName is %s' % (key[1], inner))

    def check_references(self, built):
        unverified = {}
        for key in sorted(built):
            data = self.tree.json(key)
            for kind, name, field in typed_refs(key[0], data if not isinstance(data, ValueError) else None):
                if self.in_tree(kind, name) or self.in_stock(kind, name):
                    continue
                if kind == 'alias' or (kind == 'techset' and not self.stock.get('techset')):
                    unverified.setdefault((key, kind), []).append(name)   # no offline list of stock names of this kind
                elif not self.stock_lists:
                    self.add('warn', 'REFERENCE_UNVERIFIED', '/'.join(key),
                             '%s names %s "%s": not in the tree, and no stock list was read to look it up' % (field, kind, name))
                else:
                    self.add('error', 'REFERENCE_MISSING', '/'.join(key),
                             '%s names %s "%s": not in the tree and in no stock list the zone csv ignores' % (field, kind, name))
        for kind in sorted({k for _, k in unverified}):
            names = sorted({n for (_, k), found in unverified.items() if k == kind for n in found})
            users = sum(1 for _, k in unverified if k == kind)
            self.add('info', 'STOCK_OR_MISSING', kind,
                     '%d %s name(s) used by %d file(s) are not defined by the mod, so the base game must have them: %s'
                     % (len(names), kind, users, ', '.join(names[:10]) + (' ...' if len(names) > 10 else '')))

    def check_sound(self, built):
        banks = bank_lists(self.tree)
        in_bank = set()
        for bank, paths in banks.items():
            for path in paths:
                if os.path.isfile(os.path.join(self.tree.root, path.replace('/', os.sep))):
                    in_bank.add(os.path.splitext(path)[0])
                else:
                    self.add('error', 'BANK_LIST_MISSING', '/'.join(bank),
                             'the bank names %s and the tree has no such file' % path)
        silent = {}
        for alias, rows in sorted(self.aliases.items()):
            for key, _, audio in rows:
                if audio and ('sound_assets', audio) not in self.tree.files and not self.in_stock('sound', audio):
                    self.add('error', 'SOUND_FILE_MISSING', '/'.join(key),
                             'alias %s plays "%s" and sound_assets holds no such file' % (alias, audio))
                if banks and '/'.join(key) not in in_bank and alias not in silent.setdefault(key, []):
                    silent[key].append(alias)
        for key, names in sorted(silent.items()):
            if names:
                self.add('error', 'ALIAS_LIST_NOT_IN_BANK', '/'.join(key),
                         'no built sound bank names this list: its %d alias(es) would be silent (%s%s)'
                         % (len(names), ', '.join(names[:4]), ' ...' if len(names) > 4 else ''))
        used = {key for key in built if key[0] == 'alias'}
        defined_unused = sorted(set(self.aliases) - {key[1] for key in used})
        return defined_unused

    def check_catalog(self, listed, built):
        families = self.catalog()
        if 'catalog.txt' not in self.tree.loose:
            self.add('info', 'NO_CATALOG', 'catalog.txt', 'no catalog: every weapon file is treated as its own entry')
        named = set()
        for entry in families:
            for role, name, folder in ([('weapon', entry['weapon'], 'weapons'), ('upgrade', entry['upgrade'], 'weapons')]
                                       + [('attachment', a, 'attachments') for a in entry['attachments']]):
                if not name:
                    continue
                key = (folder, name)
                named.add(key)
                if key not in self.tree.files:
                    self.add('error', 'CATALOG_NO_SOURCE', entry['weapon'],
                             'the catalog names %s %s and the tree holds no %s/%s.json' % (role, name, folder, name))
                elif key not in listed and key not in built:
                    self.add('error', 'CATALOG_NOT_BUILT', entry['weapon'],
                             'the catalog names %s %s and the zone csv does not build it' % (role, name))
            alias = entry['fire_alias']
            if alias and alias not in self.aliases:
                self.add('warn', 'CATALOG_ALIAS_UNDEFINED', entry['weapon'],
                         'the catalog keys this weapon by alias %s, which no alias list defines' % alias)
        for key in sorted(k for k in self.tree.files if k[0] == 'weapons' and k not in named):
            if 'catalog.txt' in self.tree.loose:
                self.add('warn', 'WEAPON_NOT_IN_CATALOG', key[1], 'a weapon file no catalog line names')
        weapons = {e['weapon'] for e in families} | {e['upgrade'] for e in families if e['upgrade']}
        for line in self.behaviours():
            if line['weapon'] not in weapons:
                self.add('error', 'BEHAVIOUR_UNKNOWN_WEAPON', line['weapon'], 'behaviours.txt names a weapon the catalog lacks')
            for field, effect in sorted(line['effects'].items()):
                key = ('particlesystem', effect)
                if key in self.tree.files:
                    if key not in built:
                        self.add('error', 'BEHAVIOUR_FX_NOT_BUILT', line['weapon'],
                                 '%s=%s is in the tree but nothing in the zone csv builds it' % (field, effect))
                elif not self.in_stock('vfx', effect):
                    self.add('error' if self.stock_lists else 'warn', 'BEHAVIOUR_FX_MISSING', line['weapon'],
                             '%s=%s is neither in the tree nor in a stock list' % (field, effect))
            missing = [s for s in line['sounds'] if s not in self.aliases and not self.in_stock('sound', s)]
            if missing:
                self.add('warn', 'BEHAVIOUR_SOUND_UNDEFINED', line['weapon'],
                         'sounds no alias list of the mod defines (stock or missing): %s' % ', '.join(missing))
        return families

    def check_unbuilt(self, built):
        for key in sorted(self.tree.files):
            if key[0] in FOLDER_TYPE and key[0] != 'images' and key not in built:
                self.add('warn', 'SOURCE_NOT_BUILT', '/'.join(key),
                         'in the tree, not in the zone csv and named by nothing that is: it will not be in the fastfile')
        used = set(self.roots)
        for key in built:
            used |= self.edges(key)
        idle = {}
        for key in sorted(self.listed):
            if key in self.tree.files and key not in used and key[0] not in ('weapons', 'soundbank'):
                idle.setdefault(key[0], []).append(key[1])
        for folder, names in sorted(idle.items()):
            self.add('info', 'LISTED_UNUSED', folder,
                     '%d built by the zone csv and named by no weapon, catalog or behaviour line: %s%s'
                     % (len(names), ', '.join(names[:6]), ' ...' if len(names) > 6 else ''))
        loose = sum(1 for key in self.tree.files if key[0] in ('images', 'xsurface', 'sound_assets') and key not in built)
        if loose:
            self.add('info', 'UNUSED_FILES', 'images, xsurface, sound_assets',
                     '%d file(s) nothing built refers to (dead weight, or a reference that is missing)' % loose)

    def check_binary(self, built):
        sys.path.insert(0, HERE)
        import iw7_xanim_layout as layout
        import iw7_xsurface_check as surface
        import iw7_xsurface_uv2 as uv2
        for key in sorted(self.tree.files):
            path = self.tree.files[key][0]
            try:
                if key[0] == 'xanim' and path.endswith('.xab'):
                    _, head, buffers = layout.load(path)
                    result = layout.check(head['frames'], head['bone_counts'], buffers.get('dataShort', []),
                                          buffers.get('indices', []))
                    errors = list(result.get('errors') or [])
                    if errors:    # one line per file: the first fault says what, the count says how much
                        self.add('error', 'XANIM_LAYOUT', '/'.join(key),
                                 '%d frames, %d layout fault(s) of the kind that crashes the client; first: %s'
                                 % (head['frames'], len(errors), errors[0]))
                elif key[0] == 'xsurface' and path.endswith('.xsb'):
                    errors = surface.check_file(path)['errors']
                    if errors:
                        self.add('error', 'XSURFACE', '/'.join(key),
                                 '%d surface fault(s); first: %s' % (len(errors), errors[0]))
            except Exception as error:    # a file the reader cannot follow is a fact worth a line, not a crash
                self.add('warn', 'UNREADABLE', '/'.join(key), '%s: %s' % (type(error).__name__, error))
        second = getattr(uv2, 'FLAG_SECONDUV', 0x100) | getattr(uv2, 'FLAG_SELFVIS', 0x400)
        motion = getattr(uv2, 'FLAG_MOTION', 0x8)
        for key in sorted(k for k in self.tree.files if k[0] == 'xmodel'):
            reached = self.edges(key)
            camo = sorted(m[1] for m in reached if m[0] == 'materials' and isinstance(self.tree.json(m), dict)
                          and '2uvt' in str(self.tree.json(m).get('techniqueSet->name', '')))
            if not camo:
                continue
            with_uv, without = 0, 0
            for surf in sorted(s for s in reached if s[0] == 'xsurface'):
                try:
                    with open(self.tree.files[surf][0], 'rb') as handle:
                        parsed = uv2.parse(handle.read())
                except Exception:
                    continue
                for item in parsed[-1] if isinstance(parsed, tuple) else parsed:
                    flags = item['flags'] if isinstance(item, dict) else item[0]
                    if flags & motion:
                        continue
                    with_uv += bool(flags & second)
                    without += not flags & second
            if without and not with_uv:
                self.add('error', 'CAMO_MATERIAL_WITHOUT_UV2', '/'.join(key),
                         'wears two-UV material %s and none of its %d static surfaces has a second UV set: it draws black'
                         % (camo[0], without))
            elif without:
                self.add('warn', 'CAMO_MATERIAL_PARTIAL_UV2', '/'.join(key),
                         'wears two-UV material %s; %d of %d static surfaces have no second UV set'
                         % (camo[0], without, with_uv + without))

    def check_maps(self, common_csvs, map_items):
        sys.path.insert(0, HERE)
        import iw7_mod_reference_audit as audit
        common, maps = set(), {}
        for path in common_csvs:
            common |= audit.csv_names(path)
        for item in map_items:
            name, _, paths = item.partition('=')
            maps[name] = set()
            for path in paths.split(';'):
                maps[name] |= audit.csv_names(path)
        if len(maps) < 2:
            raise SystemExit('list at least two map zones (--map name=csv)')
        found = audit.audit(audit.references(self.tree.root), audit.own_assets(self.tree.root), common, maps)
        for name, where in sorted(found.items()):
            self.add('error', 'MAP_ONLY_REFERENCE', name, 'only %s carry it, %s do not (used by %s)'
                     % (', '.join(where['in']), ', '.join(where['missing']), ', '.join(where['used_by'])))

    # ---------------------------------------------------------------- run
    def run(self, binary=True, common=(), maps=()):
        listed = self.listed = self.check_csv()
        built = self.closure(k for k in listed if k in self.tree.files)
        self.check_json()
        families = self.check_catalog(listed, built)
        for entry in families:
            self.roots |= {('weapons', entry['weapon']), ('weapons', entry['upgrade'])}
            self.roots |= {('attachments', a) for a in entry['attachments']}
        for line in self.behaviours():      # a script loads these by name: they count as used
            self.roots |= {('particlesystem', e) for e in line['effects'].values()}
            built |= self.closure(('particlesystem', e) for e in line['effects'].values()
                                  if ('particlesystem', e) in built)
            built |= self.closure(('alias', s) for s in line['sounds'] if s in self.aliases)
        for entry in families:
            if entry['fire_alias'] in self.aliases:
                built |= self.closure([('alias', entry['fire_alias'])])
        self.check_references(built)
        unused_aliases = self.check_sound(built)
        self.check_unbuilt(built)
        if binary:
            self.check_binary(built)
        if maps:
            self.check_maps(common, maps)
        self.findings.sort(key=lambda f: (ORDER[f['severity']], f['code'], f['asset']))
        return families, built, unused_aliases

    def family_state(self, families):
        """{weapon: {hash, nodes {key: digest}}} over everything each catalog entry reaches."""
        lines = {}
        for line in self.behaviours():
            lines.setdefault(line['weapon'], []).append(line)
        out = {}
        for entry in families:
            roots = [('weapons', entry['weapon'])]
            if entry['upgrade']:
                roots.append(('weapons', entry['upgrade']))
            roots += [('attachments', a) for a in entry['attachments']]
            if entry['fire_alias'] in self.aliases:
                roots.append(('alias', entry['fire_alias']))
            text = [entry['line']]
            for name in (entry['weapon'], entry['upgrade']):
                for line in lines.get(name, ()):
                    text.append(line['line'])
                    roots += [('particlesystem', e) for e in line['effects'].values()]
                    roots += [('alias', s) for s in line['sounds'] if s in self.aliases]
            reach = self.closure(r for r in roots if r[0] == 'alias' or r in self.tree.files)
            nodes = {'/'.join(key): self.node_digest(key) for key in sorted(reach)}
            nodes['catalog and behaviour lines'] = hashlib.sha256('\n'.join(text).encode()).hexdigest()[:20]
            total = hashlib.sha256(json.dumps(nodes, sort_keys=True).encode()).hexdigest()[:20]
            out[entry['weapon']] = {'hash': total, 'nodes': nodes}
        return out


def compare(previous, current):
    """{weapon: {status, changed[]}} against the accepted state; status new|changed|unchanged."""
    out = {}
    old = (previous or {}).get('weapons', {})
    for weapon, now in current.items():
        before = old.get(weapon)
        if not before:
            out[weapon] = {'status': 'new', 'changed': []}
        elif before.get('hash') == now['hash']:
            out[weapon] = {'status': 'unchanged', 'changed': []}
        else:
            a, b = before.get('nodes', {}), now['nodes']
            out[weapon] = {'status': 'changed', 'changed': sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('zone_dir', help='zonetool/<zone> source folder of the assembled mod')
    ap.add_argument('--csv', required=True, help='zone_source/<zone>.csv')
    ap.add_argument('--common', action='append', default=[], help='zone csv every map loads (map audit)')
    ap.add_argument('--map', action='append', default=[], metavar='NAME=CSV', help='a map zone csv (map audit)')
    ap.add_argument('--state', help='accepted state file: says which weapons changed since they passed in game')
    ap.add_argument('--accept', nargs='*', metavar='WEAPON',
                    help='record the current content as passed in game (all weapons, or the ones named)')
    ap.add_argument('--json', help='write the full result here')
    ap.add_argument('--no-binary', action='store_true', help='skip the animation, surface and camo UV checks')
    args = ap.parse_args(argv)
    started = time.time()
    run = Preflight(args.zone_dir, args.csv)
    families, built, unused_aliases = run.run(binary=not args.no_binary, common=args.common, maps=args.map)
    state = run.family_state(families)
    previous = None
    if args.state and os.path.isfile(args.state):
        with open(args.state, encoding='utf-8') as handle:
            previous = json.load(handle)
    diff = compare(previous, state) if args.state else {}
    counts = {s: sum(1 for f in run.findings if f['severity'] == s) for s in ORDER}
    zone = os.path.basename(os.path.normpath(args.zone_dir))
    seconds = round(time.time() - started, 2)
    print('preflight %s: %d source files, %d zone csv lines, %d catalog weapon(s), %.1f s'
          % (zone, sum(len(v) for v in run.tree.files.values()), len(run.entries), len(families), seconds))
    for finding in run.findings:
        print('  %-5s %s  %s: %s' % (finding['severity'].upper(), finding['code'], finding['asset'], finding['message']))
    print('errors %d, warnings %d, notes %d' % (counts['error'], counts['warn'], counts['info']))
    if args.state:
        again = sorted(w for w, d in diff.items() if d['status'] != 'unchanged')
        same = sorted(w for w, d in diff.items() if d['status'] == 'unchanged')
        for weapon in again:
            changed = diff[weapon]['changed']
            detail = 'never accepted' if diff[weapon]['status'] == 'new' else '%d changed: %s%s' % (
                len(changed), ', '.join(changed[:4]), ' ...' if len(changed) > 4 else '')
            print('look again in game: %s (%s)' % (weapon, detail))
        if same:
            print('unchanged since accepted, no launch needed: %s' % ', '.join(same))
    if args.accept is not None:
        if not args.state:
            raise SystemExit('--accept needs --state')
        unknown = sorted(set(args.accept) - set(state))
        if unknown:
            raise SystemExit('not a catalog weapon: %s' % ', '.join(unknown))
        kept = dict((previous or {}).get('weapons', {}))
        for weapon in (args.accept or sorted(state)):
            kept[weapon] = state[weapon]
        with open(args.state, 'w', encoding='utf-8') as handle:
            json.dump({'schema': STATE_SCHEMA, 'zone': zone, 'weapons': kept}, handle, indent=1, sort_keys=True)
        print('accepted: %s' % ', '.join(args.accept or sorted(state)))
    if args.json:
        with open(args.json, 'w', encoding='utf-8') as handle:
            json.dump({'schema': SCHEMA, 'zone': zone, 'seconds': seconds, 'counts': counts, 'findings': run.findings,
                       'stock_lists': run.stock_lists, 'built': len(built), 'unused_aliases': unused_aliases,
                       'weapons': {w: {'hash': s['hash'], 'files': len(s['nodes']), **diff.get(w, {})}
                                   for w, s in state.items()}}, handle, indent=1)
    return 1 if counts['error'] else 0


if __name__ == '__main__':
    sys.exit(main())
