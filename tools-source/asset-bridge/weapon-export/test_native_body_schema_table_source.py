"""Source constants projection/adoption tests; no SCHEMA import, header write or C++."""
import ast
import copy
import hashlib
import importlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
PRODUCT_HEADER_PIN = (1073140, 'dbedd4632d8bb20686c8c1355d4b0200fc2c6149ba141897007f41252f555b75')
CPP_FIXTURE_PIN = (31185, 'b7128cb427ffcda9a1826946d448b0a092e94ce1dedee8823a4377f918c009a4')
IMPORT_PINS = {
    'generate_native_body_schema.py': (50953, '35770c090a883e5edc2b28783a92d2954563b4fd1a62ca27949efbee54732939'),
    'generate_definition_readset.py': (11568, '809598493e3c67cc45b5e20151408ad2778a7e74e8b42ec2c304ea65d59c836e'),
}
# Executable Source is checked BEFORE either import. No sys.path mutation.
for _name, (_size, _sha) in IMPORT_PINS.items():
    _raw = (HERE / _name).read_bytes().decode('utf-8').replace('\r\n', '\n').encode()
    if len(_raw) != _size or hashlib.sha256(_raw).hexdigest() != _sha:
        raise ValueError('Test executable Source changed before import: ' + _name)
G = importlib.import_module('generate_native_body_schema')


def source_pin(raw):
    return {'git_blob': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest(),
            'bytes_lf': len(raw), 'sha256_lf': hashlib.sha256(raw).hexdigest()}


def same(test, left, right, path=()):
    """Every field/type/presence; all lists and declaration maps retain order."""
    test.assertIs(type(left), type(right), path)
    if type(left) is dict:
        test.assertEqual(set(left), set(right), path)
        if path and path[-1] in ('members', 'direct_sites', 'manual_handlers', 'source_pins', 'pins'):
            test.assertEqual(list(left), list(right), path)
        for key in left: same(test, left[key], right[key], path + (key,))
    elif type(left) in (list, tuple):
        test.assertEqual(len(left), len(right), path)
        for i, (a, b) in enumerate(zip(left, right)): same(test, a, b, path + (i,))
    else: test.assertEqual(left, right, path)


def read_cpp(text):
    """Independent finite reader of emitted aggregate syntax, never C++ eval.

    Record fields/types come from the emitted declarations, not CPP_RECORDS.
    This reader contains the reviewed data-format interpretation, not1213 rules.
    """
    records = {}
    for name, body in re.findall(r'^struct (\w+) \{([^\n]*)\};$', text, re.M):
        fields = []
        for item in body.split(';'):
            if item:
                match = re.fullmatch(r'\s*(std::uint32_t|std::uint64_t|bool|\w+) (\w+)', item)
                if not match: raise ValueError('Unknown aggregate field syntax')
                fields.append((match[2], match[1]))
        if name in records: raise ValueError('Duplicate record declaration')
        records[name] = fields
    pool_text = re.search(r'inline constexpr char string_pool\[\] = \{(.*?)\};', text, re.S)[1]
    pool = bytes(int(v, 16) for v in re.findall(r'static_cast<char>\(0x([0-9a-f]{2})\)', pool_text))
    if re.sub(r'static_cast<char>\(0x[0-9a-f]{2}\)|[,\s]', '', pool_text): raise ValueError('Unknown char-pool syntax')
    def typed(value, kind):
        if kind == 'bool':
            if type(value) is not bool: raise ValueError('Boolean lost its type')
            return value
        if kind in ('std::uint32_t', 'std::uint64_t'):
            bits = 32 if kind.endswith('32_t') else 64
            if type(value) is not int or not 0 <= value < 1 << bits: raise ValueError('Record narrowing')
            return value
        fields = records[kind]
        if type(value) is not tuple or len(value) != len(fields): raise ValueError('Record width')
        return {name: typed(v, ty) for v, (name, ty) in zip(value, fields)}
    tables = {}
    for kind, count, name, body in re.findall(r'inline constexpr std::array<([^,>]+),([0-9]+)> (\w+)\{\{(.*?)\}\};', text, re.S):
        if name in tables: raise ValueError('Duplicate table')
        tokens = re.findall(r'true|false|[0-9]+(?:ULL|U)|[{},]', body)
        if re.sub(r'true|false|[0-9]+(?:ULL|U)|[{},\s]', '', body): raise ValueError('Unknown initializer syntax')
        position = 0
        def value():
            nonlocal position
            token = tokens[position]; position += 1
            if token == '{':
                values = []
                while tokens[position] != '}':
                    values.append(value())
                    if tokens[position] == ',': position += 1
                    elif tokens[position] != '}': raise ValueError('Initializer separator')
                position += 1
                return tuple(values)
            if token in ('true', 'false'): return token == 'true'
            if re.fullmatch(r'[0-9]+(?:ULL|U)', token): return int(token.rstrip('UL'))
            raise ValueError('Unknown initializer token')
        rows = []
        while position < len(tokens):
            rows.append(typed(value(), kind))
            if tokens[position] != ',': raise ValueError('Row terminator')
            position += 1
        if len(rows) != int(count): raise ValueError('Declared table count')
        tables[name] = rows
    return tables, pool


def reconstruct(text):
    tables, pool = read_cpp(text)
    def span(value, table):
        data = pool if table == 'pool' else tables[table]
        first, count = value['offset'], value['count']
        if first > len(data) or count > len(data) - first: raise ValueError('Orphan span')
        return data[first:first + count]
    def item(table, index):
        if type(index) is not int or not 0 <= index < len(tables[table]): raise ValueError('Orphan ID')
        return tables[table][index]
    def string(index): return span(item('strings', index), 'pool').decode('utf-8', errors='strict')
    def integer(row):
        if row['negative'] and not row['magnitude']: raise ValueError('Negative zero')
        return -row['magnitude'] if row['negative'] else row['magnitude']
    type_tags = [string(v) for v in tables['type_tags']]
    op_tags = [string(v) for v in tables['op_tags']]
    manual_tags = [string(v) for v in tables['manual_tags']]
    type_names = [string(v['name']) for v in tables['types']]
    structure_names = [string(v['name']) for v in tables['structures']]
    optional_types = ('pack', 'size_basis', 'element', 'extents', 'min', 'max', 'values', 'members',
                      'bitfields', 'conversion_basis', 'semantic_domain_unknown', 'storage_domain_only')
    optional_ops = ('field', 'key', 'flavor', 'type', 'count', 'count_type', 'semantic_domain_unknown', 'handler')
    types = {}
    for row in tables['types']:
        d = {'kind': type_tags[row['kind']], 'size': row['size'], 'align': row['align']}
        for bit, key in enumerate(optional_types):
            if not row['present'] & (1 << bit): continue
            if key in ('pack', 'semantic_domain_unknown', 'storage_domain_only'): v = row[key]
            elif key in ('size_basis', 'conversion_basis'): v = string(row[key])
            elif key == 'element':
                if row['element_tag'] == 1:
                    if not 0 <= row['element'] < len(type_names): raise ValueError('Orphan element type ID')
                    v = type_names[row['element']]
                elif row['element_tag'] == 2 and d['kind'] == 'pointer':
                    v = string(row['element'])
                    if v in type_names: raise ValueError('Known element label must use tag1')
                else: raise ValueError('Noncanonical element tag/kind')
            elif key == 'extents': v = list(span(row[key], 'extents'))
            elif key in ('min', 'max'): v = integer(row['minimum' if key == 'min' else 'maximum'])
            elif key == 'values': v = [integer(n) for n in span(row[key], 'integers')]
            elif key == 'members':
                v = {}
                for pair in span(row[key], 'enum_members'):
                    name = string(pair['name'])
                    if name in v: raise ValueError('Duplicate enum declaration')
                    v[name] = integer(pair['value'])
            elif key == 'bitfields': v = [(string(n['name']), n['value']) for n in span(row[key], 'bitfields')]
            else: raise AssertionError(key)
            d[key] = v
        types[string(row['name'])] = d
        if d['kind'] in ('pointer', 'array') and 'element' not in d: raise ValueError('Missing pointer/array element')
        if d['kind'] == 'array' and row['element_tag'] != 1: raise ValueError('Array element is not a known type')
        if 'element' not in d and (row['element_tag'] != 0 or row['element'] != 0): raise ValueError('Absent element has a reference')
    structures = {}
    for owner, row in enumerate(tables['structures']):
        operations = []
        for op in span(row['ops'], 'operations'):
            d = {'op': op_tags[op['tag']], 'line': op['line']}
            for bit, key in enumerate(optional_ops):
                if not op['present'] & (1 << bit): continue
                if key in ('field', 'key', 'flavor'): v = string(op[key])
                elif key in ('type', 'count_type'): v = type_names[op[key]]
                elif key == 'count':
                    if op['count_tag'] == 1: v = op['fixed_count']
                    elif op['count_tag'] == 2: v = string(op['named_count'])
                    else: raise ValueError('Present count has no form')
                elif key == 'semantic_domain_unknown': v = op[key]
                elif key == 'handler':
                    manual = item('manuals', op['manual'])
                    if manual['owner'] != owner or manual['line'] != op['line']: raise ValueError('Manual owner/line mismatch')
                    v = [manual_tags[manual['tag']]] + [string(i) for i in span(manual['arguments'], 'argument_ids')]
                else: raise AssertionError(key)
                d[key] = v
            operations.append(d)
        structures[structure_names[owner]] = {'first': row['first'], 'keys': [string(v) for v in span(row['keys'], 'key_ids')],
            'last': row['last'], 'layout': copy.deepcopy(types[type_names[row['layout']]]),
            'source': string(row['source']), 'ops': operations}
    direct = {}
    for row in tables['direct_owners']:
        direct[structure_names[row['owner']]] = [{'line': v['line'], 'text': string(v['text'])} for v in span(row['items'], 'direct_sites')]
    manuals = {}
    for row in tables['manual_owners']:
        entries = []
        for manual_id in span(row['items'], 'manual_ids'):
            v = item('manuals', manual_id)
            if v['owner'] != row['owner']: raise ValueError('Manual list owner')
            entries.append((v['line'], manual_tags[v['tag']], *(string(i) for i in span(v['arguments'], 'argument_ids'))))
        manuals[structure_names[row['owner']]] = entries
    def pins(table): return {string(p['name']): string(p['sha256']) for p in tables[table]}
    meta = tables['metadata'][0]
    schema = {'coverage': {'typed_structures': meta['typed_structures'], 'macro_sites': meta['macro_sites'],
        'direct_sites': direct, 'manual_handlers': manuals, 'complete_pinned_extraction': meta['complete_pinned_extraction'],
        'actual_input_admissibility': meta['actual_input_admissibility'], 'runtime_abi_verified': meta['runtime_abi_verified']},
        'enum_conversion_source': {'json_revision': string(meta['json_revision']), 'pins': pins('conversion_pins')},
        'pin': string(meta['pin']), 'platform': string(meta['platform']), 'source_pins': pins('source_pins'),
        'structures': structures, 'types': types}
    provenance = {string(p['role']): {'git_blob': string(p['git_blob']), 'bytes_lf': p['bytes_lf'], 'sha256_lf': string(p['sha256_lf'])} for p in tables['provenance']}
    return schema, provenance, pins('manual_body_pins')


class TableSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (HERE / 'native_body_schema.py').read_bytes().decode('utf-8').replace('\r\n', '\n').encode()
        cls.schema = G._cpp_literal(cls.raw, G.CPP_SCHEMA_PIN)
        cls.provenance = {'schema': dict(G.CPP_SCHEMA_PIN), 'extraction_generator': dict(G.CPP_EXTRACTION_GENERATOR_PIN),
            'projection_generator': source_pin((HERE / 'generate_native_body_schema.py').read_text(encoding='utf-8').encode()),
            'body_validator': {'git_blob': '86f6f6c42840913bddeda864053475884ab493fc', 'bytes_lf': 17221,
                               'sha256_lf': '820c8580549c3d0e5022e58d5f5bfc120d23db64b9f9f6e4513e05494c178626'}}
        cls.text = G.render_cpp(cls.raw, G.CPP_SCHEMA_PIN, cls.provenance)

    def test_adopted_header_raw_pin_and_every_field(self):
        with (HERE / 'native_pair_body_schema.hpp').open('rb') as stream:
            raw = stream.read(PRODUCT_HEADER_PIN[0] + 1)
        self.assertIs(stream.closed, True)
        self.assertEqual((len(raw), hashlib.sha256(raw).hexdigest()), PRODUCT_HEADER_PIN)
        self.assertEqual(raw, self.text.encode('utf-8'))
        schema, provenance, manual_pins = reconstruct(raw.decode('utf-8', errors='strict'))
        same(self, schema, self.schema)
        same(self, provenance, self.provenance)
        same(self, manual_pins, G.MANUAL_BODY_SHA256)

    def test_table_header_and_source_test_exported_once(self):
        exports = json.loads((HERE.parents[2] / 'product.json').read_text(encoding='utf-8'))['exports']
        for name in ('native_pair_body_schema.hpp', 'test_native_pair_body_schema.cpp',
                     'test_native_body_schema_table_source.py'):
            self.assertEqual(exports.count('tools-source/asset-bridge/weapon-export/' + name), 1)
        with (HERE / 'test_native_pair_body_schema.cpp').open('rb') as stream:
            raw = stream.read(CPP_FIXTURE_PIN[0] + 1)
        self.assertIs(stream.closed, True)
        self.assertEqual((len(raw), hashlib.sha256(raw).hexdigest()), CPP_FIXTURE_PIN)

    def test_every_field_and_provenance_roundtrip(self):
        actual, provenance, manual_pins = reconstruct(self.text)
        same(self, actual, self.schema)
        same(self, provenance, self.provenance)
        same(self, manual_pins, G.MANUAL_BODY_SHA256)
        self.assertNotEqual(provenance['projection_generator'], provenance['extraction_generator'])
        self.assertEqual(len(actual['types']), 239)
        self.assertEqual(sum(len(s['ops']) for s in actual['structures'].values()), 1213)

    def test_deterministic_ram_only(self):
        with patch.object(Path, 'open', side_effect=AssertionError('Renderer IO')):
            again = G.render_cpp(self.raw, G.CPP_SCHEMA_PIN, self.provenance)
        self.assertEqual(self.text.encode(), again.encode())
        self.assertNotIn('\r', self.text)
        self.assertNotIn('size_t', self.text)
        self.assertNotIn('WeaponDef*', self.text)

    def test_pin_first_before_ast_and_no_schema_eval(self):
        with patch.object(ast, 'parse', side_effect=AssertionError('Pin must precede AST')):
            with self.assertRaises(ValueError): G.render_cpp(self.raw + b' ', G.CPP_SCHEMA_PIN, self.provenance)
            wrong_blob = dict(G.CPP_SCHEMA_PIN, git_blob='0' * 40)
            with self.assertRaises(ValueError): G._cpp_literal(self.raw, wrong_blob)
        bad = b'"""Source"""\nSCHEMA = __import__("os").getcwd()\n'
        with self.assertRaises((ValueError, TypeError)): G._cpp_literal(bad, source_pin(bad))
        bad = b'"""Source"""\nimport os\nSCHEMA = {}\n'
        with self.assertRaises(ValueError): G._cpp_literal(bad, source_pin(bad))

    def test_unknown_shapes_and_types_refuse(self):
        mutations = [
            lambda s:s['types']['int'].__setitem__('kind', 'new-kind'),
            lambda s:s['types']['int'].__setitem__('unexpected', 1),
            lambda s:s['structures']['ADSOverlay']['ops'][0].__setitem__('unexpected', 1),
            lambda s:s['structures']['ADSOverlay']['ops'][0].__setitem__('op', 'NEW_OP'),
            lambda s:s['structures']['NoteTrackToSoundEntry']['ops'][1].__setitem__('count', 0),
            lambda s:s['coverage'].__setitem__('actual_input_admissibility', 0),
            lambda s:s['types']['WeaponChargeType'].__setitem__('storage_domain_only', 1),
            lambda s:s['types']['int'].__setitem__('min', -1.5),
            lambda s:s['types']['int'].__setitem__('max', 1 << 64),
            lambda s:s['types']['int'].__setitem__('min', -(1 << 64)),
        ]
        for mutation in mutations:
            candidate = copy.deepcopy(self.schema);mutation(candidate)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError): G._cpp_project(candidate, self.provenance)

    def test_independent_comparator_information_loss(self):
        # These mutants target copied decoded data, never a second handwritten rule table.
        mutations = [
            lambda s:s['types']['std::uint64_t'].pop('min'),
            lambda s:s['types']['WeaponChargeType'].pop('values'),
            lambda s:s['types']['WeaponChargeType'].pop('members'),
            lambda s:s['types']['std::uint64_t'].__setitem__('max', (1 << 63) - 1),
            lambda s:s['types']['PenetrateType']['members'].pop('PENETRATE_TYPE_TABLE_ENTRY_COUNT'),
            lambda s:s['types']['SuitAnimType'].__setitem__('values', [0, 1, 2, 3, 4]),
            lambda s:s['structures']['ADSOverlay']['ops'].reverse(),
            lambda s:s['structures']['WeaponAttachment']['ops'][6].__setitem__('key', 'weapClass'),
            lambda s:next(o for o in s['structures']['WeaponDef']['ops'] if o.get('key') == 'unk0.unk_18').__setitem__('key', 'unk_18'),
            lambda s:s['structures']['NoteTrackToSoundEntry']['ops'][1].__setitem__('count_type', 'unsigned short'),
            lambda s:s['structures']['NoteTrackToSoundEntry']['ops'][2].__setitem__('count', 'differentCounter'),
            lambda s:s['coverage']['direct_sites']['WeaponDef'][0].__setitem__('text', 'changed'),
            lambda s:s['coverage']['direct_sites']['WeaponDef'][0].__setitem__('line', 413),
            lambda s:s['structures']['ADSOverlay'].__setitem__('source', 'weaponattachment.cpp'),
            lambda s:s['structures']['ADSOverlay'].__setitem__('first', 239),
            lambda s:s['structures']['ADSOverlay'].__setitem__('last', 249),
            lambda s:s['source_pins'].__setitem__('iw7/structs.hpp', '0' * 64),
            lambda s:s['enum_conversion_source']['pins'].__setitem__('deps/premake/json.lua', '0' * 64),
            lambda s:s['types']['GfxDrawSurfFields']['bitfields'].reverse(),
        ]
        # Root fields which are exact booleans must not compare equal to0/1.
        for key in ('complete_pinned_extraction', 'actual_input_admissibility', 'runtime_abi_verified'):
            mutations.append(lambda s,k=key:s['coverage'].__setitem__(k, int(s['coverage'][k])))
        for structure, index in (('AttCharged', 0), ('WeaponDef', 568)):
            mutations.append(lambda s,n=structure,i=index:s['structures'][n]['ops'][i].__setitem__('semantic_domain_unknown', 1))
        for key in ('semantic_domain_unknown', 'storage_domain_only'):
            mutations.append(lambda s,k=key:s['types']['WeaponChargeType'].__setitem__(k, 1))
        for mutate in mutations:
            candidate = copy.deepcopy(self.schema); mutate(candidate)
            with self.subTest(mutation=mutate), self.assertRaises(AssertionError): same(self, self.schema, candidate)

    def test_encoding_boundaries_and_orphan_references(self):
        self.assertEqual(G._cpp_integer((1 << 64) - 1), (False, (1 << 64) - 1))
        self.assertEqual(G._cpp_integer(-(1 << 63)), (True, 1 << 63))
        self.assertEqual(G._cpp_integer(0), (False, 0))
        with self.assertRaises(ValueError): G._cpp_u(1 << 32, 32)
        tables, pool = G._cpp_project(self.schema, self.provenance)
        for table, index, replacement in [('types', 8, 239), ('manuals', 0, 41), ('structures', 6, (1213, 1))]:
            candidate = copy.deepcopy(tables);row = list(candidate[table][0])
            if table == 'types': row[2] |= 1 << 2;row[7] = 1
            row[index] = replacement; candidate[table][0] = tuple(row)
            with self.subTest(table=table), self.assertRaises(ValueError): G._cpp_check_tables(candidate, pool)
        candidate = copy.deepcopy(tables);candidate['integers'][0] = (True, 0)
        with self.assertRaises(ValueError): G._cpp_check_tables(candidate, pool)
        # A textual orphan is also detected by the independent finite Source reader.
        corrupted = self.text.replace('0U,0U,0U,', '4294967296U,0U,0U,', 1)
        self.assertNotEqual(corrupted, self.text)
        with self.assertRaises(ValueError): reconstruct(corrupted)

    def test_unexpanded_pointer_labels_and_canonical_tag(self):
        actual = reconstruct(self.text)[0]
        unexpanded = [(name, value['element']) for name, value in self.schema['types'].items()
                      if value['kind'] == 'pointer' and value['element'] not in self.schema['types']]
        self.assertEqual(len(unexpanded), 30)
        for name, label in unexpanded:
            self.assertEqual(actual['types'][name]['element'], label)
        self.assertEqual(actual['types']['const char*']['element'], 'const char')
        self.assertEqual(actual['types']['XAnimParts**']['element'], 'XAnimParts*')
        tables, pool = G._cpp_project(self.schema, self.provenance)
        known = next(i for i,row in enumerate(tables['types']) if row[1] == 1 and row[7] == 1)
        candidate = copy.deepcopy(tables);row = list(candidate['types'][known]);target_name_id = candidate['types'][row[8]][0]
        row[7] = 2;row[8] = target_name_id;candidate['types'][known] = tuple(row)
        # The Source string would be identical, but the codec must reject the
        # noncanonical known-type-as-unexpanded representation independently.
        with self.assertRaises(ValueError): G._cpp_check_tables(candidate, pool)
        with patch.object(G, '_cpp_project', return_value=(candidate,pool)):
            bad_text = G.render_cpp(self.raw, G.CPP_SCHEMA_PIN, self.provenance)
        with self.assertRaises(ValueError): reconstruct(bad_text)

    def test_manual_order_and_provenance_no_retagging(self):
        candidate = copy.deepcopy(self.schema)
        candidate['coverage']['manual_handlers']['WeaponDef'][0] = (413, 'object', 'overlay', 'ADSOverlay')
        with self.assertRaises(ValueError): G._cpp_project(candidate, self.provenance)
        candidate = copy.deepcopy(self.schema)
        ops = candidate['structures']['WeaponAttachment']['ops'];manual = next(o for o in ops if o['op'] == 'MANUAL')
        ops.remove(manual);ops.insert(0, manual)
        with self.assertRaises(AssertionError): same(self, reconstruct(self.text)[0], candidate)
        provenance = copy.deepcopy(self.provenance);provenance['extraction_generator'] = provenance['projection_generator']
        with self.assertRaises(ValueError): G.render_cpp(self.raw, G.CPP_SCHEMA_PIN, provenance)

    def test_legacy_source_and_targeted_behavior_parity(self):
        # Finite pinned parent Source, not installed/native input.
        repo = HERE.parents[2]
        parent = subprocess.check_output(['git', '-C', str(repo), 'show',
            '77244a5f1143d5482642dbd8143a7403b8f46412:tools-source/asset-bridge/weapon-export/generate_native_body_schema.py']).decode()
        self.assertEqual(hashlib.sha256(parent.encode()).hexdigest(), G.CPP_EXTRACTION_GENERATOR_PIN['sha256_lf'])
        old, new = ast.parse(parent), ast.parse((HERE / 'generate_native_body_schema.py').read_text(encoding='utf-8'))
        old_functions = {n.name:n for n in old.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        new_functions = {n.name:n for n in new.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        for name, node in old_functions.items():
            self.assertEqual(ast.dump(node, include_attributes=False), ast.dump(new_functions[name], include_attributes=False), name)
        for name in ('PIN', 'PINS', 'CONVERSION_PINS', 'MANUAL', 'MANUAL_KEYS', 'MANUAL_BODY_SHA256'):
            def literal(tree):return ast.literal_eval(next(n.value for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)))
            same(self, literal(old), literal(new))
        namespace = dict(vars(G))
        for name in ('generate', 'extract', 'render'):
            module = ast.Module(body=[old_functions[name]], type_ignores=[])
            exec(compile(module, 'pinned-parent-selected-function', 'exec'), namespace)
        self.assertEqual(namespace['render'](self.schema), G.render(self.schema))
        blobs = {key:'' for key in (*G.PINS, *G.CONVERSION_PINS)}
        def error(call):
            try:call()
            except ValueError as exc:return type(exc), str(exc)
            self.fail('Expected original pin refusal')
        self.assertEqual(error(lambda:namespace['extract'](blobs)), error(lambda:G.extract(blobs)))
        with tempfile.TemporaryDirectory(prefix='owned-schema-Source-parity-') as directory:
            root = Path(directory);path = root/'src/zonetool/zonetool/iw7/assets/weapondef.cpp'
            path.parent.mkdir(parents=True);path.write_text('// Authored wrong Source pin only.\n', encoding='utf-8')
            self.assertEqual(error(lambda:namespace['generate'](root)), error(lambda:G.generate(root)))


if __name__ == '__main__':
    unittest.main()
