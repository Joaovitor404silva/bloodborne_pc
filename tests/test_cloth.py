# SPDX-License-Identifier: GPL-2.0-or-later
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import cloth  # noqa: E402
import quit_menu  # noqa: E402


class SteadyClothTest(unittest.TestCase):
    def test_the_code_fits_its_cave(self):
        (cave, code), (site, jump) = cloth.code_writes()
        self.assertEqual(cave, cloth.CAVE)
        self.assertEqual(len(code), 0x200)
        self.assertLessEqual(cave + len(code), quit_menu.CAVE_END)
        self.assertEqual(struct.unpack('<5f', code[-20:]), cloth.CONSTANTS)

    def test_the_site_jumps_to_the_cave_and_keeps_its_length(self):
        (cave, code), (site, jump) = cloth.code_writes()
        self.assertEqual(site, cloth.SITE)
        self.assertEqual(len(jump), len(cloth.SITE_BYTES))
        self.assertEqual(jump[0], 0xE9)
        self.assertEqual(site + 5 + struct.unpack_from('<i', jump, 1)[0], cave)

    def test_the_cave_returns_after_the_site(self):
        code = cloth.code_writes()[0][1]
        end = code.index(b'\xcc' * 4)
        self.assertEqual(code[end - 5], 0xE9)
        self.assertEqual(cloth.CAVE + end + struct.unpack_from('<i', code, end - 4)[0], cloth.RETURN)

    def test_other_code_at_the_site_is_refused(self):
        cloth.check_original(lambda start, end: cloth.SITE_BYTES)
        with self.assertRaises(ValueError):
            cloth.check_original(lambda start, end: b'\x90' * (end - start))


if __name__ == '__main__':
    unittest.main()
