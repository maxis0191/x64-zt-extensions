#!/usr/bin/env python3
"""Readback of a compiled IW7 zone: is what the engine's own loader read back the same as what we meant to put in?

    python iw7_zone_readback.py --source-csv zone_source/<zone>.csv --source-tree zonetool/<zone> --dump dump/<zone>
        [--log zonetool-verify-or-dump.out.log] [--noise noise.json] [--json FILE] [--strict] [--intent FILE_OR_DIR]

ZoneTool hosts the real game loader. A runner (not this tool) makes it load the compiled .ff and dump every asset
it read; this tool compares three things: the source list (what we asked for), the source tree (the values we
wrote) and the dump (what the loader gave back). It never runs ZoneTool and never opens a .ff.

    ZONE-ASSET-NOT-LOADED    error  an asked-for asset is missing from the dump (or, with --log, never loaded)
    ZONE-VALUE-DIFFERS       warn   a JSON asset holds another value in the compiled file than in the source
    ZONE-BINARY-DIFFERS      warn   a binary asset differs even after decoding (iw7VFX, xab)
    ZONE-ASSET-ADDED / ZONE-SOURCE-MISSING / ZONE-BINARY-SUMMARY / ZONE-KIND-NOT-COMPARED   facts, not faults
    ZONE-VALUE-FILLED / ZONE-VALUE-NOT-CARRIED   facts: a value the source did not write, a value the format drops
    ZONE-ROW-NOT-LOADED      error  a row of a source table (a sound alias...) is not in the compiled table
    ZONE-ROW-DIFFERS         warn   a row holds another value in the compiled table than in the source table
    ZONE-TABLES-SAME / ZONE-ROW-ADDED            facts: tables are compared row by row, however many files hold them

"Not compared" is never a pass: every kind without a decoder is counted as such. Standard library only.
"""
import argparse
import csv
import fnmatch
import math
import os
import re
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 't7-weapons'))
import iw7_audit_common as common  # noqa: E402

TOOL = 'zone-readback'
PREFIX = 'ZONE'
NOISE_SCHEMA = 'iw7.readback-noise/1'
LISTED_MISSING = 30          # ASSET-NOT-LOADED written one by one before the rest is aggregated per type
SHOWN_DIFFS = 8              # differing leaves written into one VALUE-DIFFERS finding
CHUNK = 1 << 20

# csv type -> (folder, extension of the dumped file, extensions a source tree may hold). Derived from the files
# ZoneTool wrote for stock zones (cp_zmb) and from the layout of the mod source trees; a type missing here is
# not compared. '' = file without extension.
TYPES = {
    'weapon': ('weapons', '.json', ('.json',)),
    'attachment': ('attachments', '.json', ('.json',)),
    'animpkg': ('animpkg', '.json', ('.json',)),
    'sfxpkg': ('sfxpkg', '.json', ('.json',)),
    'vfxpkg': ('vfxpkg', '.json', ('.json',)),
    'soundbank': ('soundbank', '.json', ('.json',)),
    'material': ('materials', '.json', ('.json',)),
    'gesture': ('gesture', '.json', ('.json',)),
    'laser': ('laser', '.json', ('.json',)),
    'reticle': ('reticle', '.json', ('.json',)),
    'rumble': ('rumble', '.json', ('.json',)),
    'rumblegraph': ('rumble_graph', '.json', ('.json',)),
    'tracer': ('tracer', '.json', ('.json',)),
    'netconststrings': ('netconststrings', '.json', ('.json',)),
    'behaviortree': ('behaviortree', '.json', ('.json',)),
    'lightdef': ('lights', '.json', ('.json',)),
    'xmodel': ('xmodel', '.xmb', ('.xmb',)),
    'xmodelsurfs': ('xsurface', '.xsb', ('.xsb',)),
    'xanim': ('xanim', '.xab', ('.xab',)),
    'vfx': ('particlesystem', '.iw7VFX', ('.iw7VFX',)),
    'image': ('images', '.iw7Image', ('.iw7Image', '.dds', '.tga')),
    'animclass': ('animclass', '', ('',)),
    'scriptable': ('scriptable', '', ('',)),
}
# Every asset type ZoneTool writes into a zone csv (seen in dumped stock zones). A source csv row whose first
# field is neither of these is a directive (require, ignore, ...).
ASSET_TYPES = frozenset(TYPES) | frozenset((
    'aipaths', 'col_map', 'com_map', 'domainshader', 'equipsndtable', 'fx_map', 'gfx_map', 'gfx_map_trzone',
    'gfxlightmap', 'glass_map', 'hullshader', 'impactfx', 'luafile', 'map_ents', 'navmesh', 'particlesimanimation',
    'physicsasset', 'physicsfxpipeline', 'physicsfxshape', 'physicssfxeventasset', 'pixelshader', 'playeranim',
    'proceduralbones', 'rawfile', 'scriptfile', 'spaceshiptarget', 'streaminginfo', 'stringtable', 'suit',
    'suitanimpackage', 'techset', 'vehicle', 'vertexdecl', 'vertexshader'))
LOADING = re.compile(r'Loading asset "(.*)" of type (\S+?)\.?\s*$')
LOG_LINE = re.compile(r'^\[ (INFO|WARNING|ERROR|FATAL) \]\[ (.*?) \]: ?(.*)$')


# ------------------------------------------------------------------ reading the lists
def read_rows(path):
    """(rows [(type, name, flagged)], directives [(kind, rest)]).

    A dump row `type,,name` carries a second comma: the dumper wrote no file for it (the name does not contain the
    comma). Rows of a source list never have it. Comments and blank lines are skipped."""
    rows, directives = [], []
    with open(path, encoding='utf-8', errors='replace') as handle:
        for line in handle:
            line = line.rstrip('\r\n').strip()
            if not line or line.startswith('//') or line.startswith('#'):
                continue
            kind, comma, rest = line.partition(',')
            kind = kind.strip()
            if not comma or not rest.strip(','):
                continue
            if kind not in ASSET_TYPES:
                directives.append((kind, rest.strip()))
                continue
            flagged = rest.startswith(',')
            rows.append((kind, (rest[1:] if flagged else rest).strip(), flagged))
    return rows, directives


def file_path(root, kind, name, extension):
    folder = TYPES[kind][0]
    return os.path.join(root, folder, name.replace('/', os.sep) + extension)


def is_file(path):
    try:
        return os.path.isfile(path)
    except (OSError, ValueError):
        return False


# ------------------------------------------------------------------ comparing values
def empty(value):
    return value is None or value == '' or (isinstance(value, (int, float)) and value == 0)


def f32(value):
    try:
        return struct.pack('<f', value)
    except (OverflowError, struct.error):
        return None


def equal_values(a, b):
    """Numbers equal as 32-bit floats or within 1e-6 relative (integers must match exactly); true/1 and false/0
    are the same; everything else must be equal."""
    if isinstance(a, bool):
        a = int(a)
    if isinstance(b, bool):
        b = int(b)
    numbers = isinstance(a, (int, float)) and isinstance(b, (int, float))
    if not numbers:
        return a == b
    if isinstance(a, int) and isinstance(b, int):
        return a == b
    if a == b:
        return True
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    one, other = f32(a), f32(b)
    if one is not None and one == other:
        return True
    return abs(a - b) <= 1e-6 * max(abs(a), abs(b))


ABSENT = '(absent)'
# values the compiled format does not carry, by asset kind: the loader gives them back empty for stock too
# (measured: "sounds.name" is "" in 182 of 182 sfxpkg assets dumped from the stock zone cp_zmb)
NOT_CARRIED = {'sfxpkg': ('sounds.name',)}


def diff_leaves(source, dumped):
    """[(path, source value, dump value)] where the two flattened documents disagree. A leaf on one side only
    counts unless that value is empty (empty string, null, 0, empty list or object: those leaves do not exist)."""
    one, two = common.leaves(source), common.leaves(dumped)
    out = []
    for path in sorted(set(one) | set(two)):
        if path in one and path in two:
            if not equal_values(one[path], two[path]):
                out.append((path, one[path], two[path]))
        else:
            value = one[path] if path in one else two[path]
            if not empty(value):
                out.append((path, one.get(path, ABSENT), two.get(path, ABSENT)))
    return out


def decoded_leaves(model):
    """Flattened decoded structure without the pointer values, which differ in every build."""
    return {path: value for path, value in common.leaves(model).items()
            if not path.endswith('@ptr') and path != 'rootPtr'}


def same_file_content(first, second):
    """True when two files hold the same bytes. The same file is not read; sizes are compared first."""
    try:
        if os.path.samefile(first, second):
            return True
        if os.path.getsize(first) != os.path.getsize(second):
            return False
        with open(first, 'rb') as one, open(second, 'rb') as two:
            while True:
                block = one.read(CHUNK)
                if block != two.read(CHUNK):
                    return False
                if not block:
                    return True
    except OSError:
        return False


def vfx_decoder():
    import iw7_vfx      # beside the contract; found through the path the contract set
    return iw7_vfx.decode


def compare_decoded(extension, first, second):
    """'same' | 'differs' | 'no-decoder' | 'undecodable' for two files whose bytes differ."""
    try:
        if extension == '.iw7VFX':
            decode = vfx_decoder()
            with open(first, 'rb') as one, open(second, 'rb') as two:
                a, b = decoded_leaves(decode(one.read())), decoded_leaves(decode(two.read()))
            return 'same' if set(a) == set(b) and all(equal_values(a[k], b[k]) for k in a) else 'differs'
        if extension == '.xab':
            return 'same' if common.xab_info(first) == common.xab_info(second) else 'differs'
    except Exception:    # a decoder raises its own error types on a damaged file
        return 'undecodable'
    return 'no-decoder'


# ------------------------------------------------------------------ noise
def load_noise(path, report):
    """[(kind, fnmatch pattern)] of the accepted differences; entries without a reason are reported and ignored."""
    entries = []
    if not path:
        return entries
    name = os.path.basename(path)
    try:
        doc = common.load_json(path)
    except (OSError, ValueError) as error:
        report.add('error', 'ZONE-NOISE-FILE', name, 'does not parse: %s' % error)
        return entries
    if not isinstance(doc, dict) or doc.get('schema') != NOISE_SCHEMA or not isinstance(doc.get('entries'), list):
        report.add('error', 'ZONE-NOISE-FILE', name, 'needs schema %s and a list "entries"' % NOISE_SCHEMA)
        return entries
    for number, entry in enumerate(doc['entries']):
        ok = (isinstance(entry, dict) and isinstance(entry.get('kind'), str) and isinstance(entry.get('path'), str)
              and isinstance(entry.get('why'), str) and entry['why'].strip())
        if not ok:
            report.add('error', 'ZONE-NOISE-FILE', name,
                       'entry %d is ignored: it needs "kind", "path" and a non-blank "why"' % number)
            continue
        entries.append((entry['kind'], entry['path']))
    return entries


def is_noise(noise, kind, path):
    return any(k == kind and fnmatch.fnmatchcase(path, pattern) for k, pattern in noise)


# ------------------------------------------------------------------ log
def read_log(path):
    """(set of (type, name) the loader reported, [(level, text) of ERROR/FATAL lines])."""
    loaded, problems = set(), []
    with open(path, encoding='utf-8', errors='replace') as handle:
        for line in handle:
            line = line.rstrip('\r\n')
            found = LOADING.search(line)
            if found:
                name = found.group(1)
                loaded.add((found.group(2), name[1:] if name.startswith(',') else name))
                continue
            parsed = LOG_LINE.match(line)
            if parsed and parsed.group(1) in ('ERROR', 'FATAL'):
                problems.append((parsed.group(1), parsed.group(3).strip()))
    return loaded, problems


# ------------------------------------------------------------------ audit
def audit(source_csv, source_tree, dump_dir, intent, log=None, noise=None, types=None):
    """Return a common.Report comparing the source list, the source tree and the dump of one zone."""
    report = common.Report(TOOL, dump_dir)
    intent.report_problems(report)
    zone = os.path.basename(os.path.normpath(dump_dir))
    dump_csv = os.path.join(dump_dir, zone + '.csv')
    if not is_file(dump_csv) or os.path.getsize(dump_csv) == 0:
        report.add('error', 'ZONE-DUMP-INCOMPLETE', zone,
                   'the dump holds no %s.csv, or it is empty: the loader did not write the zone back' % zone,
                   notice='nothing can be said about what the compiled file holds')
        return report
    wanted, directives = read_rows(source_csv)
    dumped, _ = read_rows(dump_csv)
    if not dumped:
        report.add('error', 'ZONE-DUMP-INCOMPLETE', zone, '%s.csv lists no asset' % zone,
                   notice='nothing can be said about what the compiled file holds')
        return report
    noise_entries = load_noise(noise, report)

    wanted_keys = {(k, n) for k, n, _ in wanted}
    dump_flag = {(k, n): flagged for k, n, flagged in dumped}
    dump_keys = set(dump_flag)
    per_type = {}

    def count(kind, what, step=1):
        entry = per_type.setdefault(kind, {'source_csv': 0, 'dump_csv': 0, 'compared': 0, 'identical': 0})
        entry[what] += step

    for kind, _ in wanted_keys:
        count(kind, 'source_csv')
    for kind, _ in dump_keys:
        count(kind, 'dump_csv')
    kinds_of_directives = {}
    for kind, _ in directives:
        kinds_of_directives[kind] = kinds_of_directives.get(kind, 0) + 1
    report.facts['directives'] = kinds_of_directives

    # R1 / R2 -- a dump limited to some asset kinds proves nothing about the other kinds
    only = {t.strip().lower() for t in types if t.strip()} if types else None
    missing = sorted(k for k in wanted_keys - dump_keys if only is None or k[0].lower() in only)
    outside = {}
    for kind, _ in wanted_keys - dump_keys - set(missing):
        outside[kind] = outside.get(kind, 0) + 1
    if outside:
        report.add('info', 'ZONE-KIND-NOT-DUMPED', zone,
                   'the dump was limited to %s; not judged: %s' % (
                       ', '.join(sorted(only)), ', '.join('%s %d' % kv for kv in sorted(outside.items()))),
                   counts=dict(sorted(outside.items())))
    reported = set()
    for kind, name in missing[:LISTED_MISSING]:
        reported.add((kind, name))
        report.add('error', 'ZONE-ASSET-NOT-LOADED', name,
                   '%s "%s" is in the source list but not in the dump of the compiled file' % (kind, name),
                   notice='this asset was asked for but is not in the compiled file: the game will not find it',
                   kind=kind)
    rest = {}
    for kind, name in missing[LISTED_MISSING:]:
        reported.add((kind, name))
        rest.setdefault(kind, []).append(name)
    for kind in sorted(rest):
        report.add('error', 'ZONE-ASSET-NOT-LOADED', '(%d more %s)' % (len(rest[kind]), kind),
                   '%d more %s assets of the source list are not in the dump: %s' % (
                       len(rest[kind]), kind, ', '.join(rest[kind][:SHOWN_DIFFS])),
                   notice='these assets were asked for but are not in the compiled file: the game will not find them',
                   kind=kind, count=len(rest[kind]), names=rest[kind])
    added = {}
    for kind, name in dump_keys - wanted_keys:
        added[kind] = added.get(kind, 0) + 1
    for kind in sorted(added):
        report.add('info', 'ZONE-ASSET-ADDED', kind,
                   '%d %s asset(s) are in the dump but not in the source list (the builder added them as dependencies)' % (
                       added[kind], kind), count=added[kind])

    # R3 / R4 / R5
    binary = {}
    not_compared = {}
    no_source, no_dump_file = {}, {}
    same_root = os.path.normcase(os.path.realpath(source_tree)) == os.path.normcase(os.path.realpath(dump_dir))
    noise_count = 0
    for kind, name in sorted(wanted_keys & dump_keys):
        if kind not in TYPES:
            not_compared[kind] = not_compared.get(kind, 0) + 1
            continue
        folder, dump_ext, source_exts = TYPES[kind]
        source_file = next((p for p in (file_path(source_tree, kind, name, e) for e in source_exts) if is_file(p)), None)
        if source_file is None:
            no_source[kind] = no_source.get(kind, 0) + 1
            continue
        dump_file = file_path(dump_dir, kind, name, dump_ext)
        if not is_file(dump_file):
            no_dump_file[kind] = no_dump_file.get(kind, 0) + 1
            continue
        count(kind, 'compared')
        source_ext = os.path.splitext(source_file)[1] if source_exts != ('',) else ''
        same_path = same_root and source_file == dump_file
        both_json = dump_ext == '.json' and source_ext == '.json'
        # two JSON files with the same bytes can still name tables whose rows differ: those go on to the row comparison
        if same_path or same_file_content(source_file, dump_file) and (not both_json or _load(source_file) is None):
            count(kind, 'identical')
            if dump_ext != '.json':
                binary.setdefault(kind, {'identical': 0, 'same_decoded': 0, 'differs': 0, 'not_compared': 0})['identical'] += 1
            continue
        if both_json:
            outcome = _compare_json(report, kind, name, source_file, dump_file, noise_entries, (source_tree, dump_dir))
            noise_count += outcome[1]
            if outcome[0] == 'same':
                count(kind, 'identical')
            continue
        row = binary.setdefault(kind, {'identical': 0, 'same_decoded': 0, 'differs': 0, 'not_compared': 0})
        verdict = compare_decoded(dump_ext, source_file, dump_file) if source_ext == dump_ext else 'no-decoder'
        if verdict == 'same':
            row['same_decoded'] += 1
            count(kind, 'identical')
        elif verdict == 'differs':
            row['differs'] += 1
            report.add('warn', 'ZONE-BINARY-DIFFERS', name,
                       '%s "%s": the compiled file holds other content than the source after decoding both' % (kind, name),
                       notice='the compiled file does not hold what was written in the source', kind=kind)
        else:
            row['not_compared'] += 1
    if noise_count:
        report.add('info', 'ZONE-NOISE-ACCEPTED', zone,
                   '%d difference(s) matched an accepted entry of the noise file and are not findings' % noise_count,
                   count=noise_count)
    for kind in sorted(binary):
        row = binary[kind]
        report.add('info', 'ZONE-BINARY-SUMMARY', kind,
                   '%s files: %d identical, %d same after decoding, %d differ, %d not compared%s' % (
                       kind, row['identical'], row['same_decoded'], row['differs'], row['not_compared'],
                       ' (no decoder for them)' if row['not_compared'] else ''), **row)
    for kind in sorted(no_source):
        report.add('info', 'ZONE-SOURCE-MISSING', kind,
                   '%d %s asset(s) of the source list have no file in the source tree (stock or generated): '
                   'nothing to compare' % (no_source[kind], kind), count=no_source[kind])
    for kind in sorted(no_dump_file):
        report.add('info', 'ZONE-DUMP-NO-FILE', kind,
                   '%d %s asset(s) are in both lists, have a source file, but the dump wrote no file: not compared' % (
                       no_dump_file[kind], kind), count=no_dump_file[kind])
    if not_compared:
        report.add('info', 'ZONE-KIND-NOT-COMPARED', zone,
                   'no comparison exists for: %s' % ', '.join('%s %d' % kv for kv in sorted(not_compared.items())),
                   counts=dict(sorted(not_compared.items())))

    # R6
    if log:
        _check_log(report, log, wanted_keys, reported)

    for key, code, text in (
            ('filled', 'ZONE-VALUE-FILLED', 'the source wrote nothing and the compiled file holds a value (filled in by the builder)'),
            ('not_carried', 'ZONE-VALUE-NOT-CARRIED', 'the compiled format does not carry the value (stock holds it empty too)')):
        for kind in sorted(report.facts.get(key, {})):
            tally = report.facts[key][kind]
            report.add('info', code, kind, '%s: %d value(s) in %d asset(s): %s; e.g. %s' % (
                kind, tally['values'], tally['assets'], text, ', '.join(tally['examples'])), kind=kind)
    report.facts['types'] = {k: per_type[k] for k in sorted(per_type)}
    report.facts['totals'] = {key: sum(v[key] for v in per_type.values())
                              for key in ('source_csv', 'dump_csv', 'compared', 'identical')}
    report.facts['source_missing'] = dict(sorted(no_source.items()))
    report.facts['not_compared'] = dict(sorted(not_compared.items()))
    report.facts['binary'] = {k: binary[k] for k in sorted(binary)}
    return report


def is_table_list(value):
    return isinstance(value, list) and bool(value) and all(
        isinstance(item, str) and item.lower().endswith('.csv') for item in value)


def table_rows(root, names):
    """{first cell, lower case: [{column: cell}, ...]} over the listed csv tables of one tree; None when a
    table cannot be read inside that tree."""
    out = {}
    for rel in names:
        path = os.path.normpath(os.path.join(root, rel))
        if os.path.isabs(rel) or not path.startswith(os.path.normpath(root) + os.sep):
            return None
        try:
            with open(path, newline='', encoding='utf-8', errors='replace') as handle:
                rows = [[cell.strip() for cell in row] for row in csv.reader(handle) if row]
        except OSError:
            return None
        for row in rows[1:]:
            if row[0]:
                # rows are matched by their name without regard to case: the name cell is compared the same way
                out.setdefault(row[0].lower(), []).append(dict(zip(rows[0], [row[0].lower()] + row[1:])))
    return out


def _number(text):
    try:
        value = float(text)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def equal_cells(a, b):
    if a == b:
        return True
    x, y = _number(a), _number(b)
    if x is not None and y is not None:
        return equal_values(x, y)
    return (a == '' and y == 0) or (b == '' and x == 0)


def _compare_tables(report, kind, name, key, source, dumped):
    """True when rows are lost or differ, False when not, None when a listed table cannot be read. The builder
    may merge several source tables into one: the rows are compared, not the list of files."""
    one, two = table_rows(*source), table_rows(*dumped)
    if one is None or two is None:
        return None
    where = '%s "%s" %s' % (kind, name, key)
    lost = sorted(set(one) - set(two))
    added = len(set(two) - set(one))
    changed = []
    for row in sorted(set(one) & set(two)):
        if len(one[row]) != len(two[row]):
            changed.append(('%s (number of rows)' % row, len(one[row]), len(two[row])))
            continue
        for first, second in zip(one[row], two[row]):
            for column in sorted(set(first) | set(second)):
                if not equal_cells(first.get(column, ''), second.get(column, '')):
                    changed.append(('%s.%s' % (row, column), first.get(column, ''), second.get(column, '')))
    if lost:
        report.add('error', 'ZONE-ROW-NOT-LOADED', name,
                   '%s: %d row(s) written in the source table(s) are not in the compiled table: %s%s' % (
                       where, len(lost), ', '.join(lost[:SHOWN_DIFFS]),
                       '' if len(lost) <= SHOWN_DIFFS else ' (+%d more)' % (len(lost) - SHOWN_DIFFS)),
                   notice='what these rows define is not in the compiled file (for a sound table: that sound cannot play)',
                   kind=kind, table=key, count=len(lost), rows=lost[:SHOWN_DIFFS])
    if changed:
        shown = '; '.join('%s: source %s, compiled %s' % (p, _short(a), _short(b)) for p, a, b in changed[:SHOWN_DIFFS])
        report.add('warn', 'ZONE-ROW-DIFFERS', name,
                   '%s: %d value(s) differ: %s%s' % (
                       where, len(changed), shown,
                       '' if len(changed) <= SHOWN_DIFFS else ' (+%d more)' % (len(changed) - SHOWN_DIFFS)),
                   notice='the compiled file does not hold the value that was written in the source table',
                   kind=kind, table=key, count=len(changed), differences=[[p, a, b] for p, a, b in changed[:SHOWN_DIFFS]])
    if added:
        report.add('info', 'ZONE-ROW-ADDED', name,
                   '%s: %d row(s) are in the compiled table but in no source table' % (where, added),
                   kind=kind, table=key, count=added)
    if not lost and not changed:
        report.add('info', 'ZONE-TABLES-SAME', name,
                   '%s: the %d named row(s) of %d source table(s) are in the compiled table(s) with the same values' % (
                       where, len(one), len(source[1])), kind=kind, table=key, rows=len(one))
    return bool(lost or changed)


def _compare_json(report, kind, name, source_file, dump_file, noise, roots=None):
    """('same' | 'differs' | 'unparsable', number of differences accepted as noise); writes the finding."""
    one, two = _load(source_file), _load(dump_file)
    if one is None or two is None:
        bad = source_file if one is None else dump_file
        report.add('warn', 'ZONE-BINARY-DIFFERS', name,
                   '%s "%s": bytes differ and %s does not parse as JSON, so the values cannot be compared' % (
                       kind, name, 'the source' if bad == source_file else 'the dump'),
                   notice='the compiled file may not hold what was written in the source', kind=kind)
        return 'unparsable', 0
    first, second, tables_differ = one[0], two[0], False
    if roots and isinstance(first, dict) and isinstance(second, dict):
        for key in sorted(set(first) & set(second)):
            if not (is_table_list(first[key]) and is_table_list(second[key])):
                continue
            verdict = _compare_tables(report, kind, name, key, (roots[0], first[key]), (roots[1], second[key]))
            if verdict is None:
                continue        # a listed table cannot be read: the two lists are compared as written
            first = {k: v for k, v in first.items() if k != key}
            second = {k: v for k, v in second.items() if k != key}
            tables_differ = tables_differ or verdict
    found = diff_leaves(first, second)
    kept = [d for d in found if not is_noise(noise, kind, d[0])]
    accepted = len(found) - len(kept)
    # the source wrote nothing there: the builder filled a value in, no written value was lost
    filled = [d for d in kept if d[1] == ABSENT]
    # the compiled format has no room for the value: stock holds it empty too
    dropped = [d for d in kept if d[2] == '' and d[0] in NOT_CARRIED.get(kind, ())]
    kept = [d for d in kept if d not in filled and d not in dropped]
    for key, group in (('filled', filled), ('not_carried', dropped)):
        if group:
            tally = report.facts.setdefault(key, {}).setdefault(kind, {'values': 0, 'assets': 0, 'examples': []})
            tally['values'] += len(group)
            tally['assets'] += 1
            for path in [d[0] for d in group]:
                if path not in tally['examples'] and len(tally['examples']) < 4:
                    tally['examples'].append(path)
    if kept:
        shown = '; '.join('%s: source %s, compiled %s' % (p, _short(a), _short(b)) for p, a, b in kept[:SHOWN_DIFFS])
        more = '' if len(kept) <= SHOWN_DIFFS else ' (+%d more)' % (len(kept) - SHOWN_DIFFS)
        report.add('warn', 'ZONE-VALUE-DIFFERS', name,
                   '%s "%s": %d value(s) differ: %s%s' % (kind, name, len(kept), shown, more),
                   notice='the compiled file does not hold the value that was written in the source',
                   kind=kind, count=len(kept), differences=[[p, a, b] for p, a, b in kept[:SHOWN_DIFFS]])
        return 'differs', accepted
    return ('differs' if tables_differ else 'same'), accepted


def _load(path):
    try:
        return (common.load_json(path),)
    except (OSError, ValueError):
        return None


def _short(value):
    text = repr(value) if not isinstance(value, str) else '"%s"' % value
    return text if len(text) <= 40 else text[:37] + '...'


def _check_log(report, log, wanted_keys, reported):
    name = os.path.basename(log)
    try:
        loaded, problems = read_log(log)
    except OSError as error:
        report.add('error', 'ZONE-LOAD-ERROR', name, 'the log cannot be read: %s' % error)
        return
    report.facts['log'] = {'loaded': len(loaded), 'problems': len(problems)}
    if not loaded:
        report.add('info', 'ZONE-LOG-NO-ASSETS', name,
                   'the log holds no "Loading asset" line: the loaded set could not be compared')
    else:
        for kind, asset in sorted(wanted_keys - loaded):
            if (kind, asset) in reported:
                continue
            report.add('error', 'ZONE-ASSET-NOT-LOADED', asset,
                       '%s "%s" is in the source list but the loader never reported loading it' % (kind, asset),
                       notice='this asset was asked for but the game loader did not load it', source='log', kind=kind)
    distinct = {}
    for level, text in problems:
        distinct[(level, text)] = distinct.get((level, text), 0) + 1
    for (level, text), count in sorted(distinct.items()):
        report.add('error', 'ZONE-LOAD-ERROR', name, '%s from the loader: %s' % (level, text),
                   notice='the loader reported a failure while reading the compiled file', count=count)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Compare the source list and tree of a zone with what the loader read back.')
    ap.add_argument('--source-csv', required=True, metavar='FILE', help='zone_source/<zone>.csv')
    ap.add_argument('--source-tree', required=True, metavar='DIR', help='zonetool/<zone> source tree')
    ap.add_argument('--dump', required=True, metavar='DIR', help='folder ZoneTool wrote for the zone (holds <zone>.csv)')
    ap.add_argument('--log', metavar='FILE', help='ZoneTool output of the verify/dump run')
    ap.add_argument('--noise', metavar='FILE', help='accepted differences (iw7.readback-noise/1)')
    ap.add_argument('--types', metavar='KINDS', help='comma list of the asset kinds the dump was limited to '
                    '(-dumpzonetypes); other kinds are not judged missing')
    common.add_common_args(ap)
    args = ap.parse_args(argv)
    for label, path, check in (('--source-csv', args.source_csv, os.path.isfile), ('--source-tree', args.source_tree, os.path.isdir),
                               ('--dump', args.dump, os.path.isdir)):
        if not check(path):
            sys.stderr.write('%s: %s does not exist\n' % (label, path))
            return 2
    intent = common.Intent.load(args.intent) if args.intent else common.Intent()
    report = audit(args.source_csv, args.source_tree, args.dump, intent, log=args.log, noise=args.noise,
                   types=args.types.split(',') if args.types else None)
    return common.finish(report, args, intent=intent)


if __name__ == '__main__':
    sys.exit(main())
