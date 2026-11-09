"""Synthetic tests for iw7_mod_preflight.py (no game data): a small coherent mod, then one fault at a time."""
import contextlib
import io
import json
import os
import shutil
import struct
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iw7_mod_preflight as preflight  # noqa: E402
import iw7_xanim_layout as layout  # noqa: E402
import iw7_xsurface_check as surface  # noqa: E402
import iw7_xsurface_uv2 as uv2  # noqa: E402
from test_iw7_xsurface_check import pack, xsb  # noqa: E402
from test_iw7_xsurface_uv2 import surface_file  # noqa: E402

ZONE = 'zonetool/z/'
CSV = 'zone_source/z.csv'
STOCK = 'zone_source/z_ref_stock.csv'
CSV_LINES = [
    '// two weapons sharing one model', 'ignore,z_ref_stock', 'weapon,gun_a', 'weapon,gun_a_up', 'weapon,gun_b',
    'attachment,att1', 'animpkg,gun_a_package', 'animpkg,gun_b_package', 'sfxpkg,gun_a_sfx', 'sfxpkg,gun_b_sfx',
    'vfxpkg,gun_a_vfx', 'soundbank,z.all', 'material,mc/gun_mat', 'xmodel,gun_view', 'xanim,gun_idle',
    'xanim,gun_b_idle', 'vfx,vfx/z/flash',
]
ALIAS_ROWS = ['Name,Sequence,File,Vol', 'gun_fire,1,z/gun_fire,0.9', 'gun_b_fire,1,z/gun_b_fire,0.9']
GUN_A = {'szInternalName': 'gun_a', 'vfxPackage': 'gun_a_vfx', 'sfxPackage': 'gun_a_sfx', 'attachments6': ['att1'],
         'weapDef': {'szXAnims': 'gun_a_package', 'gunXModel': 'gun_view', 'worldModel': 'stock_world'}}
MATERIAL = {'techniqueSet->name': 'tech_a', 'textureTable': [{'image': 'gun_col'}]}
BANK = {'name': 'z.all', 'aliases': ['sound/z.all.aliases.csv']}


def lines(items):
    return '\n'.join(items) + '\n'


def base():
    """Relative path -> text or bytes of a mod with no fault."""
    return {
        CSV: lines(CSV_LINES),
        STOCK: lines(['xmodel,stock_world', 'vfx,,vfx/stock/muzzle']),
        ZONE + 'catalog.txt': lines(['gun_fire=gun_a:gun_a_up:att1', 'gun_b_fire=gun_b']),
        ZONE + 'behaviours.txt': lines(['gun_a|ns|power=3|impact=vfx/z/flash|gun_fire']),
        ZONE + 'weapons/gun_a.json': json.dumps(GUN_A),
        ZONE + 'weapons/gun_a_up.json': json.dumps(
            {'szInternalName': 'gun_a_up', 'weapDef': {'szXAnims': 'gun_a_package', 'gunXModel': 'gun_view'}}),
        ZONE + 'weapons/gun_b.json': json.dumps(
            {'szInternalName': 'gun_b', 'sfxPackage': 'gun_b_sfx',
             'weapDef': {'szXAnims': 'gun_b_package', 'gunXModel': 'gun_view'}}),
        ZONE + 'attachments/att1.json': json.dumps({'szInternalName': 'att1'}),
        ZONE + 'animpkg/gun_a_package.json': json.dumps({'name': 'gun_a_package', 'anims': {'idle': 'gun_idle'}}),
        ZONE + 'animpkg/gun_b_package.json': json.dumps({'name': 'gun_b_package', 'anims': {'idle': 'gun_b_idle'}}),
        ZONE + 'sfxpkg/gun_a_sfx.json': json.dumps(
            {'name': 'gun_a_sfx', 'sounds': {'name': 'gun_a_sfx', 'fire': 'gun_fire', 'pickup': 'weap_pickup_stock'}}),
        ZONE + 'sfxpkg/gun_b_sfx.json': json.dumps(
            {'name': 'gun_b_sfx', 'sounds': {'name': 'gun_b_sfx', 'fire': 'gun_b_fire'}}),
        ZONE + 'vfxpkg/gun_a_vfx.json': json.dumps(
            {'name': 'gun_a_vfx', 'vfx': {'name': 'gun_a_vfx', 'flash': 'vfx/z/flash'}}),
        ZONE + 'soundbank/z.all.json': json.dumps(BANK),
        ZONE + 'sound/z.all.aliases.csv': lines(ALIAS_ROWS),
        ZONE + 'sound_assets/z/gun_fire.flac': b'fire',
        ZONE + 'sound_assets/z/gun_b_fire.flac': b'fire b',
        ZONE + 'materials/mc/gun_mat.json': json.dumps(MATERIAL),
        ZONE + 'images/gun_col.dds': b'DDS colour',
        ZONE + 'xmodel/gun_view.xmb': b'\x00\x01gun_view_lod0\x00mc/gun_mat\x00',
        ZONE + 'xsurface/gun_view_lod0.xsb': xsb(),
        ZONE + 'xanim/gun_idle.xab': b'\x00',
        ZONE + 'xanim/gun_b_idle.xab': b'\x00\x00',
        ZONE + 'particlesystem/vfx/z/flash.iw7VFX': b'VFX\x00mc/gun_mat\x00',
        ZONE + 'techsets/tech_a.techset': b'techset',
    }


def two_surfaces():
    """Two static surfaces with the same vertex count, each given a second UV set."""
    surfs = bytearray(uv2.XMODEL_SURFS_SIZE)
    struct.pack_into('<H', surfs, 16, 2)
    heads = bytearray()
    for _ in range(2):
        head = bytearray(uv2.XSURFACE_SIZE)
        struct.pack_into('<3HB', head, 0, 0x84, 3, 1, 0)
        heads += head
    data = bytes([8, 1]) + struct.pack('<I', 1) + bytes(surfs)
    data += bytes([6, 1]) + b'two_surfaces\0'
    data += bytes([8, 1]) + struct.pack('<I', 2) + bytes(heads)
    for offset in (0.0, 10.0):
        data += bytes([8, 1]) + struct.pack('<I', 3)
        for x, y in ((0.0, 0.0), (0.0, 1.0), (1.0, 0.0)):
            data += struct.pack('<3f12xI4x', offset + x, y, 0.0, pack(0.0, 0.0, 1.0))
        data += bytes([8, 1]) + struct.pack('<I', 1) + struct.pack('<3H', 0, 1, 2)
        data += bytes([8, 0]) + bytes([10, 0]) * 4
    return uv2.add_second_uv(data)[0]


class Case(unittest.TestCase):
    def build(self, changes=None, drop=()):
        files = base()
        files.update(changes or {})
        for path in drop:
            del files[path]
        root = tempfile.mkdtemp(prefix='preflight_test_')
        self.addCleanup(shutil.rmtree, root, True)
        for rel, content in files.items():
            self.put(root, rel, content)
        return root

    @staticmethod
    def put(root, rel, content):
        path = os.path.join(root, *rel.split('/'))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as handle:
            handle.write(content if isinstance(content, bytes) else content.encode('utf-8'))

    @staticmethod
    def open(root):
        return preflight.Preflight(os.path.join(root, 'zonetool', 'z'), os.path.join(root, 'zone_source', 'z.csv'))

    def check(self, changes=None, drop=(), binary=False):
        run = self.open(self.build(changes, drop))
        run.result = run.run(binary=binary)
        return run

    @staticmethod
    def codes(run, severity):
        return sorted(f['code'] for f in run.findings if f['severity'] == severity)

    def call(self, root, *extra):
        out = io.StringIO()
        argv = [os.path.join(root, 'zonetool', 'z'), '--csv', os.path.join(root, 'zone_source', 'z.csv')] + list(extra)
        with contextlib.redirect_stdout(out):
            code = preflight.main(argv)
        return code, out.getvalue()


class RulesTest(Case):
    def test_coherent_mod_has_no_error_and_no_warning(self):
        run = self.check()
        self.assertEqual(self.codes(run, 'error'), [])
        self.assertEqual(self.codes(run, 'warn'), [])
        self.assertEqual(self.codes(run, 'info'), ['STOCK_OR_MISSING'])     # the pickup alias is the base game's
        self.assertEqual([f['weapon'] for f in run.result[0]], ['gun_a', 'gun_b'])

    def test_zone_csv_line_without_a_source(self):
        run = self.check({CSV: lines(CSV_LINES + ['xanim,ghost'])})
        self.assertEqual(self.codes(run, 'error'), ['CSV_NO_SOURCE'])

    def test_zone_csv_duplicate_and_stock_shadow(self):
        run = self.check({CSV: lines(CSV_LINES + ['weapon,gun_b']),
                          STOCK: lines(['xmodel,stock_world', 'vfx,,vfx/stock/muzzle', 'xmodel,gun_view'])})
        self.assertEqual(self.codes(run, 'error'), [])
        self.assertEqual(self.codes(run, 'warn'), ['CSV_DUPLICATE', 'SHADOWED_BY_STOCK'])

    def test_source_nothing_builds(self):
        run = self.check({ZONE + 'xanim/orphan.xab': b'x'})
        self.assertEqual(self.codes(run, 'error'), [])
        self.assertEqual(self.codes(run, 'warn'), ['SOURCE_NOT_BUILT'])

    def test_built_but_used_by_nothing_is_a_note(self):
        run = self.check({ZONE + 'xanim/spare.xab': b'x', CSV: lines(CSV_LINES + ['xanim,spare'])})
        self.assertEqual(self.codes(run, 'warn'), [])
        self.assertIn('LISTED_UNUSED', self.codes(run, 'info'))

    def test_weapon_field_naming_a_missing_asset(self):
        weapon = json.loads(json.dumps(GUN_A))
        weapon['weapDef']['worldModel'] = 'nowhere_model'
        run = self.check({ZONE + 'weapons/gun_a.json': json.dumps(weapon)})
        self.assertEqual(self.codes(run, 'error'), ['REFERENCE_MISSING'])
        self.assertIn('nowhere_model', [f for f in run.findings if f['code'] == 'REFERENCE_MISSING'][0]['message'])

    def test_without_a_stock_list_a_missing_name_is_only_unverified(self):
        run = self.check({CSV: lines([line for line in CSV_LINES if not line.startswith('ignore')])})
        self.assertEqual(self.codes(run, 'error'), [])
        self.assertEqual(self.codes(run, 'warn'), ['REFERENCE_UNVERIFIED'])
        run = self.check(drop=[STOCK])
        self.assertEqual(self.codes(run, 'error'), [])
        self.assertEqual(self.codes(run, 'warn'), ['REFERENCE_UNVERIFIED', 'STOCK_LIST_MISSING'])

    def test_internal_name_differs_from_the_file(self):
        run = self.check({ZONE + 'attachments/att1.json': json.dumps({'szInternalName': 'att_other'})})
        self.assertEqual(self.codes(run, 'error'), ['NAME_MISMATCH'])

    def test_json_that_does_not_parse(self):
        run = self.check({ZONE + 'vfxpkg/gun_a_vfx.json': '{broken'})
        self.assertEqual(self.codes(run, 'error'), ['JSON_INVALID'])

    def test_catalog_names_what_is_absent_or_not_built(self):
        run = self.check({ZONE + 'catalog.txt': lines(['gun_fire=gun_a:gun_a_up:att1', 'gun_b_fire=gun_b',
                                                       'x_fire=gun_x'])})
        self.assertEqual(self.codes(run, 'error'), ['CATALOG_NO_SOURCE'])
        self.assertIn('CATALOG_ALIAS_UNDEFINED', self.codes(run, 'warn'))
        run = self.check({ZONE + 'catalog.txt': lines(['gun_fire=gun_a:gun_a_up:att1', 'gun_b_fire=gun_b::att2']),
                          ZONE + 'attachments/att2.json': json.dumps({'szInternalName': 'att2'})})
        self.assertEqual(self.codes(run, 'error'), ['CATALOG_NOT_BUILT'])

    def test_weapon_file_outside_the_catalog_and_tree_without_catalog(self):
        run = self.check({ZONE + 'weapons/gun_c.json': json.dumps({'szInternalName': 'gun_c'}),
                          CSV: lines(CSV_LINES + ['weapon,gun_c'])})
        self.assertEqual(self.codes(run, 'warn'), ['WEAPON_NOT_IN_CATALOG'])
        run = self.check(drop=[ZONE + 'catalog.txt'])
        self.assertIn('NO_CATALOG', self.codes(run, 'info'))
        self.assertEqual([f['weapon'] for f in run.result[0]], ['gun_a', 'gun_a_up', 'gun_b'])

    def test_behaviour_lines(self):
        def behave(line, more=None):
            changes = {ZONE + 'behaviours.txt': lines(['gun_a|ns|power=3|impact=vfx/z/flash|gun_fire', line])}
            changes.update(more or {})
            return self.check(changes)

        self.assertEqual(self.codes(behave('gun_zzz|ns||impact=vfx/z/flash|gun_fire'), 'error'),
                         ['BEHAVIOUR_UNKNOWN_WEAPON'])
        run = behave('gun_b|ns||impact=vfx/z/other|gun_b_fire', {ZONE + 'particlesystem/vfx/z/other.iw7VFX': b'VFX'})
        self.assertEqual(self.codes(run, 'error'), ['BEHAVIOUR_FX_NOT_BUILT'])
        self.assertEqual(self.codes(behave('gun_b|ns||impact=vfx/z/none|gun_b_fire'), 'error'), ['BEHAVIOUR_FX_MISSING'])
        run = behave('gun_b|ns||impact=vfx/stock/muzzle|mystery_alias')       # a stock effect is fine
        self.assertEqual(self.codes(run, 'error'), [])
        self.assertEqual(self.codes(run, 'warn'), ['BEHAVIOUR_SOUND_UNDEFINED'])

    def test_sound_bank_and_alias_lists(self):
        bank = dict(BANK, aliases=BANK['aliases'] + ['sound/z.gone.aliases.csv'])
        run = self.check({ZONE + 'soundbank/z.all.json': json.dumps(bank)})
        self.assertEqual(self.codes(run, 'error'), ['BANK_LIST_MISSING'])
        run = self.check({ZONE + 'sound/z.extra.aliases.csv': lines(['Name,File', 'extra_alias,z/gun_fire'])})
        self.assertEqual(self.codes(run, 'error'), ['ALIAS_LIST_NOT_IN_BANK'])

    def test_alias_audio_file(self):
        rows = ALIAS_ROWS[:2] + ['gun_b_fire,1,z/absent,0.9']
        run = self.check({ZONE + 'sound/z.all.aliases.csv': lines(rows)})
        self.assertEqual(self.codes(run, 'error'), ['SOUND_FILE_MISSING'])
        rows = ALIAS_ROWS[:2] + ['gun_b_fire,1,z' + chr(92) + 'gun_b_fire,0.9']   # older trees: backslash paths
        run = self.check({ZONE + 'sound/z.all.aliases.csv': lines(rows)})
        self.assertEqual(self.codes(run, 'error'), [])
        self.assertNotIn('UNUSED_FILES', self.codes(run, 'info'))

    def test_dumped_techsets_are_looked_up_not_indexed(self):
        run = self.check({ZONE + 'techsets/ps/a.hlsl': b'x', ZONE + 'techsets_dump/b.bin': b'x'})
        self.assertFalse([key for key in run.tree.files if key[0].startswith('techsets')])
        self.assertTrue(run.tree.has_techset('tech_a'))
        self.assertEqual(self.codes(run, 'error') + self.codes(run, 'warn'), [])


class StateTest(Case):
    def state(self, root):
        run = self.open(root)
        return run.family_state(run.run(binary=False)[0])

    def changed(self, rel, content):
        root = self.build()
        before = self.state(root)
        self.put(root, rel, content)
        diff = preflight.compare({'weapons': before}, self.state(root))
        return {weapon: item['changed'] for weapon, item in diff.items() if item['status'] != 'unchanged'}

    def test_new_then_unchanged(self):
        state = self.state(self.build())
        self.assertEqual({w: d['status'] for w, d in preflight.compare(None, state).items()},
                         {'gun_a': 'new', 'gun_b': 'new'})
        self.assertEqual({w: d['status'] for w, d in preflight.compare({'weapons': state}, state).items()},
                         {'gun_a': 'unchanged', 'gun_b': 'unchanged'})

    def test_only_the_weapon_that_reaches_the_file_changes(self):
        self.assertEqual(self.changed(ZONE + 'sound_assets/z/gun_b_fire.flac', b'louder'),
                         {'gun_b': ['sound_assets/z/gun_b_fire']})
        self.assertEqual(self.changed(ZONE + 'xanim/gun_idle.xab', b'\x01'), {'gun_a': ['xanim/gun_idle']})

    def test_shared_file_changes_every_weapon_that_wears_it(self):
        self.assertEqual(self.changed(ZONE + 'images/gun_col.dds', b'DDS other'),
                         {'gun_a': ['images/gun_col'], 'gun_b': ['images/gun_col']})

    def test_alias_row_and_script_line_count(self):
        rows = ['Name,Sequence,File,Vol', 'gun_fire,1,z/gun_fire,0.5', 'gun_b_fire,1,z/gun_b_fire,0.9']
        self.assertEqual(self.changed(ZONE + 'sound/z.all.aliases.csv', lines(rows)), {'gun_a': ['alias/gun_fire']})
        self.assertEqual(self.changed(ZONE + 'behaviours.txt', lines(['gun_a|ns|power=9|impact=vfx/z/flash|gun_fire'])),
                         {'gun_a': ['catalog and behaviour lines']})

    def test_file_no_weapon_reaches_changes_nothing(self):
        self.assertEqual(self.changed(ZONE + 'images/unused.dds', b'DDS'), {})


class CommandTest(Case):
    def test_exit_code_follows_errors(self):
        code, out = self.call(self.build(), '--no-binary')
        self.assertEqual(code, 0)
        self.assertIn('errors 0, warnings 0, notes 1', out)
        code, out = self.call(self.build({CSV: lines(CSV_LINES + ['xanim,ghost'])}), '--no-binary')
        self.assertEqual(code, 1)
        self.assertIn('ERROR CSV_NO_SOURCE', out)

    def test_accept_then_only_the_changed_weapon_comes_back(self):
        root = self.build()
        state = os.path.join(root, 'state.json')
        code, out = self.call(root, '--no-binary', '--state', state, '--accept')
        self.assertIn('look again in game: gun_a (never accepted)', out)
        self.assertIn('accepted: gun_a, gun_b', out)
        code, out = self.call(root, '--no-binary', '--state', state)
        self.assertIn('unchanged since accepted, no launch needed: gun_a, gun_b', out)
        self.assertNotIn('look again', out)
        self.put(root, ZONE + 'sound_assets/z/gun_b_fire.flac', b'louder')
        code, out = self.call(root, '--no-binary', '--state', state)
        self.assertEqual(code, 0)
        self.assertIn('look again in game: gun_b (1 changed: sound_assets/z/gun_b_fire)', out)
        self.assertIn('no launch needed: gun_a', out)
        self.call(root, '--no-binary', '--state', state, '--accept', 'gun_b')
        code, out = self.call(root, '--no-binary', '--state', state)
        self.assertNotIn('look again', out)
        with open(state, encoding='utf-8') as handle:
            self.assertEqual(json.load(handle)['schema'], preflight.STATE_SCHEMA)

    def test_accept_refuses_unknown_weapon_and_missing_state(self):
        root = self.build()
        with self.assertRaises(SystemExit):
            self.call(root, '--no-binary', '--state', os.path.join(root, 'state.json'), '--accept', 'nope')
        with self.assertRaises(SystemExit):
            self.call(root, '--no-binary', '--accept')

    def test_json_result(self):
        root = self.build()
        target = os.path.join(root, 'result.json')
        self.call(root, '--no-binary', '--json', target)
        with open(target, encoding='utf-8') as handle:
            result = json.load(handle)
        self.assertEqual(result['schema'], preflight.SCHEMA)
        self.assertEqual(result['counts'], {'error': 0, 'warn': 0, 'info': 1})
        self.assertEqual(sorted(result['weapons']), ['gun_a', 'gun_b'])
        self.assertEqual(result['stock_lists'], ['z_ref_stock'])


class BinaryTest(Case):
    def test_black_normals_are_one_error_per_file(self):
        run = self.check({ZONE + 'xsurface/gun_view_lod0.xsb': xsb(high=False)}, binary=True)
        self.assertEqual(self.codes(run, 'error'), ['XSURFACE'])
        self.assertEqual(self.codes(self.check(binary=True), 'error'), [])

    def test_file_the_reader_cannot_follow_is_a_warning(self):
        run = self.check(binary=True)
        self.assertEqual(self.codes(run, 'warn'), ['UNREADABLE', 'UNREADABLE'])   # the two placeholder animations
        self.assertEqual(self.codes(run, 'error'), [])

    def test_animation_layout_faults_are_one_error_per_file(self):
        head = {'frames': 300, 'bone_counts': [0] * 10}
        with mock.patch.object(layout, 'load', return_value=('anim', head, {})), \
                mock.patch.object(layout, 'check', return_value={'errors': ['channel 11 inline', 'channel 12 inline']}):
            run = self.check(binary=True)
        found = [f for f in run.findings if f['code'] == 'XANIM_LAYOUT']
        self.assertEqual([f['asset'] for f in found], ['xanim/gun_b_idle', 'xanim/gun_idle'])
        self.assertIn('300 frames, 2 layout fault(s)', found[0]['message'])
        self.assertIn('channel 11 inline', found[0]['message'])

    def test_two_uv_material_needs_a_second_uv_set(self):
        camo = {ZONE + 'materials/mc/gun_mat.json': json.dumps(dict(MATERIAL, **{'techniqueSet->name': 'tech_2uvt_a'})),
                ZONE + 'techsets/tech_2uvt_a.techset': b'techset'}
        run = self.check(dict(camo, **{ZONE + 'xsurface/gun_view_lod0.xsb': surface_file()}), binary=True)
        self.assertIn('CAMO_MATERIAL_WITHOUT_UV2', self.codes(run, 'error'))
        ready = uv2.add_second_uv(surface_file())[0]
        run = self.check(dict(camo, **{ZONE + 'xsurface/gun_view_lod0.xsb': ready}), binary=True)
        self.assertNotIn('CAMO_MATERIAL_WITHOUT_UV2', self.codes(run, 'error'))
        self.assertNotIn('CAMO_MATERIAL_PARTIAL_UV2', self.codes(run, 'warn'))


class SecondUvSurfaceTest(unittest.TestCase):
    def test_surface_after_a_second_uv_set_is_read(self):
        data = two_surfaces()
        name, surfaces = surface.parse(data)
        self.assertEqual(name, 'two_surfaces')
        self.assertEqual([[v[0] for v in s[1]] for s in surfaces], [[0.0, 0.0, 1.0], [10.0, 10.0, 11.0]])
        self.assertEqual([s[2] for s in surfaces], [[(0, 1, 2)], [(0, 1, 2)]])
        try:        # the count search takes the first surface's second UV set for the second surface's vertices
            searched = [[v[0] for v in s[1]] for s in surface.parse_by_search(data)[1]]
        except (ValueError, IndexError, struct.error):
            searched = None
        self.assertNotEqual(searched, [[0.0, 0.0, 1.0], [10.0, 10.0, 11.0]])


if __name__ == '__main__':
    unittest.main()
