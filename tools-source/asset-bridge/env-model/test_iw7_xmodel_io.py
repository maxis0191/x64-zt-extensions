"""Round trip of every ZoneTool IW7 xmodel/xsurface dump in a folder: python test_iw7_xmodel_io.py <dump dir>."""
import glob, os, sys, collections, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iw7_xmodel_io as io

DUMP = os.environ.get('IW7_DUMP_DIR')


def roundtrip(folder, limit=None):
    out = collections.Counter()
    for kind, pat, parse, write in (('xsb', 'xsurface/*.xsb', io.parse_xsurfs, io.write_xsurfs),
                                    ('xmb', 'xmodel/*.xmb', io.parse_xmodel, io.write_xmodel)):
        for f in sorted(glob.glob(os.path.join(folder, pat)))[:limit]:
            d = open(f, 'rb').read()
            try:
                o = write(parse(d))
            except io.StreamError as e:
                out[kind + ' refused: ' + str(e)[:40]] += 1
                continue
            out[kind + (' identical' if o == d else ' DIFFERENT')] += 1
    return out


class RoundTrip(unittest.TestCase):
    @unittest.skipUnless(DUMP, 'set IW7_DUMP_DIR to a ZoneTool IW7 dump folder')
    def test_dump_roundtrip(self):
        r = roundtrip(DUMP)
        self.assertFalse([k for k in r if 'DIFFERENT' in k], r)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        print(dict(roundtrip(sys.argv[1])))
    else:
        unittest.main()
