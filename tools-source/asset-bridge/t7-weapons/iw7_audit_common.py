#!/usr/bin/env python3
"""Shared contract of the IW7 content audits (feel, sound, effects, compiled readback). Stdlib only.

An audit answers one question about content an agent built: "is what the player will notice what somebody decided,
or only what a template happened to leave there?" It never predicts how the engine renders or plays. It reads facts
from files, and where files cannot settle the matter it says so and hands a precise question to the engine bench.

"Right" has exactly three sources, and every finding names the one it used:

    intent   a declared decision (iw7.content-intent/1): the only source for brand-new content
    stock    the population of the shipped game, read at run time from a local dump (never committed)
    source   the original game's value, where a port tool recorded one

Severity: error = files prove it is broken (a declared decision is not what was built; a reference leads nowhere;
a value no stock asset has where that is impossible to be intended). warn = a fact somebody must look at (outside
the stock central band; a whole player-facing group still equal to the template and nobody declared that).
info = where a value sits among stock. "Zero false alarms on stock" means zero errors on stock.

proof: 'data' = the files settle it. 'engine' = files only raise the question; the bench must answer it.
"""
import argparse
import csv
import fnmatch
import importlib.util
import json
import math
import os
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import iw7_mod_preflight as preflight  # noqa: E402  (Tree, read_zone_csv, catalog and behaviour readers)

SCHEMA = 'iw7.content-audit/1'
INTENT_SCHEMA = 'iw7.content-intent/1'
SEVERITIES = ('error', 'warn', 'info')
PROOFS = ('data', 'engine')
ORDER = {s: i for i, s in enumerate(SEVERITIES)}
CENTRAL = (5, 95)            # the stock "central band" in percentiles; outside it is worth a look, not a fault
UNSET_TIMER = 65535          # IW7 writes this for a timer that is not used; never part of a population
SOURCE_FOLDERS = ('weapons', 'attachments', 'animpkg', 'sfxpkg', 'vfxpkg', 'xanim', 'particlesystem', 'sound',
                  'soundbank', 'materials', 'xmodel', 'images')
QUESTION_KINDS = ('see', 'hear', 'time', 'load')

# What the player notices, as groups of fields. Key = '<file kind>:<dotted path>' (fnmatch patterns).
# File kinds: weapon (weapons/<w>.json), animpkg, sfxpkg, vfxpkg. Nothing here names a weapon.
OBSERVABLE = (
    ('switching', 'how fast the weapon comes up and goes down', (
        'animpkg:timers.iRaiseTime', 'animpkg:timers.iDropTime', 'animpkg:timers.quickRaiseTime',
        'animpkg:timers.quickDropTime', 'animpkg:timers.iFirstRaiseTime', 'animpkg:timers.iEmptyRaiseTime',
        'animpkg:timers.iEmptyDropTime')),
    ('reloading', 'how long a reload takes and when the ammo arrives', (
        'animpkg:timers.iReload*', 'animpkg:timers.iFastReload*', 'weapon:weapDef.bNoPartialReload',
        'weapon:weapDef.bClipOnly', 'weapon:weapDef.iReloadAmmoAdd', 'weapon:weapDef.iReloadStartAdd')),
    ('firing', 'how fast it shoots', (
        'weapon:weapDef.iFireTime', 'weapon:weapDef.iFireDelay', 'weapon:weapDef.burstFire*',
        'animpkg:timers.iFireDelay', 'animpkg:timers.iRechamberTime', 'animpkg:timers.iHoldFireTime',
        'animpkg:fireAnimTimesMs*')),
    ('aiming', 'whether and how the weapon aims down sights', (
        'weapon:weapDef.aimDownSight', 'weapon:iAdsTransInTime', 'weapon:iAdsTransOutTime', 'weapon:fAdsZoomFov',
        'weapon:weapDef.fAdsZoomInFrac', 'weapon:weapDef.fAdsZoomOutFrac', 'weapon:weapDef.fAdsSpread',
        'weapon:weapDef.adsMoveSpeedScale', 'weapon:weapDef.adsFireOnly', 'weapon:weapDef.noAdsWhenMagEmpty')),
    ('crosshair', 'the crosshair on screen', (
        'weapon:weapDef.reticle*', 'weapon:weapDef.iReticle*', 'weapon:weapDef.activeReticleType',
        'weapon:szLUICrosshairWidget', 'weapon:weapDef.adsShouldShowCrosshair',
        'weapon:weapDef.fHipReticleSidePos')),
    ('spread', 'how wide shots scatter from the hip', (
        'weapon:weapDef.fHipSpread*', 'weapon:weapDef.hipSpread*', 'weapon:weapDef.slideSpread*')),
    ('ammo', 'clip size, reserve and the ammo counter', (
        'weapon:iClipSize', 'weapon:weapDef.iStartAmmo', 'weapon:weapDef.iMaxAmmo',
        'weapon:weapDef.iAmmoUsedPerShot', 'weapon:weapDef.ammoCounterIcon', 'weapon:weapDef.ammoCounterClip',
        'weapon:weapDef.bDoesNotConsumeAmmo')),
    ('damage', 'how hard it hits and how far', (
        'weapon:weapDef.damage', 'weapon:weapDef.minDamage', 'weapon:weapDef.playerDamage',
        'weapon:weapDef.meleeDamage', 'weapon:weapDef.iExplosion*', 'weapon:weapDef.maxDamageRange',
        'weapon:weapDef.minDamageRange', 'weapon:weapDef.damageConeAngle')),
    ('projectile', 'what flies out of the weapon', (
        'weapon:weapDef.iProjectileSpeed*', 'weapon:weapDef.projLifetime', 'weapon:weapDef.projectileModel',
        'weapon:weapDef.projectileCurvature', 'weapon:weapDef.bProjImpactExplode',
        'weapon:weapDef.projTrailEffect*', 'weapon:weapDef.projExplosionEffect*')),
    ('recoil', 'how the view and the gun kick when firing', (
        'weapon:weapDef.fHipGunKick*', 'weapon:weapDef.fAdsGunKick*', 'weapon:weapDef.fHipViewKick*',
        'weapon:weapDef.fAdsViewKick*', 'weapon:fHipViewKickCenterSpeed', 'weapon:fAdsViewKickCenterSpeed')),
    ('movement', 'how the player moves while holding it', (
        'weapon:weapDef.moveSpeedScale', 'weapon:weapDef.sprintDurationScale', 'animpkg:timers.sprintInTime',
        'animpkg:timers.sprintOutTime', 'animpkg:timers.sprintLoopTime')),
    ('sound profile', 'the echo and tail the engine adds to its shots', (
        'sfxpkg:*ReflectionClass*', 'sfxpkg:*AdsrBaseSetting*', 'weapon:szAdsrBaseSetting',
        'weapon:sfxImpactType')),
    ('effects', 'muzzle flash and impact effects', (
        'vfxpkg:*Flash*', 'weapon:vfxImpactType', 'weapon:weapDef.fireRumble')),
)


def observable_group(key):
    """(group, plain label) of a '<kind>:<path>' key, or None when the player does not notice that field."""
    for group, label, patterns in OBSERVABLE:
        if any(fnmatch.fnmatchcase(key, pattern) for pattern in patterns):
            return group, label
    return None


# ------------------------------------------------------------------ report
class Report:
    """Findings and engine questions of one audit run. Same line style and exit rule as iw7_mod_preflight."""

    def __init__(self, tool, target):
        self.tool, self.target = tool, target
        self.findings, self.questions, self.facts = [], [], {}

    def add(self, severity, code, asset, message, notice=None, proof='data', source=None, **evidence):
        """notice = one plain sentence about what the player would notice. source = intent | stock | source."""
        if severity not in SEVERITIES or proof not in PROOFS:
            raise ValueError('bad severity or proof: %r %r' % (severity, proof))
        finding = {'severity': severity, 'code': code, 'asset': asset, 'message': message, 'proof': proof}
        if notice:
            finding['notice'] = notice
        if source:
            finding['source'] = source
        if evidence:
            finding['evidence'] = evidence
        self.findings.append(finding)
        return finding

    def ask(self, kind, asset, question, why, **how):
        """A question only the engine can answer; the bench turns the list into one run. kind: see|hear|time|load."""
        if kind not in QUESTION_KINDS:
            raise ValueError('bad question kind: %r' % kind)
        entry = {'kind': kind, 'asset': asset, 'question': question, 'why': why}
        if how:
            entry['how'] = how
        if entry not in self.questions:
            self.questions.append(entry)

    def merge(self, other):
        self.findings.extend(other.findings)
        for entry in other.questions:
            if entry not in self.questions:
                self.questions.append(entry)
        self.facts.setdefault(other.tool, other.facts)

    def counts(self):
        return {s: sum(1 for f in self.findings if f['severity'] == s) for s in SEVERITIES}

    def sorted_findings(self):
        return sorted(self.findings, key=lambda f: (ORDER[f['severity']], f['code'], f['asset']))

    def as_dict(self):
        return {'schema': SCHEMA, 'tool': self.tool, 'target': self.target, 'counts': self.counts(),
                'findings': self.sorted_findings(), 'engine_questions': self.questions, 'facts': self.facts}

    def write_text(self, stream=None):
        stream = stream or sys.stdout
        counts = self.counts()
        for f in self.sorted_findings():
            tail = '  [only the engine can confirm]' if f['proof'] == 'engine' else ''
            stream.write('  %-5s %s  %s: %s%s\n' % (f['severity'].upper(), f['code'], f['asset'], f['message'], tail))
            if f.get('notice'):
                stream.write('        player: %s\n' % f['notice'])
        stream.write('%s %s: errors %d, warnings %d, notes %d, engine questions %d\n' % (
            self.tool, self.target, counts['error'], counts['warn'], counts['info'], len(self.questions)))

    def exit_code(self):
        return 1 if self.counts()['error'] else 0


# ------------------------------------------------------------------ numbers
class Population:
    """A stock population of one number. Empty populations answer None, never a guess."""

    def __init__(self, values):
        self.values = sorted(float(v) for v in values
                             if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v))
        self.n = len(self.values)

    @property
    def min(self):
        return self.values[0] if self.n else None

    @property
    def max(self):
        return self.values[-1] if self.n else None

    def percentile(self, p):
        if not self.n:
            return None
        at = (self.n - 1) * p / 100.0
        low = int(math.floor(at))
        high = min(low + 1, self.n - 1)
        return self.values[low] + (self.values[high] - self.values[low]) * (at - low)

    @property
    def median(self):
        return self.percentile(50)

    def rank(self, value):
        """Share of the population at or below value, 0..1."""
        return None if not self.n else sum(1 for v in self.values if v <= value) / self.n

    def position(self, value, band=CENTRAL):
        """'below-all' | 'low' | 'central' | 'high' | 'above-all' | None (no population)."""
        if not self.n:
            return None
        if value < self.min:
            return 'below-all'
        if value > self.max:
            return 'above-all'
        if value < self.percentile(band[0]):
            return 'low'
        if value > self.percentile(band[1]):
            return 'high'
        return 'central'

    def describe(self):
        if not self.n:
            return 'no stock values'
        return 'stock n=%d: %s..%s, middle %s (%s..%s for 9 in 10)' % (
            self.n, fmt(self.min), fmt(self.max), fmt(self.median),
            fmt(self.percentile(CENTRAL[0])), fmt(self.percentile(CENTRAL[1])))


def fmt(value):
    if isinstance(value, float):
        return ('%.3f' % value).rstrip('0').rstrip('.') if abs(value) < 1000 else '%.0f' % value
    return str(value)


def same(a, b):
    """Equality that forgives float text round trips and nothing else."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= 1e-4 * max(1.0, abs(a), abs(b))
    return a == b


# ------------------------------------------------------------------ documents
def leaves(doc, prefix=''):
    """{dotted path: scalar} of a JSON document; list items are path[i]."""
    out = {}
    if isinstance(doc, dict):
        for key, value in doc.items():
            out.update(leaves(value, '%s.%s' % (prefix, key) if prefix else key))
    elif isinstance(doc, list):
        for index, value in enumerate(doc):
            out.update(leaves(value, '%s[%d]' % (prefix, index)))
    else:
        out[prefix] = doc
    return out


def leaf(doc, path, default=None):
    """One value by dotted path ('weapDef.iFireTime', 'anims[3]')."""
    node = doc
    for part in path.replace(']', '').replace('[', '.').split('.'):
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            return default
    return node


def nearest_stock(doc, candidates, ignore=('name', 'szInternalName', 'szDisplayName')):
    """(candidate name, share of equal leaves, compared count): which stock asset this document was made from.

    candidates = {name: document}. A share of 1.0 means the document IS that stock asset; residue checks make no
    sense then. Returns (None, 0.0, 0) with no candidate."""
    mine = {k: v for k, v in leaves(doc).items() if k.split('.')[-1] not in ignore}
    best = (None, 0.0, 0)
    for name in sorted(candidates):
        theirs = leaves(candidates[name])
        common = [k for k in mine if k in theirs]
        if not common:
            continue
        share = sum(1 for k in common if same(mine[k], theirs[k])) / len(common)
        if share > best[1]:
            best = (name, share, len(common))
    return best


def load_json(path):
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


# ------------------------------------------------------------------ trees
def is_zone_dir(path):
    return os.path.isdir(path) and (
        any(os.path.isdir(os.path.join(path, folder)) for folder in SOURCE_FOLDERS)
        or os.path.isfile(os.path.join(path, os.path.basename(os.path.normpath(path)) + '.csv')))


def locate_zone_dir(path):
    """The zonetool/<zone> source folder for a path that is one, or holds exactly one (work dir or zonetool/)."""
    path = os.path.abspath(path)
    if is_zone_dir(path):
        return path
    for base in (os.path.join(path, 'zonetool'), path):
        if os.path.isdir(base):
            found = sorted(os.path.join(base, e) for e in os.listdir(base) if is_zone_dir(os.path.join(base, e)))
            if len(found) == 1:
                return found[0]
            if found:
                raise ValueError('%s holds %d zone folders; name one: %s' % (
                    base, len(found), ', '.join(os.path.basename(f) for f in found[:8])))
    raise ValueError('no zone source folder at %s' % path)


def read_catalog(tree):
    """[{weapon, upgrade, attachments, fire_alias, line}] (catalog.txt, else one entry per weapon file)."""
    return preflight.Preflight.catalog(types.SimpleNamespace(tree=tree))


def read_behaviours(tree):
    """[{weapon, namespace, effects {key: vfx}, sounds [alias], line}] from behaviours.txt."""
    return preflight.Preflight.behaviours(types.SimpleNamespace(tree=tree))


def alias_rows(zone_dir):
    """Every row of every sound alias list under <zone>/sound, as {column: text} plus '_list' and '_line'.

    The 53 columns keep their own names (Name, File, vol_max, channel, type, SecondaryAliasName, ...)."""
    out = []
    base = os.path.join(zone_dir, 'sound')
    for here, _, names in os.walk(base):
        for name in sorted(names):
            if not name.lower().endswith('.csv'):
                continue
            path = os.path.join(here, name)
            with open(path, newline='', encoding='utf-8', errors='replace') as handle:
                rows = list(csv.reader(handle))
            if not rows or 'Name' not in rows[0] or 'File' not in rows[0]:
                continue
            head = rows[0]
            for number, row in enumerate(rows[1:], 2):
                if row and len(row) > head.index('Name') and row[head.index('Name')]:
                    entry = {column: (row[i].strip() if i < len(row) else '') for i, column in enumerate(head)}
                    entry['_list'] = os.path.relpath(path, base).replace(os.sep, '/')
                    entry['_line'] = number
                    out.append(entry)
    return out


def alias_index(rows):
    """{alias name: [its rows]}: one alias may have several rows, the engine picks one of them each time."""
    index = {}
    for row in rows:
        index.setdefault(row.get('Name', ''), []).append(row)
    return index


def alias_chain(index, name, limit=16):
    """The alias and every layer it starts through SecondaryAliasName, root first: [(alias name, [rows])].

    A name that is in no list ends the chain with (name, []): the caller decides whether stock has it."""
    out, seen = [], set()
    while name and name not in seen and len(out) < limit:
        seen.add(name)
        rows = index.get(name, [])
        out.append((name, rows))
        name = next((row.get('SecondaryAliasName', '') for row in rows if row.get('SecondaryAliasName')), '')
    return out


def number(text, default=None):
    """A float from CSV text, default when it is empty or not a number."""
    try:
        value = float(text)
    except (TypeError, ValueError):
        return default
    return value if math.isfinite(value) else default


class StockDump:
    """Read-only view of dumped stock zones. roots = zone dump folders, or folders that hold several.

    The dump is local and private: populations are computed from it at run time and never written to a repository."""

    def __init__(self, roots):
        self.zones = {}
        for root in roots or ():
            root = os.path.abspath(root)
            if is_zone_dir(root):
                self.zones.setdefault(os.path.basename(root), root)
            elif os.path.isdir(root):
                for entry in sorted(os.listdir(root)):
                    if is_zone_dir(os.path.join(root, entry)):
                        self.zones.setdefault(entry, os.path.join(root, entry))
        self._json = {}

    def __bool__(self):
        return bool(self.zones)

    def paths(self, folder, ext):
        """(zone, name, path) of every file of a source folder; name has no extension and uses '/'."""
        for zone in sorted(self.zones):
            base = os.path.join(self.zones[zone], folder)
            for here, _, names in os.walk(base):
                for name in sorted(names):
                    if name.lower().endswith(ext.lower()):
                        full = os.path.join(here, name)
                        yield zone, os.path.relpath(full, base).replace(os.sep, '/')[:-len(ext)], full

    def find(self, folder, name, ext):
        """Path of one stock file by name, first zone that has it, else None."""
        for zone in sorted(self.zones):
            path = os.path.join(self.zones[zone], folder, name.replace('/', os.sep) + ext)
            if os.path.isfile(path):
                return path
        return None

    def json(self, path):
        """Parsed JSON of a path, None when it does not parse (a dump can hold a truncated file)."""
        if path not in self._json:
            try:
                self._json[path] = load_json(path)
            except (OSError, ValueError):
                self._json[path] = None
        return self._json[path]

    def docs(self, folder):
        """(zone, name, document) of every parsable JSON file of a source folder; a name is yielded once."""
        seen = set()
        for zone, name, path in self.paths(folder, '.json'):
            if name not in seen and self.json(path) is not None:
                seen.add(name)
                yield zone, name, self.json(path)


# ------------------------------------------------------------------ animations
_XAB = None


def xab_info(path):
    """{'frames', 'rate', 'ms'} of an IW7 .xab from its header alone. ValueError when it is not one."""
    global _XAB
    if _XAB is None:
        source = os.path.join(HERE, '..', 'animation', 'xab_preflight.py')
        spec = importlib.util.spec_from_file_location('xab_preflight', source)
        _XAB = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_XAB)
    with open(path, 'rb') as handle:
        data = handle.read(4096)
    try:
        head = _XAB.header(_XAB.Reader(data), 'iw7')
    except Exception as error:   # the reader raises its own Invalid and plain struct errors on a short file
        raise ValueError('%s: %s' % (os.path.basename(path), error))
    frames, rate = head['frames'], head['rate']
    if not (rate and math.isfinite(rate) and rate > 0):
        raise ValueError('%s: frame rate %r' % (os.path.basename(path), rate))
    return {'frames': frames, 'rate': rate, 'ms': int(round(1000.0 * frames / rate))}


# ------------------------------------------------------------------ intent
class Intent:
    """Declared decisions: what somebody decided the player should get, with the reason.

    One JSON file per item (schema iw7.content-intent/1):
        {"schema": "iw7.content-intent/1", "item": "iw7_thundergun_zm", "kind": "weapon",
         "template": "iw7_facemelter_zm",                      optional: the stock asset it was made from
         "source": "BO3 thundergun",                           free text
         "decisions": {
           "weapon:weapDef.aimDownSight": {"value": false, "why": "the BO3 Thundergun cannot aim"},
           "animpkg:timers.iRaiseTime":   {"min": 900, "max": 1100, "why": "matches its 1.0 s raise animation"},
           "weapon:weapDef.fHipSpread*":  {"keep": true, "why": "hip spread of the Facemelter is wanted"}}}
    A decision without a reason is not a decision. Keys may be fnmatch patterns; an exact key wins."""

    def __init__(self):
        self.items, self.problems = {}, []

    @classmethod
    def load(cls, path):
        intent = cls()
        if not path:
            return intent
        files = [path] if os.path.isfile(path) else sorted(
            os.path.join(base, name) for base, _, names in os.walk(path) for name in names if name.endswith('.json'))
        for file in files:
            try:
                doc = load_json(file)
            except (OSError, ValueError) as error:
                intent.problems.append((file, 'does not parse: %s' % error))
                continue
            if not isinstance(doc, dict) or doc.get('schema') != INTENT_SCHEMA:
                if os.path.isfile(path):
                    intent.problems.append((file, 'schema is not %s' % INTENT_SCHEMA))
                continue
            item = doc.get('item')
            if not isinstance(item, str) or not isinstance(doc.get('decisions'), dict):
                intent.problems.append((file, 'needs "item" and "decisions"'))
                continue
            for key, decision in doc['decisions'].items():
                if not (isinstance(decision, dict) and isinstance(decision.get('why'), str) and decision['why'].strip()
                        and (decision.get('keep') is True or 'value' in decision
                             or 'min' in decision or 'max' in decision)):
                    intent.problems.append((file, '%s: needs a reason ("why") and one of value, min/max, keep' % key))
            intent.items[item] = doc
        return intent

    def template(self, item):
        return (self.items.get(item) or {}).get('template')

    def decision(self, item, key):
        """The valid decision that covers this key for this item, or None."""
        decisions = (self.items.get(item) or {}).get('decisions') or {}
        hits = [decisions[key]] if key in decisions else [
            decisions[p] for p in sorted(decisions) if fnmatch.fnmatchcase(key, p)]
        for decision in hits:
            if isinstance(decision, dict) and isinstance(decision.get('why'), str) and decision['why'].strip():
                return decision
        return None

    def judge(self, item, key, actual):
        """'match' | 'mismatch' | 'keep' | None (nobody declared this). Never guesses."""
        decision = self.decision(item, key)
        if decision is None:
            return None
        if decision.get('keep') is True:
            return 'keep'
        if 'value' in decision:
            return 'match' if same(decision['value'], actual) else 'mismatch'
        if isinstance(actual, (int, float)) and not isinstance(actual, bool):
            low, high = decision.get('min'), decision.get('max')
            if (low is None or actual >= low) and (high is None or actual <= high):
                return 'match'
            return 'mismatch'
        return 'mismatch'

    def wanted(self, item, key):
        """Plain text of what was declared, for a message."""
        decision = self.decision(item, key) or {}
        if 'value' in decision:
            what = json.dumps(decision['value'])
        elif decision.get('keep') is True:
            what = 'keep the template value'
        else:
            what = 'between %s and %s' % (decision.get('min', 'any'), decision.get('max', 'any'))
        return '%s (%s)' % (what, decision.get('why', ''))

    def report_problems(self, report):
        for file, text in self.problems:
            report.add('error', 'INTENT-FILE', os.path.basename(file), text, source='intent')


# ------------------------------------------------------------------ shared judgement: decided, or left by a template
def template_of(doc, stock, folder, name=None):
    """(name, document, share equal) of the stock document this one was made from: the named one when the dump
    has it, else the stock document of that folder with the most equal values. (None, None, 0.0) without stock."""
    if not stock:
        return None, None, 0.0
    if name:
        path = stock.find(folder, name, '.json')
        found = stock.json(path) if path else None
        if isinstance(found, dict):
            mine, theirs = leaves(doc), leaves(found)
            shared = [k for k in mine if k in theirs]
            equal = sum(1 for k in shared if same(mine[k], theirs[k]))
            return name, found, (equal / len(shared) if shared else 0.0)
    candidates = {n: d for _, n, d in stock.docs(folder)}
    best, share, _ = nearest_stock(doc, candidates)
    return (best, candidates[best], share) if best is not None else (None, None, 0.0)


class GroupJudge:
    """Judges the player-facing groups (OBSERVABLE) of ONE item across its documents: weapon, animpkg, sfxpkg, vfxpkg.

    feed() each document with the stock document it was made from; report() then writes, per group:
      error <P>-INTENT          a declared decision is not what was built                      (source intent)
      warn  <P>-TEMPLATE-GROUP  every value of the group equals the template and nobody declared any of them
      info  <P>-TEMPLATE-PART   some undeclared values equal the template
    A value that differs from the template and is not declared is only counted: somebody changed it."""

    def __init__(self, intent, item):
        self.intent, self.item, self.groups = intent, item, {}

    def feed(self, kind, doc, template_doc=None, template_name=None):
        base = leaves(template_doc) if isinstance(template_doc, dict) else {}
        for path, value in leaves(doc).items():
            key = '%s:%s' % (kind, path)
            hit = observable_group(key)
            if not hit:
                continue
            group = self.groups.setdefault(hit[0], {
                'label': hit[1], 'fields': 0, 'declared': 0, 'changed': 0, 'template': [], 'mismatch': []})
            group['fields'] += 1
            verdict = self.intent.judge(self.item, key, value)
            if verdict is not None:
                group['declared'] += 1
                if verdict == 'mismatch':
                    group['mismatch'].append((key, value))
            elif path in base and same(base[path], value):
                group['template'].append((key, value, template_name))
            else:
                group['changed'] += 1

    def report(self, report, prefix='FEEL', only=None):
        """only: the group names this tool owns (None = all). Each audit reports its own groups, none twice."""
        facts = report.facts.setdefault('groups', {}).setdefault(self.item, {})
        for name, _, _ in OBSERVABLE:
            group = self.groups.get(name)
            if not group or (only is not None and name not in only):
                continue
            facts[name] = {'values': group['fields'], 'declared': group['declared'], 'changed': group['changed'],
                           'template': len(group['template'])}
            for key, value in group['mismatch']:
                report.add('error', prefix + '-INTENT', self.item,
                           '%s is %s but the declared decision is %s' % (
                               key, fmt(value), self.intent.wanted(self.item, key)),
                           notice=group['label'], source='intent', group=name, key=key, actual=value)
            left = group['template']
            if not left:
                continue
            origins = ' and '.join(sorted({origin for _, _, origin in left if origin})) or 'the template'
            sample = ', '.join('%s=%s' % (key.split(':', 1)[1], fmt(value)) for key, value, _ in left[:4])
            more = '' if len(left) <= 4 else ' and %d more' % (len(left) - 4)
            whole = len(left) == group['fields']
            share = ('all %d values' % len(left)) if whole else ('%d of %d values' % (len(left), group['fields']))
            report.add('warn' if whole else 'info', prefix + ('-TEMPLATE-GROUP' if whole else '-TEMPLATE-PART'),
                       self.item, '%s: %s are still those of %s (%s%s)' % (name, share, origins, sample, more),
                       notice=('%s: nobody decided this, it is whatever %s had' % (group['label'], origins))
                       if whole else None,
                       source='stock', group=name, keys=[key for key, _, _ in left])

    def skeleton(self, template=None, source='', only=None):
        """An intent document listing every undeclared value still equal to the template, each with an EMPTY reason.
        It changes nothing until somebody writes the reasons: a decision without a reason is not a decision."""
        decisions = {}
        for name, _, _ in OBSERVABLE:
            if only is not None and name not in only:
                continue
            for key, value, _ in (self.groups.get(name) or {}).get('template', ()):
                decisions[key] = {'value': value, 'why': ''}
        doc = {'schema': INTENT_SCHEMA, 'item': self.item, 'kind': 'weapon', 'source': source, 'decisions': decisions}
        if template:
            doc['template'] = template
        return doc


# ------------------------------------------------------------------ command line
def add_common_args(parser):
    parser.add_argument('--stock', action='append', default=[], metavar='DIR',
                        help='dumped stock zone folder, or a folder holding several (repeatable; '
                             'default: the IW7_STOCK_DUMP environment variable, %s-separated)' % os.pathsep)
    parser.add_argument('--intent', metavar='FILE_OR_DIR', help='declared decisions (iw7.content-intent/1)')
    parser.add_argument('--json', metavar='FILE', help='write the full result here')
    return parser


def stock_from_args(args):
    roots = list(args.stock) or [p for p in os.environ.get('IW7_STOCK_DUMP', '').split(os.pathsep) if p]
    return StockDump(roots)


def finish(report, args, stream=None):
    """Print the report, write --json, return the exit code."""
    report.write_text(stream)
    if getattr(args, 'json', None):
        with open(args.json, 'w', encoding='utf-8') as handle:
            json.dump(report.as_dict(), handle, indent=1, sort_keys=True)
    return report.exit_code()


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='List what the audits treat as noticed by the player.')
    ap.parse_args()
    for group, label, patterns in OBSERVABLE:
        print('%-14s %s\n    %s' % (group, label, '\n    '.join(patterns)))
