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
            ['wpn_rgun_sweet_plr', 'wpn/fire_sweet.flac', 'wpn_rgun_lfe_plr', '70', '70'],
            ['wpn_rgun_lfe_plr', 'wpn/fire_sweet.flac', '', '70', '70'],
            ['wpn_rgun_pap_plr', 'wpn/fire.flac', 'wpn_rgun_fire_plr', '90', '90'],
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
            ['plr2', 'x', '', '', '', 'hybrid_pcm', 'weap_plr_fire_2_2d', '0.8', '0.9', ''],
            ['plr3', 'x', '', '', '', 'hybrid_pcm', 'weap_plr_fire_3_2d', '0.8', '0.9', ''],
            ['lfe', 'x', '', '', '', 'loaded', 'weap_plr_fire_lfe_2d', '0.8', '0.9', ''],
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
        self.assertEqual(set(self.rows), {'wpn_rgun_fire_plr', 'wpn_rgun_sweet_plr', 'wpn_rgun_lfe_plr', 'wpn_rgun_reload_open',
                                          'wpn_rgun_exp', 'wpn_rgun_exp_tail'})
        self.assertEqual(self.rows['wpn_rgun_fire_plr']['channel'], 'weap_plr_fire_overlap_2d')
        self.assertEqual(self.rows['wpn_rgun_fire_plr']['SecondaryAliasName'], 'wpn_rgun_sweet_plr')
        self.assertEqual(self.rows['wpn_rgun_reload_open']['channel'], 'scn_fx_unres_2d')
        self.assertEqual(self.rows['wpn_rgun_exp']['channel'], 'explo_1_3d')

    def test_each_fire_layer_has_its_own_channel(self):
        # stock chains: overlap, fire_2, fire_3 ..., the LFE layer on the LFE channel and loaded
        self.assertEqual(self.rows['wpn_rgun_sweet_plr']['channel'], 'weap_plr_fire_2_2d')
        self.assertEqual(self.rows['wpn_rgun_lfe_plr']['channel'], 'weap_plr_fire_lfe_2d')
        self.assertEqual(self.rows['wpn_rgun_lfe_plr']['type'], 'loaded')

    def test_pap_root_chaining_into_the_base_root_keeps_layers_apart(self):
        out = os.path.join(self.root, 'pap')
        sound.main(['--bo3-aliases', os.path.join(self.root, 'bo3.csv'), '--flac-root', os.path.join(self.root, 'flac'),
                    '--template', os.path.join(self.root, 'stock.csv'), '--out', out, '--bank', 'b', '--zone', 'z',
                    '--prefix', 'p', '--alias', 'wpn_rgun_fire_plr', 'wpn_rgun_pap_plr'])
        with open(os.path.join(out, 'sound', 'b.aliases.csv'), newline='') as f:
            rows = {r['Name']: r['channel'] for r in csv.DictReader(f)}
        self.assertEqual(rows['wpn_rgun_pap_plr'], 'weap_plr_fire_overlap_2d')
        self.assertEqual(rows['wpn_rgun_fire_plr'], 'weap_plr_fire_2_2d')
        self.assertEqual(rows['wpn_rgun_sweet_plr'], 'weap_plr_fire_3_2d')

    def test_layer_shared_by_player_and_npc_chains_is_copied_per_role(self):
        # DG-2: wpn_tesla_fire_plr and wpn_tesla_fire_npc both end in the flux layers
        write_csv(os.path.join(self.root, 'shared.csv'), [
            ['Name', 'FileSpec', 'Secondary', 'VolMin', 'VolMax'],
            ['wpn_t_fire_plr', 'wpn/fire.flac', 'wpn_t_flux_l', '90', '90'],
            ['wpn_t_fire_npc', 'wpn/fire.flac', 'wpn_t_flux_l', '90', '90'],
            ['wpn_t_flux_l', 'wpn/fire_sweet.flac', 'wpn_t_flux_r', '90', '90'],
            ['wpn_t_flux_r', 'wpn/fire_sweet.flac', '', '90', '90'],
        ])
        stock = os.path.join(self.root, 'stock_npc.csv')
        with open(os.path.join(self.root, 'stock.csv'), newline='') as f:
            rows = list(csv.reader(f))
        write_csv(stock, rows + [['npc', 'x', '', '', '', 'loaded', 'weap_npc_main_3d', '0.5', '0.5', '']])
        out = os.path.join(self.root, 'shared')
        sound.main(['--bo3-aliases', os.path.join(self.root, 'shared.csv'), '--flac-root', os.path.join(self.root, 'flac'),
                    '--template', stock, '--out', out, '--bank', 'b', '--zone', 'z', '--prefix', 'p',
                    '--alias', 'wpn_t_fire_plr', 'wpn_t_fire_npc', '--role', 'wpn_t_fire_plr=player',
                    '--role', 'wpn_t_fire_npc=npc'])
        with open(os.path.join(out, 'sound', 'b.aliases.csv'), newline='') as f:
            rows = {r['Name']: r for r in csv.DictReader(f)}
        chan = {n: (r['channel'], r['type'], r['SecondaryAliasName'], r['File']) for n, r in rows.items()}
        self.assertEqual(chan['wpn_t_fire_plr'], ('weap_plr_fire_overlap_2d', 'hybrid_pcm', 'wpn_t_flux_l', 'p/wpn_t_fire_plr'))
        self.assertEqual(chan['wpn_t_flux_l'], ('weap_plr_fire_2_2d', 'hybrid_pcm', 'wpn_t_flux_r', 'p/wpn_t_flux_l'))
        self.assertEqual(chan['wpn_t_flux_r'], ('weap_plr_fire_3_2d', 'hybrid_pcm', '', 'p/wpn_t_flux_r'))
        self.assertEqual(chan['wpn_t_fire_npc'], ('weap_npc_main_3d', 'loaded', 'wpn_t_flux_l_npc', 'p/wpn_t_fire_npc'))
        # NPC chains also put each layer on its own stock channel (main, mech, mid)
        self.assertEqual(chan['wpn_t_flux_l_npc'], ('weap_npc_mech_3d', 'loaded', 'wpn_t_flux_r_npc', 'p/wpn_t_flux_l_npc'))
        self.assertEqual(chan['wpn_t_flux_r_npc'], ('weap_npc_mid_3d', 'loaded', '', 'p/wpn_t_flux_r_npc'))
        # every layer keeps the stock row of the role's root channel, only the channel differs
        self.assertEqual(rows['wpn_t_flux_r_npc']['vol_max'], rows['wpn_t_fire_npc']['vol_max'])
        # each copy has its own FLAC, so ZoneTool gives the hybrid and the loaded copy separate bank entries
        self.assertTrue(os.path.isfile(os.path.join(out, 'sound_assets', 'p', 'wpn_t_flux_l_npc.flac')))

    def test_too_deep_chain_is_refused(self):
        with self.assertRaises(SystemExit):
            sound.layer_channel('player', 'wpn_x_plr', len(sound.LAYER_CHANNELS['player']))
        with self.assertRaises(SystemExit):
            sound.layer_channel('npc', 'wpn_x_npc', len(sound.LAYER_CHANNELS['npc']))
        # roles without layer channels keep their single channel at any depth
        self.assertEqual(sound.layer_channel('foley', 'wpn_x_reload', 5), 'scn_fx_unres_2d')

    def test_lfe_layer_takes_no_depth(self):
        # Thundergun PaP NPC: pap > fire > lfe > flux_l > flux_r fits main, mech, (lfe), mid, dist
        links = {'pap': 'fire', 'fire': 'lfe', 'lfe': 'flux_l', 'flux_l': 'flux_r'}
        depth = sound.chain_depths(['pap', 'fire', 'lfe', 'flux_l', 'flux_r'], lambda n: links.get(n, ''), lambda n: 'lfe' in n)
        self.assertEqual([sound.layer_channel('npc', n, depth[n]) for n in ('pap', 'fire', 'lfe', 'flux_l', 'flux_r')],
                         ['weap_npc_main_3d', 'weap_npc_mech_3d', 'weap_npc_lfe_3d', 'weap_npc_mid_3d', 'weap_npc_dist_3d'])

    def test_impact_chain_layers_take_explosion_channels(self):
        self.assertEqual(self.rows['wpn_rgun_exp']['channel'], 'explo_1_3d')
        self.assertEqual(self.rows['wpn_rgun_exp_tail']['channel'], 'explo_2_3d')
        self.assertEqual(self.rows['wpn_rgun_exp_tail']['type'], 'loaded')

    def test_silent_links_are_skipped(self):
        # a chain never names an alias the bank lacks: the silent middle layer is stepped over
        self.assertEqual(self.rows['wpn_rgun_exp']['SecondaryAliasName'], 'wpn_rgun_exp_tail')

    def test_volume_is_relative_to_the_chain_root(self):
        # The audible stock row (not the muted one) is the template.
        self.assertAlmostEqual(float(self.rows['wpn_rgun_fire_plr']['vol_max']), 0.9, places=5)
        # 20 below the root: a tenth of the stock volume.
        self.assertAlmostEqual(float(self.rows['wpn_rgun_sweet_plr']['vol_max']), 0.09, places=5)

    def test_gain_raises_every_volume_up_to_the_stock_cap(self):
        out = os.path.join(self.root, 'gain')
        sound.main(['--bo3-aliases', os.path.join(self.root, 'bo3.csv'), '--flac-root', os.path.join(self.root, 'flac'),
                    '--template', os.path.join(self.root, 'stock.csv'), '--out', out, '--bank', 'b', '--zone', 'z',
                    '--prefix', 'p', '--alias', 'wpn_rgun_fire_plr', '--gain-db', '6'])
        with open(os.path.join(out, 'sound', 'b.aliases.csv'), newline='') as f:
            rows = {r['Name']: r for r in csv.DictReader(f)}
        self.assertAlmostEqual(float(rows['wpn_rgun_fire_plr']['vol_max']), 1.0, places=5)   # 0.9 * 2 capped
        self.assertAlmostEqual(float(rows['wpn_rgun_sweet_plr']['vol_max']), 0.09 * 10 ** 0.3, places=4)

    def test_loaded_mod_files_without_stock_references(self):
        for name, row in self.rows.items():
            # player fire layers start from an uncompressed head, as every stock player fire sound
            self.assertEqual(row['type'], 'hybrid_pcm' if name.endswith('_plr') and 'lfe' not in name else 'loaded')
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
