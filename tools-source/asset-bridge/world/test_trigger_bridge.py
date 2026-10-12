"""Original data only; no native process, SDK copy, extraction or game."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random
import tempfile
import unittest

import trigger_bridge as bridge

ROOT = Path(__file__).resolve().parent


def original():
    return json.loads((ROOT / 'fixtures/original-trigger.json').read_text())


class TriggerBridgeTest(unittest.TestCase):
    def test_original_golden_records(self):
        source = original()
        before = deepcopy(source)
        output = bridge.convert(source)
        self.assertEqual(source, before)
        self.assertEqual(output['triggerType'], [3])
        self.assertEqual(output['trigger']['models'], [
            {'contents': 1, 'hullCount': 1, 'firstHull': 0, 'windingCount': 0,
             'firstWinding': 0, 'flags': 0, 'physicsAsset': None, 'physicsShapeOverrideIdx': 65535}])
        self.assertEqual(output['trigger']['hulls'], source['trigger']['hulls'])
        self.assertEqual(output['trigger']['slabs'], source['trigger']['slabs'])
        self.assertEqual(output['trigger']['windings'], [])
        self.assertFalse(output['runtime_ready'])
        saved = json.loads((ROOT / 'fixtures/original-trigger.iw7.json').read_text())
        self.assertEqual(saved.pop('source_sha256'), hashlib.sha256(
            (ROOT / 'fixtures/original-trigger.json').read_bytes()).hexdigest())
        self.assertEqual(saved, output)

    def test_all_512_h1_flag_combinations(self):
        # Independent literal mapping from the five matching enum members.
        for value in range(512):
            with self.subTest(value=value):
                if value & (2 | 64 | 128 | 256):
                    with self.assertRaisesRegex(ValueError, 'Unsupported H1'):
                        bridge.convert_type(value)
                else:
                    expected = (value & 1) | ((value & 60) >> 1)
                    self.assertEqual(bridge.convert_type(value), expected)
        for value in (-1, 2**31, True, '1', 1.0, 2**30):
            with self.subTest(value=value), self.assertRaises(ValueError):
                bridge.convert_type(value)

    def test_seeded_original_geometries(self):
        rng = random.Random(20261012)
        for _ in range(100):
            source = original()
            center = [rng.randint(-512, 512) / 4 for _ in range(3)]
            extent = [rng.randint(1, 128) / 4 for _ in range(3)]
            source['trigger']['hulls'][0]['bounds'] = {'midPoint': center, 'halfSize': extent}
            for index, slab in enumerate(source['trigger']['slabs']):
                slab['midPoint'], slab['halfSize'] = center[index], extent[index]
            result = bridge.convert(source)
            self.assertEqual(result['trigger']['hulls'], source['trigger']['hulls'])
            self.assertEqual(result['trigger']['slabs'], source['trigger']['slabs'])

    def test_native_scalar_and_referenced_ranges(self):
        cases = [
            ('model', 'contents', 2**31), ('model', 'contents', -2**31-1),
            ('model', 'contents', True), ('model', 'hullCount', -1),
            ('model', 'hullCount', 65536), ('model', 'hullCount', 2),
            ('model', 'firstHull', 65535), ('hull', 'firstSlab', 3),
            ('hull', 'slabCount', 4), ('hull', 'contents', 2**32),
        ]
        for kind, key, value in cases:
            source = original()
            record = source['trigger']['models' if kind == 'model' else 'hulls'][0]
            record[key] = value
            with self.subTest(case=(kind, key, value)), self.assertRaises(ValueError):
                bridge.convert(source)

    def test_counts_and_caps(self):
        for key in ('count', 'hullCount', 'slabCount'):
            for value in (-1, True, 999999):
                source = original(); source['trigger'][key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    bridge.convert(source)
        source = original(); source['triggerType'] = []
        with self.assertRaises(ValueError):
            bridge.convert(source)
        source = original(); source['trigger']['slabs'].append(source['trigger']['slabs'][0])
        with self.assertRaises(ValueError):
            bridge.convert(source)

    def test_float_validation(self):
        for value in (float('inf'), float('nan'), 1e100, 1e-100, 10**400, True, '1'):
            source = original(); source['trigger']['slabs'][0]['midPoint'] = value
            with self.subTest(value=str(value)), self.assertRaises(ValueError):
                bridge.convert(source)
        for key in ('bounds', 'slab'):
            source = original()
            if key == 'bounds':
                source['trigger']['hulls'][0]['bounds']['halfSize'][0] = -1
            else:
                source['trigger']['slabs'][0]['halfSize'] = -1
            with self.assertRaises(ValueError):
                bridge.convert(source)
        source = original(); source['trigger']['slabs'][0]['dir'] = [0, 0, 0]
        with self.assertRaises(ValueError):
            bridge.convert(source)
        source = original(); source['trigger']['slabs'][0]['dir'] = [1, 0]
        with self.assertRaises(ValueError):
            bridge.convert(source)
        self.assertEqual(bridge.f32(0.1, 'test'), 0.10000000149011612)

    def test_unsupported_fields_are_not_dropped(self):
        for target, name, value in (
            ('root', 'havokWorldShapeData', 'not supported'),
            ('trigger', 'windings', []), ('model', 'physicsAsset', 'original_shape'),
            ('hull', 'extra', 0), ('slab', 'extra', 0), ('bounds', 'padding', 0),
        ):
            source = original()
            targets = {'root': source, 'trigger': source['trigger'],
                       'model': source['trigger']['models'][0], 'hull': source['trigger']['hulls'][0],
                       'slab': source['trigger']['slabs'][0], 'bounds': source['trigger']['hulls'][0]['bounds']}
            targets[target][name] = value
            with self.subTest(target=target), self.assertRaisesRegex(ValueError, 'exact supported fields'):
                bridge.convert(source)

    def test_empty_and_shared_ranges(self):
        source = {'schema': bridge.INPUT_SCHEMA, 'trigger':
                  {'count': 0, 'models': [], 'hullCount': 0, 'hulls': [], 'slabCount': 0, 'slabs': []},
                  'triggerType': []}
        self.assertEqual(bridge.convert(source)['trigger']['count'], 0)
        source = original()
        source['trigger']['models'] *= 2; source['trigger']['count'] = 2
        source['triggerType'] = [0, 61]
        self.assertEqual(bridge.convert(source)['triggerType'], [0, 31])

    def test_json_boundaries(self):
        for data in (b'{"schema":1,"schema":2}', b'{"x":NaN}', b'\xff',
                     b' ' * (bridge.MAX_BYTES + 1), b'[' * 2000 + b']' * 2000):
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                bridge.parse(data)
        value = {'text': '"' + '[' * 100 + '\\' + '}' * 100}
        self.assertEqual(bridge.parse(json.dumps(value).encode()), value)

    def test_cli_file_contract(self):
        with tempfile.TemporaryDirectory(prefix='.trigger-test-', dir=ROOT) as temporary:
            folder = Path(temporary).resolve()
            self.assertEqual(folder.parent, ROOT)  # exact owned cleanup root
            input_path, output_path = folder / 'in.json', folder / 'out.json'
            input_path.write_text(json.dumps(original()))
            result = bridge.write_conversion(input_path, output_path)
            self.assertEqual(json.loads(output_path.read_text()), result)
            self.assertEqual(len(result['source_sha256']), 64)
            frozen = output_path.read_bytes()
            with self.assertRaises(FileExistsError):
                bridge.write_conversion(input_path, output_path)
            self.assertEqual(output_path.read_bytes(), frozen)
            source = original(); source['triggerType'][0] = 2
            input_path.write_text(json.dumps(source))
            with self.assertRaises(ValueError):
                bridge.write_conversion(input_path, folder / 'rejected.json')
            self.assertFalse((folder / 'rejected.json').exists())
            with self.assertRaises(ValueError):
                bridge.write_conversion('relative.json', output_path)
            with self.assertRaises(ValueError):
                bridge.write_conversion(input_path, folder / 'misleading.ents.data')


if __name__ == '__main__':
    unittest.main(verbosity=2)
