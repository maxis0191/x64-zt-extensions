"""Owned synthetic input/Source causals. No native, captured body or game work."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import generate_native_body_schema as generator
from native_body_schema import SCHEMA
import neutral_pair_bodies as production
from test_neutral_pair_inputs import fixture, encode, sha, CSV


def zero(ty):
    d = SCHEMA['types'][ty]
    return False if d['kind'] == 'bool' else d['values'][0] if d['kind'] == 'enum' and d['values'] else 0


def authored(ty):
    """Owned finite fixture builder, not a serializer or actual body capture."""
    result = {}
    for r in SCHEMA['structures'][ty]['ops']:
        kind = r['op']
        if kind == 'MANUAL':
            op, *args = r['handler']
            if op == 'object': result[args[0]] = authored(args[1])
            elif op == 'entries': result[args[0]] = None
            elif op == 'graphs': result['accuracyGraphKnots'] = [None, None]
            elif op == 'definition': result['weapDef'] = authored('WeaponDef')
            elif op == 'original_graphs':
                result['accuracyGraphName'] = ['', '']
                result['originalAccuracyGraphKnotCount'] = [0, 0]
            elif op == 'overrides':
                for key, target in [('animOverrides', 'AnimOverride'), ('sfxOverrides', 'SFXOverride'), ('vfxOverrides', 'VFXOverride')]:
                    result[key] = [authored(target) for _ in range(21)]
            elif op == 'unk_material': result.setdefault('unk0', {})['material'] = None
            continue
        key, native = r['key'], r['type']
        if kind in ('FIELD', 'FIELD_RENAME'): value = zero(native)
        elif 'ARR' in kind and SCHEMA['types'][native]['kind'] == 'array':
            elem = SCHEMA['types'][native]['element']
            scalar = SCHEMA['types'][elem]['kind'] in ('int', 'enum', 'float', 'double', 'bool')
            value = [zero(elem) if scalar else None for _ in range(r['count'])]
        else: value = None
        if key.startswith('unk0.'): result.setdefault('unk0', {})[key[5:]] = value
        else: result[key] = value
    return result


def private_pair():
    weapon, pap = authored('WeaponCompleteDef'), authored('WeaponAttachment')
    weapon.update(szInternalName='sdk_shredder_clone_zm', szDisplayName='A',
                  attachments6=['sdk_shredder_clone_pap_zm'], szAltWeaponName='abcde')
    weapon['weapDef']['weapType'] = 1
    pap.update(szInternalName='sdk_shredder_clone_pap_zm', szDisplayName='abcde', weaponType=0, papAttachment=True)
    return weapon, pap


def invoke(weapon, pap):
    report, wr, ar = fixture(encode(weapon), encode(pap))
    raw = encode(report)
    return production.validate_private_pair_bodies(raw, len(raw), sha(raw), wr, ar, CSV)


class NativeBodySchemaTests(unittest.TestCase):
    def test_complete_source_tables_and_critical_independent_types(self):
        self.assertEqual(len(SCHEMA['structures']), 41)
        self.assertEqual(SCHEMA['coverage']['macro_sites'], 1203)
        self.assertFalse(SCHEMA['coverage']['actual_input_admissibility'])
        expected = {'WeaponCompleteDef': (312, 8), 'WeaponDef': (5144, 8), 'WeaponAttachment': (536, 8),
                    'Material': (280, 8), 'FxCombinedDef': (16, 8), 'NoteTrackToSoundEntry': (24, 8),
                    'NoteTrackToSuitSoundEntry': (24, 8), 'GrenadeRotationParams': (52, 4),
                    'GfxDrawSurfFields': (16, 8), 'GfxDrawSurf': (16, 8), 'MaterialInfo': (48, 8)}
        for ty, pair in expected.items():
            self.assertEqual((SCHEMA['types'][ty]['size'], SCHEMA['types'][ty]['align']), pair)
        attachment = {r.get('key'): r for r in SCHEMA['structures']['WeaponAttachment']['ops']}
        self.assertEqual(attachment['reticles']['count_type'], 'int')
        self.assertEqual(attachment['worldModelVariations']['count_type'], 'unsigned int')
        self.assertEqual(production.__all__, ('validate_private_pair_bodies',))

    def test_full_private_positive_returns_none_and_exact_unpadded_demand(self):
        weapon, pap = private_pair()
        original = copy.deepcopy((weapon, pap))
        self.assertIsNone(invoke(weapon, pap))
        self.assertEqual((weapon, pap), original)
        trace = production._inspect(weapon, pap)
        self.assertEqual(trace.offset, 6096)
        self.assertEqual(trace.cells, 1)
        self.assertEqual(trace.script_entries, 1)
        self.assertEqual([e[2] for e in trace.events], [0, 312, 334, 336, 344, 352, 378, 384, 5528, 6064, 6090])

    def test_raw_pin_refuses_before_either_body_decoder(self):
        w, a = private_pair(); report, wr, ar = fixture(encode(w), encode(a)); raw = encode(report)
        with patch.object(production, '_decode', side_effect=AssertionError('body decoded')) as decoder:
            with self.assertRaises(ValueError): production.validate_private_pair_bodies(raw, len(raw), '0' * 64, wr, ar, CSV)
            with self.assertRaises(ValueError): production.validate_private_pair_bodies(raw, len(raw), sha(raw), wr + b' ', ar, CSV)
            decoder.assert_not_called()

    def test_every_typed_family_positive_and_closed_refusal(self):
        for ty in SCHEMA['structures']:
            value = authored(ty)
            parent = {'accuracyGraphKnots': [None, None]} if ty == 'WeaponDef' else None
            with self.subTest(ty=ty):
                production._walk(ty, value, ty, production._Trace(), parent)
                value['unexplained'] = 0
                with self.assertRaisesRegex(ValueError, 'closed object'):
                    production._walk(ty, value, ty, production._Trace(), parent)

    def test_each_optional_block_and_location22_use_full_allocation(self):
        for rule in SCHEMA['structures']['WeaponAttachment']['ops']:
            if rule['op'] != 'OPTIONAL': continue
            w, a = private_pair()
            target = SCHEMA['types'][rule['type']]['element']
            a[rule['key']] = authored(target)
            with self.subTest(block=rule['key']):
                self.assertIsNone(invoke(w, a))
                trace = production._inspect(w, a)
                self.assertEqual(trace.offset, 6096 + SCHEMA['types'][target]['size'])
        w, a = private_pair(); a['locationDamage'] = [0.0] * 22
        self.assertIsNone(invoke(w, a))
        self.assertEqual(production._inspect(w, a).offset, 6184)
        a['locationDamage'].pop()
        with self.assertRaises(ValueError): invoke(w, a)

    def test_override_tables_interleave_by_index_in_native_order(self):
        d = authored('WeaponDef')
        d['animOverrides'][0]['overrides'] = 'aaaaaaa'
        d['sfxOverrides'][0]['overrides'] = 'bbbbbbb'
        d['animOverrides'][1]['overrides'] = 'ccccccc'
        trace = production._Trace(); production._walk('WeaponDef', d, 'def', trace, {'accuracyGraphKnots': [None, None]})
        events = [e[0] for e in trace.events if not e[0].endswith('.name')]
        self.assertEqual(events, ['def.animOverrides[0].overrides', 'def.sfxOverrides[0].overrides', 'def.animOverrides[1].overrides'])

    def test_private_identity_profile_pap_and_all_six_slots(self):
        for field, value in [('szInternalName', 'wrong'), ('weaponType', 3), ('papAttachment', 1)]:
            w, a = private_pair(); a[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): invoke(w, a)
        w, a = private_pair(); w['weapDef']['weapType'] = 3
        with self.assertRaises(ValueError): invoke(w, a)
        for alteration in ('missing', 'duplicate', 'wrongslot', 'alias'):
            w, a = private_pair()
            if alteration == 'missing': w['attachments6'] = None
            elif alteration == 'duplicate': w['attachments5'] = w['attachments6'][:]
            elif alteration == 'wrongslot': w['attachments5'], w['attachments6'] = w['attachments6'], None
            else: w['attachments6'] = [',' + a['szInternalName']]
            with self.subTest(alteration=alteration), self.assertRaises(ValueError): invoke(w, a)

    def test_scalar_types_ranges_enums_floating_targets(self):
        cases = [(True, 'int'), (1.0, 'int'), (-1, 'unsigned int'), (1 << 32, 'unsigned int'),
                 (1, 'bool'), (2, 'FxCombinedType'), (13, 'weapType_t'),
                 (float('inf'), 'float'), (1e100, 'float'), (1e-100, 'float')]
        for value, ty in cases:
            with self.subTest(value=value, ty=ty), self.assertRaises(ValueError): production._scalar(value, ty, 'field')
        for value, ty in [(0, 'unsigned int'), ((1 << 32) - 1, 'unsigned int'), (-2147483648, 'int'),
                          (3.4028234663852886e38, 'float'), (1.401298464324817e-45, 'float'), (-0.0, 'float')]:
            production._scalar(value, ty, 'field')

    def test_exact_empty_enum_exception_has_only_storage_domain(self):
        desc = SCHEMA['types']['WeaponChargeType']
        self.assertTrue(desc['semantic_domain_unknown'])
        self.assertTrue(desc['storage_domain_only'])
        self.assertEqual(desc['members'], {})
        self.assertEqual(desc['values'], [])
        sites = [(ty, r['field']) for ty, s in SCHEMA['structures'].items() for r in s['ops'] if r.get('semantic_domain_unknown')]
        self.assertEqual(sorted(sites), [('AttCharged', 'chargeType'), ('WeaponDef', 'chargeType')])
        for value in (-2147483648, 0, 2147483647): production._scalar(value, 'WeaponChargeType', 'charge')
        for value in (-2147483649, 2147483648, True, 1.0, None, '0'):
            with self.assertRaises(ValueError): production._scalar(value, 'WeaponChargeType', 'charge')

    def test_shared_groups_null_zero_and_both_mismatch_orders(self):
        for ty, left, right in [('WeaponCompleteDef', 'notetrackSoundMapKeys', 'notetrackSoundMapValues'),
                                ('WeaponAttachment', 'worldModelVariations', 'viewModelVariations'),
                                ('WeaponDef', 'complexWorldModel', 'complexGunXModelRightHand')]:
            for lv, rv in [([None], [None, None]), ([None, None], [None]), (None, [None]), ([], [None]), ([None], [])]:
                d = authored(ty); d[left], d[right] = lv, rv
                with self.subTest(ty=ty, lv=lv, rv=rv), self.assertRaises(ValueError): production._shared_groups(ty, d, ty)
        entries = authored('NoteTrackToSoundEntry'); entries.update(notetrackSoundMapKeys=['aaaaaaa'], notetrackSoundMapValues=['bbbbbbb'])
        trace = production._Trace(); production._walk('NoteTrackToSoundEntry', entries, 'entry', trace)
        self.assertEqual(trace.cells, 2)
        self.assertEqual(trace.script_entries, 2)
        self.assertEqual(trace.offset, 24)  # 2*4-byte cells + 2*(7+NUL).

    def test_fixed_arrays_flat_dotted_attachment_keys_and_fx(self):
        d = authored('WeaponDef'); parent = {'accuracyGraphKnots': [None, None]}
        for value in (None, [None] * 3, [[None] * 4]):
            bad = copy.deepcopy(d); bad['turretBarrelSpinUpSnd'] = value
            with self.assertRaises(ValueError): production._walk('WeaponDef', bad, 'weapondef', production._Trace(), parent)
        a = authored('AttADSOverlay')
        self.assertIn('overlay.shader', a)
        self.assertNotIn('overlay', a)
        a['overlay'] = {'shader': None}
        with self.assertRaises(ValueError): production._walk('AttADSOverlay', a, 'overlay', production._Trace())
        for value in ({'type': 2, 'fx': 'x'}, {'type': False, 'fx': 'x'}, {'type': 0, 'name': 'x'}, {'type': 1, 'fx': ''}):
            with self.assertRaises(ValueError): production._fx(value, 'fx', production._Trace())
        for tag in (0, 1):
            trace = production._Trace(); production._fx({'type': tag, 'fx': 'aaaaaaa'}, 'fx', trace)
            self.assertEqual(trace.offset, 16)

    def test_graph_manual_parent_counts_shapes_and_zero_omission(self):
        d = authored('WeaponDef'); parent = {'accuracyGraphKnots': [None, None]}
        d['originalAccuracyGraphKnots'] = None
        with self.assertRaisesRegex(ValueError, 'closed'): production._walk('WeaponDef', d, 'def', production._Trace(), parent)
        d = authored('WeaponDef'); parent = {'accuracyGraphKnots': [None, [[1.0, 2.0]]]}
        d.update(originalAccuracyGraphKnots=[None, [[3.0, 4.0]]], originalAccuracyGraphKnotCount=[0, 1])
        production._walk('WeaponDef', d, 'def', production._Trace(), parent)
        for knots, counts in [([None, []], [0, 1]), ([None, [[1, 2, 3]]], [0, 1]), ([None, [[1, 2]]], [0, 2])]:
            bad = copy.deepcopy(d); bad.update(originalAccuracyGraphKnots=knots, originalAccuracyGraphKnotCount=counts)
            with self.assertRaises(ValueError): production._walk('WeaponDef', bad, 'def', production._Trace(), parent)

    def test_all_four_original_graph_emission_cases_and_no_extra_tail(self):
        for counts in ([0, 0], [1, 0], [0, 1], [1, 1]):
            d = authored('WeaponDef')
            parent = {'accuracyGraphKnots': [None if n == 0 else [[1.0, 2.0]] for n in counts]}
            d['originalAccuracyGraphKnotCount'] = list(counts)
            highest = 2 if counts[1] else 1 if counts[0] else 0
            if highest: d['originalAccuracyGraphKnots'] = [None if not n else [[3.0, 4.0]] for n in counts[:highest]]
            with self.subTest(counts=counts):
                production._walk('WeaponDef', d, 'def', production._Trace(), parent)
                if highest:
                    missing = copy.deepcopy(d); del missing['originalAccuracyGraphKnots']
                    with self.assertRaises(ValueError): production._walk('WeaponDef', missing, 'def', production._Trace(), parent)
                    d['originalAccuracyGraphKnots'].append(None)
                else: d['originalAccuracyGraphKnots'] = None
                with self.assertRaises(ValueError): production._walk('WeaponDef', d, 'def', production._Trace(), parent)

    def test_weapon_nested_json_is_not_attachment_literal_dotted_json(self):
        d = authored('WeaponDef'); parent = {'accuracyGraphKnots': [None, None]}
        self.assertIn('shader', d['overlay'])
        self.assertIn('projExplosionEffect', d)
        self.assertNotIn('overlay.shader', d)
        for key in ('overlay.shader', 'projExplosionEffect.type'):
            bad = copy.deepcopy(d); bad[key] = None
            with self.assertRaises(ValueError): production._walk('WeaponDef', bad, 'def', production._Trace(), parent)

    def test_uint16_manual_outer_cast_precedes_allocation(self):
        class HugeList(list):
            def __len__(self): return 65536
        # Exact list is required; a subclass cannot masquerade as a huge allocation.
        with self.assertRaises(ValueError): production._manual(['entries', 'rows', 'NoteTrackToSoundEntry'], {'rows': HugeList()}, 'root', production._Trace(), None)
        with self.assertRaises(ValueError): production._manual(['entries', 'rows', 'NoteTrackToSoundEntry'], {'rows': [None] * 65536}, 'root', production._Trace(), None)
        for count in (0, 65535): production._scalar(count, 'unsigned short', 'cast')
        with self.assertRaises(ValueError): production._scalar(65536, 'unsigned short', 'cast')

    def test_full_material_vs_shell_and_inline_pointer_array_demand(self):
        full, shell = production._Trace(), production._Trace()
        production._asset('aaaaaaa', 'Material', 'full', full, full=True)
        production._asset('aaaaaaa', 'Material', 'shell', shell)
        self.assertEqual((full.offset, shell.offset), (288, 16))
        d = authored('WeaponDef'); d['camoWorldModelMaterialOverride'] = ['aaaaaaa'] + [None] * 15
        trace = production._Trace(); production._walk('WeaponDef', d, 'def', trace, {'accuracyGraphKnots': [None, None]})
        self.assertEqual((trace.offset, trace.cells), (16, 0))

    def test_real_unk_material_handler_counts_full_material_and_order(self):
        w, a = private_pair()
        w['weapDef']['unk0']['material'] = 'aaaaaaa'
        self.assertIsNone(invoke(w, a))
        trace = production._inspect(w, a)
        self.assertEqual(trace.offset, 6096 + 280 + 8)
        events = [e for e in trace.events if '.unk0.material' in e[0]]
        self.assertEqual(events, [('weapon.weapDef.unk0.material', 'Material', 5528, 280, 8),
                                  ('weapon.weapDef.unk0.material.name', 'char', 5808, 8, 1)])
        following = next(e for e in trace.events if e[0] == 'attachment')
        self.assertEqual(following[2], 5816)

    def test_cursor_utf8_chain_effective_header_and_zero_no_padding(self):
        for text, align_type, expected in [('é', 'float', 3), ('€', 'const char*', 4)]:
            trace = production._Trace(); trace.string(text, 'string')
            self.assertEqual(trace.offset, expected)
            with self.assertRaisesRegex(ValueError, 'misalignment'): trace.allocate(align_type, 1, 'next')
            self.assertEqual(trace.offset, expected)
        trace = production._Trace(); trace.string('€', 'string'); trace.allocate('float', 1, 'four'); trace.allocate('const char*', 1, 'eight')
        self.assertEqual(trace.offset, 16)
        trace = production._Trace(); trace.string('é', 'string'); trace.allocate('const char*', 0, 'zero')
        self.assertEqual(trace.offset, 3)
        with self.assertRaisesRegex(ValueError, 'misalignment'): production._fx({'type': 0, 'fx': 'x'}, 'typed-char-header', trace)
        with self.assertRaisesRegex(ValueError, 'unknown type'): trace.allocate('Unknown', 1, 'unknown')

    def test_two_root_cursor_not_reset_and_realistic_legacy_refusal(self):
        w, a = private_pair(); del w['szAltWeaponName']; w['szAltWeaponName'] = None
        with self.assertRaisesRegex(ValueError, 'misalignment'): invoke(w, a)
        w, a = private_pair(); a['szDisplayName'] = None
        a['tracer'] = authored('AttAmmoTracer')
        with self.assertRaisesRegex(ValueError, 'misalignment'): invoke(w, a)

    def test_checked_arithmetic_and_native_aggregate_are_independent(self):
        t = production._Trace()
        with self.assertRaisesRegex(ValueError, 'multiplication'): t.allocate('float', (1 << 64) // 4, 'multiply')
        t.offset = (1 << 64) - 4
        with self.assertRaisesRegex(ValueError, 'addition'): t.allocate('float', 1, 'add')
        t = production._Trace(); t.allocate('char', 8192, 'first', cells=True)
        with self.assertRaisesRegex(ValueError, 'aggregate'): t.allocate('char', 1, 'second-root', cells=True)
        self.assertEqual(t.offset, 8192)

    def test_strict_decode_and_lossy_normalization_refusals(self):
        for raw in (b'\xef\xbb\xbf{}', b'{"x":1,"x":2}', b'{} {}', b'{"x":NaN}', b'{"x":1e999}',
                    b'{"x":"\\ud800"}', b'{"x":"a\\u0000b"}', b'{"x":1e-999}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError): production._decode(raw, 'body')
        for value in ('', 'a\0b', '\ud800'):
            with self.assertRaises(ValueError): production._cstring(value, 'script', production._Trace(), script=True)
        trace = production._Trace(); production._cstring('', 'weapon-string', trace, empty=True)
        self.assertEqual(trace.offset, 1)

    def test_production_module_has_no_io_native_process_or_parser_calls(self):
        tree = ast.parse(Path(production.__file__).read_text())
        imports = {n.names[0].name for n in ast.walk(tree) if isinstance(n, ast.Import)}
        self.assertEqual(imports, {'json', 'math', 'struct'})
        calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertFalse(calls & {'open', 'eval', 'exec', 'compile', '__import__'})
        self.assertNotIn('ctypes', Path(production.__file__).read_text())


class SourceGrammarTests(unittest.TestCase):
    def test_reviewed_bitfields_share_units_and_never_straddle(self):
        self.assertEqual(generator.uint64_bitfield_units([16, 32, 2, 14]), (8, 8))
        self.assertEqual(generator.uint64_bitfield_units([16, 32, 2, 14, 64]), (16, 8))
        self.assertEqual(generator.uint64_bitfield_units([63, 2]), (16, 8))
        for widths in ([0], [65], [True], []):
            with self.assertRaises(ValueError): generator.uint64_bitfield_units(widths)
        native = 'struct GfxDrawSurfFields { unsigned __int64 objectId:16; unsigned __int64 pad0:32; unsigned __int64 tessellation:2; unsigned __int64 pad1:14; unsigned __int64 pad2:64; }; struct Packed128 { std::uint64_t p0; std::uint64_t p1; }; union GfxDrawSurf { GfxDrawSurfFields fields; Packed128 packed; };'
        d = generator.Declarations(native)
        self.assertEqual((d.describe('GfxDrawSurf')['size'], d.describe('GfxDrawSurf')['align']), (16, 8))
        self.assertEqual(d.describe('GfxDrawSurfFields')['bitfields'], [('objectId', 16), ('pad0', 32), ('tessellation', 2), ('pad1', 14), ('pad2', 64)])
        for changed in (native.replace('pad1:14', 'pad1:15'), native.replace('GfxDrawSurfFields', 'UnknownBits')):
            with self.assertRaisesRegex(ValueError, 'Unreviewed native bitfield'):
                generator.Declarations(changed).describe('GfxDrawSurf')
    def test_unknown_manual_and_nonmacro_sites_cannot_be_omitted(self):
        body = '\nWEAPON_PARSE_FIELD(x);\n'
        generator.body_coverage('Owned', body)
        with self.assertRaisesRegex(ValueError, 'Unclassified'):
            generator.body_coverage('Owned', body + 'data["unmapped"].get<int>();')
        with patch.dict(generator.MANUAL_BODY_SHA256, {'Owned': sha(body.encode())}):
            generator.body_coverage('Owned', body)
            with self.assertRaisesRegex(ValueError, 'Unreviewed manual'):
                generator.body_coverage('Owned', body + 'mem->allocate<int>();')
    def test_pin_drift_refuses_before_extraction(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pins = {}
            conversion = {}
            inputs = [(name, root / 'src/zonetool/zonetool' / name, pins) for name in generator.PINS]
            inputs += [(name, root / name, conversion) for name in generator.CONVERSION_PINS]
            for name, path, destination in inputs:
                path.parent.mkdir(parents=True, exist_ok=True)
                raw = ('// owned Source fixture ' + name + '\n').encode()
                path.write_bytes(raw)
                destination[name] = sha(raw)
            for name, path, _ in inputs:
                original = path.read_bytes(); path.write_bytes(original + b'// drift\n')
                with patch.object(generator, 'PINS', pins), patch.object(generator, 'CONVERSION_PINS', conversion), patch.object(generator, 'extract', side_effect=AssertionError('extraction ran')) as extract:
                    with self.assertRaisesRegex(ValueError, 'Source changed'): generator.generate(root)
                    extract.assert_not_called()
                path.write_bytes(original)

    def test_finite_unknown_declaration_macro_and_enum_refuse(self):
        d = generator.Declarations('struct Owned { int x; };')
        with self.assertRaises(ValueError): d.describe('Mystery')
        with self.assertRaises(ValueError): generator.macro_rule('Owned', 'WEAPON_PARSE_UNREVIEWED', 'x', d, 1)
        with self.assertRaises(ValueError): generator.macro_rule('Owned', 'WEAPON_PARSE_FIELD', 'x, y', d, 1)
        with self.assertRaises(ValueError): generator.integer('__import__("os")')
        with self.assertRaises(ValueError): generator.integer('1 << 999')
        with self.assertRaisesRegex(ValueError, 'Unknown empty enum'):
            generator.Declarations('enum Unknown : std::int32_t { };').describe('Unknown')
        charge = generator.Declarations('enum WeaponChargeType : std::int32_t { }; struct Other { WeaponChargeType x; };')
        with self.assertRaisesRegex(ValueError, 'outside its two'):
            generator.macro_rule('Other', 'WEAPON_PARSE_FIELD', 'x', charge, 1)

    def test_simple_alignment_union_pack_and_array_source_layout(self):
        d = generator.Declarations('struct Owned { char a; int b; }; union U { char a; int b; };\n#pragma pack(push, 2)\nstruct P { char a; int b; };\n#pragma pack(pop)')
        self.assertEqual((d.describe('Owned')['size'], d.describe('Owned')['align']), (8, 4))
        self.assertEqual((d.describe('U')['size'], d.describe('U')['align']), (4, 4))
        self.assertEqual((d.describe('P')['size'], d.describe('P')['align']), (6, 2))
        self.assertEqual(d.describe('int[3]')['size'], 12)


if __name__ == '__main__': unittest.main()
