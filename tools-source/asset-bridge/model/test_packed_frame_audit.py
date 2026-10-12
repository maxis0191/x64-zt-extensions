import math
import struct
import unittest
from packed_frame_audit import audit_frames, decode, read_prefix

def quad():
    # Literal words, independent of any forward encoder: +Z normal and +X tangent.
    return {'rows':[{'position':p, 'uv':uv, 'normal':0xFFF80200, 'tangent':0xE00803FF}
                    for p, uv in (((0,0,0),(0,0)), ((1,0,0),(1,0)), ((0,1,0),(0,1)))],
            'triangles':[(0,1,2)]}

class PackedFrames(unittest.TestCase):
    def test_six_literal_axes(self):
        words = [0xE00803FF,0xE0080000,0xE00FFE00,0xE0000200,0xFFF80200,0xC0080200]
        axes = [(1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)]
        for word, axis in zip(words, axes):
            self.assertLessEqual(max(abs(a-b) for a,b in zip(decode(word), axis)), 1/1023+1e-12)
    def test_geometry_and_uv_derived_frame(self):
        report = audit_frames(quad())
        self.assertTrue(report['source_geometry_consistent'])
        self.assertEqual(report['positive_uv_handedness_triangles'], 1)
    def test_signed_decoder_is_not_equivalent(self):
        self.assertFalse(audit_frames(quad(), 'signed10')['source_geometry_consistent'])
    def test_reversed_normal_detected(self):
        mesh = quad();mesh['rows'][0]['normal'] = 0xC0080200
        self.assertFalse(audit_frames(mesh)['source_geometry_consistent'])
    def test_mirrored_uv_is_observed_without_guessing_alpha(self):
        mesh = quad()
        for v in mesh['rows']: v['uv'] = (v['uv'][0], -v['uv'][1])
        report = audit_frames(mesh)
        self.assertEqual(report['negative_uv_handedness_triangles'], 1)
        self.assertTrue(report['source_geometry_consistent'])
    def test_degenerate_and_nonfinite_refused(self):
        mesh = quad();mesh['rows'][1]['uv'] = (0,0)
        with self.assertRaises(ValueError): audit_frames(mesh)
        mesh = quad();mesh['rows'][0]['position'] = (math.nan,0,0)
        with self.assertRaises(ValueError): audit_frames(mesh)
    def test_prefix_bounds_and_counts(self):
        for payload in (b'', b'\x08\x01', b'\x08\x01'+struct.pack('<I',0xffffffff)):
            with self.assertRaises(ValueError): read_prefix(payload)

if __name__ == '__main__': unittest.main()
