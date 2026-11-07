"""Synthetic tests for t7_weapon_kick.py (no game data)."""
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t7_weapon_kick as kick  # noqa: E402


def weapdef():
    raw = bytearray(0x2000)
    struct.pack_into("<if8f5f", raw, 0x1208, 0, 0.0, -35, -40, 0, 0, 825, 2000, 25, 100, 40, 55, 30, 25, -25)
    struct.pack_into("<if8f5f", raw, 0x1268, 2, 50.0, -30, -35, -2, 18, 1000, 1200, 100, 2, 40, 45, 30, 25, -25)
    return bytes(raw)


class KickTest(unittest.TestCase):
    def test_fields(self):
        f = kick.kick_fields(weapdef())
        self.assertEqual(f["fAdsGunKickPitchMin"], -35.0)
        self.assertEqual(f["fAdsGunKickAccel"], 825.0)
        self.assertEqual(f["fHipGunKickYawMax"], 18.0)
        self.assertEqual((f["fHipGunKickSpeedMax"], f["fHipGunKickStaticDecay"]), (1200.0, 2.0))
        self.assertEqual((f["fHipViewKickPitchMin"], f["fHipViewKickPitchMax"]), (40.0, 45.0))
        self.assertEqual(f["fHipViewKickMagMin"], 30.0)
        # BO3 stores yaw 25 / -25: IW7 gets an ordered range.
        self.assertEqual((f["fHipViewKickYawMin"], f["fHipViewKickYawMax"]), (-25.0, 25.0))
        self.assertEqual((f["hipGunKickReducedKickBullets"], f["hipGunKickReducedKickPercent"]), (2, 50.0))
        self.assertEqual(f["fAdsGunKickMagMin"], 0.0)
        self.assertEqual(len(f), 32)   # 16 IW7 fields per block


if __name__ == "__main__":
    unittest.main()
