"""Synthetic tests for t7_weapon_sound.py (no game data)."""
import csv
import json
import shutil
import subprocess
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
        # the fixture FLACs are placeholders: the hybrid head decoder is stubbed (PcmHeadTest decodes a real one)
        self._pcm_head = sound.pcm_head
        sound.pcm_head = lambda path, ffmpeg='ffmpeg': b'head:' + os.path.basename(path).encode()
        self.addCleanup(setattr, sound, 'pcm_head', self._pcm_head)
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
            ['wpn_rgun_exp', 'wpn/exp.flac', 'wpn_rgun_exp_silent', '', ''],
            ['wpn_rgun_exp_silent', '', 'wpn_rgun_exp_tail', '', ''],
            ['wpn_rgun_exp_tail', 'wpn/exp.flac', '', '', ''],
            ['wpn_rgun_loop', '', '', '', ''],
        ])
        write_csv(os.path.join(self.root, 'stock.csv'), [
            TEMPLATE,
            ['muted', 'x', '', 'stop', 'sub', 'streamed', 'weap_plr_fire_overlap_2d', '0', '0', 'duck_a'],
            ['plr', 'x', '', 'stop', 'sub', 'streamed', 'weap_plr_fire_overlap_2d', '0.8', '0.9', 'duck_b'],
            ['foley', 'x', '', '', '', 'streamed', 'scn_fx_unres_2d', '0.5', '0.6', ''],
            ['boom', 'x', '', '', '', 'streamed', 'explo_1_3d', '1', '1', 'duck_c'],
        ])
        self.out = os.path.join(self.root, 'out')
        sound.main(['--bo3-aliases', os.path.join(self.root, 'bo3.csv'), '--flac-root', os.path.join(self.root, 'flac'),
                    '--template', os.path.join(self.root, 'stock.csv'), '--out', self.out, '--bank', 'test.all',
                    '--zone', 'test', '--prefix', 'test/rgun',
                    '--alias', 'wpn_rgun_fire_plr', 'wpn_rgun_reload_open', 'wpn_rgun_exp', 'wpn_rgun_loop'])
        with open(os.path.join(self.out, 'sound', 'test.all.aliases.csv'), newline='') as f:
            rows = list(csv.DictReader(f))
        self.rows = {r['Name']: r for r in rows}

    def test_follows_secondary_chain_and_roles(self):
        self.assertEqual(set(self.rows), {'wpn_rgun_fire_plr', 'wpn_rgun_sweet_plr', 'wpn_rgun_reload_open', 'wpn_rgun_exp',
                                          'wpn_rgun_exp_tail'})
        self.assertEqual(self.rows['wpn_rgun_fire_plr']['channel'], 'weap_plr_fire_overlap_2d')
        self.assertEqual(self.rows['wpn_rgun_fire_plr']['SecondaryAliasName'], 'wpn_rgun_sweet_plr')
        self.assertEqual(self.rows['wpn_rgun_reload_open']['channel'], 'scn_fx_unres_2d')
        self.assertEqual(self.rows['wpn_rgun_exp']['channel'], 'explo_1_3d')

    def test_silent_links_are_skipped(self):
        # a chain never names an alias the bank lacks: the silent middle layer is stepped over
        self.assertEqual(self.rows['wpn_rgun_exp']['SecondaryAliasName'], 'wpn_rgun_exp_tail')

    def test_volume_is_relative_to_the_chain_root(self):
        # The audible stock row (not the muted one) is the template.
        self.assertAlmostEqual(float(self.rows['wpn_rgun_fire_plr']['vol_max']), 0.9, places=5)
        # 20 below the root: a tenth of the stock volume.
        self.assertAlmostEqual(float(self.rows['wpn_rgun_sweet_plr']['vol_max']), 0.09, places=5)

    def test_loaded_mod_files_without_stock_references(self):
        for name, row in self.rows.items():
            # player fire layers start from an uncompressed head, as every stock player fire sound
            self.assertEqual(row['type'], 'hybrid_pcm' if name.endswith('_plr') else 'loaded')
            self.assertEqual(row['duck'], '')
            self.assertEqual(row['StopAliasName'], '')
            self.assertEqual(row['Subtitle'], '')
            # never a backslash: ZoneTool's CSV reader turns \t and \n into whitespace (t7\tesla_gun_zm)
            self.assertTrue(row['File'].startswith('test/rgun/'))
            self.assertNotIn('\\', row['File'])
        head = os.path.join(self.out, 'sound_assets', 'test', 'rgun', 'wpn_rgun_fire_plr.pcmhead')
        with open(head, 'rb') as f:
            self.assertEqual(f.read(), b'head:wpn_rgun_fire_plr.flac')
        self.assertFalse(os.path.exists(head.replace('fire_plr', 'exp')))
        flac = os.path.join(self.out, 'sound_assets', 'test', 'rgun', 'wpn_rgun_exp.flac')
        with open(flac, 'rb') as f:
            self.assertEqual(f.read(), b'fLaCexp')
        with open(os.path.join(self.out, 'soundbank', 'test.all.json')) as f:
            bank = json.load(f)
        self.assertEqual(bank['aliases'], ['sound/test.all.aliases.csv'])
        self.assertEqual(bank['zone'], 'test')

    def test_filespec_with_or_without_all_prefix(self):
        # GrayWolf writes every sound under all/; BO3 alias tables name some with the prefix, some without.
        root = os.path.join(self.root, 'gw')
        os.makedirs(os.path.join(root, 'all', 'wpn'))
        with open(os.path.join(root, 'all', 'wpn', 'a.flac'), 'wb') as f:
            f.write(b'fLaCa')
        for spec in ('wpn\\a.flac', 'all\\wpn\\a.flac', 'all/wpn/a.flac', 'wpn\\a.opus'):
            self.assertEqual(sound.resolve_flac(root, spec), os.path.join(root, 'all', 'wpn', 'a.flac'))
        self.assertIsNone(sound.resolve_flac(root, 'wpn\\missing.flac'))

    def test_explicit_role_reaches_the_chain(self):
        out = os.path.join(self.root, 'out2')
        sound.main(['--bo3-aliases', os.path.join(self.root, 'bo3.csv'), '--flac-root', os.path.join(self.root, 'flac'),
                    '--template', os.path.join(self.root, 'stock.csv'), '--out', out, '--bank', 'b', '--zone', 'z',
                    '--prefix', 'p', '--alias', 'wpn_rgun_reload_open', '--role', 'wpn_rgun_reload_open=impact'])
        with open(os.path.join(out, 'sound', 'b.aliases.csv'), newline='') as f:
            rows = {r['Name']: r for r in csv.DictReader(f)}
        self.assertEqual(rows['wpn_rgun_reload_open']['channel'], 'explo_1_3d')

    def test_empty_bo3_alias_is_silent(self):
        self.assertNotIn('wpn_rgun_loop', self.rows)

    def test_unknown_alias_is_reported_silent(self):
        import contextlib
        import io
        import json
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            sound.main(['--bo3-aliases', os.path.join(self.root, 'bo3.csv'), '--flac-root', os.path.join(self.root, 'flac'),
                        '--template', os.path.join(self.root, 'stock.csv'), '--out', os.path.join(self.root, 'out3'),
                        '--bank', 'b', '--zone', 'z', '--prefix', 'p', '--alias', 'wpn_missing', 'wpn_rgun_reload_open',
                        '--role', 'wpn_rgun_reload_open=impact'])
        report = {r['alias']: r for r in json.loads(buf.getvalue())['aliases']}
        self.assertEqual(report['wpn_missing'], {'alias': 'wpn_missing', 'silent': True, 'unresolved': True})
        self.assertNotIn('silent', report['wpn_rgun_reload_open'])


@unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg not on PATH')
class PcmHeadTest(unittest.TestCase):
    def test_first_512_frames_as_16_bit_pcm(self):
        root = tempfile.mkdtemp()
        flac = os.path.join(root, 'tone.flac')
        # 0.1 s stereo ramp at 48 kHz, encoded as FLAC
        subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=0.1:sample_rate=48000',
                        '-ac', '2', '-c:a', 'flac', flac], check=True)
        head = sound.pcm_head(flac)
        self.assertEqual(sound.flac_channels(flac), 2)
        self.assertEqual(len(head), sound.HYBRID_PCM_FRAMES * 2 * 2)   # stock stereo head: 2048 bytes
        full = subprocess.run(['ffmpeg', '-v', 'error', '-i', flac, '-f', 's16le', '-'], capture_output=True).stdout
        self.assertEqual(head, full[:len(head)])


if __name__ == '__main__':
    unittest.main()
