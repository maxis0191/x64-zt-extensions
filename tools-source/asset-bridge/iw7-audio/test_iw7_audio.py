"""Synthetic tests for iw7_sab.py and iwz_audio_bank.py (no game data)."""
import csv
import json
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iw7_sab  # noqa: E402
import iwz_audio_bank as bank  # noqa: E402


def flac_bytes(rate=48000, channels=2, frames=96000, block=1024, payload=b'\xff\xf8frames'):
    info = struct.pack('>HH', block, block) + b'\0' * 6
    info += bytes([(rate >> 12) & 0xFF, (rate >> 4) & 0xFF, (((channels - 1) << 1) | ((rate << 4) & 0xF0)) & 0xFF])
    info += bytes([(15 << 4) | ((frames >> 32) & 0x0F)]) + struct.pack('>I', frames & 0xFFFFFFFF) + b'\0' * 16
    return b'fLaC' + bytes([0x80]) + len(info).to_bytes(3, 'big') + info + payload


def write_bank(path, entries):
    """entries: list of (name, payload bytes, rate, channels, frames, looping)."""
    data_off = 0x1000
    blob = b''
    rows = []
    for name, payload, rate, ch, frames, loop in entries:
        rows.append((iw7_sab.snd_hash_name(name), len(payload), 0, frames, 0, data_off + len(blob), rate, ch, loop, 8,
                     0, 0, 0, 0, 0, 0, 0))
        blob += payload
    entry_off = data_off + len(blob)
    table = b''.join(iw7_sab.ENTRY.pack(*r) for r in rows)
    names_off = entry_off + len(table)
    names = b''.join(n.encode().ljust(128, b'\0') for n, *_ in entries)
    header = iw7_sab.HEADER.pack(iw7_sab.MAGIC, 0x17, 44, 16, 64, len(entries), 8, 0x17, 0, entry_off, 0, b'\0' * 16,
                                 b'\0' * 512, 0, names_off, b'testzone', b'pc', b'all', 0x17, len(blob), b'\0' * 5)
    with open(path, 'wb') as f:
        f.write(header.ljust(data_off, b'\0') + blob + table + names)


class SabTest(unittest.TestCase):
    def test_hash_is_case_insensitive_and_matches_engine_seed(self):
        self.assertEqual(iw7_sab.snd_hash_name('AMB\\X'), iw7_sab.snd_hash_name('amb\\x'))
        self.assertEqual(iw7_sab.snd_hash_name(''), 0)
        self.assertEqual(iw7_sab.snd_hash_name('a'), (65599 * 5381 + ord('a')) & 0xFFFFFFFF)

    def test_list_and_extract_rebuild_a_flac_container(self):
        root = tempfile.mkdtemp()
        p = os.path.join(root, 'test.sabl')
        write_bank(p, [('amb\\hum_lp', b'\xff\xf8abc', 48000, 2, 4800, 1), ('evt\\one', b'\xff\xf8de', 36000, 1, 360, 0)])
        b = iw7_sab.Bank(p)
        self.assertEqual(b.zone, 'testzone')
        names = [e['name'] for e in b.entries()]
        self.assertEqual(names, ['amb\\hum_lp', 'evt\\one'])
        self.assertAlmostEqual(b.entries()[0]['seconds'], 0.1)
        out = os.path.join(root, 'out')
        self.assertEqual(iw7_sab.main(['extract', p, '--name', 'evt\\one', '--out', out]), 0)
        f = os.path.join(out, 'evt', 'one.flac')
        info = bank.flac_info(f)
        self.assertEqual((info['rate'], info['channels'], info['frames'], info['bits']), (36000, 1, 360, 16))
        with open(f, 'rb') as h:
            self.assertTrue(h.read().endswith(b'\xff\xf8de'))

    def test_missing_name_fails(self):
        root = tempfile.mkdtemp()
        p = os.path.join(root, 'test.sabl')
        write_bank(p, [('a', b'\xff\xf8', 48000, 1, 10, 0)])
        self.assertEqual(iw7_sab.main(['extract', p, '--name', 'b', '--out', os.path.join(root, 'o')]), 1)


HEADER = ['Name', 'SecondaryAliasName', 'StopAliasName', 'Subtitle', 'File', 'vol_min', 'vol_max', 'dist_min', 'dist_max',
          'channel', 'type', 'loop', 'volumefalloffcurve', 'MusicContent', 'duck']


class BankTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.tpl = os.path.join(self.root, 'stock.aliases.csv')
        with open(self.tpl, 'w', newline='') as f:
            csv.writer(f).writerows([
                HEADER,
                ['mus_wave', '', 'stop', 'sub', 'music\\wave', '0.4', '0.4', '5000', '25000', 'music_lr', 'streamed', 'nonlooping', 'default', 'none', 'duck_a'],
                ['emt_hum', '', '', '', 'amb\\hum_lp', '0.2', '0.2', '35', '450', 'amb_elm_unres_3d', 'loaded', 'rlooping', 'reaction', 'none', ''],
                ['emt_creak', '', '', '', 'amb\\creak_1', '0.1', '0.1', '55', '350', 'amb_elm_unres_3d', 'loaded', 'nonlooping', 'default', 'music', ''],
                ['emt_creak', '', '', '', 'amb\\creak_2', '0.1', '0.1', '55', '350', 'amb_elm_unres_3d', 'loaded', 'nonlooping', 'default', 'none', ''],
            ])
        self.sabl = os.path.join(self.root, 'stock.sabl')
        write_bank(self.sabl, [('amb\\hum_lp', b'\xff\xf8h', 48000, 2, 48000, 1), ('amb\\creak_1', b'\xff\xf8c1', 48000, 2, 4800, 0),
                               ('amb\\creak_2', b'\xff\xf8c2', 48000, 2, 4800, 0)])
        self.song = os.path.join(self.root, 'song.flac')
        with open(self.song, 'wb') as f:
            f.write(flac_bytes(frames=48000 * 300))
        self.out = os.path.join(self.root, 'out')

    def spec(self, **over):
        s = {'bank': 'cp_test.all', 'zone': 'cp_test', 'template_aliases': self.tpl, 'stock_banks': [self.sabl],
             'aliases': [
                 {'name': 'mus_song', 'template': 'mus_wave', 'source': self.song, 'file': 'iwz\\mus\\song',
                  'set': {'vol_max': 0.5, 'vol_min': 0.5, 'MusicContent': 'music'}},
                 {'name': 'emt_hum', 'source': 'stock'},
                 {'name': 'emt_creak', 'source': 'stock'},
             ]}
        s.update(over)
        return s

    def test_builds_bank_sources_and_manifest(self):
        r = bank.build(self.spec(), self.out)
        self.assertEqual(r['errors'], [])
        with open(os.path.join(self.out, 'sound', 'cp_test.all.aliases.csv'), newline='') as f:
            rows = list(csv.DictReader(f))
        self.assertEqual([x['Name'] for x in rows], ['mus_song', 'emt_hum', 'emt_creak', 'emt_creak'])
        song = rows[0]
        self.assertEqual((song['File'], song['channel'], song['type'], song['vol_max']), ('iwz\\mus\\song', 'music_lr', 'streamed', '0.500000'))
        self.assertEqual((song['duck'], song['StopAliasName'], song['Subtitle']), ('', '', ''))
        self.assertTrue(os.path.isfile(os.path.join(self.out, 'sound_assets', 'amb', 'creak_2.flac')))
        with open(os.path.join(self.out, 'soundbank', 'cp_test.all.json')) as f:
            sb = json.load(f)
        self.assertEqual((sb['name'], sb['zone'], sb['aliases']), ('cp_test.all', 'cp_test', ['sound/cp_test.all.aliases.csv']))
        self.assertEqual(r['expected_files'], {'sabl': 'cp_test.sabl', 'sabs': 'cp_test.sabs'})
        with open(os.path.join(self.out, 'zone_rows.csv')) as f:
            self.assertEqual(f.read().strip(), 'soundbank,cp_test.all')

    def test_sound_zones_copy_tables_and_rename_rows(self):
        defs = os.path.join(self.root, 'defs')
        os.makedirs(os.path.join(defs, 'unk'))
        for key, suffix in bank.DEF_TABLES:
            with open(os.path.join(defs, 'stock.all.%s.csv' % suffix), 'w') as f:
                f.write('col' + chr(10) + suffix + chr(10))
        with open(os.path.join(defs, 'unk', 'stock.all.json'), 'w') as f:
            f.write('[]')
        head = ['ReverbIndex', 'Zone_Name', 'Ambience', 'Mix', 'Reverb', 'Filter', 'Occlusion']
        with open(os.path.join(defs, 'stock.all.zone.csv'), 'w', newline='') as f:
            csv.writer(f).writerows([head, ['5', 'stock_room', 'emt_hum', 'mix_a', 'lg_room', 'default', 'occ'],
                                     ['6', 'stock_ext', 'amb_missing', '', 'ext', 'default', 'occ']])
        z = {'defs': defs, 'defs_bank': 'stock.all', 'rows': [{'name': 'cp_test', 'copy': 'stock_room'}]}
        r = bank.build(self.spec(zones=z), self.out)
        self.assertEqual(r['errors'], [])
        self.assertEqual(r['sound_zones'][0]['reverb'], 'lg_room')
        with open(os.path.join(self.out, 'sound', 'cp_test.all.zone.csv'), newline='') as f:
            rows = list(csv.reader(f))
        self.assertEqual(rows[1:], [['5', 'cp_test', 'emt_hum', 'mix_a', 'lg_room', 'default', 'occ']])
        with open(os.path.join(self.out, 'soundbank', 'cp_test.all.json')) as f:
            sb = json.load(f)
        self.assertEqual(sb['ReverbDefs'], ['sound/cp_test.all.reverbs.csv'])
        self.assertEqual(sb['Unks'], ['sound/unk/cp_test.all.json'])
        self.assertTrue(os.path.isfile(os.path.join(self.out, 'sound', 'cp_test.all.mixes.csv')))
        z['rows'] = [{'name': 'cp_test', 'copy': 'stock_ext'}, {'name': 'x', 'copy': 'nope'}]
        errors = chr(10).join(bank.build(self.spec(zones=z), os.path.join(self.root, 'out2'))['errors'])
        self.assertIn('ambience bed amb_missing is not an alias', errors)
        self.assertIn('stock zone nope not found', errors)
        # no_mix: the zone keeps its bed, reverb, filter and occlusion without the stock mix
        z['rows'] = [{'name': 'cp_test', 'copy': 'stock_room', 'no_mix': True}]
        r = bank.build(self.spec(zones=z), os.path.join(self.root, 'out3'))
        self.assertEqual((r['errors'], r['sound_zones'][0]['mix'], r['sound_zones'][0]['ambience']), ([], '', 'emt_hum'))

    def test_rejects_values_stock_never_uses(self):
        s = self.spec()
        s['aliases'][0]['set']['channel'] = 'music_bogus'
        self.assertTrue(any('music_bogus' in e for e in bank.build(s, self.out, check_only=True)['errors']))

    def test_long_loaded_audio_must_stream(self):
        s = self.spec()
        s['aliases'][0]['set']['type'] = 'loaded'
        self.assertTrue(any('stream it' in e for e in bank.build(s, self.out)['errors']))

    def test_3d_alias_needs_a_falloff_range(self):
        s = self.spec()
        s['aliases'][1]['set'] = {'dist_min': 500.0, 'dist_max': 100.0}
        self.assertTrue(any('dist_max' in e for e in bank.build(s, self.out, check_only=True)['errors']))

    def test_retrigger_clip_crossfades_back_into_the_loop(self):
        import array
        loop = array.array('h', [1000 + (i % 7) * 10 for i in range(40)])   # 20 stereo frames
        clip = bank.retrigger_samples(loop, 2, 4)                            # 4-frame overlap
        self.assertEqual(len(clip), len(loop) + 8)
        self.assertEqual(clip[0], 0)
        # started again every len(loop) samples: tail of the old copy + head of the new copy == the loop
        for i in range(8):
            self.assertLessEqual(abs(clip[len(loop) + i] + clip[i] - loop[i]), 1)
        self.assertEqual(clip[8:len(loop)].tolist(), loop[8:].tolist())

    def test_retrigger_alias_gets_a_twin_row(self):
        s = self.spec()
        s['aliases'].append({'name': 'emt_bed', 'template': 'emt_hum', 'source': 'stock', 'retrigger_overlap': 0.01,
                             'set': {'loop': 'nonlooping'}})
        r = bank.build(s, self.out, check_only=True)
        self.assertEqual(r['errors'], [])
        orig = bank.make_retrigger
        bank.make_retrigger = lambda path, overlap: None
        try:
            r = bank.build(s, self.out)
        finally:
            bank.make_retrigger = orig
        self.assertEqual(r['errors'], [])
        with open(os.path.join(self.out, 'sound', 'cp_test.all.aliases.csv'), newline='') as f:
            rows = {x['Name']: x for x in csv.DictReader(f)}
        self.assertIn('emt_bed_b', rows)
        self.assertNotIn('emt_hum_b', rows)
        self.assertEqual(rows['emt_bed_b']['File'], rows['emt_bed']['File'])
        self.assertEqual((rows['emt_bed']['channel'], rows['emt_bed_b']['channel']), ('amb_elm_unres_3d', 'amb_elm_unres_2d'))

    def test_variants_from_stock_aliases_and_files(self):
        # one alias, several rows: every row of a stock alias of a second template table, plus a file
        tpl2 = os.path.join(self.root, 'other.aliases.csv')
        with open(tpl2, 'w', newline='') as f:
            csv.writer(f).writerows([HEADER, ['other_creak', '', '', '', 'amb\\creak_2', '0.3', '0.3', '55', '350',
                                              'amb_elm_unres_3d', 'loaded', 'nonlooping', 'default', 'none', '']])
        s = self.spec(template_aliases=[self.tpl, tpl2])
        s['aliases'].append({'name': 'amb_mix', 'template': 'emt_creak', 'set': {'vol_max': 0.2, 'vol_min': 0.2},
                             'variants': [{'stock': 'emt_creak'}, {'stock': 'other_creak'},
                                          {'source': self.song, 'file': 'iwz\\amb\\x', 'set': {'type': 'streamed'}}]})
        r = bank.build(s, self.out)
        self.assertEqual(r['errors'], [])
        with open(os.path.join(self.out, 'sound', 'cp_test.all.aliases.csv'), newline='') as f:
            rows = [x for x in csv.DictReader(f) if x['Name'] == 'amb_mix']
        self.assertEqual([x['File'] for x in rows], ['amb\\creak_1', 'amb\\creak_2', 'amb\\creak_2', 'iwz\\amb\\x'])
        self.assertEqual([x['vol_max'] for x in rows], ['0.200000'] * 4)
        self.assertEqual(rows[-1]['type'], 'streamed')
        s['aliases'][-1]['variants'].append({'stock': 'nope'})
        self.assertTrue(any('nope' in e for e in bank.build(s, self.out, check_only=True)['errors']))

    def test_ambience_volmod_is_accepted(self):
        # vol_mod ambience is the stock bed row's value; it is not what kept the Station Zero beds silent
        tpl = os.path.join(self.root, 'beds.aliases.csv')
        with open(tpl, 'w', newline='') as f:
            csv.writer(f).writerows([HEADER + ['vol_mod'],
                                     ['amb_bed', '', '', '', 'amb\\hum_lp', '0.27', '0.27', '5000', '25000', 'amb_bed_2d', 'loaded', 'looping', 'default', 'none', '', 'ambience'],
                                     ['emt_x', '', '', '', 'amb\\hum_lp', '0.2', '0.2', '35', '450', 'amb_elm_unres_3d', 'loaded', 'rlooping', 'default', 'none', '', 'emitter']])
        s = self.spec(template_aliases=tpl, aliases=[{'name': 'amb_bed', 'source': 'stock'}])
        self.assertEqual(bank.build(s, self.out, check_only=True)['errors'], [])

    def test_file_names_survive_zonetool_csv_escapes(self):
        # ZoneTool's CSV reader turns "\t" into a tab: stock "cp\trolley_movement_lp" broke a build
        self.assertEqual(bank.zonetool_safe_file('cp\\trolley_movement_lp.LL.75.0.all'), 'cp/trolley_movement_lp.LL.75.0.all')
        self.assertEqual(bank.zonetool_safe_file('amb_emitters\\emt_hum'), 'amb_emitters\\emt_hum')
        with open(self.tpl, 'a', newline='') as f:
            csv.writer(f).writerow(['coaster_low', '', '', '', 'cp\\trolley_lp', '0', '0', '150', '1000', 'amb_elm_unres_3d',
                                    'loaded', 'rlooping', 'default', 'none', ''])
        write_bank(self.sabl, [('cp\\trolley_lp', b'\xff\xf8t', 48000, 1, 4800, 1)])
        s = self.spec(aliases=[{'name': 'amb_train', 'template': 'coaster_low', 'source': 'stock', 'set': {'vol_min': 0.3, 'vol_max': 0.3}}])
        r = bank.build(s, self.out)
        self.assertEqual(r['errors'], [])
        with open(os.path.join(self.out, 'sound', 'cp_test.all.aliases.csv'), newline='') as f:
            row = list(csv.DictReader(f))[0]
        self.assertEqual(row['File'], 'cp/trolley_lp')
        self.assertTrue(os.path.isfile(os.path.join(self.out, 'sound_assets', 'cp', 'trolley_lp.flac')))

    def test_variables_expand(self):
        self.assertEqual(bank.expand({'a': ['${X}/y']}, {'X': 'root'}), {'a': ['root/y']})
        with self.assertRaises(SystemExit):
            bank.expand('${MISSING}', {})


if __name__ == '__main__':
    unittest.main()
