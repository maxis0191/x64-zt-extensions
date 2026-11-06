"""Synthetic tests for t7_weapon_sound.py (no game data)."""
import csv
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_weapon_sound as sound  # noqa: E402

TEMPLATE = ['Name', 'File', 'SecondaryAliasName', 'StopAliasName', 'Subtitle', 'type', 'channel', 'vol_min', 'vol_max', 'duck']


def write_csv(path, rows):
    with open(path, 'w', newline='') as f:
        csv.writer(f).writerows(rows)


class WeaponSoundTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, 'flac', 'wpn'))
        for name in ('fire', 'fire_sweet', 'reload', 'exp'):
            with open(os.path.join(self.root, 'flac', 'wpn', name + '.flac'), 'wb') as f:
                f.write(b'fLaC' + name.encode())
        write_csv(os.path.join(self.root, 'bo3.csv'), [
            ['Name', 'FileSpec', 'Secondary', 'VolMin', 'VolMax'],
            ['wpn_rgun_fire_plr', 'wpn/fire.flac', 'wpn_rgun_sweet_plr', '90', '90'],
            ['wpn_rgun_sweet_plr', 'wpn/fire_sweet.flac', '', '70', '70'],
            ['wpn_rgun_reload_open', 'wpn/reload.flac', '', '80', '80'],
            ['wpn_rgun_exp', 'wpn/exp.flac', '', '', ''],
        ])
        write_csv(os.path.join(self.root, 'stock.csv'), [
            TEMPLATE,
            ['muted', 'x', '', 'stop', 'sub', 'streamed', 'weap_plr_fire_1_2d', '0', '0', 'duck_a'],
            ['plr', 'x', '', 'stop', 'sub', 'streamed', 'weap_plr_fire_1_2d', '0.8', '0.9', 'duck_b'],
            ['foley', 'x', '', '', '', 'streamed', 'scn_fx_unres_2d', '0.5', '0.6', ''],
            ['boom', 'x', '', '', '', 'streamed', 'explo_1_3d', '1', '1', 'duck_c'],
        ])
        self.out = os.path.join(self.root, 'out')
        sound.main(['--bo3-aliases', os.path.join(self.root, 'bo3.csv'), '--flac-root', os.path.join(self.root, 'flac'),
                    '--template', os.path.join(self.root, 'stock.csv'), '--out', self.out, '--bank', 'test.all',
                    '--zone', 'test', '--prefix', 'test/rgun',
                    '--alias', 'wpn_rgun_fire_plr', 'wpn_rgun_reload_open', 'wpn_rgun_exp'])
        with open(os.path.join(self.out, 'sound', 'test.all.aliases.csv'), newline='') as f:
            rows = list(csv.DictReader(f))
        self.rows = {r['Name']: r for r in rows}

    def test_follows_secondary_chain_and_roles(self):
        self.assertEqual(set(self.rows), {'wpn_rgun_fire_plr', 'wpn_rgun_sweet_plr', 'wpn_rgun_reload_open', 'wpn_rgun_exp'})
        self.assertEqual(self.rows['wpn_rgun_fire_plr']['channel'], 'weap_plr_fire_1_2d')
        self.assertEqual(self.rows['wpn_rgun_fire_plr']['SecondaryAliasName'], 'wpn_rgun_sweet_plr')
        self.assertEqual(self.rows['wpn_rgun_reload_open']['channel'], 'scn_fx_unres_2d')
        self.assertEqual(self.rows['wpn_rgun_exp']['channel'], 'explo_1_3d')

    def test_volume_is_relative_to_the_chain_root(self):
        # The audible stock row (not the muted one) is the template.
        self.assertAlmostEqual(float(self.rows['wpn_rgun_fire_plr']['vol_max']), 0.9, places=5)
        # 20 below the root: a tenth of the stock volume.
        self.assertAlmostEqual(float(self.rows['wpn_rgun_sweet_plr']['vol_max']), 0.09, places=5)

    def test_loaded_mod_files_without_stock_references(self):
        for row in self.rows.values():
            self.assertEqual(row['type'], 'loaded')
            self.assertEqual(row['duck'], '')
            self.assertEqual(row['StopAliasName'], '')
            self.assertEqual(row['Subtitle'], '')
            self.assertTrue(row['File'].startswith('test\\rgun\\'))
        flac = os.path.join(self.out, 'sound_assets', 'test', 'rgun', 'wpn_rgun_exp.flac')
        with open(flac, 'rb') as f:
            self.assertEqual(f.read(), b'fLaCexp')
        with open(os.path.join(self.out, 'soundbank', 'test.all.json')) as f:
            bank = json.load(f)
        self.assertEqual(bank['aliases'], ['sound/test.all.aliases.csv'])
        self.assertEqual(bank['zone'], 'test')

    def test_unknown_alias_is_refused(self):
        with self.assertRaises(SystemExit):
            sound.main(['--bo3-aliases', os.path.join(self.root, 'bo3.csv'), '--flac-root', os.path.join(self.root, 'flac'),
                        '--template', os.path.join(self.root, 'stock.csv'), '--out', self.out, '--alias', 'wpn_missing'])


if __name__ == '__main__':
    unittest.main()
