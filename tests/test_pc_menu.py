from paths import ROOT
import re
import struct
import sys
import unittest

sys.path.insert(0, str(ROOT / 'scripts'))
import pc_menu  # noqa: E402
import quit_menu  # noqa: E402
import rebirth  # noqa: E402


class PcMenuTests(unittest.TestCase):
    def test_code_fits_its_page_and_leaves_the_other_menus_alone(self):
        writes = dict(pc_menu.code_writes())
        cave = writes[pc_menu.CAVE]
        self.assertLessEqual(pc_menu.CAVE + len(cave), quit_menu.CAVE_END)
        others = quit_menu.code_writes() + rebirth.code_writes()
        for offset, data in writes.items():
            for other, other_data in others:
                self.assertFalse(offset < other + len(other_data) and other < offset + len(data),
                                 f'{offset:#x} overlaps {other:#x}')
        for offset, original in pc_menu.ORIGINAL.items():
            self.assertEqual(len(writes[offset]), len(bytes.fromhex(original)))

    def test_page_table_holds_every_page_and_the_opener_counts_them(self):
        writes = dict(pc_menu.code_writes())
        cave = writes[pc_menu.CAVE]
        at = cave.index(pc_menu.TABLE_MAGIC) + 8
        count = len(pc_menu.GAME_PAGES) + len(pc_menu.PAGES)
        offsets = struct.unpack_from(f'<{count}Q', cave, at)
        self.assertEqual(list(offsets[:6]), pc_menu.GAME_PAGES)
        for (name, _), offset in zip(pc_menu.PAGES, offsets[6:]):
            start = offset - pc_menu.CAVE
            self.assertEqual(cave[start:start + len(name) + 1], name.encode() + b'\0')
        self.assertEqual(writes[pc_menu.PAGE_COUNT], bytes.fromhex('4883fa') + bytes([count]))

    def test_texts_match_the_port(self):
        source = (ROOT / 'gpu/shim/bbport_pc_menu.cpp').read_text(encoding='utf-8')
        names = pc_menu.texts()[200]
        lines = re.search(r'enum Line : int \{(.*?)LineCount', source, re.S).group(1)
        self.assertEqual(len([n for n in lines.replace('\n', ' ').split(',') if n.strip()]),
                         len(pc_menu.LINES))
        for constant, value in re.findall(r'(\w+_TEXT) = (\d+)', source):
            self.assertIn(int(value), names, constant)
        pages = re.search(r'PageNames\[PageCount\] = \{(.*?)\}', source).group(1)
        self.assertEqual(re.findall(r'"(\w+)"', pages), [name for name, _ in pc_menu.PAGES])


if __name__ == '__main__':
    unittest.main()
