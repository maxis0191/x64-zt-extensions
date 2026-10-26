"""Source tests for the T7 sound bank reader and the IW7 sound bank source writer."""
import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kino_sound  # noqa: E402
import t7_sab  # noqa: E402


def t7_bank(path, payloads, version=15):
    """Synthetic T7 bank: 0x40 header, data, then 36-byte entries."""
    data = b"".join(payloads)
    eoff = 0x40 + len(data)
    head = struct.pack("<8IQQQ", t7_sab.MAGIC, version, 36, 0, 0, len(payloads), 0, 0, 0, eoff, 0)
    entries = b""
    off = 0x40
    for i, p in enumerate(payloads):
        entries += struct.pack("<IIIIQ", 0x100 + i, len(p), 48000 * (i + 1), 0, off) + bytes([6, 2, 0, 8]) + bytes(8)
        off += len(p)
    with open(path, "wb") as f:
        f.write(head.ljust(0x40, bytes(1)) + data + entries)


class T7SoundBank(unittest.TestCase):
    def test_list_and_extract_flac(self):
        with tempfile.TemporaryDirectory() as d:
            bank = os.path.join(d, "x.all.sabs")
            t7_bank(bank, [b"fLaC" + b"a" * 12, b"fLaC" + b"b" * 20])
            e = t7_sab.entries(bank)
            self.assertEqual([x["id"] for x in e], [0x100, 0x101])
            self.assertEqual((e[1]["rate"], e[1]["channels"], e[1]["seconds"]), (48000, 2, 2.0))
            out = os.path.join(d, "o.flac")
            t7_sab.extract(bank, 1, out)
            with open(out, "rb") as f:
                self.assertEqual(f.read(), b"fLaC" + b"b" * 20)

    def test_refuses_other_versions(self):
        with tempfile.TemporaryDirectory() as d:
            bank = os.path.join(d, "x.sabs")
            t7_bank(bank, [], version=4)
            with self.assertRaises(ValueError):
                t7_sab.entries(bank)


class SoundBankSource(unittest.TestCase):
    def test_music_alias_row_and_asset(self):
        with tempfile.TemporaryDirectory() as d:
            tpl = os.path.join(d, "t.csv")
            with open(tpl, "w", newline="") as f:
                f.write("Name,SecondaryAliasName,File,vol_min,vol_max\ncp_level_up,cp_level_up_lr,music\\x,1,1\n")
            flac = os.path.join(d, "s.flac")
            with open(flac, "wb") as f:
                f.write(b"fLaC")
            argv = sys.argv
            sys.argv = ["kino_sound", "--out", d, "--zone", "mod", "--template", tpl, "--music", "kino_mus_x=" + flac]
            try:
                kino_sound.main()
            finally:
                sys.argv = argv
            with open(os.path.join(d, "sound", "kino.all.aliases.csv")) as f:
                rows = f.read().splitlines()
            self.assertEqual(rows[1], "kino_mus_x,,music\\mod\\kino_mus_x,0.800000,0.800000")
            self.assertTrue(os.path.isfile(os.path.join(d, "sound_assets", "music", "mod", "kino_mus_x.flac")))
            self.assertTrue(os.path.isfile(os.path.join(d, "soundbank", "kino.all.json")))


if __name__ == "__main__":
    unittest.main()
