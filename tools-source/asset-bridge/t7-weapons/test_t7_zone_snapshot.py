"""Synthetic tests for t7_zone_snapshot.py: a fake ZoneTool, no game data."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_zone_snapshot as snap  # noqa: E402

FAKE_ZONETOOL = r'''
import os, sys, time
args = sys.argv[1:]
log, zone, release = args[args.index("-assetlog") + 1], args[args.index("-holdzone") + 1], args[-1]
open(log, "w").write("23\tweapon\tray_gun\t0x1000\n")
print("[ INFO ] Loading zone", zone, flush=True)
print("[ INFO ][ zonetool::t7::handle_params ]: ZONETOOL_HOLD %s %d" % (zone, os.getpid()), flush=True)
while not os.path.exists(release):
    time.sleep(0.05)
'''
FAKE_DIES = 'print("cannot load zone", flush=True)\nraise SystemExit(3)\n'


class SnapshotTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def fake(self, body):
        path = os.path.join(self.root, "zt.py")
        with open(path, "w") as f:
            f.write(body)
        return [sys.executable, path]

    def test_reads_while_held_then_releases(self):
        seen = []

        def readers(python, pid, paths):
            seen.append((pid, os.path.exists(paths["assetlog"])))
            return [[python, "-c", "print('read %d')" % pid]]
        out = snap.snapshot(self.fake(FAKE_ZONETOOL), self.root, "zm_levelcommon",
                            os.path.join(self.root, "out"), readers=readers, timeout=30)
        self.assertEqual(len(seen), 1)
        self.assertTrue(seen[0][1], "readers run after the asset log exists")
        self.assertEqual(out["readers"], ["read %d" % out["holder_pid"]])
        self.assertTrue(out["paths"]["weapons"].endswith("zm_levelcommon.weapons.json"))
        self.assertEqual([f for f in os.listdir(self.root) if f.startswith("release")], [])

    def test_zonetool_exit_before_hold_fails(self):
        with self.assertRaises(SystemExit) as ctx:
            snap.snapshot(self.fake(FAKE_DIES), self.root, "zm_x", os.path.join(self.root, "out"),
                          readers=lambda *a: [], timeout=30)
        self.assertIn("cannot load zone", str(ctx.exception))

    def test_reader_commands_target_the_holder(self):
        cmds = snap.reader_commands("py", 42, snap.outputs("o", "zm_x"))
        self.assertEqual([c[2].rsplit(os.sep, 1)[-1] for c in cmds], ["t7_weapon_scan.py", "t7_fx_read.py"])
        self.assertTrue(all(c[c.index("--pid") + 1] == "42" for c in cmds))


if __name__ == "__main__":
    unittest.main()
